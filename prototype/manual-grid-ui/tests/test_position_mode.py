from app.account_state import normalize_account, normalize_position_mode
from app.calculations import calculate_configuration


INSTRUMENT = {"tick_size": "0.1", "qty_step": "1", "min_order_qty": "1", "min_notional_value": "5"}


def order(offset="10"):
    return {"offset_pct": offset, "qty": "1", "filled_qty": "0", "tps": []}


def config(mode, *, enabled_long=True, enabled_short=True):
    return {"symbol": "ETHUSDT", "mark_price": "100", "available_margin": "1000", "leverage": "2", "fee_rate": None, "position_mode": mode, "position_mode_symbol": "ETHUSDT", "enabled_long": enabled_long, "enabled_short": enabled_short, "allocation": {"long_pct": "40", "short_pct": "20", "reserve_pct": "40"}, "active_long_count": 1 if enabled_long else 0, "active_short_count": 1 if enabled_short else 0, "long": [order()] if enabled_long else [], "short": [order()] if enabled_short else []}


def test_position_mode_is_inferred_per_symbol_from_position_idx():
    assert normalize_position_mode({"list": [{"positionIdx": 1}]}) == "HEDGE"
    assert normalize_position_mode({"list": [{"positionIdx": 0}]}) == "ONE_WAY"
    assert normalize_position_mode({"list": []}) == "UNKNOWN"


def test_normalized_account_keeps_factual_mode_and_symbol():
    result = normalize_account({"list": []}, {"list": [{"symbol": "ETHUSDT", "positionIdx": 0, "side": "Buy", "size": "1"}]}, {"list": []}, {"list": [{"symbol": "ETHUSDT", "markPrice": "100"}]}, {"symbol": "ETHUSDT"}, "bybit_read_only")
    assert result["position_mode"] == "ONE_WAY"
    assert result["position_mode_symbol"] == "ETHUSDT"


def test_normalized_account_exposes_side_specific_unrealized_pnl_without_total_fallback():
    result = normalize_account({"list": [{"totalPerpUPL": "999"}]}, {"list": [{"symbol": "ETHUSDT", "side": "Buy", "positionIdx": 1, "size": "1", "unrealisedPnl": "100"}]}, {"list": []}, {"list": [{"symbol": "ETHUSDT", "markPrice": "100"}]}, {"symbol": "ETHUSDT"}, "bybit_read_only")
    assert result["long_unrealized_pnl"] == "100"
    assert result["short_unrealized_pnl"] is None


def test_hedge_allows_both_and_one_way_allows_each_single_side():
    assert calculate_configuration(config("HEDGE"), instrument=INSTRUMENT)["validation_state"] == "VALID"
    assert calculate_configuration(config("HEDGE", enabled_short=False), instrument=INSTRUMENT)["validation_state"] == "VALID"
    assert calculate_configuration(config("ONE_WAY", enabled_short=False), instrument=INSTRUMENT)["validation_state"] == "VALID"
    assert calculate_configuration(config("ONE_WAY", enabled_long=False), instrument=INSTRUMENT)["validation_state"] == "VALID"


def test_one_way_and_unknown_block_only_two_sided_configuration():
    one_way = calculate_configuration(config("ONE_WAY"), instrument=INSTRUMENT)
    unknown = calculate_configuration(config("UNKNOWN"), instrument=INSTRUMENT)
    assert one_way["validation_state"] == "BLOCKED"
    assert one_way["validation_errors"][-1]["errors"] == ["Одновременный Long + Short требует Hedge Mode."]
    assert unknown["validation_state"] == "BLOCKED"
    assert "Position Mode" in unknown["validation_errors"][-1]["errors"][0]


def test_disabled_side_does_not_require_orders_or_active_window():
    result = calculate_configuration(config("ONE_WAY", enabled_short=False), instrument=INSTRUMENT)
    assert result["short"]["orders"] == []
    assert result["short"]["disabled"] is True
    assert result["long"]["status"] == "VALID"
