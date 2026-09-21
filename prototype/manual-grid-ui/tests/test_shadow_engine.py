from decimal import Decimal

from app.shadow.capital import capital_snapshot, side_budgets
from app.shadow.engine import evaluate_restructuring, generate_grid
from app.shadow.geometry import distribution_vector, geometry_proportions
from app.shadow.lots import apply_fill, tp_prices, tp_quantities
from app.shadow.sizing import normalized_weights, planned_margin, quantity_for_budget
from app.shadow.overrides import apply_field_overrides
from app.shadow.trailing import trail_pending_grid


INSTRUMENT = {"tick_size": "0.1", "qty_step": "0.1", "min_order_qty": "0.1", "min_notional_value": "5"}


def configuration():
    side = {"enabled": True, "order_count": 10, "grid_depth_pct": "30", "first_order_offset_pct": "5", "distribution_coefficient": "1.5", "leverage": "2", "martingale_coefficient": "1.2", "active_order_count": 3, "tp_steps": [{"move_pct": "10", "close_pct": "50"}], "trailing_enabled": False}
    return {"symbol": "BTCUSDT", "allocation": {"long_pct": "30", "short_pct": "20", "reserve_pct": "50"}, "long": side, "short": {**side, "enabled": False}}


def account(available="1000"):
    return {"mark_price": "100", "wallet_balance": "1000", "equity": "1000", "available_margin": available, "realized_pnl": "0", "unrealized_pnl": "0"}


def test_geometry_supports_one_ten_and_large_counts_and_mirrors():
    for count in (1, 10, 37):
        values = distribution_vector(count, Decimal("5"), Decimal("30"), Decimal("1.5"))
        assert len(values) == count and values[0] == Decimal("5") and values[-1] == (Decimal("5") if count == 1 else Decimal("30"))
        assert geometry_proportions(values)[-1] == Decimal("1")


def test_sizing_is_normalized_and_preserves_relative_curve_under_budget_changes():
    prices = [Decimal("95"), Decimal("90"), Decimal("85")]
    for budget in (Decimal("700"), Decimal("1000"), Decimal("1300")):
        quantities = quantity_for_budget(budget, prices, Decimal("2"), Decimal("0.1"), Decimal("0.1"), Decimal("1.2"))
        assert planned_margin(prices, quantities, Decimal("2")) <= budget
    assert normalized_weights(3, Decimal("1.2"))[2] > normalized_weights(3, Decimal("1.2"))[0]


def test_capital_policy_uses_factual_available_margin_and_keeps_reserve():
    snapshot = capital_snapshot(account("1200"))
    budgets = side_budgets(snapshot, Decimal("30"), Decimal("20"), Decimal("50"))
    assert budgets == {"long": Decimal("360"), "short": Decimal("240"), "reserve": Decimal("600")}


def test_generated_long_grid_is_virtual_and_short_is_independent():
    result = generate_grid(account=account(), configuration=configuration(), instrument=INSTRUMENT)
    assert result["mode"] == "SHADOW / SIMULATION"
    assert result["sides"]["long"]["orders"][0]["status"] == "VIRTUAL"
    assert result["sides"]["short"]["status"] == "DISABLED"
    assert result["sides"]["long"]["planned_margin"] <= result["sides"]["long"]["budget"]


def test_partial_fill_and_tp_use_open_factual_quantity():
    lot = {"configured_qty": Decimal("200"), "filled_qty": Decimal("0"), "closed_qty": Decimal("0")}
    apply_fill(lot, Decimal("40"), Decimal("100")); apply_fill(lot, Decimal("55"), Decimal("105"))
    assert lot["filled_qty"] == Decimal("95")
    assert tp_quantities(lot["open_qty"], [Decimal("50")]) == [Decimal("47.5")]
    assert tp_prices(lot["actual_avg_fill"], "long", [Decimal("10")], Decimal("0.1")) == [Decimal("113.2")]


def test_restructuring_returns_before_after_shadow_proposal_without_execution():
    current = generate_grid(account=account("1000"), configuration=configuration(), instrument=INSTRUMENT)
    changed = evaluate_restructuring(current, trigger="CAPITAL_STATE_CHANGE", account=account("700"), configuration=configuration(), instrument=INSTRUMENT)
    assert changed["revision_type"] == "DYNAMIC_SIZING"
    assert changed["execution"] == "NOT_SENT"
    assert changed["changes"]


def test_trailing_moves_pending_entries_and_planned_tp_but_not_filled_lot():
    grid = generate_grid(account=account(), configuration=configuration(), instrument=INSTRUMENT)["sides"]["long"]
    grid["orders"][0]["planned_tp"] = [{"move_pct": "10"}]
    grid["orders"][1]["filled_qty"] = Decimal("1")
    old_filled_price = grid["orders"][1]["entry_price"]
    trail_pending_grid(grid, new_anchor=Decimal("105"), tick_size=Decimal("0.1"))
    assert grid["orders"][0]["entry_price"] != old_filled_price
    assert grid["orders"][0]["planned_tp"][0]["price"] is not None
    assert grid["orders"][1]["entry_price"] != grid["orders"][0]["entry_price"]


def test_manual_locked_qty_is_preserved_and_budget_violation_blocks():
    orders = [{"level": 1, "entry_price": Decimal("100"), "qty": Decimal("1")}, {"level": 2, "entry_price": Decimal("100"), "qty": Decimal("1")}]
    result = apply_field_overrides(orders, [{"level": 1, "field": "qty", "value": "10"}], leverage=Decimal("1"), budget=Decimal("500"))
    assert result["orders"][0]["qty"] == Decimal("10")
    assert result["orders"][0]["manual_qty_lock"] is True
    assert result["status"] == "BLOCKED"
