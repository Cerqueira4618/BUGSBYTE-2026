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


def _split_symbol_pair(symbol: str) -> tuple[str, str] | None:
    normalized = symbol.upper().strip()
    for suffix in QUOTE_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            return normalized[: -len(suffix)], suffix
    return None


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
        self.order_books: dict[str, dict[str, NormalizedOrderBook]] = {}
        self.opportunities: deque[Opportunity] = deque(maxlen=600)
        self.executed_trades: deque[SimulatedTrade] = deque(maxlen=300)
        self.metrics_log: deque[dict] = deque(maxlen=600)
        self.total_pnl_usd = 0.0
        self.balance_usd = config.starting_balance_usd
        self.fees = {feed.name: feed.fee for feed in config.feeds if feed.enabled}
        self.simulation_volume_usd: float | None = None
        enabled_exchange_names = [feed.name for feed in config.feeds if feed.enabled]
        initial_quote_balance = (
            config.starting_balance_usd / len(enabled_exchange_names)
            if enabled_exchange_names
            else 0.0
        )
        self.inventory_by_exchange: dict[str, dict[str, object]] = {
            exchange_name: {
                "quote_asset": "USDT",
                "quote_balance": initial_quote_balance,
                "asset_balances": {},
            }
            for exchange_name in enabled_exchange_names
        }

    def set_simulation_volume_usd(self, value: float | None) -> None:
        if value is None or value <= 0:
            self.simulation_volume_usd = None
            return
        self.simulation_volume_usd = float(value)

    def _resolve_trade_size(self, buy_book: NormalizedOrderBook) -> float:
        if self.simulation_volume_usd is None:
            return self.config.trade_size
        reference_price = buy_book.best_ask or 0.0
        if reference_price <= 0:
            return 0.0
        return self.simulation_volume_usd / reference_price

    def _get_base_balance(self, exchange: str, base_asset: str) -> float:
        wallet = self.inventory_by_exchange.get(exchange, {})
        asset_balances = wallet.get("asset_balances")
        if not isinstance(asset_balances, dict):
            return 0.0
        return float(asset_balances.get(base_asset, 0.0))

    def _add_base_balance(self, exchange: str, base_asset: str, delta: float) -> None:
        wallet = self.inventory_by_exchange.setdefault(
            exchange,
            {"quote_asset": "USDT", "quote_balance": 0.0, "asset_balances": {}},
        )
        asset_balances = wallet.get("asset_balances")
        if not isinstance(asset_balances, dict):
            asset_balances = {}
            wallet["asset_balances"] = asset_balances
        current_value = float(asset_balances.get(base_asset, 0.0))
        asset_balances[base_asset] = current_value + delta

    def _inventory_view(self) -> dict[str, dict[str, object]]:
        current_base_asset = (_split_symbol_pair(self.config.symbol) or ("BASE", "USDT"))[0]
        inventory: dict[str, dict[str, object]] = {}
        for exchange, wallet in self.inventory_by_exchange.items():
            quote_asset = str(wallet.get("quote_asset", "USDT"))
            quote_balance = float(wallet.get("quote_balance", 0.0))
            asset_balances = wallet.get("asset_balances")
            normalized_asset_balances: dict[str, float] = {}
            if isinstance(asset_balances, dict):
                normalized_asset_balances = {
                    str(asset).upper(): round(float(balance), 8)
                    for asset, balance in asset_balances.items()
                }
            inventory[exchange] = {
                "quote_asset": quote_asset,
                "quote_balance": round(quote_balance, 8),
                "base_asset": current_base_asset,
                "base_balance": round(normalized_asset_balances.get(current_base_asset, 0.0), 8),
                "asset_balances": normalized_asset_balances,
            }
        return inventory

    async def on_order_book(self, book: NormalizedOrderBook) -> None:
        async with self._lock:
            books_by_exchange = self.order_books.setdefault(book.symbol, {})
            books_by_exchange[book.exchange] = book
            await self._evaluate_all_pairs(symbol=book.symbol, last_exchange=book.exchange)

    async def _evaluate_all_pairs(self, symbol: str, last_exchange: str) -> None:
        books_by_exchange = self.order_books.get(symbol, {})
        exchanges = list(books_by_exchange.keys())
        if len(exchanges) < 2:
            return

        now = datetime.now(timezone.utc)
        for buy_exchange, sell_exchange in permutations(exchanges, 2):
            buy_book = books_by_exchange[buy_exchange]
            sell_book = books_by_exchange[sell_exchange]
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
                trade_size=self._resolve_trade_size(buy_book),
            )
            self.opportunities.append(opportunity)
            if self._persistence is not None and opportunity.status == "accepted":
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
        trade_size: float | None = None,
    ) -> Opportunity:
        size = trade_size if trade_size is not None else self.config.trade_size
        if size <= 0:
            return Opportunity(
                timestamp=timestamp,
                status="discarded",
                reason="invalid_trade_size",
                symbol=buy_book.symbol,
                buy_exchange=buy_book.exchange,
                sell_exchange=sell_book.exchange,
                trade_size=size,
                gross_spread_pct=0.0,
                net_spread_pct=0.0,
                expected_profit_usd=0.0,
                latency_ms=latency_ms,
                buy_vwap=0.0,
                sell_vwap=0.0,
                buy_book_updated_at=buy_book.exchange_timestamp,
                sell_book_updated_at=sell_book.exchange_timestamp,
            )

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
                buy_book_updated_at=buy_book.exchange_timestamp,
                sell_book_updated_at=sell_book.exchange_timestamp,
            )

        buy_fee = self.fees.get(buy_book.exchange, 0.0)
        sell_fee = self.fees.get(sell_book.exchange, 0.0)

        buy_unit_with_fee = buy_vwap * (1 + buy_fee)
        sell_unit_after_fee = sell_vwap * (1 - sell_fee)

        net_profit = ((sell_unit_after_fee - buy_unit_with_fee) * size) - self.config.transfer_cost_usd

        gross_spread_pct = ((sell_vwap - buy_vwap) / buy_vwap) * 100 if buy_vwap > 0 else 0.0
        buy_total_with_fee = buy_unit_with_fee * size
        net_spread_pct = (net_profit / buy_total_with_fee) * 100 if buy_total_with_fee > 0 else 0.0

        buy_wallet = self.inventory_by_exchange.get(buy_book.exchange)
        buy_quote_balance = float(buy_wallet.get("quote_balance", 0.0)) if buy_wallet else 0.0
        if buy_total_with_fee > buy_quote_balance:
            return Opportunity(
                timestamp=timestamp,
                status="discarded",
                reason="insufficient_exchange_balance",
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
                buy_book_updated_at=buy_book.exchange_timestamp,
                sell_book_updated_at=sell_book.exchange_timestamp,
            )

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
                buy_book_updated_at=buy_book.exchange_timestamp,
                sell_book_updated_at=sell_book.exchange_timestamp,
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
            buy_book_updated_at=buy_book.exchange_timestamp,
            sell_book_updated_at=sell_book.exchange_timestamp,
        )

    def _simulate_execution(
        self,
        opportunity: Opportunity,
        buy_book: NormalizedOrderBook,
        sell_book: NormalizedOrderBook,
    ) -> None:
        buy_fee = self.fees.get(opportunity.buy_exchange, 0.0)
        sell_fee = self.fees.get(opportunity.sell_exchange, 0.0)
        buy_cost = opportunity.buy_vwap * opportunity.trade_size * (1 + buy_fee)
        sell_value = opportunity.sell_vwap * opportunity.trade_size * (1 - sell_fee)

        buy_wallet = self.inventory_by_exchange.setdefault(
            opportunity.buy_exchange,
            {"quote_asset": "USDT", "quote_balance": 0.0, "asset_balances": {}},
        )
        sell_wallet = self.inventory_by_exchange.setdefault(
            opportunity.sell_exchange,
            {"quote_asset": "USDT", "quote_balance": 0.0, "asset_balances": {}},
        )

        buy_wallet["quote_balance"] = float(buy_wallet.get("quote_balance", 0.0)) - buy_cost
        sell_wallet["quote_balance"] = float(sell_wallet.get("quote_balance", 0.0)) + sell_value

        base_asset = (_split_symbol_pair(opportunity.symbol) or ("BASE", "USDT"))[0]
        self._add_base_balance(opportunity.buy_exchange, base_asset, opportunity.trade_size)
        self._add_base_balance(opportunity.sell_exchange, base_asset, -opportunity.trade_size)

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
                "symbols": self.config.symbols,
                "trade_size": self.config.trade_size,
                "simulation_volume_usd": self.simulation_volume_usd,
                "balance_usd": self.balance_usd,
                "total_pnl_usd": self.total_pnl_usd,
                "inventory_by_exchange": self._inventory_view(),
                "active_exchanges": sorted(
                    {
                        exchange
                        for books_by_exchange in self.order_books.values()
                        for exchange in books_by_exchange
                    }
                ),
                "latest_opportunity": opportunity_to_dict(latest) if latest else None,
            }

    async def list_opportunities(
        self,
        limit: int = 100,
        symbols: list[str] | None = None,
        simulation_volume_usd: float | None = None,
    ) -> list[Opportunity]:
        async with self._lock:
            if simulation_volume_usd is not None and simulation_volume_usd > 0:
                generated: list[Opportunity] = []
                symbols_set = {s.upper() for s in symbols} if symbols else None
                now = datetime.now(timezone.utc)
                for books_by_exchange in self.order_books.values():
                    exchanges = list(books_by_exchange.keys())
                    if len(exchanges) < 2:
                        continue
                    for buy_exchange, sell_exchange in permutations(exchanges, 2):
                        buy_book = books_by_exchange[buy_exchange]
                        sell_book = books_by_exchange[sell_exchange]
                        if buy_book.symbol != sell_book.symbol:
                            continue
                        if symbols_set and buy_book.symbol.upper() not in symbols_set:
                            continue

                        reference_price = buy_book.best_ask or 0.0
                        if reference_price <= 0:
                            continue

                        trade_size = simulation_volume_usd / reference_price
                        decision_latency_ms = (
                            now - max(buy_book.received_timestamp, sell_book.received_timestamp)
                        ).total_seconds() * 1000

                        generated.append(
                            self._evaluate_pair(
                                buy_book=buy_book,
                                sell_book=sell_book,
                                latency_ms=max(decision_latency_ms, 0.0),
                                timestamp=now,
                                trade_size=trade_size,
                            )
                        )

                if generated:
                    return generated[-limit:]

            items = list(self.opportunities)[-limit:]
            if symbols:
                symbols_set = {s.upper() for s in symbols}
                items = [item for item in items if item.symbol.upper() in symbols_set]

            if items:
                return items

            if self._db is not None:
                list_fn = getattr(self._db, "list_opportunities", None)
                if callable(list_fn):
                    try:
                        return await list_fn(limit=limit, symbols=symbols)
                    except Exception:
                        return []

            return items

    async def list_trades(self, limit: int = 100, symbols: list[str] | None = None) -> list[SimulatedTrade]:
        async with self._lock:
            items = list(self.executed_trades)[-limit:]
            if symbols:
                symbols_set = {s.upper() for s in symbols}
                items = [item for item in items if item.symbol.upper() in symbols_set]

            if items:
                return items

            if self._db is not None:
                list_fn = getattr(self._db, "list_trades", None)
                if callable(list_fn):
                    try:
                        return await list_fn(limit=limit, symbols=symbols)
                    except Exception:
                        return []

            return items

    async def spread_series(self, limit: int = 200) -> list[dict]:
        async with self._lock:
            return list(self.metrics_log)[-limit:]