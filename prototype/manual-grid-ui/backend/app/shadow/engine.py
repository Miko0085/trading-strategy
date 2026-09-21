from __future__ import annotations

from copy import deepcopy
from decimal import ROUND_DOWN, Decimal
from typing import Any

from .capital import capital_snapshot, side_budgets
from .geometry import distribution_vector, geometry_prices
from .sizing import normalized_weights, planned_margin, quantity_for_budget
from .overrides import apply_field_overrides
from .reinvestment import calculate_net_realized_profit, realized_reinvest_amount


TRIGGERS = {"ENTRY_PARTIAL_FILL", "ENTRY_FULL_FILL", "TP_PARTIAL_FILL", "TP_FULL_FILL", "MANUAL_PARTIAL_CLOSE", "MANUAL_FULL_CLOSE", "CAPITAL_STATE_CHANGE", "TRAILING_TRIGGER"}


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: object) -> Decimal | None:
    return None if value in (None, "") else _decimal(value)


def _side_reinvest_pct(configuration: dict[str, Any], side: str, field: str) -> Decimal:
    value = configuration.get(side, {}).get(field, configuration.get(field, "0"))
    return _decimal(value or "0")


def _budget_inputs(configuration: dict[str, Any], account: dict[str, object], snapshot: Any, *, previous_state: dict[str, Any] | None = None) -> dict[str, Decimal]:
    allocation = configuration["allocation"]
    long_pct = _decimal(allocation["long_pct"])
    short_pct = _decimal(allocation["short_pct"])
    reserve_pct = _decimal(allocation["reserve_pct"]) if allocation.get("reserve_pct") not in (None, "") else Decimal("100") - long_pct - short_pct
    previous_state = previous_state or {}
    from .capital import side_budgets
    return side_budgets(
        snapshot, long_pct, short_pct, reserve_pct,
        long_unrealized_reinvest_pct=_side_reinvest_pct(configuration, "long", "long_unrealized_reinvest_pct"),
        short_unrealized_reinvest_pct=_side_reinvest_pct(configuration, "short", "short_unrealized_reinvest_pct"),
        long_realized_reinvest_pct=_side_reinvest_pct(configuration, "long", "realized_reinvest_pct"),
        short_realized_reinvest_pct=_side_reinvest_pct(configuration, "short", "realized_reinvest_pct"),
        long_unrealized_pnl=_optional_decimal(account.get("long_unrealized_pnl")),
        short_unrealized_pnl=_optional_decimal(account.get("short_unrealized_pnl")),
        previous_long_strategy_deposit=_optional_decimal(previous_state.get("long_strategy_deposit")),
        previous_short_strategy_deposit=_optional_decimal(previous_state.get("short_strategy_deposit")),
        include_metadata=True,
    )


def generate_side(side: str, *, anchor_price: Decimal, budget: Decimal, order_count: int, grid_depth_pct: Decimal, first_order_offset_pct: Decimal, distribution_coefficient: Decimal, leverage: Decimal, martingale_multiplier: Decimal, instrument: dict[str, object], active_order_count: int, tp_steps: list[dict[str, object]] | None = None) -> dict[str, Any]:
    tick_size = _decimal(instrument["tick_size"])
    qty_step = _decimal(instrument["qty_step"])
    min_order_qty = _decimal(instrument["min_order_qty"])
    distances = distribution_vector(order_count, first_order_offset_pct, grid_depth_pct, distribution_coefficient)
    prices = geometry_prices(anchor_price, side, distances, tick_size)
    quantities = quantity_for_budget(budget, prices, leverage, qty_step, min_order_qty, martingale_multiplier)
    min_notional = _decimal(instrument["min_notional_value"])
    orders = []
    for index, (price, quantity) in enumerate(zip(prices, quantities, strict=True)):
        errors = []
        if quantity < min_order_qty:
            errors.append(f"qty must be >= {min_order_qty}")
        if price * quantity < min_notional:
            errors.append(f"notional must be >= {min_notional}")
        orders.append({"level": index + 1, "status": "VIRTUAL", "source": "ALGORITHM", "entry_price": price, "qty": quantity, "filled_qty": Decimal("0"), "open_qty": Decimal("0"), "closed_qty": Decimal("0"), "remaining_entry_qty": quantity, "actual_avg_fill": None, "strategy_lots": [], "executions": [], "planned_tp": deepcopy(tp_steps or []), "validation_errors": errors})
    return {"side": side, "status": "VIRTUAL", "anchor_price": anchor_price, "martingale_multiplier": martingale_multiplier, "min_notional_value": min_notional, "geometry": {"distances_pct": distances, "proportions": [distance / distances[-1] for distance in distances]}, "budget": budget, "planned_margin": planned_margin(prices, quantities, leverage), "active_order_count": min(active_order_count, order_count), "orders": orders, "strategy_lots": [], "executions": []}


