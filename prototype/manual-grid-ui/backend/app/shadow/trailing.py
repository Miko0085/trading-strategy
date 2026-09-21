from __future__ import annotations

from decimal import Decimal

from .geometry import geometry_prices


def trail_pending_grid(grid: dict, *, new_anchor: Decimal, tick_size: Decimal) -> dict:
    """Move only unfilled, non-locked virtual entries; preserve geometry proportions."""
    distances = [Decimal(str(value)) for value in grid.get("geometry", {}).get("distances_pct", [])]
    prices = geometry_prices(new_anchor, grid["side"], distances, tick_size)
    for order, price in zip(grid.get("orders", []), prices, strict=True):
        if Decimal(str(order.get("filled_qty", "0"))) == 0 and not order.get("manual_price_lock", False):
            order["entry_price"] = price
            for tp in order.get("planned_tp", []):
                move = Decimal(str(tp.get("move_pct", "0")))
                tp["price"] = (price * (Decimal("1") + move / 100 if grid["side"] == "long" else Decimal("1") - move / 100) / tick_size).quantize(Decimal("1")) * tick_size
    grid["anchor_price"] = new_anchor
    return grid
