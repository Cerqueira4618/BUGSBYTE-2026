import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .models import opportunity_to_dict, simulated_trade_to_dict
from .service import ArbitrageService


def _symbol_name(symbol: str) -> str:
    names = {
        "BTCUSDT": "Bitcoin (BTC/USDT)",
        "ETHUSDT": "Ethereum (ETH/USDT)",
        "ADAUSDT": "Cardano (ADA/USDT)",
        "BNBUSDT": "BNB (BNB/USDT)",
        "SOLUSDT": "Solana (SOL/USDT)",
    }
    key = symbol.upper()
    return names.get(key, key)


def _parse_cors_origins(raw: str | None) -> list[str]:
    if not raw:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


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
    return await service.engine.snapshot()


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