def generate_grid(*, account: dict[str, object], configuration: dict[str, Any], instrument: dict[str, object]) -> dict[str, Any]:
    snapshot = capital_snapshot(account)
    budgets = _budget_inputs(configuration, account, snapshot)
    position_mode = str(account.get("position_mode", "UNKNOWN")).upper()
    both_enabled = bool(configuration["long"].get("enabled", True) and configuration["short"].get("enabled", True))
    mode_errors = []
    if both_enabled and position_mode != "HEDGE":
        mode_errors.append("Одновременный Long + Short требует Hedge Mode." if position_mode == "ONE_WAY" else "Не удалось подтвердить Position Mode. Двухсторонняя конфигурация недоступна, пока режим Bybit не подтверждён.")
    result = {"mode": "SHADOW / SIMULATION", "symbol": configuration["symbol"], "position_mode": position_mode, "capital_snapshot": snapshot.as_dict(), "budgets": {key: str(value) for key, value in budgets.items()}, "sides": {}}
    for side in ("long", "short"):
        side_config = configuration[side]
        if side_config.get("enabled", True):
            generated = generate_side(side, anchor_price=_decimal(side_config.get("anchor_price", account["mark_price"])), budget=budgets[side], instrument=instrument, order_count=int(side_config["order_count"]), grid_depth_pct=_decimal(side_config["grid_depth_pct"]), first_order_offset_pct=_decimal(side_config["first_order_offset_pct"]), distribution_coefficient=_decimal(side_config["distribution_coefficient"]), leverage=_decimal(side_config["leverage"]), martingale_multiplier=_decimal(side_config.get("martingale_multiplier", side_config.get("martingale_coefficient", "1.20"))), active_order_count=int(side_config["active_order_count"]), tp_steps=side_config.get("tp_steps", []))
            override = apply_field_overrides(generated["orders"], side_config.get("manual_overrides", []), leverage=_decimal(side_config["leverage"]), budget=budgets[side])
            generated["orders"] = override["orders"]
            generated["override_state"] = {"locked_fields": override["locked_fields"], "validation_errors": override["validation_errors"]}
            generated["planned_margin"] = override["planned_margin"]
            if override["status"] == "BLOCKED":
                generated["status"] = "BLOCKED"
            generated["validation_state"] = "BLOCKED" if generated["status"] == "BLOCKED" or any(order.get("validation_errors") for order in generated["orders"]) else "VALID"
            result["sides"][side] = generated
        else:
            result["sides"][side] = {"side": side, "status": "DISABLED", "orders": [], "budget": budgets[side]}
    side_valid = all(side.get("status") == "VIRTUAL" and side["planned_margin"] <= side["budget"] and not any(order.get("validation_errors") for order in side.get("orders", [])) and not side.get("override_state", {}).get("validation_errors") for side in result["sides"].values() if side.get("status") != "DISABLED")
    result["validation"] = {"state": "VALID" if side_valid and not mode_errors else "BLOCKED", "errors": mode_errors}
    result["strategy_state"] = {
        "long_strategy_deposit": str(budgets["long_strategy_deposit"]),
        "short_strategy_deposit": str(budgets["short_strategy_deposit"]),
        "cumulative_realized_reinvest": {"long": "0", "short": "0"},
        "applied_reinvest_execution_ids": [],
        "reinvest_audit": [],
    }
    result["shadow_summary"] = {
        side: {
            "base_budget": str(budgets[f"base_{side}_budget"]),
            "strategy_deposit": str(budgets[f"{side}_strategy_deposit"]),
            "cumulative_realized_reinvest": "0",
            "current_unrealized_boost": str(budgets[f"{side}_unrealized_boost"]),
            "effective_budget": str(budgets[side]),
        }
        for side in ("long", "short")
    }
    return result


