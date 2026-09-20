from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Iterable


ZERO = Decimal("0")


def D(value: object) -> Decimal:
    return Decimal(str(value))


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
