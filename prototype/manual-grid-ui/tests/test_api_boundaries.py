import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.bybit import ReadOnlyBybitClient, ReadOnlyBybitError
from app.config import Settings
import app.config as config_module
from app.main import create_app
from app.account_service import AccountStateService


def test_calculate_endpoint_returns_decimal_normalized_result():
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="", bybit_api_secret="", allow_fixture_data=True))
    payload = {"symbol": "BTCUSDT", "mark_price": "100", "available_margin": "1000", "leverage": "2", "allocation": {"long_pct": "40", "short_pct": "20", "reserve_pct": "40"}, "active_long_count": 1, "active_short_count": 1, "instrument": {"tick_size": "0.1", "qty_step": "1", "min_order_qty": "1", "min_notional_value": "5"}, "long": [{"offset_pct": "10", "qty": "10", "filled_qty": "0", "tps": [{"move_pct": "10", "close_pct": "25"}]}], "short": [{"offset_pct": "10", "qty": "10", "filled_qty": "0", "tps": [{"move_pct": "10", "close_pct": "25"}]}]}
    with TestClient(app) as client:
        response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    assert response.json()["long"]["orders"][0]["tp_steps"][0]["qty"] == "2.5"


def test_repeated_calculation_state_reads_use_fresh_account_cache():
    class FakeClient:
        api_key = "key"

        def __init__(self):
            self.calls = {"ticker": 0, "instrument": 0, "wallet": 0, "positions": 0, "orders": 0}

        async def mark_price(self, category, symbol):
            self.calls["ticker"] += 1
            return {"list": [{"symbol": symbol, "markPrice": "100"}]}

        async def instrument(self, category, symbol):
            self.calls["instrument"] += 1
            return {"list": [{"symbol": symbol, "lotSizeFilter": {"qtyStep": "1", "minOrderQty": "1", "minNotionalValue": "5"}, "priceFilter": {"tickSize": "0.1"}}]}

        async def account_state(self):
            self.calls["wallet"] += 1
            return {"list": [{"totalWalletBalance": "100", "totalEquity": "100", "totalAvailableBalance": "80"}]}

        async def positions(self, category, symbol):
            self.calls["positions"] += 1
            return {"list": [{"symbol": symbol, "side": "Buy", "size": "0", "positionIdx": 1}]}

        async def open_orders(self, category, symbol):
            self.calls["orders"] += 1
            return {"list": []}

    async def exercise():
        client = FakeClient()
        service = AccountStateService(client, stale_after_seconds=30)
        await service.refresh("BTCUSDT", require_private=True)
        for _ in range(10):
            state = await service.get_fresh_or_refresh("BTCUSDT", max_age=30, require_private=True)
            assert state["source"] == "bybit_read_only"
        assert client.calls == {"ticker": 1, "instrument": 1, "wallet": 1, "positions": 1, "orders": 1}

    asyncio.run(exercise())


def test_health_does_not_claim_private_readiness_without_credentials():
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="", bybit_api_secret=""))
    with TestClient(app) as client:
        body = client.get("/api/health").json()
    assert body == {"status": "ok", "private_integration": False, "read_only": False, "environment": "mainnet", "credential_source": "none", "account_state_ready": False, "orders_ready": False, "private_state_ready": False}


def test_read_only_validation_refuses_write_key(monkeypatch):
    client = ReadOnlyBybitClient("key", "secret")

    async def fake_private_get(path, params=None):
        return {"result": {"readOnly": 0}}

    monkeypatch.setattr(client, "private_get", fake_private_get)
    try:
        asyncio.run(client.validate_read_only())
    except ReadOnlyBybitError as exc:
        assert "not read-only" in str(exc)
    else:
        raise AssertionError("write-enabled key was accepted")


def test_api_has_no_trading_write_routes_or_client_methods():
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="", bybit_api_secret=""))
    routes = {route.path for route in app.routes}
    assert not {route for route in routes if any(word in route for word in ("place", "amend", "cancel", "close", "leverage"))}
    assert not any(name in dir(ReadOnlyBybitClient) for name in ("place_order", "amend_order", "cancel_order", "close_position", "set_leverage"))


