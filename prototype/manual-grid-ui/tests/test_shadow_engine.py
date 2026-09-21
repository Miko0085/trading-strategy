from decimal import Decimal

from app.shadow.capital import capital_snapshot, side_budgets
from app.shadow.engine import apply_realized_execution, evaluate_restructuring, generate_grid
from app.shadow.geometry import distribution_vector, geometry_proportions
from app.shadow.lots import apply_fill, tp_prices, tp_quantities
from app.shadow.sizing import normalized_weights, planned_margin, quantity_for_budget
from app.shadow.overrides import apply_field_overrides
from app.shadow.trailing import trail_pending_grid
from app.shadow.reinvestment import calculate_effective_side_budget, calculate_net_realized_profit, next_strategy_deposit, realized_reinvest_amount


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


def test_allocation_can_leave_capital_unallocated_and_extras_are_directional_and_guarded():
    snapshot = capital_snapshot(account("1000"))
    budgets = side_budgets(snapshot, Decimal("20"), Decimal("20"), Decimal("40"), long_to_short_reinvestment_pct=Decimal("10"), short_to_long_reinvestment_pct=Decimal("20"), long_unrealized_pnl=Decimal("500"), short_unrealized_pnl=Decimal("100"))
    assert budgets["long"] + budgets["short"] + budgets["reserve"] <= Decimal("1000")
    assert budgets["reserve"] == Decimal("400")
    assert budgets["long_extra"] == Decimal("20")  # Short uPnL * short_to_long
    assert budgets["short_extra"] == Decimal("50")  # Long uPnL * long_to_short


def test_non_trailing_restructure_preserves_prices_and_factual_lot_and_deducts_used_capital():
    current = generate_grid(account=account("1000"), configuration=configuration(), instrument=INSTRUMENT)
    order = current["sides"]["long"]["orders"][0]
    apply_fill(order, Decimal("1"), Decimal("95"))
    order["closed_qty"] = Decimal("0.25")
    order["strategy_lots"] = [{"lot_id": "lot-1", "filled_qty": "1"}]
    order["executions"] = [{"execution_id": "exec-1"}]
    before_prices = [item["entry_price"] for item in current["sides"]["long"]["orders"]]
    result = evaluate_restructuring(current, trigger="CAPITAL_STATE_CHANGE", account=account("700"), configuration=configuration(), instrument=INSTRUMENT)
    after = result["after"]["sides"]["long"]
    assert [item["entry_price"] for item in after["orders"]] == before_prices
    assert after["orders"][0]["filled_qty"] == Decimal("1")
    assert after["orders"][0]["closed_qty"] == Decimal("0.25")
    assert after["orders"][0]["actual_avg_fill"] == Decimal("95")
    assert after["orders"][0]["strategy_lots"] == [{"lot_id": "lot-1", "filled_qty": "1"}]
    assert after["orders"][0]["executions"] == [{"execution_id": "exec-1"}]
    assert after["factual_used_capital"] == Decimal("47.5")


def test_partial_fill_survives_a_second_restructuring():
    current = generate_grid(account=account("1000"), configuration=configuration(), instrument=INSTRUMENT)
    order = current["sides"]["long"]["orders"][0]
    apply_fill(order, Decimal("0.4"), Decimal("95"))
    first = evaluate_restructuring(current, trigger="ENTRY_PARTIAL_FILL", account=account("900"), configuration=configuration(), instrument=INSTRUMENT)["after"]
    second = evaluate_restructuring(first, trigger="CAPITAL_STATE_CHANGE", account=account("800"), configuration=configuration(), instrument=INSTRUMENT)["after"]
    preserved = second["sides"]["long"]["orders"][0]
    assert preserved["filled_qty"] == Decimal("0.4")
    assert preserved["open_qty"] == Decimal("0.4")
    assert preserved["actual_avg_fill"] == Decimal("95")


