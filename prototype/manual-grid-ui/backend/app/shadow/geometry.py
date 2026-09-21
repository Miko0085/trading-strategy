from __future__ import annotations

from decimal import Decimal


def distribution_vector(order_count: int, first_offset_pct: Decimal, depth_pct: Decimal, coefficient: Decimal) -> list[Decimal]:
    """Return deterministic anchor distances; exact strategy formula remains replaceable."""
    if order_count < 1:
        raise ValueError("order_count must be >= 1")
    if first_offset_pct <= 0 or depth_pct < first_offset_pct or coefficient <= 0:
        raise ValueError("invalid geometry parameters")
    if order_count == 1:
        return [first_offset_pct]
    span = depth_pct - first_offset_pct
    denominator = Decimal(order_count - 1)
    return [first_offset_pct + span * ((Decimal(index) / denominator) ** coefficient) for index in range(order_count)]


def geometry_prices(anchor_price: Decimal, side: str, distances_pct: list[Decimal], tick_size: Decimal) -> list[Decimal]:
    if anchor_price <= 0 or tick_size <= 0:
        raise ValueError("anchor_price and tick_size must be positive")
    values = [anchor_price * (Decimal("1") - distance / 100 if side == "long" else Decimal("1") + distance / 100) for distance in distances_pct]
    return [(value / tick_size).quantize(Decimal("1")) * tick_size for value in values]


def geometry_proportions(distances_pct: list[Decimal]) -> list[Decimal]:
    if not distances_pct:
        return []
    last = distances_pct[-1]
    return [distance / last for distance in distances_pct] if last else [Decimal("0") for _ in distances_pct]
