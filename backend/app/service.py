from __future__ import annotations

import asyncio
from pathlib import Path

from .config import AppConfig, load_config
from .db import Database
from .engine import ArbitrageEngine
from .market_data import BinanceDepthFeed, MarketDataFeed, SimulatedDepthFeed, UpholdTickerFeed
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

    async def stop(self) -> None:
        if not self._started:
            return
        await asyncio.gather(*(feed.stop() for feed in self.feeds), return_exceptions=True)
        await self.persistence.stop()
        await self.db.close()
        self._started = False