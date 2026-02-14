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


KNOWN_QUOTES = ("USDT", "USDC", "USD", "ETH", "BTC", "EUR")
DEFAULT_INITIAL_CRYPTO_ALLOCATION = 0.5
MIN_DYNAMIC_TRADE_SIZE_FACTOR = 0.1


def split_symbol(symbol: str) -> tuple[str, str]:
    value = symbol.upper().strip()
    for quote in sorted(KNOWN_QUOTES, key=len, reverse=True):
        if value.endswith(quote) and len(value) > len(quote):
            return value[: -len(quote)], quote
    if len(value) > 3:
        return value[:-3], value[-3:]
    return value, "USD"


def bootstrap_price_for_symbol(symbol: str) -> float:
    defaults = {
        "BTCUSDT": 50000.0,
        "ETHUSDT": 3000.0,
        "ADAUSDT": 0.8,
        "BNBUSDT": 500.0,
        "SOLUSDT": 120.0,
        "BTCETH": 15.0,
        "ETHBTC": 0.066,
    }
    return defaults.get(symbol.upper(), 1.0)


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


def _depth_available(levels: list[OrderBookLevel]) -> float:
    return sum(max(level.quantity, 0.0) for level in levels)


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
        self.base_asset, self.quote_asset = split_symbol(self.config.symbol)
        self.exchange_balances: dict[str, dict[str, float]] = {}
        self.exchange_enabled: dict[str, bool] = {
            feed.name: feed.enabled for feed in config.feeds
        }
        self._reset_inventory()

    def _reset_inventory(self) -> None:
        exchanges = [feed.name for feed in self.config.feeds]
        per_exchange_quote = (
            self.config.starting_balance_usd / len(exchanges)
            if exchanges
            else 0.0
        )
        bootstrap_price = bootstrap_price_for_symbol(self.config.symbol)
        self.exchange_balances = {
            exchange: {
                self.base_asset: (per_exchange_quote * DEFAULT_INITIAL_CRYPTO_ALLOCATION) / bootstrap_price,
                self.quote_asset: per_exchange_quote * (1 - DEFAULT_INITIAL_CRYPTO_ALLOCATION),
            }
            for exchange in exchanges
        }

    def set_exchange_enabled(self, exchange: str, enabled: bool) -> None:
        key = exchange.strip().lower()
        if not key:
            return
        self.exchange_enabled[key] = enabled
        if not enabled:
            self.order_books.pop(key, None)

    def set_simulation_volume_usd(self, volume_usd: float) -> None:
        self.config.simulation_volume_usd = max(float(volume_usd), 1.0)

    def _max_size_by_funds(
        self,
        *,
        buy_exchange: str,
        sell_exchange: str,
        reference_buy_price: float,
    ) -> float:
        buy_fee = self.fees.get(buy_exchange, 0.0)
        buy_unit_cost = reference_buy_price * (1 + buy_fee)

        buy_wallet = self.exchange_balances.get(buy_exchange, {})
        sell_wallet = self.exchange_balances.get(sell_exchange, {})

        available_quote = max(buy_wallet.get(self.quote_asset, 0.0), 0.0)
        available_base = max(sell_wallet.get(self.base_asset, 0.0), 0.0)

        if buy_unit_cost <= 0:
            return 0.0

        max_size_by_quote = available_quote / buy_unit_cost
        return min(max_size_by_quote, available_base)

    def set_symbol(self, symbol: str) -> None:
        self.config.symbol = symbol.upper().strip()
        self.base_asset, self.quote_asset = split_symbol(self.config.symbol)
        self.order_books.clear()
        self.metrics_log.clear()
        self._reset_inventory()

    async def on_order_book(self, book: NormalizedOrderBook) -> None:
        async with self._lock:
            if not self.exchange_enabled.get(book.exchange, True):
                return
            self.order_books[book.exchange] = book
            await self._evaluate_all_pairs(last_exchange=book.exchange)

    async def _evaluate_all_pairs(self, last_exchange: str) -> None:
        exchanges = list(self.order_books.keys())
        if len(exchanges) < 2:
            return

        now = datetime.now(timezone.utc)
        for buy_exchange, sell_exchange in permutations(exchanges, 2):
            if not self.exchange_enabled.get(buy_exchange, True):
                continue
            if not self.exchange_enabled.get(sell_exchange, True):
                continue
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
        max_depth_size = min(_depth_available(buy_book.asks), _depth_available(sell_book.bids))
        reference_buy_price = buy_book.best_ask or 0.0
        desired_size_from_volume = (
            self.config.simulation_volume_usd / reference_buy_price
            if reference_buy_price > 0
            else 0.0
        )
        max_funds_size = self._max_size_by_funds(
            buy_exchange=buy_book.exchange,
            sell_exchange=sell_book.exchange,
            reference_buy_price=reference_buy_price,
        )
        target_size = min(desired_size_from_volume, max_depth_size, max_funds_size)
        min_dynamic_size = max(desired_size_from_volume * MIN_DYNAMIC_TRADE_SIZE_FACTOR, 0.0001)

        if target_size < min_dynamic_size:
            return Opportunity(
                timestamp=timestamp,
                status="no_funds",
                reason="No Funds",
                symbol=buy_book.symbol,
                buy_exchange=buy_book.exchange,
                sell_exchange=sell_book.exchange,
                trade_size=0.0,
                gross_spread_pct=0.0,
                net_spread_pct=0.0,
                expected_profit_usd=0.0,
                latency_ms=latency_ms,
                buy_vwap=reference_buy_price,
                sell_vwap=sell_book.best_bid or 0.0,
            )

        size = target_size
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

        buy_unit_with_fee = buy_vwap * (1 + buy_fee)
        sell_unit_after_fee = sell_vwap * (1 - sell_fee)

        net_profit = ((sell_unit_after_fee - buy_unit_with_fee) * size) - self.config.transfer_cost_usd

        gross_spread_pct = ((sell_vwap - buy_vwap) / buy_vwap) * 100 if buy_vwap > 0 else 0.0
        buy_total_with_fee = buy_unit_with_fee * size
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

        buy_fee = self.fees.get(opportunity.buy_exchange, 0.0)
        sell_fee = self.fees.get(opportunity.sell_exchange, 0.0)
        buy_cost_with_fee = opportunity.buy_vwap * opportunity.trade_size * (1 + buy_fee)
        sell_proceeds_after_fee = opportunity.sell_vwap * opportunity.trade_size * (1 - sell_fee)

        buy_wallet = self.exchange_balances.setdefault(
            opportunity.buy_exchange,
            {self.base_asset: 0.0, self.quote_asset: 0.0},
        )
        sell_wallet = self.exchange_balances.setdefault(
            opportunity.sell_exchange,
            {self.base_asset: 0.0, self.quote_asset: 0.0},
        )

        buy_wallet[self.quote_asset] = max(
            0.0,
            buy_wallet.get(self.quote_asset, 0.0) - buy_cost_with_fee,
        )
        buy_wallet[self.base_asset] = buy_wallet.get(self.base_asset, 0.0) + opportunity.trade_size

        sell_wallet[self.base_asset] = max(
            0.0,
            sell_wallet.get(self.base_asset, 0.0) - opportunity.trade_size,
        )
        sell_wallet[self.quote_asset] = sell_wallet.get(self.quote_asset, 0.0) + max(
            0.0,
            sell_proceeds_after_fee - self.config.transfer_cost_usd,
        )

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
                "simulation_volume_usd": self.config.simulation_volume_usd,
                "balance_usd": self.balance_usd,
                "total_pnl_usd": self.total_pnl_usd,
                "active_exchanges": list(self.order_books.keys()),
                "exchange_states": [
                    {"exchange": exchange, "enabled": enabled}
                    for exchange, enabled in self.exchange_enabled.items()
                ],
                "base_asset": self.base_asset,
                "quote_asset": self.quote_asset,
                "exchange_inventory": [
                    {
                        "exchange": exchange,
                        "base_balance": wallet.get(self.base_asset, 0.0),
                        "quote_balance": wallet.get(self.quote_asset, 0.0),
                        "enabled": self.exchange_enabled.get(exchange, True),
                    }
                    for exchange, wallet in self.exchange_balances.items()
                ],
                "latest_opportunity": opportunity_to_dict(latest) if latest else None,
            }

    async def list_opportunities(self, limit: int = 100, symbols: list[str] | None = None) -> list[Opportunity]:
        async with self._lock:
            if self._db is not None:
                list_fn = getattr(self._db, "list_opportunities", None)
                if callable(list_fn):
                    try:
                        return await list_fn(limit=limit, symbols=symbols)
                    except Exception:
                        return list(self.opportunities)[-limit:]
            items = list(self.opportunities)[-limit:]
            if symbols:
                symbols_set = {s.upper() for s in symbols}
                return [item for item in items if item.symbol.upper() in symbols_set]
            return items

    async def list_trades(self, limit: int = 100, symbols: list[str] | None = None) -> list[SimulatedTrade]:
        async with self._lock:
            if self._db is not None:
                list_fn = getattr(self._db, "list_trades", None)
                if callable(list_fn):
                    try:
                        return await list_fn(limit=limit, symbols=symbols)
                    except Exception:
                        return list(self.executed_trades)[-limit:]
            items = list(self.executed_trades)[-limit:]
            if symbols:
                symbols_set = {s.upper() for s in symbols}
                return [item for item in items if item.symbol.upper() in symbols_set]
            return items

    async def spread_series(self, limit: int = 200) -> list[dict]:
        async with self._lock:
            return list(self.metrics_log)[-limit:]