def _used_capital(orders: list[dict[str, Any]], leverage: Decimal) -> Decimal:
    return sum((
        max(Decimal("0"), _decimal(order.get("open_qty", _decimal(order.get("filled_qty", "0")) - _decimal(order.get("closed_qty", "0"))))) * _decimal(order.get("actual_avg_fill") or order.get("entry_price", "0")) / leverage
        for order in orders if _decimal(order.get("filled_qty", "0")) > 0
    ), Decimal("0"))


def is_future_resizable(order: dict[str, Any]) -> bool:
    """Only future intent may be resized; factual fills and manual locks stay fixed."""
    filled = _decimal(order.get("filled_qty", "0"))
    target = _decimal(order.get("configured_qty", order.get("qty", "0")))
    return not order.get("manual_qty_lock", False) and filled < target


def _restructure_side(side_state: dict[str, Any], *, budget: Decimal, leverage: Decimal, qty_step: Decimal, min_order_qty: Decimal, trigger: str, new_anchor: Decimal | None, tick_size: Decimal) -> dict[str, Any]:
    """Resize the existing state; never manufacture a new factual grid."""
    side = deepcopy(side_state)
    orders = side.setdefault("orders", [])
    if trigger == "TRAILING_TRIGGER" and new_anchor is not None:
        # Import at module level so this is the sole trailing entry point.
        from .trailing import trail_pending_grid
        trail_pending_grid(side, new_anchor=new_anchor, tick_size=tick_size)

    factual_used = _used_capital(orders, leverage)
    remaining = max(Decimal("0"), budget - factual_used)
    locked_future = sum((
        _decimal(order.get("entry_price", "0")) * max(Decimal("0"), _decimal(order.get("qty", "0")) - _decimal(order.get("filled_qty", "0"))) / leverage
        for order in orders
        if is_future_resizable(order) is False and _decimal(order.get("filled_qty", "0")) < _decimal(order.get("qty", "0")) and order.get("manual_qty_lock", False)
    ), Decimal("0"))
    auto = [order for order in orders if is_future_resizable(order)]
    auto_budget = max(Decimal("0"), remaining - locked_future)
    prices = [_decimal(order["entry_price"]) for order in auto]
    if auto:
        # This is explicitly a multiplier: 1.20 means the next weight is 1.20x.
        coefficient = _decimal(side.get("martingale_multiplier", side.get("martingale_coefficient", "1.20")))
        weights = normalized_weights(len(auto), coefficient)
        raw = [(auto_budget * weight * leverage / price / qty_step).to_integral_value(rounding=ROUND_DOWN) * qty_step for weight, price in zip(weights, prices, strict=True)]
        for order, future_qty in zip(auto, raw, strict=True):
            filled = _decimal(order.get("filled_qty", "0"))
            order["qty"] = filled + future_qty
            order["configured_qty"] = filled + future_qty
            order["remaining_entry_qty"] = future_qty
    errors: list[str] = []
    if locked_future > remaining:
        errors.append("Ручные future-ордера превышают доступный budget стороны.")
    min_notional = _decimal(side.get("min_notional_value", "0"))
    for order in orders:
        future_qty = max(Decimal("0"), _decimal(order.get("qty", "0")) - _decimal(order.get("filled_qty", "0")))
        if future_qty <= 0:
            continue
        order_errors: list[str] = []
        if (future_qty / qty_step).to_integral_value() * qty_step != future_qty:
            order_errors.append(f"qty must follow qtyStep {qty_step}")
        if future_qty < min_order_qty:
            order_errors.append(f"qty must be >= {min_order_qty}")
        if min_notional and _decimal(order.get("entry_price", "0")) * future_qty < min_notional:
            order_errors.append(f"notional must be >= {min_notional}")
        order["validation_errors"] = order_errors
        errors.extend([f"Level {order.get('level')}: {item}" for item in order_errors])
    side["budget"] = budget
    side["factual_used_capital"] = factual_used
    side["locked_future_manual_capital"] = locked_future
    side["budget_for_auto_levels"] = auto_budget
    side["planned_margin"] = sum((_decimal(order.get("entry_price", "0")) * _decimal(order.get("qty", "0")) / leverage for order in orders), Decimal("0"))
    side["strategy_lots"] = deepcopy(side.get("strategy_lots", []))
    side["executions"] = deepcopy(side.get("executions", []))
    side["validation_state"] = "BLOCKED" if errors else "VALID"
    side["validation_errors"] = errors
    side["status"] = "BLOCKED" if errors else side.get("status", "VIRTUAL")
    return side


