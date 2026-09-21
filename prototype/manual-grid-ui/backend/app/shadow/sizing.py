from __future__ import annotations

from decimal import ROUND_DOWN, Decimal


def normalized_weights(order_count: int, martingale_coefficient: Decimal) -> list[Decimal]:
    if order_count < 1 or martingale_coefficient <= 0:
        raise ValueError("invalid sizing parameters")
    raw = [martingale_coefficient ** index for index in range(order_count)]
    total = sum(raw, Decimal("0"))
    return [value / total for value in raw]


def quantity_for_budget(budget: Decimal, prices: list[Decimal], leverage: Decimal, qty_step: Decimal, min_order_qty: Decimal, martingale_coefficient: Decimal) -> list[Decimal]:
    if budget < 0 or leverage <= 0 or qty_step <= 0:
        raise ValueError("invalid budget, leverage or qty_step")
    weights = normalized_weights(len(prices), martingale_coefficient)
    quantities = [(budget * weight * leverage / price / qty_step).to_integral_value(rounding=ROUND_DOWN) * qty_step for weight, price in zip(weights, prices, strict=True)]
    # Rounding down is intentional: the virtual plan must never exceed the side budget.
    while sum((price * quantity / leverage for price, quantity in zip(prices, quantities, strict=True)), Decimal("0")) > budget:
        index = max((i for i, quantity in enumerate(quantities) if quantity >= qty_step), key=lambda i: quantities[i], default=None)
        if index is None:
            break
        quantities[index] -= qty_step
    return quantities


def planned_margin(prices: list[Decimal], quantities: list[Decimal], leverage: Decimal) -> Decimal:
    return sum((price * quantity / leverage for price, quantity in zip(prices, quantities, strict=True)), Decimal("0"))
