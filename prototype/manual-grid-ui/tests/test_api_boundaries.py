import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.bybit import ReadOnlyBybitClient, ReadOnlyBybitError
from app.config import Settings
import app.config as config_module
from app.main import create_app


def test_calculate_endpoint_returns_decimal_normalized_result():
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="", bybit_api_secret="", allow_fixture_data=True))
    payload = {"symbol": "BTCUSDT", "mark_price": "100", "available_margin": "1000", "leverage": "2", "allocation": {"long_pct": "40", "short_pct": "20", "reserve_pct": "40"}, "active_long_count": 1, "active_short_count": 1, "instrument": {"tick_size": "0.1", "qty_step": "1", "min_order_qty": "1", "min_notional_value": "5"}, "long": [{"offset_pct": "10", "qty": "10", "filled_qty": "0", "tps": [{"move_pct": "10", "close_pct": "25"}]}], "short": [{"offset_pct": "10", "qty": "10", "filled_qty": "0", "tps": [{"move_pct": "10", "close_pct": "25"}]}]}
    with TestClient(app) as client:
        response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    assert response.json()["long"]["orders"][0]["tp_steps"][0]["qty"] == "2.5"


def test_health_does_not_claim_private_readiness_without_credentials():
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="", bybit_api_secret=""))
    with TestClient(app) as client:
        body = client.get("/api/health").json()
    assert body == {"status": "ok", "private_integration": False, "read_only": False, "environment": "mainnet"}


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
    (module_root / ".env").write_text("DATABASE_URL=module-db\nBYBIT_API_KEY=module-key\n", encoding="utf-8")
    (repository_root / ".env").write_text("DATABASE_URL=root-db\nBYBIT_API_KEY=root-key\nBYBIT_API_SECRET=root-secret\nBYBIT_TESTNET=true\n", encoding="utf-8")
    for name in ("DATABASE_URL", "BYBIT_API_KEY", "BYBIT_API_SECRET", "BYBIT_TESTNET", "MANUAL_GRID_ALLOWED_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config_module, "MODULE_ROOT", Path(module_root))
    monkeypatch.setattr(config_module, "REPOSITORY_ROOT", Path(repository_root))
    settings = Settings()
    assert settings.database_url == "module-db"
    assert settings.bybit_api_key == "module-key"
    assert settings.bybit_api_secret == "root-secret"
    assert settings.bybit_testnet is True


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
