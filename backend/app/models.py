from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class OrderBookLevel:
    price: float
    quantity: float


@dataclass(slots=True)
class NormalizedOrderBook:
    exchange: str
    symbol: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    exchange_timestamp: datetime
    received_timestamp: datetime = field(default_factory=utc_now)

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None


@dataclass(slots=True)
class Opportunity:
    timestamp: datetime
    status: Literal["accepted", "discarded", "no_funds", "insufficient_liquidity"]
    reason: str
    symbol: str
    buy_exchange: str
    sell_exchange: str
    trade_size: float
    gross_spread_pct: float
    net_spread_pct: float
    expected_profit_usd: float
    latency_ms: float
    buy_vwap: float
    sell_vwap: float
    buy_book_updated_at: datetime | None = None
    sell_book_updated_at: datetime | None = None


@dataclass(slots=True)
class SimulatedTrade:
    timestamp: datetime
    symbol: str
    buy_exchange: str
    sell_exchange: str
    size: float
    pnl_usd: float
    latency_ms: float


def level_to_dict(level: OrderBookLevel) -> dict:
    return {"price": level.price, "quantity": level.quantity}


def order_book_to_dict(book: NormalizedOrderBook) -> dict:
    return {
        "exchange": book.exchange,
        "symbol": book.symbol,
        "bids": [level_to_dict(level) for level in book.bids],
        "asks": [level_to_dict(level) for level in book.asks],
        "best_bid": book.best_bid,
        "best_ask": book.best_ask,
        "exchange_timestamp": book.exchange_timestamp.isoformat(),
        "received_timestamp": book.received_timestamp.isoformat(),
    }


def opportunity_to_dict(item: Opportunity) -> dict:
    return {
        "timestamp": item.timestamp.isoformat(),
        "status": item.status,
        "reason": item.reason,
        "symbol": item.symbol,
        "buy_exchange": item.buy_exchange,
        "sell_exchange": item.sell_exchange,
        "trade_size": item.trade_size,
        "gross_spread_pct": item.gross_spread_pct,
        "net_spread_pct": item.net_spread_pct,
        "expected_profit_usd": item.expected_profit_usd,
        "latency_ms": item.latency_ms,
        "buy_vwap": item.buy_vwap,
        "sell_vwap": item.sell_vwap,
        "buy_book_updated_at": item.buy_book_updated_at.isoformat() if item.buy_book_updated_at else None,
        "sell_book_updated_at": item.sell_book_updated_at.isoformat() if item.sell_book_updated_at else None,
    }


def simulated_trade_to_dict(item: SimulatedTrade) -> dict:
    return {
        "timestamp": item.timestamp.isoformat(),
        "symbol": item.symbol,
        "buy_exchange": item.buy_exchange,
        "sell_exchange": item.sell_exchange,
        "size": item.size,
        "pnl_usd": item.pnl_usd,
        "latency_ms": item.latency_ms,
    }