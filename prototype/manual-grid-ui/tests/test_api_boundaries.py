import asyncio

from fastapi.testclient import TestClient

from app.bybit import ReadOnlyBybitClient, ReadOnlyBybitError
from app.config import Settings
from app.main import create_app


def test_calculate_endpoint_returns_decimal_normalized_result():
    app = create_app(Settings(database_url="postgresql://unused", bybit_api_key="", bybit_api_secret=""))
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
