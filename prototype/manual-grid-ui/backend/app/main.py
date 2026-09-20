from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .bybit import ReadOnlyBybitClient, ReadOnlyBybitError
from .config import Settings
from .db import RevisionRepository
from .schemas import RevisionIn


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.validate()
    app = FastAPI(title="Manual Grid UI API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=[settings.allowed_origins], allow_methods=["GET", "POST"], allow_headers=["*"])
    client = ReadOnlyBybitClient(settings.bybit_api_key, settings.bybit_api_secret, settings.bybit_testnet) if settings.private_configured else None
    app.state.settings, app.state.bybit, app.state.revisions = settings, client, []
    app.state.repository = RevisionRepository(settings.database_url)

    @app.on_event("startup")
    async def validate_private_key() -> None:
        if client:
            try:
                app.state.key_info = await client.validate_read_only()
            except ReadOnlyBybitError:
                raise

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "private_integration": bool(client), "read_only": bool(client) and hasattr(app.state, "key_info")}

    @app.get("/api/state/{symbol}")
    async def state(symbol: str) -> dict[str, Any]:
        if not client:
            return {"symbol": symbol.upper(), "source": "demo", "available_margin": "10000", "equity": "10000", "mark_price": "0.3996", "positions": [], "orders": []}
        try:
            wallet = await client.account_state()
            positions = await client.positions("linear", symbol.upper())
            orders = await client.open_orders("linear", symbol.upper())
            ticker = await client.mark_price("linear", symbol.upper())
            account = (wallet.get("list") or [{}])[0]
            ticker_row = (ticker.get("list") or [{}])[0]
            return {
                "symbol": symbol.upper(), "source": "bybit_read_only",
                "available_margin": account.get("totalAvailableBalance"),
                "equity": account.get("totalEquity"), "wallet_balance": account.get("totalWalletBalance"),
                "initial_margin": account.get("totalInitialMargin"), "maintenance_margin": account.get("totalMaintenanceMargin"),
                "mark_price": ticker_row.get("markPrice") or ticker_row.get("lastPrice"),
                "positions": positions.get("list", []), "orders": orders.get("list", []),
            }
        except ReadOnlyBybitError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.post("/api/revisions")
    async def save_revision(item: RevisionIn) -> dict[str, Any]:
        try:
            record = app.state.repository.save(item.symbol, item.comment, item.payload)
        except Exception as exc:  # noqa: BLE001 -- API boundary returns a safe storage error
            raise HTTPException(503, "PostgreSQL недоступен или миграция не выполнена") from exc
        return record

    @app.get("/api/revisions")
    async def revisions(symbol: str | None = None) -> list[dict[str, Any]]:
        try:
            return app.state.repository.list(symbol)
        except Exception as exc:  # noqa: BLE001 -- API boundary returns a safe storage error
            raise HTTPException(503, "PostgreSQL недоступен или миграция не выполнена") from exc

    @app.get("/api/audit")
    async def audit() -> list[dict[str, Any]]:
        try:
            return [{"action": "revision_saved", "entity": item["symbol"], "created_at": item["created_at"]} for item in app.state.repository.list()]
        except Exception as exc:  # noqa: BLE001 -- API boundary returns a safe storage error
            raise HTTPException(503, "PostgreSQL недоступен или миграция не выполнена") from exc

    return app


app = create_app()
