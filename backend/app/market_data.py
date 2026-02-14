from __future__ import annotations

import abc
import asyncio
import contextlib
import json
import logging
import random
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable

from websockets.client import connect
from websockets.exceptions import ConnectionClosed

from .models import NormalizedOrderBook, OrderBookLevel

OrderBookCallback = Callable[[NormalizedOrderBook], Awaitable[None]]

logger = logging.getLogger(__name__)


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
        self.ws_url = f"wss://stream.binance.com:9443/ws/{stream}"
        self.ping_interval_sec = ping_interval_sec
        self.ping_timeout_sec = ping_timeout_sec
        self.stale_timeout_sec = stale_timeout_sec
        self.backoff_min_sec = backoff_min_sec
        self.backoff_max_sec = backoff_max_sec
        self.backoff_factor = backoff_factor
        self.backoff_jitter = backoff_jitter

    def _next_backoff(self, attempt: int) -> float:
        base = self.backoff_min_sec * (self.backoff_factor**max(attempt, 0))
        delay = min(self.backoff_max_sec, base)
        if self.backoff_jitter > 0:
            delay = delay + random.uniform(-self.backoff_jitter, self.backoff_jitter) * delay
        return max(0.0, delay)

    async def _run_loop(self, callback: OrderBookCallback) -> None:
        attempt = 0
        while self._running:
            try:
                async with connect(
                    self.ws_url,
                    ping_interval=self.ping_interval_sec,
                    ping_timeout=self.ping_timeout_sec,
                    close_timeout=5,
                    open_timeout=10,
                ) as websocket:
                    attempt = 0
                    while self._running:
                        try:
                            message = await asyncio.wait_for(
                                websocket.recv(), timeout=self.stale_timeout_sec
                            )
                        except asyncio.TimeoutError as exc:
                            raise RuntimeError(
                                f"stale websocket: no messages for {self.stale_timeout_sec}s"
                            ) from exc
                        except ConnectionClosed as exc:
                            raise RuntimeError("websocket closed") from exc

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
                delay = self._next_backoff(attempt)
                attempt += 1
                logger.warning(
                    "[%s] WS error; reconnecting in %.1fs (attempt=%s)",
                    self.name,
                    delay,
                    attempt,
                    exc_info=True,
                )
                await asyncio.sleep(delay)


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