def evaluate_restructuring(current: dict[str, Any], *, trigger: str, account: dict[str, object], configuration: dict[str, Any], instrument: dict[str, object]) -> dict[str, Any]:
    if trigger not in TRIGGERS:
        raise ValueError(f"unsupported restructuring trigger: {trigger}")
    proposed = deepcopy(current)
    snapshot = capital_snapshot(account)
    budgets = _budget_inputs(configuration, account, snapshot, previous_state=current.get("strategy_state"))
    for side_name in ("long", "short"):
        side_config = configuration[side_name]
        if not side_config.get("enabled", True):
            continue
        current_side = proposed.setdefault("sides", {}).setdefault(side_name, {"side": side_name, "orders": []})
        proposed["sides"][side_name] = _restructure_side(
            current_side, budget=budgets[side_name], leverage=_decimal(side_config["leverage"]),
            qty_step=_decimal(instrument["qty_step"]), min_order_qty=_decimal(instrument["min_order_qty"]),
            trigger=trigger, new_anchor=_decimal(side_config.get("anchor_price", account["mark_price"])) if trigger == "TRAILING_TRIGGER" else None,
            tick_size=_decimal(instrument["tick_size"]),)
    proposed["capital_snapshot"] = snapshot.as_dict()
    proposed["budgets"] = {key: str(value) for key, value in budgets.items()}
    state = proposed.setdefault("strategy_state", {})
    state.setdefault("applied_reinvest_execution_ids", [])
    state.setdefault("reinvest_audit", [])
    state["long_strategy_deposit"] = str(budgets["long_strategy_deposit"])
    state["short_strategy_deposit"] = str(budgets["short_strategy_deposit"])
    cumulative = state.get("cumulative_realized_reinvest", {"long": "0", "short": "0"})
    proposed["shadow_summary"] = {
        side: {
            "base_budget": str(budgets[f"base_{side}_budget"]),
            "strategy_deposit": str(budgets[f"{side}_strategy_deposit"]),
            "cumulative_realized_reinvest": str(cumulative.get(side, "0")),
            "current_unrealized_boost": str(budgets[f"{side}_unrealized_boost"]),
            "effective_budget": str(budgets[side]),
        }
        for side in ("long", "short")
    }
    side_errors = [error for side in proposed.get("sides", {}).values() for error in side.get("validation_errors", [])]
    proposed["validation"] = {"state": "BLOCKED" if side_errors else "VALID", "errors": side_errors}
    changes = []
    for side in ("long", "short"):
        old_orders = current.get("sides", {}).get(side, {}).get("orders", [])
        new_orders = proposed.get("sides", {}).get(side, {}).get("orders", [])
        for old, new in zip(old_orders, new_orders):
            if old.get("qty") != new.get("qty") or old.get("entry_price") != new.get("entry_price"):
                changes.append({"side": side, "level": old.get("level"), "old_entry": old.get("entry_price"), "new_entry": new.get("entry_price"), "old_qty": old.get("qty"), "new_qty": new.get("qty"), "reason": trigger})
    return {"mode": "SHADOW / SIMULATION", "trigger": trigger, "source": "ALGORITHM", "before": current, "after": proposed, "changes": changes, "revision_type": "DYNAMIC_SIZING" if trigger != "TRAILING_TRIGGER" else "TRAILING", "execution": "NOT_SENT"}