def test_instrument_list_request_is_public_and_does_not_require_symbol(monkeypatch):
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="", bybit_api_secret=""))

    async def fake_instrument(category, symbol=None):
        assert category == "linear"
        assert symbol is None
        return {"list": [{"symbol": "BTCUSDT"}, {"symbol": "SUIUSDT"}]}

    with TestClient(app) as client:
        monkeypatch.setattr(app.state.bybit, "instrument", fake_instrument)
        response = client.get("/api/symbols?query=sui")
    assert response.status_code == 200
    assert response.json()["symbols"] == ["SUIUSDT"]


def test_env_precedence_uses_module_settings_and_root_only_for_bybit(monkeypatch, tmp_path):
    module_root = tmp_path / "module"
    repository_root = tmp_path / "repository"
    module_root.mkdir()
    repository_root.mkdir()
    (module_root / ".env").write_text("DATABASE_URL=module-db\nBYBIT_API_KEY=module-key\nBYBIT_API_SECRET=module-secret\nBYBIT_TESTNET=false\n", encoding="utf-8")
    (repository_root / ".env").write_text("DATABASE_URL=root-db\nBYBIT_API_KEY=root-key\nBYBIT_API_SECRET=root-secret\nBYBIT_TESTNET=true\n", encoding="utf-8")
    for name in ("DATABASE_URL", "BYBIT_API_KEY", "BYBIT_API_SECRET", "BYBIT_TESTNET", "MANUAL_GRID_ALLOWED_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config_module, "MODULE_ROOT", Path(module_root))
    monkeypatch.setattr(config_module, "REPOSITORY_ROOT", Path(repository_root))
    settings = Settings()
    assert settings.database_url == "module-db"
    assert settings.bybit_api_key == "module-key"
    assert settings.bybit_api_secret == "module-secret"
    assert settings.bybit_testnet is False


def test_repository_root_is_derived_from_config_file_location():
    expected_root = Path(__file__).resolve().parents[3]
    assert config_module.REPOSITORY_ROOT == expected_root
    assert (config_module.REPOSITORY_ROOT / ".git").exists()
    assert config_module.MODULE_ROOT == config_module.REPOSITORY_ROOT / "prototype" / "manual-grid-ui"


def test_blank_module_credentials_fall_back_to_complete_root_bundle(monkeypatch, tmp_path):
    module_root = tmp_path / "module"
    repository_root = tmp_path / "repository"
    module_root.mkdir()
    repository_root.mkdir()
    (module_root / ".env").write_text("BYBIT_API_KEY=\nBYBIT_API_SECRET=\nBYBIT_TESTNET=false\n", encoding="utf-8")
    (repository_root / ".env").write_text("BYBIT_API_KEY=root-key\nBYBIT_API_SECRET=root-secret\nBYBIT_TESTNET=true\n", encoding="utf-8")
    for name in ("BYBIT_API_KEY", "BYBIT_API_SECRET", "BYBIT_TESTNET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config_module, "MODULE_ROOT", module_root)
    monkeypatch.setattr(config_module, "REPOSITORY_ROOT", repository_root)
    settings = Settings()
    assert (settings.bybit_api_key, settings.bybit_api_secret, settings.bybit_testnet, settings.credential_source) == ("root-key", "root-secret", True, "root_env")


def test_process_bundle_has_highest_priority_and_owns_environment(monkeypatch, tmp_path):
    module_root = tmp_path / "module"
    repository_root = tmp_path / "repository"
    module_root.mkdir()
    repository_root.mkdir()
    (module_root / ".env").write_text("BYBIT_API_KEY=module-key\nBYBIT_API_SECRET=module-secret\nBYBIT_TESTNET=false\n", encoding="utf-8")
    (repository_root / ".env").write_text("BYBIT_API_KEY=root-key\nBYBIT_API_SECRET=root-secret\nBYBIT_TESTNET=true\n", encoding="utf-8")
    monkeypatch.setenv("BYBIT_API_KEY", "process-key")
    monkeypatch.setenv("BYBIT_API_SECRET", "process-secret")
    monkeypatch.setenv("BYBIT_TESTNET", "false")
    monkeypatch.setattr(config_module, "MODULE_ROOT", module_root)
    monkeypatch.setattr(config_module, "REPOSITORY_ROOT", repository_root)
    settings = Settings()
    assert (settings.bybit_api_key, settings.bybit_api_secret, settings.bybit_testnet, settings.credential_source) == ("process-key", "process-secret", False, "process_env")


def test_failed_read_only_validation_keeps_backend_alive_and_public_api_available(monkeypatch):
    async def reject_validation(self):
        raise ReadOnlyBybitError("remote failure")

    monkeypatch.setattr(ReadOnlyBybitClient, "validate_read_only", reject_validation)
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="key", bybit_api_secret="secret", bybit_testnet=False))
    with TestClient(app) as client:
        health = client.get("/api/health").json()
        diagnostics = client.get("/api/diagnostics/bybit").json()
    assert health["status"] == "ok"
    assert health["private_state_ready"] is False
    assert diagnostics["read_only_validated"] is False
    assert diagnostics["query_api_status"] == "error"
    assert diagnostics["api_key_present"] is True
    assert diagnostics["api_secret_present"] is True
    assert "remote failure" not in str(diagnostics).lower()


