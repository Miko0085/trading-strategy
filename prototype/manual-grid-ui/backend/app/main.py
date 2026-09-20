from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from .account_service import AccountStateService
from .bybit import ReadOnlyBybitClient, ReadOnlyBybitError
from .calculations import calculate_configuration
from .config import Settings
from .db import RevisionRepository
from .schemas import GridConfigurationDTO, SaveRevisionDTO


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.validate()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http_client = httpx.AsyncClient(base_url="https://api-testnet.bybit.com" if settings.bybit_testnet else "https://api.bybit.com", timeout=10)
        client = ReadOnlyBybitClient(settings.bybit_api_key, settings.bybit_api_secret, settings.bybit_testnet, http_client)
        app.state.bybit = client
        app.state.private_ready = False
        app.state.account_service = AccountStateService(client, stale_after_seconds=settings.stale_after_seconds)
        app.state.diagnostics = {
            "repository_root_found": settings.repository_root_found,
            "root_env_found": settings.root_env_found,
            "module_env_found": settings.module_env_found,
            "api_key_present": bool(settings.bybit_api_key),
            "api_secret_present": bool(settings.bybit_api_secret),
            "credential_source": settings.credential_source,
            "environment": settings.environment,
            "private_configured": settings.private_configured,
            "read_only_validated": False,
            "query_api_status": "error",
            "wallet_status": "error",
            "positions_status": "error",
            "open_orders_status": "error",
            "private_state_ready": False,
            "last_safe_error": "Не найден API ключ или secret" if not settings.private_configured else None,
        }
        try:
            if settings.private_configured:
                await run_private_diagnostics(app, "BTCUSDT")
            yield
        finally:
            await client.close()

    app = FastAPI(title="Manual Grid UI API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[settings.allowed_origins], allow_methods=["GET", "POST"], allow_headers=["*"])
    app.state.settings = settings
    app.state.repository = RevisionRepository(settings.database_url)

    async def run_private_diagnostics(app: FastAPI, symbol: str) -> dict[str, Any]:
        diagnostic = dict(app.state.diagnostics)
        if not settings.private_configured:
            diagnostic["last_safe_error"] = "Не найден API ключ или secret"
            app.state.private_ready = False
            app.state.diagnostics = diagnostic
            return diagnostic
        try:
            await app.state.bybit.validate_read_only()
            diagnostic["read_only_validated"] = True
            diagnostic["query_api_status"] = "ok"
        except ReadOnlyBybitError:
            diagnostic["last_safe_error"] = "Не удалось подтвердить режим только чтение"
            app.state.private_ready = False
            app.state.diagnostics = diagnostic
            return diagnostic

        probes = (
            ("wallet_status", lambda: app.state.bybit.account_state()),
            ("positions_status", lambda: app.state.bybit.positions("linear", symbol)),
            ("open_orders_status", lambda: app.state.bybit.open_orders("linear", symbol)),
        )
        for status_name, probe in probes:
            try:
                result = await probe()
                if not isinstance(result.get("list"), list):
                    raise ReadOnlyBybitError("Bybit result list is missing")
                diagnostic[status_name] = "ok"
            except ReadOnlyBybitError:
                diagnostic[status_name] = "error"
                if diagnostic["last_safe_error"] is None:
                    diagnostic["last_safe_error"] = {
                        "wallet_status": "Данные кошелька Bybit недоступны",
                        "positions_status": "Данные позиций Bybit недоступны",
                        "open_orders_status": "Ордера Bybit недоступны",
                    }[status_name]
        diagnostic["private_state_ready"] = diagnostic["read_only_validated"] and all(diagnostic[name] == "ok" for name in ("wallet_status", "positions_status", "open_orders_status"))
        app.state.private_ready = diagnostic["private_state_ready"]
        app.state.diagnostics = diagnostic
        return diagnostic

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        diagnostic = app.state.diagnostics
        return {"status": "ok", "private_integration": settings.private_configured, "read_only": diagnostic["read_only_validated"], "environment": settings.environment, "credential_source": settings.credential_source, "private_state_ready": diagnostic["private_state_ready"]}

    @app.get("/api/diagnostics/bybit")
    async def bybit_diagnostics(symbol: str = "BTCUSDT") -> dict[str, Any]:
        return await run_private_diagnostics(app, symbol.upper())

    @app.get("/api/symbols")
    async def symbols(query: str = "") -> dict[str, Any]:
        try:
            values: list[str] = []
            cursor: str | None = None
            for _ in range(10):
                result = await app.state.bybit.instrument("linear", **({"cursor": cursor} if cursor else {}))
                values.extend(item["symbol"] for item in result.get("list", []) if item.get("symbol") and query.upper() in item["symbol"])
                cursor = result.get("nextPageCursor")
                if not cursor or len(values) >= 100:
                    break
            return {"symbols": values[:100], "updated_at": datetime.now(UTC).isoformat()}
        except ReadOnlyBybitError as exc:
            raise HTTPException(502, "Не удалось получить список инструментов") from exc

    @app.get("/api/state/{symbol}")
    async def state(symbol: str) -> dict[str, Any]:
        symbol = symbol.upper()
        try:
            return await app.state.account_service.refresh(symbol, require_private=app.state.private_ready)
        except ReadOnlyBybitError as exc:
            raise HTTPException(502, "Bybit state is unavailable") from exc

    async def authoritative_payload(configuration: GridConfigurationDTO, client_payload: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        client_payload = client_payload or {}
        if app.state.private_ready:
            state = await app.state.account_service.get(configuration.symbol, require_private=True)
            if state.get("available_margin") is None or state.get("mark_price") is None:
                raise ReadOnlyBybitError("Critical account state is unavailable")
            factual = {
                "mark_price": state["mark_price"],
                "available_margin": state["available_margin"],
                "instrument": state["instrument"],
                "account": {
                    "available_margin": state["available_margin"],
                    "long_initial_margin": (state.get("long") or {}).get("initial_margin"),
                    "short_initial_margin": (state.get("short") or {}).get("initial_margin"),
                },
                "account_state_timestamp": state.get("updated_at"),
                "instrument_source": "bybit_read_only",
            }
        elif settings.allow_fixture_data:
            factual = {key: client_payload.get(key) for key in ("mark_price", "available_margin", "instrument", "account", "account_state_timestamp", "instrument_source")}
            factual["account"] = factual.get("account") or {"available_margin": factual.get("available_margin")}
            if not factual.get("mark_price") or not factual.get("available_margin") or not factual.get("instrument"):
                raise ReadOnlyBybitError("Fixture factual state is incomplete")
        else:
            raise ReadOnlyBybitError("Private read-only Bybit state is required for authoritative calculation")
        normalized = configuration.domain_payload()
        normalized.update({key: value for key, value in factual.items() if value is not None})
        return normalized, factual

    @app.post("/api/calculate")
    async def calculate(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            configuration = GridConfigurationDTO.model_validate(payload)
            factual_payload, _ = await authoritative_payload(configuration, payload)
            return calculate_configuration(factual_payload, instrument=factual_payload["instrument"], account=factual_payload["account"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        except ReadOnlyBybitError as exc:
            raise HTTPException(503, "Нет подтверждённого состояния аккаунта Bybit") from exc

    @app.post("/api/revisions")
    async def save_revision(item: SaveRevisionDTO) -> dict[str, Any]:
        try:
            raw_configuration = item.configuration.model_dump(mode="json", by_alias=False) if item.configuration else item.payload or {}
            raw_configuration["symbol"] = item.symbol
            configuration = GridConfigurationDTO.model_validate(raw_configuration)
            factual_payload, factual = await authoritative_payload(configuration, raw_configuration)
            calculation = calculate_configuration(factual_payload, instrument=factual_payload["instrument"], account=factual_payload["account"])
            persisted = {"configuration": configuration.domain_payload(), "market_snapshot": factual, "calculation": jsonable_encoder(calculation)}
            return app.state.repository.save(item.symbol, item.comment, persisted, environment="testnet" if settings.bybit_testnet else "mainnet")
        except Exception as exc:  # noqa: BLE001 -- API boundary returns safe storage error
            if isinstance(exc, (KeyError, TypeError, ValueError)):
                raise HTTPException(422, str(exc)) from exc
            if isinstance(exc, ReadOnlyBybitError):
                raise HTTPException(503, "Нет подтверждённого состояния аккаунта Bybit") from exc
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
