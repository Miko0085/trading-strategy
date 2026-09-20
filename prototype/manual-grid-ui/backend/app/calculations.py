from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

from .active_window import ActiveWindowPolicy


ZERO = Decimal("0")


def D(value: object) -> Decimal:
    return Decimal(str(value))


def required_decimal(item: dict[str, Any], key: str) -> Decimal:
    value = item.get(key)
    if value is None or str(value) == "":
        raise ValueError(f"{key} is required")
    return D(value)


def quantize_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= ZERO:
        raise ValueError("step must be positive")
    return (value / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step


def entry_prices(mark_price: Decimal, side: str, offsets_pct: Iterable[Decimal], tick_size: Decimal) -> list[Decimal]:
    previous = mark_price
    result: list[Decimal] = []
    for offset in offsets_pct:
        fraction = abs(offset) / Decimal("100")
        raw = previous * (Decimal("1") - fraction if side == "long" else Decimal("1") + fraction)
        previous = quantize_step(raw, tick_size)
        result.append(previous)
    return result


def weighted_average(fills: Iterable[tuple[Decimal, Decimal]]) -> Decimal | None:
    total_qty = sum((qty for qty, _ in fills), ZERO)
    if total_qty == ZERO:
        return None
    return sum((qty * price for qty, price in fills), ZERO) / total_qty


def notional(price: Decimal, qty: Decimal) -> Decimal:
    return price * qty


def estimated_margin(price: Decimal, qty: Decimal, leverage: Decimal) -> Decimal:
    if leverage <= ZERO:
        raise ValueError("leverage must be positive")
    return notional(price, qty) / leverage


def allocation_limits(available_margin: Decimal, long_pct: Decimal, short_pct: Decimal, reserve_pct: Decimal) -> dict[str, Decimal]:
    if long_pct + short_pct + reserve_pct != Decimal("100"):
        raise ValueError("allocation percentages must total 100")
    return {
        "long": available_margin * long_pct / 100,
        "short": available_margin * short_pct / 100,
        "reserve": available_margin * reserve_pct / 100,
    }


def tp_price(entry_price: Decimal, side: str, move_pct: Decimal, tick_size: Decimal) -> Decimal:
    fraction = move_pct / 100
    raw = entry_price * (Decimal("1") + fraction if side == "long" else Decimal("1") - fraction)
    return quantize_step(raw, tick_size)


def tp_quantity(filled_qty: Decimal, close_pct: Decimal) -> Decimal:
    return filled_qty * close_pct / 100


def gross_pnl(entry_price: Decimal, exit_price: Decimal, qty: Decimal, side: str) -> Decimal:
    return (exit_price - entry_price) * qty if side == "long" else (entry_price - exit_price) * qty


def fee_estimate(notional_value: Decimal, fee_rate: Decimal) -> Decimal:
    return abs(notional_value) * fee_rate


def planned_grid_margin(orders: Iterable[dict], leverage: Decimal) -> Decimal:
    return sum((estimated_margin(D(item["price"]), D(item["qty"]), leverage) for item in orders), ZERO)


def allocation_guard(available_margin: Decimal, allocation_pct: Decimal, planned_margin_value: Decimal) -> dict[str, Decimal | bool]:
    limit = available_margin * allocation_pct / 100
    remaining = limit - planned_margin_value
    return {"limit": limit, "planned": planned_margin_value, "remaining": remaining, "allowed": remaining >= ZERO, "excess": max(ZERO, -remaining)}


def validate_tp_steps(steps: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    total = ZERO
    for index, step in enumerate(steps, start=1):
        move = required_decimal(step, "move_pct")
        close = required_decimal(step, "close_pct")
        if move <= ZERO:
            errors.append(f"TP {index}: move_pct must be > 0")
        if close <= ZERO or close > Decimal("100"):
            errors.append(f"TP {index}: close_pct must be between 0 and 100")
        total += close
    if total > Decimal("100"):
        errors.append("TP close_pct total must be <= 100")
    return errors


def cumulative_averages(prices: list[Decimal], quantities: list[Decimal]) -> list[Decimal | None]:
    result: list[Decimal | None] = []
    fills: list[tuple[Decimal, Decimal]] = []
    for price, quantity in zip(prices, quantities, strict=True):
        fills.append((quantity, price))
        result.append(weighted_average(fills))
    return result


def calculate_side(
    *, side: str, mark_price: Decimal, orders: list[dict[str, Any]], active_count: int,
    tick_size: Decimal, qty_step: Decimal, min_order_qty: Decimal, min_notional_value: Decimal,
    leverage: Decimal | None, fee_rate: Decimal | None,
) -> dict[str, Any]:
    if active_count < 1 or active_count > len(orders):
        raise ValueError(f"{side} active_count must be between 1 and order count")
    offsets = [required_decimal(item, "offset_pct") for item in orders]
    if any(offset <= ZERO for offset in offsets):
        raise ValueError(f"{side} offset_pct must be > 0")
    prices = entry_prices(mark_price, side, offsets, tick_size)
    errors: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    quantities = [required_decimal(item, "qty") for item in orders]
    for index, (item, price, quantity) in enumerate(zip(orders, prices, quantities, strict=True), start=1):
        item_errors: list[str] = []
        if quantity <= ZERO:
            item_errors.append("qty must be > 0")
        if quantity < min_order_qty:
            item_errors.append(f"qty must be >= {min_order_qty}")
        if quantize_step(quantity, qty_step) != quantity:
            item_errors.append(f"qty must respect qty_step {qty_step}")
        if notional(price, quantity) < min_notional_value:
            item_errors.append(f"notional must be >= {min_notional_value}")
        tps = item.get("tps", [])
        item_errors.extend(validate_tp_steps(tps))
        filled_qty = D(item.get("filled_qty", "0"))
        actual_closed_qty = D(item.get("actual_closed_qty", "0"))
        if actual_closed_qty > filled_qty:
            item_errors.append("actual_closed_qty cannot exceed filled_qty")
        actual_entry = D(item["avg_fill_price"]) if item.get("avg_fill_price") is not None else price
        base_qty = filled_qty if filled_qty > ZERO else quantity
        tp_results: list[dict[str, Any]] = []
        gross_total = ZERO
        fee_total = ZERO
        for step in tps:
            step_qty = tp_quantity(base_qty, required_decimal(step, "close_pct"))
            exit_price = tp_price(actual_entry, side, required_decimal(step, "move_pct"), tick_size)
            gross = gross_pnl(actual_entry, exit_price, step_qty, side)
            fee = fee_estimate(notional(actual_entry, step_qty) + notional(exit_price, step_qty), fee_rate) if fee_rate is not None else None
            if fee is not None:
                fee_total += fee
            gross_total += gross
            tp_results.append({"price": exit_price, "qty": step_qty, "close_pct": required_decimal(step, "close_pct"), "gross_pnl": gross, "fee": fee, "net_pnl": gross - fee if fee is not None else None, "basis": "actual_fill" if filled_qty > ZERO and item.get("avg_fill_price") is not None else "planned_entry"})
        validation = item_errors
        if validation:
            errors.append({"level": index, "errors": validation})
        planned_tp_qty = sum((x["qty"] for x in tp_results), ZERO)
        normalized.append({"level": index, "planned_entry_price": price, "configured_qty": quantity, "price": price, "qty": quantity, "notional": notional(price, quantity), "planned_margin": estimated_margin(price, quantity, leverage) if leverage is not None else None, "filled_qty": filled_qty, "actual_avg_entry_price": actual_entry if filled_qty > ZERO and item.get("avg_fill_price") is not None else None, "avg_entry_price": actual_entry if filled_qty > ZERO else None, "actual_closed_qty": actual_closed_qty, "open_qty": max(ZERO, filled_qty - actual_closed_qty), "planned_tp_qty": planned_tp_qty, "planned_remaining_after_all_tp": max(ZERO, base_qty - planned_tp_qty), "tp_steps": tp_results, "gross_pnl": gross_total, "fee_estimate": fee_total if fee_rate is not None else None, "net_pnl": gross_total - fee_total if fee_rate is not None else None, "validation_errors": validation, "status": "VALID" if not validation else "BLOCKED"})
    planned_margins = [item["planned_margin"] for item in normalized]
    full_margin = sum((item for item in planned_margins if item is not None), ZERO) if leverage is not None else None
    active_margin = sum((normalized[index]["planned_margin"] for index in range(active_count) if normalized[index]["planned_margin"] is not None), ZERO) if leverage is not None else None
    queued_margin = full_margin - active_margin if full_margin is not None and active_margin is not None else None
    prices_list = [item["price"] for item in normalized]
    planned_avg = weighted_average(list(zip(quantities, prices_list, strict=True)))
    cumulative = cumulative_averages(prices_list, quantities)
    for item, cumulative_average in zip(normalized, cumulative, strict=True):
        item["cumulative_planned_average"] = cumulative_average
    aggregate_gross = sum((item["gross_pnl"] for item in normalized), ZERO)
    aggregate_fee = sum((item["fee_estimate"] for item in normalized if item["fee_estimate"] is not None), ZERO) if fee_rate is not None else None
    policy = ActiveWindowPolicy(len(normalized), active_count)
    return {"side": side, "orders": normalized, "active_window_levels": policy.active_levels(), "queued_levels": policy.queued_levels(), "next_activation_candidate": policy.queued_levels()[0] if policy.queued_levels() else None, "full_grid_planned_margin": full_margin, "active_window_planned_margin": active_margin, "queued_planned_margin": queued_margin, "planned_qty": sum(quantities, ZERO), "planned_average": planned_avg, "cumulative_planned_average": cumulative, "aggregate_tp_gross_pnl": aggregate_gross, "aggregate_fee_estimate": aggregate_fee, "aggregate_net_pnl": aggregate_gross - aggregate_fee if aggregate_fee is not None else None, "validation_errors": errors, "status": "VALID" if not errors else "BLOCKED"}


def calculate_configuration(payload: dict[str, Any], *, instrument: dict[str, Any], account: dict[str, Any] | None = None) -> dict[str, Any]:
    allocation = payload["allocation"]
    available = required_decimal(account, "available_margin") if account is not None else required_decimal(payload, "available_margin")
    if any(D(allocation[key]) < ZERO or D(allocation[key]) > Decimal("100") for key in ("long_pct", "short_pct", "reserve_pct")):
        raise ValueError("allocation percentages must be between 0 and 100")
    limits = {key: required_decimal(instrument, key) for key in ("tick_size", "qty_step", "min_order_qty", "min_notional_value")}
    leverage_value = payload.get("leverage", payload.get("planning_leverage"))
    leverage = D(leverage_value) if leverage_value is not None else None
    fee_rate = D(payload["fee_rate"]) if payload.get("fee_rate") is not None else None
    allocation_result = allocation_limits(available, D(allocation["long_pct"]), D(allocation["short_pct"]), D(allocation["reserve_pct"]))
    mark = required_decimal(payload, "mark_price")
    result: dict[str, Any] = {"symbol": payload["symbol"], "mark_price": mark, "available_margin": available, "instrument": limits, "leverage": leverage, "fee_rate": fee_rate, "allocation_limits": allocation_result, "account_state_timestamp": payload.get("account_state_timestamp"), "instrument_source": payload.get("instrument_source")}
    for side in ("long", "short"):
        result[side] = calculate_side(side=side, mark_price=mark, orders=payload[side], active_count=int(payload[f"active_{side}_count"]), leverage=leverage, fee_rate=fee_rate, **limits)
        result[side]["allocation_limit"] = allocation_result[side]
        current_margin = (account or {}).get(f"{side}_initial_margin")
        result[side]["current_used_context"] = D(current_margin) if current_margin not in (None, "") else None
        result[side]["current_position_context"] = result[side]["current_used_context"]
        result[side]["remaining_limit"] = allocation_result[side] - (result[side]["full_grid_planned_margin"] or ZERO)
        result[side]["utilization_pct"] = ((result[side]["full_grid_planned_margin"] or ZERO) / allocation_result[side] * 100) if allocation_result[side] else None
        result[side]["excess"] = max(ZERO, -result[side]["remaining_limit"]) if leverage is not None else None
        if result[side]["remaining_limit"] < ZERO:
            result[side]["validation_errors"].append({"level": 0, "errors": ["full grid exceeds allocation limit"]})
            result[side]["status"] = "BLOCKED"
    result["combined_planned_margin"] = (result["long"]["full_grid_planned_margin"] or ZERO) + (result["short"]["full_grid_planned_margin"] or ZERO)
    result["combined_gross_pnl"] = result["long"]["aggregate_tp_gross_pnl"] + result["short"]["aggregate_tp_gross_pnl"]
    fees = [result[side]["aggregate_fee_estimate"] for side in ("long", "short")]
    result["combined_fee_estimate"] = sum(fees, ZERO) if all(fee is not None for fee in fees) else None
    result["combined_net_pnl"] = result["combined_gross_pnl"] - result["combined_fee_estimate"] if result["combined_fee_estimate"] is not None else None
    result["validation_errors"] = result["long"]["validation_errors"] + result["short"]["validation_errors"]
    result["validation_state"] = "VALID" if result["long"]["status"] == result["short"]["status"] == "VALID" else "BLOCKED"
    return result