def test_private_state_ready_requires_read_only_wallet_positions_and_orders(monkeypatch):
    async def accept_validation(self):
        return {"readOnly": 1}

    async def wallet(self):
        return {"list": [{"totalAvailableBalance": "100"}]}

    async def positions(self, category, symbol):
        return {"list": []}

    async def orders(self, category, symbol):
        return {"list": []}

    monkeypatch.setattr(ReadOnlyBybitClient, "validate_read_only", accept_validation)
    monkeypatch.setattr(ReadOnlyBybitClient, "account_state", wallet)
    monkeypatch.setattr(ReadOnlyBybitClient, "positions", positions)
    monkeypatch.setattr(ReadOnlyBybitClient, "open_orders", orders)
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="key", bybit_api_secret="secret", bybit_testnet=False))
    with TestClient(app) as client:
        diagnostics = client.get("/api/diagnostics/bybit?symbol=BTCUSDT").json()
        health = client.get("/api/health").json()
    assert diagnostics["read_only_validated"] is True
    assert diagnostics["wallet_status"] == diagnostics["positions_status"] == diagnostics["open_orders_status"] == "ok"
    assert diagnostics["private_state_ready"] is True
    assert health["private_state_ready"] is True
    assert "key" not in str(health).lower()
    assert "secret" not in str(health).lower()


def test_orders_failure_keeps_private_account_state_available(monkeypatch):
    async def accept_validation(self):
        return {"readOnly": 1}

    async def wallet(self):
        return {"list": [{"totalWalletBalance": "100", "totalEquity": "101", "totalAvailableBalance": "80"}]}

    async def positions(self, category, symbol):
        return {"list": [{"symbol": symbol, "side": "Buy", "size": "2", "avgPrice": "90", "positionIdx": 1}]}

    async def orders(self, category, symbol):
        raise ReadOnlyBybitError("orders unavailable")

    monkeypatch.setattr(ReadOnlyBybitClient, "validate_read_only", accept_validation)
    monkeypatch.setattr(ReadOnlyBybitClient, "account_state", wallet)
    monkeypatch.setattr(ReadOnlyBybitClient, "positions", positions)
    monkeypatch.setattr(ReadOnlyBybitClient, "open_orders", orders)
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="key", bybit_api_secret="secret"))
    with TestClient(app) as client:
        diagnostics = client.get("/api/diagnostics/bybit?symbol=BTCUSDT").json()
        state = client.get("/api/state/BTCUSDT").json()
    assert diagnostics["account_state_ready"] is True
    assert diagnostics["orders_ready"] is False
    assert diagnostics["private_state_ready"] is False
    assert state["source"] == "bybit_read_only"
    assert state["wallet_balance"] == "100"
    assert state["long"]["size"] == "2"
    assert state["orders_available"] is False
    assert state["orders"] == []


