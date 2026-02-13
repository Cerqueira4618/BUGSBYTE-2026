from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FeedConfig:
    name: str
    kind: str
    fee: float
    enabled: bool = True
    price_offset: float = 0.0
    volatility: float = 2.0
    depth_levels: int = 20


@dataclass(slots=True)
class AppConfig:
    symbol: str
    trade_size: float
    transfer_cost_usd: float
    starting_balance_usd: float
    auto_simulate_execution: bool
    opportunity_threshold_usd: float
    feeds: list[FeedConfig]


def _default_config() -> AppConfig:
    return AppConfig(
        symbol="BTCUSDT",
        trade_size=0.05,
        transfer_cost_usd=1.0,
        starting_balance_usd=10000,
        auto_simulate_execution=True,
        opportunity_threshold_usd=0.01,
        feeds=[
            FeedConfig(name="binance", kind="binance_ws", fee=0.001, enabled=True),
            FeedConfig(
                name="sim_exchange",
                kind="simulated",
                fee=0.0015,
                enabled=True,
                price_offset=220.0,
                volatility=3.5,
                depth_levels=20,
            ),
            FeedConfig(
                name="sim_exchange_b",
                kind="simulated",
                fee=0.0012,
                enabled=True,
                price_offset=-220.0,
                volatility=3.0,
                depth_levels=20,
            ),
        ],
    )


def load_config(root_path: Path) -> AppConfig:
    config_path = root_path / "config.json"
    if not config_path.exists():
        return _default_config()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    feeds = [
        FeedConfig(
            name=feed["name"],
            kind=feed["kind"],
            fee=float(feed["fee"]),
            enabled=bool(feed.get("enabled", True)),
            price_offset=float(feed.get("price_offset", 0.0)),
            volatility=float(feed.get("volatility", 2.0)),
            depth_levels=int(feed.get("depth_levels", 20)),
        )
        for feed in data.get("feeds", [])
    ]

    return AppConfig(
        symbol=data.get("symbol", "BTCUSDT"),
        trade_size=float(data.get("trade_size", 0.05)),
        transfer_cost_usd=float(data.get("transfer_cost_usd", 1.0)),
        starting_balance_usd=float(data.get("starting_balance_usd", 10000)),
        auto_simulate_execution=bool(data.get("auto_simulate_execution", True)),
        opportunity_threshold_usd=float(data.get("opportunity_threshold_usd", 0.01)),
        feeds=feeds,
    )