from decimal import Decimal

import pytest

from app.account_state import normalize_account, normalize_instrument, normalize_positions
from app.active_window import ActiveWindowPolicy
from app.calculations import calculate_configuration


INSTRUMENT = {"tick_size": "0.1", "qty_step": "1", "min_order_qty": "1", "min_notional_value": "5"}


def config(**overrides):
    value = {"symbol": "BTCUSDT", "mark_price": "100", "available_margin": "1000", "leverage": "2", "fee_rate": None, "allocation": {"long_pct": "40", "short_pct": "20", "reserve_pct": "40"}, "active_long_count": 1, "active_short_count": 1, "long": [{"offset_pct": "10", "qty": "10", "filled_qty": "0", "tps": [{"move_pct": "10", "close_pct": "25"}]}], "short": [{"offset_pct": "10", "qty": "10", "filled_qty": "0", "tps": [{"move_pct": "10", "close_pct": "25"}]}]}
    value.update(overrides)
    return value


def test_tp_close_percentage_changes_quantity_and_pnl():
    result = calculate_configuration(config(), instrument=INSTRUMENT)
    tp = result["long"]["orders"][0]["tp_steps"][0]
    assert tp["qty"] == Decimal("2.5")
    assert tp["gross_pnl"] == Decimal("22.5")


def test_tp_uses_actual_average_fill():
    payload = config(long=[{"offset_pct": "10", "qty": "10", "filled_qty": "4", "avg_fill_price": "95", "tps": [{"move_pct": "10", "close_pct": "50"}]}])
    result = calculate_configuration(payload, instrument=INSTRUMENT)
    tp = result["long"]["orders"][0]["tp_steps"][0]
    assert tp["basis"] == "actual_fill"
    assert tp["price"] == Decimal("104.5")
    assert tp["qty"] == Decimal("2")


def test_tp_sum_over_one_hundred_blocks_side():
    payload = config(long=[{"offset_pct": "10", "qty": "10", "filled_qty": "0", "tps": [{"move_pct": "2", "close_pct": "60"}, {"move_pct": "3", "close_pct": "50"}]}])
    result = calculate_configuration(payload, instrument=INSTRUMENT)
    assert result["long"]["status"] == "BLOCKED"


def test_active_window_progresses_after_completion():
    policy = ActiveWindowPolicy(20, 5)
    assert policy.active_levels() == [1, 2, 3, 4, 5]
    assert policy.active_levels({1}) == [2, 3, 4, 5, 6]
    assert policy.queued_levels({1})[:2] == [7, 8]


def test_instrument_metadata_is_normalized_without_defaults():
    result = normalize_instrument({"list": [{"symbol": "BTCUSDT", "lotSizeFilter": {"qtyStep": "0.001", "minOrderQty": "0.001", "minNotionalValue": "5"}, "priceFilter": {"tickSize": "0.1"}}]})
    assert result == {"symbol": "BTCUSDT", "tick_size": "0.1", "qty_step": "0.001", "min_order_qty": "0.001", "min_notional_value": "5"}


def test_hedge_positions_are_normalized_to_long_short():
    result = normalize_positions({"list": [{"symbol": "BTCUSDT", "side": "Buy", "positionIdx": 1, "size": "2", "avgPrice": "100", "unrealisedPnl": "3", "leverage": "5"}, {"symbol": "BTCUSDT", "side": "Sell", "positionIdx": 2, "size": "1", "avgPrice": "110", "unrealisedPnl": "-2", "leverage": "3"}]}, "105")
    assert [item["side"] for item in result] == ["long", "short"]
    assert result[0]["notional"] == "210"


def test_normalized_account_keeps_actual_averages_and_exposure():
    result = normalize_account({"list": [{"totalWalletBalance": "1000", "totalEquity": "1010", "totalAvailableBalance": "800"}]}, {"list": [{"side": "Buy", "positionIdx": 1, "size": "2", "avgPrice": "100"}, {"side": "Sell", "positionIdx": 2, "size": "1", "avgPrice": "110"}]}, {"list": []}, {"list": [{"symbol": "BTCUSDT", "markPrice": "105"}]}, {"symbol": "BTCUSDT"}, "bybit_read_only")
    assert result["long"]["avg_entry_price"] == "100"
    assert result["short"]["avg_entry_price"] == "110"
    assert result["gross_exposure"] == "315"
    assert result["net_exposure"] == "105"


def test_missing_side_size_does_not_become_fake_zero():
    result = normalize_account({"list": []}, {"list": [{"side": "Buy", "positionIdx": 1, "avgPrice": "100"}]}, {"list": []}, {"list": [{"symbol": "BTCUSDT", "markPrice": "105"}]}, {"symbol": "BTCUSDT"}, "bybit_read_only")
    assert result["long"]["size"] is None
    assert result["gross_exposure"] is None