def test_private_calculation_ignores_forged_browser_facts():
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="", bybit_api_secret=""))

    class FakeAccountService:
        async def get(self, symbol, *, require_private=False):
            assert symbol == "BTCUSDT"
            assert require_private is True
            return {"mark_price": "200", "available_margin": "500", "instrument": {"tick_size": "0.1", "qty_step": "1", "min_order_qty": "1", "min_notional_value": "5"}, "updated_at": "2026-09-20T00:00:00+00:00", "source": "bybit_read_only", "long": {}, "short": {}}

    payload = {"symbol": "BTCUSDT", "mark_price": "99999", "available_margin": "1000000", "leverage": "2", "allocation": {"longPct": "40", "shortPct": "20", "reservePct": "40"}, "activeLongCount": 1, "activeShortCount": 1, "instrument": {"tick_size": "0.000001", "qty_step": "0.000001", "min_order_qty": "0.000001", "min_notional_value": "0.01"}, "long": [{"offsetPct": "10", "qty": "10", "tps": [{"movePct": "10", "closePct": "25"}]}], "short": [{"offsetPct": "10", "qty": "10", "tps": [{"movePct": "10", "closePct": "25"}]}]}
    with TestClient(app) as client:
        app.state.private_ready = True
        app.state.account_service = FakeAccountService()
        response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    assert response.json()["available_margin"] == "500"
    assert response.json()["mark_price"] == "200"
    assert response.json()["instrument"]["tick_size"] == "0.1"


def test_blocked_revision_is_saved_after_server_recalculation():
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="", bybit_api_secret=""))

    class FakeAccountService:
        async def get(self, symbol, *, require_private=False):
            return {"mark_price": "100", "available_margin": "100", "instrument": {"tick_size": "0.1", "qty_step": "1", "min_order_qty": "1", "min_notional_value": "5"}, "updated_at": "2026-09-20T00:00:00+00:00", "source": "bybit_read_only", "long": {}, "short": {}}

    class FakeRepository:
        def save(self, symbol, comment, payload, *, environment):
            assert payload["configuration"]["allocation"] == {"long_pct": "40", "short_pct": "20", "reserve_pct": "40"}
            assert payload["calculation"]["validation_state"] == "BLOCKED"
            return {"symbol": symbol, "validation_state": payload["calculation"]["validation_state"]}

    configuration = {"symbol": "BTCUSDT", "allocation": {"longPct": "40", "shortPct": "20", "reservePct": "40"}, "planningLeverage": "1", "activeLongCount": 1, "activeShortCount": 1, "long": [{"id": "l1", "offsetPct": "10", "qty": "100", "tps": [{"movePct": "10", "closePct": "25"}]}], "short": [{"id": "s1", "offsetPct": "10", "qty": "1", "tps": [{"movePct": "10", "closePct": "25"}]}]}
    with TestClient(app) as client:
        app.state.private_ready = True
        app.state.account_service = FakeAccountService()
        app.state.repository = FakeRepository()
        response = client.post("/api/revisions", json={"symbol": "BTCUSDT", "configuration": configuration})
    assert response.status_code == 200
    assert response.json()["validation_state"] == "BLOCKED"


def test_revisions_have_no_update_or_delete_api():
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="", bybit_api_secret=""))
    with TestClient(app) as client:
        assert client.put("/api/revisions/revision-id", json={"comment": "changed"}).status_code == 404
        assert client.patch("/api/revisions/revision-id", json={"comment": "changed"}).status_code == 404
        assert client.delete("/api/revisions/revision-id").status_code == 404
