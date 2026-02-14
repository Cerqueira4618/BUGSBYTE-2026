from __future__ import annotations

import abc
import asyncio
import contextlib
import json
import logging
import random
from decimal import Decimal
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from typing import Awaitable, Callable

from websockets.client import connect
from websockets.exceptions import ConnectionClosed

from .models import NormalizedOrderBook, OrderBookLevel

OrderBookCallback = Callable[[NormalizedOrderBook], Awaitable[None]]

logger = logging.getLogger(__name__)

QUOTE_SUFFIXES = (
    "USDT",
    "USDC",
    "EUR",
    "USD",
    "AVAX",
    "LINK",
    "DOT",
    "XRP",
    "BNB",
    "SOL",
    "ADA",
    "BTC",
    "ETH",
)


def split_symbol(symbol: str) -> tuple[str, str] | None:
    normalized = symbol.upper().strip()
    for suffix in QUOTE_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            base = normalized[: -len(suffix)]
            return base, suffix
    return None


class MarketDataFeed(abc.ABC):
    def __init__(self, name: str, symbol: str) -> None:
        self.name = name
        self.symbol = symbol
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self, callback: OrderBookCallback) -> None:
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(callback), name=f"feed-{self.name}")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    @abc.abstractmethod
    async def _run_loop(self, callback: OrderBookCallback) -> None:
        raise NotImplementedError


class BinanceDepthFeed(MarketDataFeed):
    def __init__(
        self,
        name: str,
        symbol: str,
        *,
        ping_interval_sec: float = 20.0,
        ping_timeout_sec: float = 20.0,
        stale_timeout_sec: float = 10.0,
        backoff_min_sec: float = 1.0,
        backoff_max_sec: float = 30.0,
        backoff_factor: float = 2.0,
        backoff_jitter: float = 0.3,
    ) -> None:
        super().__init__(name=name, symbol=symbol)
        stream = f"{symbol.lower()}@depth20@100ms"
        self.ws_urls = [
            f"wss://stream.binance.com:443/ws/{stream}",
            f"wss://stream.binance.com:9443/ws/{stream}",
            f"wss://data-stream.binance.vision/ws/{stream}",
        ]

    async def _run_loop(self, callback: OrderBookCallback) -> None:
        while self._running:
            connected = False
            for ws_url in self.ws_urls:
                if not self._running:
                    return
                try:
                    async with connect(ws_url, ping_interval=20, ping_timeout=20) as websocket:
                        connected = True
                        async for message in websocket:
                            payload = json.loads(message)
                            if "bids" not in payload or "asks" not in payload:
                                continue

                            bids = [
                                OrderBookLevel(price=float(level[0]), quantity=float(level[1]))
                                for level in payload["bids"]
                                if float(level[1]) > 0
                            ]
                            asks = [
                                OrderBookLevel(price=float(level[0]), quantity=float(level[1]))
                                for level in payload["asks"]
                                if float(level[1]) > 0
                            ]
                            if not bids or not asks:
                                continue

                            exchange_time = payload.get("E")
                            exchange_timestamp = (
                                datetime.fromtimestamp(exchange_time / 1000, tz=timezone.utc)
                                if exchange_time
                                else datetime.now(timezone.utc)
                            )

                            await callback(
                                NormalizedOrderBook(
                                    exchange=self.name,
                                    symbol=self.symbol,
                                    bids=bids,
                                    asks=asks,
                                    exchange_timestamp=exchange_timestamp,
                                )
                            )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    continue

            if not connected:
                await asyncio.sleep(1.0)


def uphold_pair_from_symbol(symbol: str) -> str:
    parsed = split_symbol(symbol)
    if parsed is None:
        return symbol
    base, quote = parsed
    if quote == "USDT":
        return f"{base}USD"
    return symbol


class UpholdTickerFeed(MarketDataFeed):
    def __init__(self, name: str, symbol: str) -> None:
        super().__init__(name=name, symbol=symbol)
        self._pair = uphold_pair_from_symbol(symbol)
        self._url = f"https://api.uphold.com/v0/ticker/{self._pair}"

    async def _fetch_ticker(self) -> dict:
        def _request() -> dict:
            request = Request(
                self._url,
                headers={"Accept": "application/json", "User-Agent": "BUGSBYTE-Arbitrage/1.0"},
            )
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))

        return await asyncio.to_thread(_request)

    async def _run_loop(self, callback: OrderBookCallback) -> None:
        attempt = 0
        while self._running:
            try:
                payload = await self._fetch_ticker()
                bid_raw = payload.get("bid")
                ask_raw = payload.get("ask")
                if bid_raw is None or ask_raw is None:
                    await asyncio.sleep(1.0)
                    continue

                bid = float(Decimal(str(bid_raw)))
                ask = float(Decimal(str(ask_raw)))
                if bid <= 0 or ask <= 0 or bid >= ask:
                    await asyncio.sleep(1.0)
                    continue

                qty = 100.0
                bids = [OrderBookLevel(price=bid, quantity=qty)]
                asks = [OrderBookLevel(price=ask, quantity=qty)]

                await callback(
                    NormalizedOrderBook(
                        exchange=self.name,
                        symbol=self.symbol,
                        bids=bids,
                        asks=asks,
                        exchange_timestamp=datetime.now(timezone.utc),
                    )
                )
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(2.0)


