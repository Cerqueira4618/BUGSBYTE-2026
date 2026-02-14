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

STABLE_QUOTES = {"USDT", "USDC", "USD", "EUR"}
NETWORK_FEE_UNITS = {
    "USDT": 1.0,
    "USDC": 1.0,
    "USD": 1.0,
    "EUR": 1.0,
    "ADA": 0.8,
    "ETH": 0.003,
    "BTC": 0.0004,
    "SOL": 0.01,
    "BNB": 0.005,
    "XRP": 0.25,
}

DEFAULT_ASSET_PRICES_USD = {
    "BTC": 72000.0,
    "ETH": 3000.0,
    "SOL": 160.0,
    "BNB": 600.0,
    "ADA": 0.6,
    "XRP": 0.55,
    "DOT": 7.0,
    "LINK": 18.0,
    "AVAX": 35.0,
}
INITIAL_USD_PER_CRYPTO_PER_WALLET = 2000.0
INITIAL_USDT_PER_WALLET = 2000.0


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
        base_assets = sorted(
            {
                parsed[0]
                for symbol in config.symbols
                if (parsed := _split_symbol_pair(symbol)) is not None
            }
        )
        self.inventory_by_exchange = self._build_initial_inventory(
            exchanges=enabled_exchange_names,
            base_assets=base_assets,
        )

    def _reference_asset_price(self, asset: str) -> float:
        return float(DEFAULT_ASSET_PRICES_USD.get(asset.upper(), 1.0))

    def _build_initial_inventory(
        self,
        *,
        exchanges: list[str],
        base_assets: list[str],
    ) -> dict[str, dict[str, object]]:
        if not exchanges:
            return {}

        inventory: dict[str, dict[str, object]] = {}
        for exchange in exchanges:
            asset_balances: dict[str, float] = {}
            for asset in base_assets:
                reference_price = self._reference_asset_price(asset)
                if reference_price <= 0:
                    continue
                asset_balances[asset] = INITIAL_USD_PER_CRYPTO_PER_WALLET / reference_price

            inventory[exchange] = {
                "quote_asset": "USDT",
                "quote_balance": INITIAL_USDT_PER_WALLET,
                "asset_balances": asset_balances,
            }

        return inventory

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

    def _find_exchange_asset_price_usd(self, exchange: str, asset: str) -> float:
        normalized_asset = asset.upper()
        if normalized_asset in STABLE_QUOTES:
            return 1.0

        best_price = 0.0
        for symbol, books_by_exchange in self.order_books.items():
            parsed = _split_symbol_pair(symbol)
            if not parsed:
                continue
            base_asset, quote_asset = parsed
            if base_asset != normalized_asset or quote_asset not in STABLE_QUOTES:
                continue
            book = books_by_exchange.get(exchange)
            if not book:
                continue

            bid = book.best_bid or 0.0
            ask = book.best_ask or 0.0
            if bid > 0 and ask > 0:
                price = (bid + ask) / 2
            else:
                price = bid or ask

            if price > best_price:
                best_price = price

        if best_price > 0:
            return best_price
        return self._reference_asset_price(normalized_asset)

    def _estimate_wallet_value_usd(self, exchange: str, wallet: dict[str, object]) -> float:
        quote_balance = float(wallet.get("quote_balance", 0.0))
        total = quote_balance

        asset_balances = wallet.get("asset_balances")
        if isinstance(asset_balances, dict):
            for asset, balance in asset_balances.items():
                asset_balance = float(balance)
                if asset_balance <= 0:
                    continue
                unit_price = self._find_exchange_asset_price_usd(exchange, str(asset))
                total += asset_balance * unit_price

        return total

    def _wallet_status(self, exchange: str, wallet: dict[str, object]) -> str:
        quote_asset = str(wallet.get("quote_asset", "USDT"))
        quote_balance = float(wallet.get("quote_balance", 0.0))
        current_symbol = self.config.symbol
        parsed = _split_symbol_pair(current_symbol)
        if not parsed:
            return "OK"

        base_asset, _ = parsed
        reference_book = self.order_books.get(current_symbol, {}).get(exchange)
        required_quote = 0.0
        if reference_book and reference_book.best_ask and reference_book.best_ask > 0:
            fee = self.fees.get(exchange, 0.0)
            required_quote = reference_book.best_ask * self.config.trade_size * (1 + fee)

        base_balance = self._get_base_balance(exchange, base_asset)
        low_quote = required_quote > 0 and quote_balance < required_quote
        low_base = base_balance < self.config.trade_size

        if low_quote and low_base:
            return f"Low {quote_asset} & {base_asset}"
        if low_quote:
            return f"Low {quote_asset}"
        if low_base:
            return f"Low {base_asset}"
        return "OK"

    def _network_fee_units(self, asset: str) -> float:
        return float(NETWORK_FEE_UNITS.get(asset.upper(), 0.5))

    def estimate_transfer_fee(
        self,
        symbol: str,
        reference_price: float | None = None,
        exchange: str | None = None,
    ) -> tuple[str, float, float]:
        parsed = _split_symbol_pair(symbol)
        if not parsed:
            return "USD", 0.0, self.config.transfer_cost_usd

        base_asset, quote_asset = parsed
        fee_units = self._network_fee_units(base_asset)

        unit_price_usd = 0.0
        if quote_asset in STABLE_QUOTES and reference_price and reference_price > 0:
            unit_price_usd = reference_price
        elif exchange:
            unit_price_usd = self._find_exchange_asset_price_usd(exchange, base_asset)

        if unit_price_usd <= 0:
            return base_asset, fee_units, self.config.transfer_cost_usd
        return base_asset, fee_units, fee_units * unit_price_usd

    def _transfer_cost_for_asset(self, asset: str, exchange: str) -> float:
        fee_units = self._network_fee_units(asset)
        unit_price_usd = self._find_exchange_asset_price_usd(exchange, asset)
        if unit_price_usd <= 0:
            if asset.upper() in STABLE_QUOTES:
                unit_price_usd = 1.0
            else:
                return self.config.transfer_cost_usd
        return fee_units * unit_price_usd

    def _apply_transfer_cost(self, cost_usd: float | None = None) -> None:
        applied = self.config.transfer_cost_usd if cost_usd is None else max(float(cost_usd), 0.0)
        self.total_pnl_usd -= applied
        self.balance_usd -= applied

    def _transfer_quote_between_exchanges(self, from_exchange: str, to_exchange: str, amount: float) -> bool:
        if amount <= 0:
            return False
        from_wallet = self.inventory_by_exchange.get(from_exchange)
        to_wallet = self.inventory_by_exchange.get(to_exchange)
        if not from_wallet or not to_wallet:
            return False

        from_quote_balance = float(from_wallet.get("quote_balance", 0.0))
        if from_quote_balance < amount:
            return False

        from_wallet["quote_balance"] = from_quote_balance - amount
        to_wallet["quote_balance"] = float(to_wallet.get("quote_balance", 0.0)) + amount
        quote_asset = str(from_wallet.get("quote_asset", "USDT"))
        transfer_cost = self._transfer_cost_for_asset(quote_asset, from_exchange)
        self._apply_transfer_cost(transfer_cost)
        return True

    def _transfer_base_between_exchanges(
        self,
        *,
        from_exchange: str,
        to_exchange: str,
        base_asset: str,
        amount: float,
    ) -> bool:
        if amount <= 0:
            return False
        available = self._get_base_balance(from_exchange, base_asset)
        if available < amount:
            return False

        self._add_base_balance(from_exchange, base_asset, -amount)
        self._add_base_balance(to_exchange, base_asset, amount)
        transfer_cost = self._transfer_cost_for_asset(base_asset, from_exchange)
        self._apply_transfer_cost(transfer_cost)
        return True

    async def rebalance_quotes(self) -> dict[str, float | int]:
        async with self._lock:
            wallets = {
                exchange: float(data.get("quote_balance", 0.0))
                for exchange, data in self.inventory_by_exchange.items()
            }
            if len(wallets) < 2:
                return {
                    "transfers": 0,
                    "moved_quote_usd": 0.0,
                    "target_quote_usd": 0.0,
                }

            target_balance = sum(wallets.values()) / len(wallets)
            moved_quote = 0.0
            transfer_count = 0

            while True:
                donor = max(wallets, key=wallets.get)
                receiver = min(wallets, key=wallets.get)
                donor_surplus = wallets[donor] - target_balance
                receiver_deficit = target_balance - wallets[receiver]
                transfer_amount = min(donor_surplus, receiver_deficit)

                if transfer_amount <= 0.01:
                    break

                if not self._transfer_quote_between_exchanges(donor, receiver, transfer_amount):
                    break

                wallets[donor] -= transfer_amount
                wallets[receiver] += transfer_amount
                moved_quote += transfer_amount
                transfer_count += 1

            return {
                "transfers": transfer_count,
                "moved_quote_usd": round(moved_quote, 8),
                "target_quote_usd": round(target_balance, 8),
            }

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
                "total_value_usd": round(self._estimate_wallet_value_usd(exchange, wallet), 8),
                "status": self._wallet_status(exchange, wallet),
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
                status="insufficient_liquidity",
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

        _, _, transfer_cost_usd = self.estimate_transfer_fee(
            buy_book.symbol,
            reference_price=buy_vwap,
            exchange=buy_book.exchange,
        )
        net_profit = ((sell_unit_after_fee - buy_unit_with_fee) * size) - transfer_cost_usd

        gross_spread_pct = ((sell_vwap - buy_vwap) / buy_vwap) * 100 if buy_vwap > 0 else 0.0
        buy_total_with_fee = buy_unit_with_fee * size
        net_spread_pct = (net_profit / buy_total_with_fee) * 100 if buy_total_with_fee > 0 else 0.0

        base_asset = (_split_symbol_pair(buy_book.symbol) or ("BASE", "USDT"))[0]

        buy_wallet = self.inventory_by_exchange.get(buy_book.exchange)
        buy_quote_balance = float(buy_wallet.get("quote_balance", 0.0)) if buy_wallet else 0.0

        if buy_total_with_fee > buy_quote_balance:
            return Opportunity(
                timestamp=timestamp,
                status="no_funds",
                reason="insufficient_quote_balance",
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

        sell_base_balance = self._get_base_balance(sell_book.exchange, base_asset)

        if sell_base_balance < size:
            return Opportunity(
                timestamp=timestamp,
                status="no_funds",
                reason="insufficient_base_balance",
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
        base_asset = (_split_symbol_pair(opportunity.symbol) or ("BASE", "USDT"))[0]

        buy_wallet = self.inventory_by_exchange.setdefault(
            opportunity.buy_exchange,
            {"quote_asset": "USDT", "quote_balance": 0.0, "asset_balances": {}},
        )
        sell_wallet = self.inventory_by_exchange.setdefault(
            opportunity.sell_exchange,
            {"quote_asset": "USDT", "quote_balance": 0.0, "asset_balances": {}},
        )

        buy_quote_balance = float(buy_wallet.get("quote_balance", 0.0))
        buy_shortfall = buy_cost - buy_quote_balance
        if buy_shortfall > 0:
            self._transfer_quote_between_exchanges(
                from_exchange=opportunity.sell_exchange,
                to_exchange=opportunity.buy_exchange,
                amount=buy_shortfall,
            )
            buy_quote_balance = float(buy_wallet.get("quote_balance", 0.0))

        if buy_quote_balance < buy_cost:
            return

        sell_base_balance = self._get_base_balance(opportunity.sell_exchange, base_asset)
        sell_shortfall = opportunity.trade_size - sell_base_balance
        if sell_shortfall > 0:
            self._transfer_base_between_exchanges(
                from_exchange=opportunity.buy_exchange,
                to_exchange=opportunity.sell_exchange,
                base_asset=base_asset,
                amount=sell_shortfall,
            )
            sell_base_balance = self._get_base_balance(opportunity.sell_exchange, base_asset)

        if sell_base_balance < opportunity.trade_size:
            return

        buy_wallet["quote_balance"] = float(buy_wallet.get("quote_balance", 0.0)) - buy_cost
        sell_wallet["quote_balance"] = float(sell_wallet.get("quote_balance", 0.0)) + sell_value

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
            inventory = self._inventory_view()
            portfolio_total_usd = sum(
                float(wallet.get("total_value_usd", 0.0))
                for wallet in inventory.values()
            )
            return {
                "symbol": self.config.symbol,
                "symbols": self.config.symbols,
                "trade_size": self.config.trade_size,
                "simulation_volume_usd": self.simulation_volume_usd,
                "balance_usd": self.balance_usd,
                "total_pnl_usd": self.total_pnl_usd,
                "portfolio_total_usd": round(portfolio_total_usd, 8),
                "inventory_by_exchange": inventory,
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