def _execution_side(execution: dict[str, Any]) -> str | None:
    raw_side = str(execution.get("side", "")).lower()
    if raw_side in {"buy", "long"} or str(execution.get("position_idx", execution.get("positionIdx", ""))) == "1":
        return "long"
    if raw_side in {"sell", "short"} or str(execution.get("position_idx", execution.get("positionIdx", ""))) == "2":
        return "short"
    return None


def apply_realized_execution(current: dict[str, Any], *, execution: dict[str, Any], configuration: dict[str, Any]) -> dict[str, Any]:
    """Apply one factual close execution to persistent shadow accounting.

    This is intentionally separate from entry fills: only close/TP/manual-close
    triggers can increase StrategyDeposit.
    """
    result = deepcopy(current)
    state = result.setdefault("strategy_state", {})
    applied = state.setdefault("applied_reinvest_execution_ids", [])
    audit = state.setdefault("reinvest_audit", [])
    execution_id = execution.get("execution_id", execution.get("execId"))
    if not execution_id or execution_id in applied:
        return result
    trigger = str(execution.get("trigger", ""))
    close_triggers = {"TP_PARTIAL_FILL", "TP_FULL_FILL", "MANUAL_PARTIAL_CLOSE", "MANUAL_FULL_CLOSE"}
    if trigger not in close_triggers:
        return result
    side = _execution_side(execution)
    if side is None:
        return result
    pnl_value = _optional_decimal(execution.get("realized_pnl", execution.get("execPnl")))
    fee = _optional_decimal(execution.get("fee", execution.get("execFee")))
    pnl = calculate_net_realized_profit(pnl_value, fee, realized_pnl_is_net=bool(execution.get("realized_pnl_is_net", execution.get("execPnlIsNet", False))))
    net_profit = pnl["net_realized_profit"]
    reinvest_pct = _decimal(configuration.get(side, {}).get("realized_reinvest_pct", "0") or "0")
    previous = _decimal(state.get(f"{side}_strategy_deposit", result.get("budgets", {}).get(side, "0")))
    reinvest_amount = realized_reinvest_amount(net_profit if isinstance(net_profit, Decimal) else None, reinvest_pct)
    new_deposit = previous + reinvest_amount
    state[f"{side}_strategy_deposit"] = str(new_deposit)
    state.setdefault("cumulative_realized_reinvest", {"long": "0", "short": "0"})
    state["cumulative_realized_reinvest"][side] = str(_decimal(state["cumulative_realized_reinvest"].get(side, "0")) + reinvest_amount)
    applied.append(execution_id)
    audit.append({"side": side, "execution_id": execution_id, "previous_strategy_deposit": str(previous), "gross_realized_pnl": pnl["gross_realized_pnl"], "fee": pnl["fee"], "net_realized_profit": net_profit, "reinvest_pct": reinvest_pct, "reinvest_amount": reinvest_amount, "new_strategy_deposit": new_deposit, "timestamp": execution.get("timestamp")})
    summary = result.setdefault("shadow_summary", {}).setdefault(side, {})
    summary["strategy_deposit"] = str(new_deposit)
    summary["cumulative_realized_reinvest"] = state["cumulative_realized_reinvest"][side]
    summary["effective_budget"] = str(new_deposit + _decimal(summary.get("current_unrealized_boost", "0")))
    result["strategy_state"] = state
    return result