class KrakenDepthFeed(MarketDataFeed):
    """Real-time order book from Kraken public WebSocket v2 API."""

    _SYMBOL_MAP: dict[str, str] = {
        "BTCUSDT": "BTC/USDT",
        "ETHUSDT": "ETH/USDT",
        "SOLUSDT": "SOL/USDT",
        "BTCEUR": "BTC/EUR",
        "ETHEUR": "ETH/EUR",
        "SOLEUR": "SOL/EUR",
        "BTCUSD": "BTC/USD",
        "ETHUSD": "ETH/USD",
        "SOLUSD": "SOL/USD",
    }

    def __init__(self, name: str, symbol: str) -> None:
        super().__init__(name=name, symbol=symbol)
        self.ws_url = "wss://ws.kraken.com/v2"
        mapped = self._SYMBOL_MAP.get(symbol.upper())
        if mapped:
            self.kraken_pair = mapped
        else:
            parsed = split_symbol(symbol)
            self.kraken_pair = f"{parsed[0]}/{parsed[1]}" if parsed else symbol

    async def _run_loop(self, callback: OrderBookCallback) -> None:
        while self._running:
            try:
                async with connect(self.ws_url, ping_interval=20, ping_timeout=20) as websocket:
                    await websocket.send(json.dumps({
                        "method": "subscribe",
                        "params": {"channel": "book", "symbol": [self.kraken_pair], "depth": 25},
                    }))

                    current_bids: dict[float, float] = {}
                    current_asks: dict[float, float] = {}

                    async for message in websocket:
                        if not self._running:
                            break
                        payload = json.loads(message)
                        if payload.get("channel") != "book":
                            continue
                        for data in payload.get("data", []):
                            for bid in data.get("bids", []):
                                p, q = float(bid["price"]), float(bid["qty"])
                                if q == 0:
                                    current_bids.pop(p, None)
                                else:
                                    current_bids[p] = q
                            for ask in data.get("asks", []):
                                p, q = float(ask["price"]), float(ask["qty"])
                                if q == 0:
                                    current_asks.pop(p, None)
                                else:
                                    current_asks[p] = q
                        if not current_bids or not current_asks:
                            continue
                        bids = [OrderBookLevel(price=p, quantity=q) for p, q in sorted(current_bids.items(), reverse=True)[:20]]
                        asks = [OrderBookLevel(price=p, quantity=q) for p, q in sorted(current_asks.items())[:20]]
                        await callback(NormalizedOrderBook(
                            exchange=self.name, symbol=self.symbol, bids=bids, asks=asks,
                            exchange_timestamp=datetime.now(timezone.utc),
                        ))
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(2.0)


class BybitDepthFeed(MarketDataFeed):
    """Real-time order book from Bybit public WebSocket v5 API."""

    def __init__(self, name: str, symbol: str) -> None:
        super().__init__(name=name, symbol=symbol)
        self.ws_url = "wss://stream.bybit.com/v5/public/spot"

    async def _run_loop(self, callback: OrderBookCallback) -> None:
        while self._running:
            try:
                async with connect(self.ws_url, ping_interval=20, ping_timeout=20) as websocket:
                    await websocket.send(json.dumps({
                        "op": "subscribe",
                        "args": [f"orderbook.50.{self.symbol}"],
                    }))

                    current_bids: dict[float, float] = {}
                    current_asks: dict[float, float] = {}

                    async for message in websocket:
                        if not self._running:
                            break
                        payload = json.loads(message)
                        if "data" not in payload:
                            continue
                        data = payload["data"]
                        if payload.get("type") == "snapshot":
                            current_bids.clear()
                            current_asks.clear()
                        for bid in data.get("b", []):
                            p, q = float(bid[0]), float(bid[1])
                            if q == 0:
                                current_bids.pop(p, None)
                            else:
                                current_bids[p] = q
                        for ask in data.get("a", []):
                            p, q = float(ask[0]), float(ask[1])
                            if q == 0:
                                current_asks.pop(p, None)
                            else:
                                current_asks[p] = q
                        if not current_bids or not current_asks:
                            continue
                        ts = payload.get("ts")
                        exchange_timestamp = (
                            datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)
                            if ts else datetime.now(timezone.utc)
                        )
                        bids = [OrderBookLevel(price=p, quantity=q) for p, q in sorted(current_bids.items(), reverse=True)[:20]]
                        asks = [OrderBookLevel(price=p, quantity=q) for p, q in sorted(current_asks.items())[:20]]
                        await callback(NormalizedOrderBook(
                            exchange=self.name, symbol=self.symbol, bids=bids, asks=asks,
                            exchange_timestamp=exchange_timestamp,
                        ))
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(2.0)


class SimulatedDepthFeed(MarketDataFeed):
    def __init__(
        self,
        name: str,
        symbol: str,
        *,
        price_offset: float = 0.0,
        volatility: float = 2.0,
        depth_levels: int = 20,
    ) -> None:
        super().__init__(name=name, symbol=symbol)
        self.price_offset = price_offset
        self.volatility = volatility
        self.depth_levels = depth_levels
        self._reference_price = 50000 + price_offset

    async def _run_loop(self, callback: OrderBookCallback) -> None:
        while self._running:
            drift = random.uniform(-self.volatility, self.volatility)
            self._reference_price = max(1000, self._reference_price + drift)

            bids: list[OrderBookLevel] = []
            asks: list[OrderBookLevel] = []
            spread = max(0.5, random.uniform(1.0, 5.0))
            best_bid = self._reference_price - spread / 2
            best_ask = self._reference_price + spread / 2

            for level_index in range(self.depth_levels):
                step = level_index * random.uniform(0.2, 1.2)
                qty = round(random.uniform(0.02, 0.6), 5)
                bids.append(OrderBookLevel(price=round(best_bid - step, 2), quantity=qty))
                asks.append(OrderBookLevel(price=round(best_ask + step, 2), quantity=qty))

            await callback(
                NormalizedOrderBook(
                    exchange=self.name,
                    symbol=self.symbol,
                    bids=bids,
                    asks=asks,
                    exchange_timestamp=datetime.now(timezone.utc),
                )
            )
            await asyncio.sleep(0.2)