from __future__ import annotations

from copy import deepcopy
from decimal import ROUND_DOWN, Decimal
from typing import Any

from .capital import capital_snapshot, side_budgets
from .geometry import distribution_vector, geometry_prices
from .sizing import normalized_weights, planned_margin, quantity_for_budget
from .overrides import apply_field_overrides


TRIGGERS = {"ENTRY_PARTIAL_FILL", "ENTRY_FULL_FILL", "TP_PARTIAL_FILL", "TP_FULL_FILL", "MANUAL_PARTIAL_CLOSE", "MANUAL_FULL_CLOSE", "CAPITAL_STATE_CHANGE", "TRAILING_TRIGGER"}


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def generate_side(side: str, *, anchor_price: Decimal, budget: Decimal, order_count: int, grid_depth_pct: Decimal, first_order_offset_pct: Decimal, distribution_coefficient: Decimal, leverage: Decimal, martingale_coefficient: Decimal, instrument: dict[str, object], active_order_count: int, tp_steps: list[dict[str, object]] | None = None) -> dict[str, Any]:
    tick_size = _decimal(instrument["tick_size"])
    qty_step = _decimal(instrument["qty_step"])
    min_order_qty = _decimal(instrument["min_order_qty"])
    distances = distribution_vector(order_count, first_order_offset_pct, grid_depth_pct, distribution_coefficient)
    prices = geometry_prices(anchor_price, side, distances, tick_size)
    quantities = quantity_for_budget(budget, prices, leverage, qty_step, min_order_qty, martingale_coefficient)
    min_notional = _decimal(instrument["min_notional_value"])
    orders = []
    for index, (price, quantity) in enumerate(zip(prices, quantities, strict=True)):
        errors = []
        if quantity < min_order_qty:
            errors.append(f"qty must be >= {min_order_qty}")
        if price * quantity < min_notional:
            errors.append(f"notional must be >= {min_notional}")
        orders.append({"level": index + 1, "status": "VIRTUAL", "source": "ALGORITHM", "entry_price": price, "qty": quantity, "filled_qty": Decimal("0"), "open_qty": Decimal("0"), "closed_qty": Decimal("0"), "remaining_entry_qty": quantity, "actual_avg_fill": None, "strategy_lots": [], "executions": [], "planned_tp": deepcopy(tp_steps or []), "validation_errors": errors})
    return {"side": side, "status": "VIRTUAL", "anchor_price": anchor_price, "martingale_coefficient": martingale_coefficient, "geometry": {"distances_pct": distances, "proportions": [distance / distances[-1] for distance in distances]}, "budget": budget, "planned_margin": planned_margin(prices, quantities, leverage), "active_order_count": min(active_order_count, order_count), "orders": orders, "strategy_lots": [], "executions": []}


def generate_grid(*, account: dict[str, object], configuration: dict[str, Any], instrument: dict[str, object]) -> dict[str, Any]:
    snapshot = capital_snapshot(account)
    allocation = configuration["allocation"]
    long_pct = _decimal(configuration["long"].get("allocation_pct", allocation["long_pct"]))
    short_pct = _decimal(configuration["short"].get("allocation_pct", allocation["short_pct"]))
    reserve_pct = _decimal(allocation["reserve_pct"]) if allocation.get("reserve_pct") not in (None, "") else Decimal("100") - long_pct - short_pct
    budgets = side_budgets(
        snapshot, long_pct, short_pct, reserve_pct,
        long_to_short_reinvestment_pct=_decimal(configuration.get("long_to_short_reinvestment_pct", configuration["long"].get("opposite_upnl_reinvestment_pct", "0"))),
        short_to_long_reinvestment_pct=_decimal(configuration.get("short_to_long_reinvestment_pct", configuration["short"].get("opposite_upnl_reinvestment_pct", "0"))),
        long_unrealized_pnl=_decimal(account.get("long_unrealized_pnl", account.get("unrealized_pnl", "0"))),
        short_unrealized_pnl=_decimal(account.get("short_unrealized_pnl", account.get("unrealized_pnl", "0"))),
    )
    position_mode = str(account.get("position_mode", "UNKNOWN")).upper()
    both_enabled = bool(configuration["long"].get("enabled", True) and configuration["short"].get("enabled", True))
    mode_errors = []
    if both_enabled and position_mode != "HEDGE":
        mode_errors.append("Одновременный Long + Short требует Hedge Mode." if position_mode == "ONE_WAY" else "Не удалось подтвердить Position Mode. Двухсторонняя конфигурация недоступна, пока режим Bybit не подтверждён.")
    result = {"mode": "SHADOW / SIMULATION", "symbol": configuration["symbol"], "position_mode": position_mode, "capital_snapshot": snapshot.as_dict(), "budgets": {key: str(value) for key, value in budgets.items()}, "sides": {}}
    for side in ("long", "short"):
        side_config = configuration[side]
        if side_config.get("enabled", True):
            generated = generate_side(side, anchor_price=_decimal(side_config.get("anchor_price", account["mark_price"])), budget=budgets[side], instrument=instrument, order_count=int(side_config["order_count"]), grid_depth_pct=_decimal(side_config["grid_depth_pct"]), first_order_offset_pct=_decimal(side_config["first_order_offset_pct"]), distribution_coefficient=_decimal(side_config["distribution_coefficient"]), leverage=_decimal(side_config["leverage"]), martingale_coefficient=_decimal(side_config["martingale_coefficient"]), active_order_count=int(side_config["active_order_count"]), tp_steps=side_config.get("tp_steps", []))
            override = apply_field_overrides(generated["orders"], side_config.get("manual_overrides", []), leverage=_decimal(side_config["leverage"]), budget=budgets[side])
            generated["orders"] = override["orders"]
            generated["override_state"] = {"locked_fields": override["locked_fields"], "validation_errors": override["validation_errors"]}
            generated["planned_margin"] = override["planned_margin"]
            if override["status"] == "BLOCKED":
                generated["status"] = "BLOCKED"
            result["sides"][side] = generated
        else:
            result["sides"][side] = {"side": side, "status": "DISABLED", "orders": [], "budget": budgets[side]}
    side_valid = all(side.get("status") == "VIRTUAL" and side["planned_margin"] <= side["budget"] and not any(order.get("validation_errors") for order in side.get("orders", [])) and not side.get("override_state", {}).get("validation_errors") for side in result["sides"].values() if side.get("status") != "DISABLED")
    result["validation"] = {"state": "VALID" if side_valid and not mode_errors else "BLOCKED", "errors": mode_errors}
    return result


