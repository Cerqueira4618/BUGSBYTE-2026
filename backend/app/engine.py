from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
from itertools import permutations

from .config import AppConfig
from .models import (
    NormalizedOrderBook,
    Opportunity,
    OrderBookLevel,
    SimulatedTrade,
    opportunity_to_dict,
)


def _compute_vwap_for_buy(levels: list[OrderBookLevel], quantity: float) -> tuple[float, float]:
    remaining = quantity
    total_cost = 0.0
    filled = 0.0
    for level in levels:
        if remaining <= 0:
            break
        take = min(level.quantity, remaining)
        if take <= 0:
            continue
        total_cost += level.price * take
        remaining -= take
        filled += take
    avg_price = total_cost / filled if filled > 0 else 0.0
    return avg_price, filled


def _compute_vwap_for_sell(levels: list[OrderBookLevel], quantity: float) -> tuple[float, float]:
    remaining = quantity
    total_value = 0.0
    filled = 0.0
    for level in levels:
        if remaining <= 0:
            break
        take = min(level.quantity, remaining)
        if take <= 0:
            continue
        total_value += level.price * take
        remaining -= take
        filled += take
    avg_price = total_value / filled if filled > 0 else 0.0
    return avg_price, filled


def _reserve_from_levels(levels: list[OrderBookLevel], quantity: float) -> None:
    remaining = quantity
    for level in levels:
        if remaining <= 0:
            break
        if level.quantity <= 0:
            continue
        consume = min(level.quantity, remaining)
        level.quantity -= consume
        remaining -= consume


