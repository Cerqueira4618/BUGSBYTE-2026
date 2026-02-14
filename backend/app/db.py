from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import DateTime, Float, Integer, String, desc, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .models import Opportunity, SimulatedTrade


class Base(DeclarativeBase):
    pass


class OpportunityRecord(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    status: Mapped[str] = mapped_column(String(20), index=True)
    reason: Mapped[str] = mapped_column(String(120))

    symbol: Mapped[str] = mapped_column(String(40), index=True)
    buy_exchange: Mapped[str] = mapped_column(String(60), index=True)
    sell_exchange: Mapped[str] = mapped_column(String(60), index=True)

    trade_size: Mapped[float] = mapped_column(Float)
    gross_spread_pct: Mapped[float] = mapped_column(Float)
    net_spread_pct: Mapped[float] = mapped_column(Float)
    expected_profit_usd: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)

    buy_vwap: Mapped[float] = mapped_column(Float)
    sell_vwap: Mapped[float] = mapped_column(Float)

    @staticmethod
    def from_model(item: Opportunity) -> "OpportunityRecord":
        return OpportunityRecord(**asdict(item))

    def to_model(self) -> Opportunity:
        return Opportunity(
            timestamp=self.timestamp,
            status=self.status,  # type: ignore[arg-type]
            reason=self.reason,
            symbol=self.symbol,
            buy_exchange=self.buy_exchange,
            sell_exchange=self.sell_exchange,
            trade_size=self.trade_size,
            gross_spread_pct=self.gross_spread_pct,
            net_spread_pct=self.net_spread_pct,
            expected_profit_usd=self.expected_profit_usd,
            latency_ms=self.latency_ms,
            buy_vwap=self.buy_vwap,
            sell_vwap=self.sell_vwap,
        )


class TradeRecord(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    symbol: Mapped[str] = mapped_column(String(40), index=True)
    buy_exchange: Mapped[str] = mapped_column(String(60), index=True)
    sell_exchange: Mapped[str] = mapped_column(String(60), index=True)

    size: Mapped[float] = mapped_column(Float)
    pnl_usd: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)

    @staticmethod
    def from_model(item: SimulatedTrade) -> "TradeRecord":
        return TradeRecord(**asdict(item))

    def to_model(self) -> SimulatedTrade:
        return SimulatedTrade(
            timestamp=self.timestamp,
            symbol=self.symbol,
            buy_exchange=self.buy_exchange,
            sell_exchange=self.sell_exchange,
            size=self.size,
            pnl_usd=self.pnl_usd,
            latency_ms=self.latency_ms,
        )


class Database:
    def __init__(self, url: str, *, echo: bool = False) -> None:
        self.url = url
        self.engine: AsyncEngine = create_async_engine(url, echo=echo)
        self.sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    @classmethod
    def from_env(cls, root_path: Path) -> "Database":
        url = os.getenv("DATABASE_URL")
        if not url:
            data_dir = root_path / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            sqlite_path = (data_dir / "bugsbyte.db").resolve().as_posix()
            url = f"sqlite+aiosqlite:///{sqlite_path}"
        echo = os.getenv("SQLALCHEMY_ECHO", "0").strip() == "1"
        return cls(url, echo=echo)

    async def init(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()

    async def insert_opportunity(self, item: Opportunity) -> None:
        async with self.sessionmaker() as session:
            session.add(OpportunityRecord.from_model(item))
            await session.commit()

    async def insert_trade(self, item: SimulatedTrade) -> None:
        async with self.sessionmaker() as session:
            session.add(TradeRecord.from_model(item))
            await session.commit()

    async def list_opportunities(self, limit: int = 100, symbols: list[str] | None = None) -> list[Opportunity]:
        limit = max(1, min(int(limit), 5000))
        symbols = [s.upper() for s in symbols] if symbols else None
        async with self.sessionmaker() as session:
            stmt = select(OpportunityRecord).order_by(desc(OpportunityRecord.timestamp)).limit(limit)
            if symbols:
                stmt = stmt.where(OpportunityRecord.symbol.in_(symbols))
            rows = (await session.execute(stmt)).scalars().all()
        return [row.to_model() for row in reversed(rows)]

    async def list_trades(self, limit: int = 100, symbols: list[str] | None = None) -> list[SimulatedTrade]:
        limit = max(1, min(int(limit), 5000))
        symbols = [s.upper() for s in symbols] if symbols else None
        async with self.sessionmaker() as session:
            stmt = select(TradeRecord).order_by(desc(TradeRecord.timestamp)).limit(limit)
            if symbols:
                stmt = stmt.where(TradeRecord.symbol.in_(symbols))
            rows = (await session.execute(stmt)).scalars().all()
        return [row.to_model() for row in reversed(rows)]
