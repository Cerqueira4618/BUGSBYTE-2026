from __future__ import annotations

import asyncio
from pathlib import Path

from .config import AppConfig, load_config
from .db import Database
from .engine import ArbitrageEngine
from .market_data import BinanceDepthFeed, BybitDepthFeed, KrakenDepthFeed, MarketDataFeed, SimulatedDepthFeed, UpholdTickerFeed
from .persistence import PersistenceManager


class ArbitrageService:
    def __init__(self, root_path: Path) -> None:
        self.config: AppConfig = load_config(root_path)
        self.db = Database.from_env(root_path)
        self.persistence = PersistenceManager(self.db)
        self.engine = ArbitrageEngine(self.config, db=self.db, persistence=self.persistence)
        self.feeds: list[MarketDataFeed] = []
        self._started = False

    def _build_feeds(self) -> list[MarketDataFeed]:
        feeds: list[MarketDataFeed] = []
        for feed_cfg in self.config.feeds:
            if not feed_cfg.enabled:
                continue
            if feed_cfg.kind == "binance_ws":
                feeds.append(BinanceDepthFeed(name=feed_cfg.name, symbol=self.config.symbol))
                continue
            if feed_cfg.kind == "uphold_ticker":
                feeds.append(UpholdTickerFeed(name=feed_cfg.name, symbol=self.config.symbol))
                continue
            if feed_cfg.kind == "kraken_ws":
                feeds.append(KrakenDepthFeed(name=feed_cfg.name, symbol=self.config.symbol))
                continue
            if feed_cfg.kind == "bybit_ws":
                feeds.append(BybitDepthFeed(name=feed_cfg.name, symbol=self.config.symbol))
                continue
            if feed_cfg.kind == "simulated":
                feeds.append(
                    SimulatedDepthFeed(
                        name=feed_cfg.name,
                        symbol=self.config.symbol,
                        price_offset=feed_cfg.price_offset,
                        volatility=feed_cfg.volatility,
                        depth_levels=feed_cfg.depth_levels,
                    )
                )
        return feeds

    async def start(self) -> None:
        if self._started:
            return
        await self.db.init()
        await self.persistence.start()
        self.feeds = self._build_feeds()
        await asyncio.gather(*(feed.start(self.engine.on_order_book) for feed in self.feeds))
        self._started = True

    async def _stop_feeds(self) -> None:
        await asyncio.gather(*(feed.stop() for feed in self.feeds), return_exceptions=True)
        self.feeds = []

    async def set_symbol(self, symbol: str) -> None:
        next_symbol = symbol.upper().strip()
        if not next_symbol or next_symbol == self.config.symbol:
            return

        if self._started:
            await self._stop_feeds()

        self.config.symbol = next_symbol
        self.engine.set_symbol(next_symbol)
        self.feeds = self._build_feeds()

        if self._started:
            await asyncio.gather(*(feed.start(self.engine.on_order_book) for feed in self.feeds))

    async def set_exchange_enabled(self, exchange: str, enabled: bool) -> None:
        target = exchange.strip().lower()
        if not target:
            return

        for feed_cfg in self.config.feeds:
            if feed_cfg.name.lower() == target:
                feed_cfg.enabled = enabled
                break
        else:
            return

        self.engine.set_exchange_enabled(target, enabled)

        if self._started:
            await self._stop_feeds()
            self.feeds = self._build_feeds()
            await asyncio.gather(*(feed.start(self.engine.on_order_book) for feed in self.feeds))

    def set_simulation_volume_usd(self, volume_usd: float) -> None:
        self.config.simulation_volume_usd = max(float(volume_usd), 1.0)
        self.engine.set_simulation_volume_usd(self.config.simulation_volume_usd)

    def exchange_states(self) -> list[dict[str, object]]:
        return [
            {"exchange": feed.name, "enabled": feed.enabled}
            for feed in self.config.feeds
        ]

    async def stop(self) -> None:
        if not self._started:
            return
        await self._stop_feeds()
        await self.persistence.stop()
        await self.db.close()
        self._started = False