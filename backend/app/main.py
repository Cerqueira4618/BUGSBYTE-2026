import os
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import opportunity_to_dict, simulated_trade_to_dict
from .service import ArbitrageService


def _symbol_name(symbol: str) -> str:
    names = {
        "BTCUSDT": "Bitcoin (BTC/USDT)",
        "ETHUSDT": "Ethereum (ETH/USDT)",
        "ADAUSDT": "Cardano (ADA/USDT)",
        "BNBUSDT": "BNB (BNB/USDT)",
        "SOLUSDT": "Solana (SOL/USDT)",
        "BTCETH": "Bitcoin (BTC/ETH)",
        "ETHBTC": "Ethereum (ETH/BTC)",
    }
    key = symbol.upper()
    return names.get(key, key)


class SymbolSelectionPayload(BaseModel):
    symbol: str


class ExchangeTogglePayload(BaseModel):
    exchange: str
    enabled: bool


class SimulationVolumePayload(BaseModel):
    volume_usd: float


def _parse_cors_origins(raw: str | None) -> list[str]:
    if not raw:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _coingecko_id(symbol: str) -> str | None:
    ids = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "BNB": "binancecoin",
        "XRP": "ripple",
        "ADA": "cardano",
        "AVAX": "avalanche-2",
        "DOT": "polkadot",
        "LINK": "chainlink",
    }
    return ids.get(symbol.upper())


def _fetch_market_chart(coin_id: str, days: int) -> list[dict[str, float]]:
    api_key = os.getenv("COINGECKO_API_KEY") or "CG-DemoAPIKey"
    url = (
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        f"?vs_currency=eur&days={days}&interval=daily&precision=2"
        f"&x_cg_demo_api_key={api_key}"
    )
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "BUGSBYTE-Market/1.0",
        },
    )
    with urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))

    prices = payload.get("prices", [])
    return [
        {"time": int(point[0]), "price": float(point[1])}
        for point in prices
        if isinstance(point, list) and len(point) >= 2
    ]


def _fetch_binance_klines(symbol: str, days: int) -> list[dict[str, float]]:
    pair = f"{symbol.upper()}EUR"
    url = (
        "https://api.binance.com/api/v3/klines"
        f"?symbol={pair}&interval=1d&limit={days}"
    )
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "BUGSBYTE-Market/1.0",
        },
    )
    with urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, list):
        return []

    items: list[dict[str, float]] = []
    for row in payload:
        if not isinstance(row, list) or len(row) < 5:
            continue
        open_time = int(row[0])
        close_price = float(row[4])
        items.append({"time": open_time, "price": close_price})
    return items


@asynccontextmanager
async def lifespan(app: FastAPI):
    backend_root = Path(__file__).resolve().parents[1]
    service = ArbitrageService(root_path=backend_root)
    app.state.arbitrage_service = service
    await service.start()
    try:
        yield
    finally:
        await service.stop()


app = FastAPI(title="BUGSBYTE API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(os.getenv("CORS_ORIGINS")),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {
        "service": "bugsbyte-api",
        "status": "ok",
        "module": "arbitrage-mvp",
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/echo")
def echo(message: str = "hello") -> dict:
    return {"message": message}


@app.get("/api/arbitrage/status")
async def arbitrage_status() -> dict:
    service: ArbitrageService = app.state.arbitrage_service
    snapshot = await service.engine.snapshot()
    if "exchange_states" not in snapshot:
        snapshot["exchange_states"] = service.exchange_states()
    return snapshot


@app.post("/api/arbitrage/symbol")
async def arbitrage_set_symbol(payload: SymbolSelectionPayload) -> dict:
    service: ArbitrageService = app.state.arbitrage_service
    await service.set_symbol(payload.symbol)
    snapshot = await service.engine.snapshot()
    if "exchange_states" not in snapshot:
        snapshot["exchange_states"] = service.exchange_states()
    return snapshot


@app.post("/api/arbitrage/exchanges")
async def arbitrage_toggle_exchange(payload: ExchangeTogglePayload) -> dict:
    service: ArbitrageService = app.state.arbitrage_service
    await service.set_exchange_enabled(payload.exchange, payload.enabled)
    snapshot = await service.engine.snapshot()
    if "exchange_states" not in snapshot:
        snapshot["exchange_states"] = service.exchange_states()
    return snapshot


@app.post("/api/arbitrage/simulation-volume")
async def arbitrage_set_simulation_volume(payload: SimulationVolumePayload) -> dict:
    service: ArbitrageService = app.state.arbitrage_service
    service.set_simulation_volume_usd(payload.volume_usd)
    snapshot = await service.engine.snapshot()
    if "exchange_states" not in snapshot:
        snapshot["exchange_states"] = service.exchange_states()
    return snapshot


@app.get("/api/arbitrage/opportunities")
async def arbitrage_opportunities(limit: int = 100, symbols: list[str] | None = Query(None)) -> dict:
    service: ArbitrageService = app.state.arbitrage_service
    items = await service.engine.list_opportunities(limit=limit, symbols=symbols)
    return {
        "items": [
            {
                **opportunity_to_dict(item),
                "symbol_name": _symbol_name(item.symbol),
            }
            for item in items
        ]
    }


@app.get("/api/arbitrage/trades")
async def arbitrage_trades(limit: int = 100, symbols: list[str] | None = Query(None)) -> dict:
    service: ArbitrageService = app.state.arbitrage_service
    items = await service.engine.list_trades(limit=limit, symbols=symbols)
    return {
        "items": [
            {
                **simulated_trade_to_dict(item),
                "symbol_name": _symbol_name(item.symbol),
            }
            for item in items
        ]
    }


@app.get("/api/arbitrage/spread-series")
async def arbitrage_spread_series(limit: int = 200) -> dict:
    service: ArbitrageService = app.state.arbitrage_service
    items = await service.engine.spread_series(limit=limit)
    return {"items": items}


@app.get("/api/market/history")
async def market_history(symbol: str = Query(...), days: int = Query(30, ge=7, le=90)) -> dict:
    coin_id = _coingecko_id(symbol)
    if not coin_id:
        raise HTTPException(status_code=400, detail=f"Símbolo sem mapeamento: {symbol}")

    items: list[dict[str, float]] = []
    source = "coingecko"

    try:
        items = await asyncio.to_thread(_fetch_market_chart, coin_id, days)
    except Exception:
        items = []

    if not items:
        try:
            items = await asyncio.to_thread(_fetch_binance_klines, symbol, days)
            source = "binance"
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Falha ao obter histórico de mercado") from exc

    if not items:
        raise HTTPException(status_code=404, detail="Sem histórico disponível")

    return {
        "symbol": symbol.upper(),
        "currency": "EUR",
        "days": days,
        "source": source,
        "items": items,
    }


@app.websocket("/ws/arbitrage")
async def arbitrage_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    service: ArbitrageService = app.state.arbitrage_service
    try:
        while True:
            snapshot = await service.engine.snapshot()
            spread_series = await service.engine.spread_series(limit=50)
            await websocket.send_json(
                {
                    "type": "arbitrage_snapshot",
                    "snapshot": snapshot,
                    "spread_series": spread_series,
                }
            )
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.close(code=1011)