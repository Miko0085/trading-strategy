from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .account_state import normalize_account, normalize_instrument
from .bybit import ReadOnlyBybitClient, ReadOnlyBybitError
from .calculations import calculate_configuration
from .config import Settings
from .db import RevisionRepository
from .schemas import RevisionIn


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.validate()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http_client = httpx.AsyncClient(base_url="https://api-testnet.bybit.com" if settings.bybit_testnet else "https://api.bybit.com", timeout=10)
        client = ReadOnlyBybitClient(settings.bybit_api_key, settings.bybit_api_secret, settings.bybit_testnet, http_client)
        app.state.bybit = client
        app.state.private_ready = False
        if settings.private_configured:
            await client.validate_read_only()
            app.state.private_ready = True
        try:
            yield
        finally:
            await client.close()

    app = FastAPI(title="Manual Grid UI API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[settings.allowed_origins], allow_methods=["GET", "POST"], allow_headers=["*"])
    app.state.settings = settings
    app.state.repository = RevisionRepository(settings.database_url)

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "private_integration": settings.private_configured, "read_only": bool(getattr(app.state, "private_ready", False)), "environment": "testnet" if settings.bybit_testnet else "mainnet"}

    @app.get("/api/symbols")
    async def symbols(query: str = "") -> dict[str, Any]:
        try:
            result = await app.state.bybit.instrument("linear")
            values = [item.get("symbol") for item in result.get("list", []) if item.get("symbol") and query.upper() in item["symbol"]]
            return {"symbols": values[:100], "updated_at": datetime.now(UTC).isoformat()}
        except ReadOnlyBybitError as exc:
            raise HTTPException(502, "Не удалось получить список инструментов") from exc

    @app.get("/api/state/{symbol}")
    async def state(symbol: str) -> dict[str, Any]:
        symbol = symbol.upper()
        try:
            ticker = await app.state.bybit.mark_price("linear", symbol)
            instrument = normalize_instrument(await app.state.bybit.instrument("linear", symbol))
            wallet = await app.state.bybit.account_state() if app.state.private_ready else {}
            positions = await app.state.bybit.positions("linear", symbol) if app.state.private_ready else {}
            orders = await app.state.bybit.open_orders("linear", symbol) if app.state.private_ready else {}
            normalized = normalize_account(wallet, positions, orders, ticker, instrument, "bybit_read_only" if app.state.private_ready else "public_only")
            normalized["updated_at"] = datetime.now(UTC).isoformat()
            normalized["stale"] = False
            return normalized
        except ReadOnlyBybitError as exc:
            raise HTTPException(502, "Bybit state is unavailable; cached values must be treated as stale") from exc

    @app.post("/api/calculate")
    async def calculate(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            instrument = payload.get("instrument") or normalize_instrument(await app.state.bybit.instrument("linear", payload["symbol"].upper()))
            return calculate_configuration(payload, instrument=instrument, account=payload.get("account"))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        except ReadOnlyBybitError as exc:
            raise HTTPException(502, "Не удалось получить ограничения инструмента") from exc

    @app.post("/api/revisions")
    async def save_revision(item: RevisionIn) -> dict[str, Any]:
        try:
            return app.state.repository.save(item.symbol, item.comment, item.payload, environment="testnet" if settings.bybit_testnet else "mainnet")
        except Exception as exc:  # noqa: BLE001 -- API boundary returns safe storage error
            raise HTTPException(503, "PostgreSQL недоступен или миграция не выполнена") from exc

    @app.get("/api/revisions")
    async def revisions(symbol: str | None = None) -> list[dict[str, Any]]:
        try:
            return app.state.repository.list(symbol)
        except Exception as exc:  # noqa: BLE001 -- API boundary returns safe storage error
            raise HTTPException(503, "PostgreSQL недоступен или миграция не выполнена") from exc

    @app.get("/api/audit")
    async def audit(filter: str = "all") -> list[dict[str, Any]]:
        try:
            return app.state.repository.audit(filter)
        except Exception as exc:  # noqa: BLE001 -- API boundary returns safe storage error
            raise HTTPException(503, "PostgreSQL недоступен или миграция не выполнена") from exc

    return app


app = create_app()
