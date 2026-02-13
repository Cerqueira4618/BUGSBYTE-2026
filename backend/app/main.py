import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _parse_cors_origins(raw: str | None) -> list[str]:
    if not raw:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="BUGSBYTE API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(os.getenv("CORS_ORIGINS")),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {"service": "bugsbyte-api", "status": "ok"}


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/echo")
def echo(message: str = "hello") -> dict:
    return {"message": message}