def test_locked_future_capital_is_reserved_before_auto_normalization():
    current = generate_grid(account=account("1000"), configuration=configuration(), instrument=INSTRUMENT)
    orders = current["sides"]["long"]["orders"]
    orders[0]["manual_qty_lock"] = True
    orders[0]["qty"] = Decimal("2")
    result = evaluate_restructuring(current, trigger="CAPITAL_STATE_CHANGE", account=account("1000"), configuration=configuration(), instrument=INSTRUMENT)
    side = result["after"]["sides"]["long"]
    assert side["locked_future_manual_capital"] == orders[0]["entry_price"]
    assert side["budget_for_auto_levels"] == side["budget"] - side["locked_future_manual_capital"]
    auto_margin = sum((item["entry_price"] * item["qty"] / Decimal("2") for item in side["orders"][1:]), Decimal("0"))
    assert auto_margin <= side["budget_for_auto_levels"]


def test_trailing_only_moves_pending_entries_and_keeps_filled_entry_fixed():
    current = generate_grid(account=account("1000"), configuration=configuration(), instrument=INSTRUMENT)
    filled = current["sides"]["long"]["orders"][0]
    apply_fill(filled, Decimal("1"), Decimal("95"))
    old_filled_price = filled["entry_price"]
    old_pending_prices = [item["entry_price"] for item in current["sides"]["long"]["orders"][1:]]
    trailing_configuration = configuration()
    trailing_configuration["long"]["anchor_price"] = "105"
    result = evaluate_restructuring(current, trigger="TRAILING_TRIGGER", account=account("1000"), configuration=trailing_configuration, instrument=INSTRUMENT)
    after_orders = result["after"]["sides"]["long"]["orders"]
    assert after_orders[0]["entry_price"] == old_filled_price
    assert [item["entry_price"] for item in after_orders[1:]] != old_pending_prices


def test_planned_tp_templates_are_not_shared_between_grid_orders():
    grid = generate_grid(account=account(), configuration=configuration(), instrument=INSTRUMENT)["sides"]["long"]
    grid["orders"][0]["planned_tp"][0]["move_pct"] = "99"
    assert grid["orders"][1]["planned_tp"][0]["move_pct"] == "10"


def test_partial_close_frees_factual_used_capital():
    current = generate_grid(account=account("1000"), configuration=configuration(), instrument=INSTRUMENT)
    order = current["sides"]["long"]["orders"][0]
    order.update({"filled_qty": Decimal("100"), "closed_qty": Decimal("50"), "open_qty": Decimal("50"), "actual_avg_fill": Decimal("100")})
    result = evaluate_restructuring(current, trigger="TP_PARTIAL_FILL", account=account("1000"), configuration=configuration(), instrument=INSTRUMENT)
    assert result["after"]["sides"]["long"]["factual_used_capital"] == Decimal("2500")


def test_locked_future_over_budget_blocks_instead_of_clamping():
    current = generate_grid(account=account("1000"), configuration=configuration(), instrument=INSTRUMENT)
    order = current["sides"]["long"]["orders"][0]
    order["manual_qty_lock"] = True
    order["qty"] = Decimal("1000")
    result = evaluate_restructuring(current, trigger="CAPITAL_STATE_CHANGE", account=account("100"), configuration=configuration(), instrument=INSTRUMENT)
    assert result["after"]["sides"]["long"]["validation_state"] == "BLOCKED"
    assert "Ручные future-ордера" in result["after"]["sides"]["long"]["validation_errors"][0]
    assert result["after"]["validation"]["state"] == "BLOCKED"


def test_realized_deposit_is_persistent_but_unrealized_boost_is_temporary_and_capped():
    assert realized_reinvest_amount(Decimal("100"), Decimal("50")) == Decimal("50")
    assert realized_reinvest_amount(Decimal("-100"), Decimal("50")) == Decimal("0")
    assert next_strategy_deposit(Decimal("3000"), Decimal("100"), Decimal("50")) == Decimal("3050")
    result = calculate_effective_side_budget(capital_base=Decimal("10000"), long_pct=Decimal("30"), short_pct=Decimal("30"), reserve_pct=Decimal("30"), long_unrealized_pnl=Decimal("1000"), short_unrealized_pnl=Decimal("1000"), long_unrealized_reinvest_pct=Decimal("100"), short_unrealized_reinvest_pct=Decimal("100"))
    assert result["reserve"] == Decimal("3000")
    assert result["long"] + result["short"] <= Decimal("7000")


