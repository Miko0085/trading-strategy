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
from .shadow.engine import apply_realized_execution, evaluate_restructuring, generate_grid


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
            "account_state_ready": False,
            "orders_ready": False,
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
        diagnostic["account_state_ready"] = diagnostic["read_only_validated"] and all(diagnostic[name] == "ok" for name in ("wallet_status", "positions_status"))
        diagnostic["orders_ready"] = diagnostic["read_only_validated"] and diagnostic["open_orders_status"] == "ok"
        diagnostic["private_state_ready"] = diagnostic["account_state_ready"] and diagnostic["orders_ready"]
        app.state.private_ready = diagnostic["private_state_ready"]
        app.state.diagnostics = diagnostic
        return diagnostic

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        diagnostic = app.state.diagnostics
        return {"status": "ok", "private_integration": settings.private_configured, "read_only": diagnostic["read_only_validated"], "environment": settings.environment, "credential_source": settings.credential_source, "account_state_ready": diagnostic["account_state_ready"], "orders_ready": diagnostic["orders_ready"], "private_state_ready": diagnostic["private_state_ready"]}

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
            account_ready = app.state.diagnostics["account_state_ready"] or app.state.private_ready
            service = app.state.account_service
            if hasattr(service, "get_fresh_or_refresh"):
                return await service.get_fresh_or_refresh(symbol, max_age=settings.stale_after_seconds, require_private=account_ready)
            return await service.get(symbol, require_private=account_ready)
        except ReadOnlyBybitError as exc:
            raise HTTPException(502, "Bybit state is unavailable") from exc

    @app.get("/api/market/klines/{symbol}")
    async def market_klines(symbol: str, interval: str = "15", limit: int = 200) -> dict[str, Any]:
        allowed_intervals = {"1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"}
        interval = interval.upper() if interval.upper() in {"D", "W", "M"} else interval
        if interval not in allowed_intervals:
            raise HTTPException(422, "Unsupported kline interval")
        if limit < 20 or limit > 1000:
            raise HTTPException(422, "Kline limit must be between 20 and 1000")
        try:
            result = await app.state.bybit.klines("linear", symbol.upper(), interval=interval, limit=limit)
            rows = result.get("list", [])
            candles = [
                {
                    "time": int(row[0]) // 1000,
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]) if len(row) > 5 else None,
                }
                for row in reversed(rows)
                if isinstance(row, list) and len(row) >= 5
            ]
            return {"symbol": symbol.upper(), "interval": interval, "source": "BYBIT_PUBLIC", "candles": candles}
        except (ReadOnlyBybitError, ValueError, TypeError) as exc:
            raise HTTPException(502, "Не удалось получить публичные свечи Bybit") from exc

    async def shadow_factual(symbol: str) -> dict[str, Any]:
        if not (app.state.diagnostics["account_state_ready"] or app.state.private_ready):
            raise ReadOnlyBybitError("Нет подтверждённого состояния аккаунта Bybit")
        service = app.state.account_service
        return await service.get_fresh_or_refresh(symbol.upper(), max_age=settings.stale_after_seconds, require_private=True)

    @app.post("/api/shadow/generate")
    async def shadow_generate(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            symbol = str(payload.get("symbol", "")).upper()
            configuration = dict(payload.get("configuration") or payload)
            configuration["symbol"] = symbol
            factual = await shadow_factual(symbol)
            return jsonable_encoder(generate_grid(account=factual, configuration=configuration, instrument=factual["instrument"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        except ReadOnlyBybitError as exc:
            raise HTTPException(503, "Нет подтверждённого состояния аккаунта Bybit") from exc

    @app.post("/api/shadow/restructure")
    async def shadow_restructure(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            symbol = str(payload.get("symbol", "")).upper()
            factual = await shadow_factual(symbol)
            return jsonable_encoder(evaluate_restructuring(payload["current"], trigger=str(payload["trigger"]), account=factual, configuration={**payload["configuration"], "symbol": symbol}, instrument=factual["instrument"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        except ReadOnlyBybitError as exc:
            raise HTTPException(503, "Нет подтверждённого состояния аккаунта Bybit") from exc

    @app.post("/api/shadow/apply-realized-execution")
    async def shadow_apply_realized_execution(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return jsonable_encoder(apply_realized_execution(payload["current"], execution=payload["execution"], configuration=payload["configuration"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/shadow/revisions")
    async def save_shadow_revision(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            symbol = str(payload.get("symbol", "")).upper()
            evaluation = payload["evaluation"]
            if evaluation.get("execution") != "NOT_SENT":
                raise ValueError("Shadow revision must remain virtual")
            return app.state.repository.save_shadow_revision(symbol, evaluation)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 -- API boundary returns safe storage error
            raise HTTPException(503, "PostgreSQL недоступен или migration 003 не выполнена") from exc

    @app.get("/api/shadow/revisions")
    async def shadow_revisions(symbol: str | None = None) -> list[dict[str, Any]]:
        try:
            return app.state.repository.list_shadow_revisions(symbol.upper() if symbol else None)
        except Exception as exc:  # noqa: BLE001 -- API boundary returns safe storage error
            raise HTTPException(503, "PostgreSQL недоступен или migration 003 не выполнена") from exc

    async def authoritative_payload(configuration: GridConfigurationDTO, client_payload: dict[str, Any] | None = None, *, force_refresh: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
        client_payload = client_payload or {}
        if app.state.diagnostics["account_state_ready"] or app.state.private_ready:
            service = app.state.account_service
            if force_refresh and hasattr(service, "refresh"):
                state = await service.refresh(configuration.symbol, require_private=True)
            elif hasattr(service, "get_fresh_or_refresh"):
                state = await service.get_fresh_or_refresh(configuration.symbol, max_age=settings.stale_after_seconds, require_private=True)
            else:
                state = await service.get(configuration.symbol, require_private=True)
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
                "position_mode": state.get("position_mode", "UNKNOWN"),
                "position_mode_symbol": state.get("position_mode_symbol", configuration.symbol),
            }
        elif settings.allow_fixture_data:
            factual = {key: client_payload.get(key) for key in ("mark_price", "available_margin", "instrument", "account", "account_state_timestamp", "instrument_source", "position_mode", "position_mode_symbol")}
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
            factual_payload, factual = await authoritative_payload(configuration, raw_configuration, force_refresh=True)
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

    @app.post("/api/audit/generated-grid")
    async def audit_generated_grid(payload: dict[str, Any]) -> dict[str, Any]:
        symbol = str(payload.get("symbol", "")).upper()
        if not symbol or payload.get("source") != "GENERATED_ALGORITHM":
            raise HTTPException(422, "generated grid audit payload is invalid")
        try:
            return app.state.repository.save_apply_audit(symbol, payload, environment=settings.environment)
        except Exception as exc:  # noqa: BLE001 -- API boundary returns safe storage error
            raise HTTPException(503, "PostgreSQL недоступен или миграция не выполнена") from exc

    return app


app = create_app()