def _used_capital(orders: list[dict[str, Any]], leverage: Decimal) -> Decimal:
    return sum((
        _decimal(order.get("filled_qty", "0")) * _decimal(order.get("actual_avg_fill") or order.get("entry_price", "0")) / leverage
        for order in orders if _decimal(order.get("filled_qty", "0")) > 0
    ), Decimal("0"))


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
        _decimal(order.get("entry_price", "0")) * _decimal(order.get("qty", "0")) / leverage
        for order in orders
        if _decimal(order.get("filled_qty", "0")) == 0 and order.get("manual_qty_lock", False)
    ), Decimal("0"))
    auto = [order for order in orders if _decimal(order.get("filled_qty", "0")) == 0 and not order.get("manual_qty_lock", False)]
    auto_budget = max(Decimal("0"), remaining - locked_future)
    prices = [_decimal(order["entry_price"]) for order in auto]
    if auto:
        # This is explicitly a multiplier: 1.20 means the next weight is 1.20x.
        coefficient = _decimal(side.get("martingale_coefficient", side.get("martingale_multiplier", "1.20")))
        weights = normalized_weights(len(auto), coefficient)
        raw = [(auto_budget * weight * leverage / price / qty_step).to_integral_value(rounding=ROUND_DOWN) * qty_step for weight, price in zip(weights, prices, strict=True)]
        for order, qty in zip(auto, raw, strict=True):
            order["qty"] = qty
            order["remaining_entry_qty"] = qty
    side["budget"] = budget
    side["factual_used_capital"] = factual_used
    side["locked_future_manual_capital"] = locked_future
    side["budget_for_auto_levels"] = auto_budget
    side["planned_margin"] = sum((_decimal(order.get("entry_price", "0")) * _decimal(order.get("qty", "0")) / leverage for order in orders), Decimal("0"))
    side["strategy_lots"] = deepcopy(side.get("strategy_lots", []))
    side["executions"] = deepcopy(side.get("executions", []))
    return side


def evaluate_restructuring(current: dict[str, Any], *, trigger: str, account: dict[str, object], configuration: dict[str, Any], instrument: dict[str, object]) -> dict[str, Any]:
    if trigger not in TRIGGERS:
        raise ValueError(f"unsupported restructuring trigger: {trigger}")
    proposed = deepcopy(current)
    snapshot = capital_snapshot(account)
    allocation = configuration["allocation"]
    long_pct = _decimal(configuration["long"].get("allocation_pct", allocation["long_pct"]))
    short_pct = _decimal(configuration["short"].get("allocation_pct", allocation["short_pct"]))
    reserve_pct = _decimal(allocation.get("reserve_pct", Decimal("100") - long_pct - short_pct))
    budgets = side_budgets(snapshot, long_pct, short_pct, reserve_pct,
        long_to_short_reinvestment_pct=_decimal(configuration.get("long_to_short_reinvestment_pct", configuration["long"].get("opposite_upnl_reinvestment_pct", "0"))),
        short_to_long_reinvestment_pct=_decimal(configuration.get("short_to_long_reinvestment_pct", configuration["short"].get("opposite_upnl_reinvestment_pct", "0"))),
        long_unrealized_pnl=_decimal(account.get("long_unrealized_pnl", account.get("unrealized_pnl", "0"))),
        short_unrealized_pnl=_decimal(account.get("short_unrealized_pnl", account.get("unrealized_pnl", "0"))))
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
    changes = []
    for side in ("long", "short"):
        old_orders = current.get("sides", {}).get(side, {}).get("orders", [])
        new_orders = proposed.get("sides", {}).get(side, {}).get("orders", [])
        for old, new in zip(old_orders, new_orders):
            if old.get("qty") != new.get("qty") or old.get("entry_price") != new.get("entry_price"):
                changes.append({"side": side, "level": old.get("level"), "old_entry": old.get("entry_price"), "new_entry": new.get("entry_price"), "old_qty": old.get("qty"), "new_qty": new.get("qty"), "reason": trigger})
    return {"mode": "SHADOW / SIMULATION", "trigger": trigger, "source": "ALGORITHM", "before": current, "after": proposed, "changes": changes, "revision_type": "DYNAMIC_SIZING" if trigger != "TRAILING_TRIGGER" else "TRAILING", "execution": "NOT_SENT"}