def test_net_realized_profit_requires_explicit_fee_semantics():
    assert calculate_net_realized_profit(Decimal("100"), Decimal("2")) ["net_realized_profit"] == Decimal("98")
    assert calculate_net_realized_profit(Decimal("98"), Decimal("2"), realized_pnl_is_net=True)["net_realized_profit"] == Decimal("98")
    assert calculate_net_realized_profit(Decimal("100"), None)["net_realized_profit"] is None


def test_realized_close_updates_persistent_deposit_and_deduplicates_execution():
    current = generate_grid(account=account(), configuration=configuration(), instrument=INSTRUMENT)
    config = configuration()
    config["long"]["realized_reinvest_pct"] = "50"
    execution = {"execution_id": "close-1", "side": "Buy", "trigger": "TP_PARTIAL_FILL", "realized_pnl": "100", "fee": "0"}
    first = apply_realized_execution(current, execution=execution, configuration=config)
    assert first["strategy_state"]["long_strategy_deposit"] == "350"
    replay = apply_realized_execution(first, execution=execution, configuration=config)
    assert replay["strategy_state"]["long_strategy_deposit"] == "350"
    assert len(replay["strategy_state"]["reinvest_audit"]) == 1


def test_realized_reinvest_is_side_specific_and_negative_profit_does_not_change_deposit():
    current = generate_grid(account=account(), configuration=configuration(), instrument=INSTRUMENT)
    config = configuration()
    config["long"]["realized_reinvest_pct"] = "50"
    negative = apply_realized_execution(current, execution={"execution_id": "close-2", "side": "Buy", "trigger": "MANUAL_FULL_CLOSE", "realized_pnl": "-100", "fee": "0"}, configuration=config)
    assert negative["strategy_state"]["long_strategy_deposit"] == "300"
    short = apply_realized_execution(negative, execution={"execution_id": "close-3", "side": "Sell", "trigger": "TP_FULL_FILL", "realized_pnl": "100", "fee": "0"}, configuration=config)
    assert short["strategy_state"]["short_strategy_deposit"] == "200"
    assert short["strategy_state"]["long_strategy_deposit"] == "300"


def test_restructuring_starts_from_persisted_strategy_deposit():
    current = generate_grid(account=account(), configuration=configuration(), instrument=INSTRUMENT)
    config = configuration()
    config["allocation"]["reserve_pct"] = "20"
    config["long"]["realized_reinvest_pct"] = "50"
    current = apply_realized_execution(current, execution={"execution_id": "close-4", "side": "Buy", "trigger": "TP_FULL_FILL", "realized_pnl": "100", "fee": "0"}, configuration=config)
    revised = evaluate_restructuring(current, trigger="CAPITAL_STATE_CHANGE", account=account(), configuration=config, instrument=INSTRUMENT)["after"]
    assert revised["strategy_state"]["long_strategy_deposit"] == "350"
    assert revised["shadow_summary"]["long"]["strategy_deposit"] == "350"


def test_canonical_unrealized_direction_uses_opposite_side_only():
    snapshot = capital_snapshot(account("1000"))
    budgets = side_budgets(snapshot, Decimal("20"), Decimal("20"), Decimal("40"), long_unrealized_reinvest_pct=Decimal("10"), short_unrealized_reinvest_pct=Decimal("20"), long_unrealized_pnl=Decimal("100"), short_unrealized_pnl=Decimal("500"))
    assert budgets["long"] - Decimal("200") == Decimal("50")
    assert budgets["short"] - Decimal("200") == Decimal("20")


def test_generated_side_allocation_is_ignored_in_favor_of_global_policy_and_old_multiplier_loads():
    config = configuration()
    config["long"]["allocation_pct"] = "99"
    config["long"]["martingale_coefficient"] = "1.5"
    result = generate_grid(account=account(), configuration=config, instrument=INSTRUMENT)
    assert result["sides"]["long"]["budget"] == Decimal("300")
    assert result["sides"]["long"]["martingale_multiplier"] == Decimal("1.5")
