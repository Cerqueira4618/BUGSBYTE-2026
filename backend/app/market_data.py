from __future__ import annotations

import abc
import asyncio
import contextlib
import json
import random
from datetime import datetime, timezone
from typing import Awaitable, Callable

from websockets.client import connect

from .models import NormalizedOrderBook, OrderBookLevel

OrderBookCallback = Callable[[NormalizedOrderBook], Awaitable[None]]


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
    def __init__(self, name: str, symbol: str) -> None:
        super().__init__(name=name, symbol=symbol)
        stream = f"{symbol.lower()}@depth20@100ms"
        self.ws_url = f"wss://stream.binance.com:9443/ws/{stream}"

    async def _run_loop(self, callback: OrderBookCallback) -> None:
        while self._running:
            try:
                async with connect(self.ws_url, ping_interval=20, ping_timeout=20) as websocket:
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
                await asyncio.sleep(1.0)


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