class ArbitrageEngine:
    def __init__(
        self,
        config: AppConfig,
        *,
        db: object | None = None,
        persistence: object | None = None,
    ) -> None:
        self.config = config
        self._lock = asyncio.Lock()
        self._db = db
        self._persistence = persistence
        self.order_books: dict[str, NormalizedOrderBook] = {}
        self.opportunities: deque[Opportunity] = deque(maxlen=600)
        self.executed_trades: deque[SimulatedTrade] = deque(maxlen=300)
        self.metrics_log: deque[dict] = deque(maxlen=600)
        self.total_pnl_usd = 0.0
        self.balance_usd = config.starting_balance_usd
        self.fees = {feed.name: feed.fee for feed in config.feeds if feed.enabled}

    async def on_order_book(self, book: NormalizedOrderBook) -> None:
        async with self._lock:
            self.order_books[book.exchange] = book
            await self._evaluate_all_pairs(last_exchange=book.exchange)

    async def _evaluate_all_pairs(self, last_exchange: str) -> None:
        exchanges = list(self.order_books.keys())
        if len(exchanges) < 2:
            return

        now = datetime.now(timezone.utc)
        for buy_exchange, sell_exchange in permutations(exchanges, 2):
            buy_book = self.order_books[buy_exchange]
            sell_book = self.order_books[sell_exchange]
            if buy_book.symbol != sell_book.symbol:
                continue

            decision_latency_ms = (
                now - max(buy_book.received_timestamp, sell_book.received_timestamp)
            ).total_seconds() * 1000

            opportunity = self._evaluate_pair(
                buy_book=buy_book,
                sell_book=sell_book,
                latency_ms=max(decision_latency_ms, 0.0),
                timestamp=now,
            )
            self.opportunities.append(opportunity)
            if self._persistence is not None:
                submit = getattr(self._persistence, "submit_opportunity", None)
                if callable(submit):
                    submit(opportunity)
            self.metrics_log.append(
                {
                    "timestamp": now.isoformat(),
                    "spread_gross_pct": opportunity.gross_spread_pct,
                    "spread_net_pct": opportunity.net_spread_pct,
                    "expected_profit_usd": opportunity.expected_profit_usd,
                    "status": opportunity.status,
                    "reason": opportunity.reason,
                    "pair": f"{buy_exchange}->{sell_exchange}",
                    "trigger_exchange": last_exchange,
                    "latency_ms": opportunity.latency_ms,
                }
            )

            if (
                self.config.auto_simulate_execution
                and opportunity.status == "accepted"
                and opportunity.expected_profit_usd >= self.config.opportunity_threshold_usd
            ):
                self._simulate_execution(opportunity, buy_book, sell_book)

    def _evaluate_pair(
        self,
        *,
        buy_book: NormalizedOrderBook,
        sell_book: NormalizedOrderBook,
        latency_ms: float,
        timestamp: datetime,
    ) -> Opportunity:
        size = self.config.trade_size
        buy_vwap, buy_filled = _compute_vwap_for_buy(buy_book.asks, size)
        sell_vwap, sell_filled = _compute_vwap_for_sell(sell_book.bids, size)
        filled = min(buy_filled, sell_filled)

        if filled < size:
            return Opportunity(
                timestamp=timestamp,
                status="discarded",
                reason="insufficient_depth",
                symbol=buy_book.symbol,
                buy_exchange=buy_book.exchange,
                sell_exchange=sell_book.exchange,
                trade_size=size,
                gross_spread_pct=0.0,
                net_spread_pct=0.0,
                expected_profit_usd=0.0,
                latency_ms=latency_ms,
                buy_vwap=buy_vwap,
                sell_vwap=sell_vwap,
            )

        buy_fee = self.fees.get(buy_book.exchange, 0.0)
        sell_fee = self.fees.get(sell_book.exchange, 0.0)
        buy_total = buy_vwap * size
        sell_total = sell_vwap * size

        buy_total_with_fee = buy_total * (1 + buy_fee)
        sell_total_after_fee = sell_total * (1 - sell_fee)
        net_profit = sell_total_after_fee - buy_total_with_fee - self.config.transfer_cost_usd

        gross_spread_pct = ((sell_vwap - buy_vwap) / buy_vwap) * 100 if buy_vwap > 0 else 0.0
        net_spread_pct = (net_profit / buy_total_with_fee) * 100 if buy_total_with_fee > 0 else 0.0

        if net_profit <= 0:
            return Opportunity(
                timestamp=timestamp,
                status="discarded",
                reason="fees_and_transfer_filtered",
                symbol=buy_book.symbol,
                buy_exchange=buy_book.exchange,
                sell_exchange=sell_book.exchange,
                trade_size=size,
                gross_spread_pct=gross_spread_pct,
                net_spread_pct=net_spread_pct,
                expected_profit_usd=net_profit,
                latency_ms=latency_ms,
                buy_vwap=buy_vwap,
                sell_vwap=sell_vwap,
            )

        return Opportunity(
            timestamp=timestamp,
            status="accepted",
            reason="profitable",
            symbol=buy_book.symbol,
            buy_exchange=buy_book.exchange,
            sell_exchange=sell_book.exchange,
            trade_size=size,
            gross_spread_pct=gross_spread_pct,
            net_spread_pct=net_spread_pct,
            expected_profit_usd=net_profit,
            latency_ms=latency_ms,
            buy_vwap=buy_vwap,
            sell_vwap=sell_vwap,
        )

    def _simulate_execution(
        self,
        opportunity: Opportunity,
        buy_book: NormalizedOrderBook,
        sell_book: NormalizedOrderBook,
    ) -> None:
        _reserve_from_levels(buy_book.asks, opportunity.trade_size)
        _reserve_from_levels(sell_book.bids, opportunity.trade_size)

        self.total_pnl_usd += opportunity.expected_profit_usd
        self.balance_usd += opportunity.expected_profit_usd
        self.executed_trades.append(
            SimulatedTrade(
                timestamp=opportunity.timestamp,
                symbol=opportunity.symbol,
                buy_exchange=opportunity.buy_exchange,
                sell_exchange=opportunity.sell_exchange,
                size=opportunity.trade_size,
                pnl_usd=opportunity.expected_profit_usd,
                latency_ms=opportunity.latency_ms,
            )
        )
        if self._persistence is not None and self.executed_trades:
            submit = getattr(self._persistence, "submit_trade", None)
            if callable(submit):
                submit(self.executed_trades[-1])

    async def snapshot(self) -> dict:
        async with self._lock:
            latest = self.opportunities[-1] if self.opportunities else None
            return {
                "symbol": self.config.symbol,
                "trade_size": self.config.trade_size,
                "balance_usd": self.balance_usd,
                "total_pnl_usd": self.total_pnl_usd,
                "active_exchanges": list(self.order_books.keys()),
                "latest_opportunity": opportunity_to_dict(latest) if latest else None,
            }

    async def list_opportunities(self, limit: int = 100) -> list[Opportunity]:
        async with self._lock:
            if self._db is not None:
                list_fn = getattr(self._db, "list_opportunities", None)
                if callable(list_fn):
                    try:
                        return await list_fn(limit=limit)
                    except Exception:
                        return list(self.opportunities)[-limit:]
            return list(self.opportunities)[-limit:]

    async def list_trades(self, limit: int = 100) -> list[SimulatedTrade]:
        async with self._lock:
            if self._db is not None:
                list_fn = getattr(self._db, "list_trades", None)
                if callable(list_fn):
                    try:
                        return await list_fn(limit=limit)
                    except Exception:
                        return list(self.executed_trades)[-limit:]
            return list(self.executed_trades)[-limit:]

    async def spread_series(self, limit: int = 200) -> list[dict]:
        async with self._lock:
            return list(self.metrics_log)[-limit:]