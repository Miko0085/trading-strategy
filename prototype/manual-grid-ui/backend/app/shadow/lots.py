from __future__ import annotations

from decimal import Decimal


def apply_fill(lot: dict[str, object], fill_qty: Decimal, fill_price: Decimal) -> dict[str, object]:
    if fill_qty <= 0 or fill_price <= 0:
        raise ValueError("fill_qty and fill_price must be positive")
    old_qty = Decimal(str(lot.get("filled_qty", "0")))
    old_avg = lot.get("actual_avg_fill")
    old_notional = old_qty * Decimal(str(old_avg)) if old_avg is not None else Decimal("0")
    total_qty = old_qty + fill_qty
    lot["filled_qty"] = total_qty
    lot["actual_avg_fill"] = (old_notional + fill_qty * fill_price) / total_qty
    lot["open_qty"] = total_qty - Decimal(str(lot.get("closed_qty", "0")))
    lot["configured_qty"] = Decimal(str(lot.get("configured_qty", "0")))
    lot["remaining_entry_qty"] = max(Decimal("0"), lot["configured_qty"] - total_qty)
    return lot


def tp_quantities(open_qty: Decimal, close_percentages: list[Decimal]) -> list[Decimal]:
    if open_qty < 0 or sum(close_percentages, Decimal("0")) > 100:
        raise ValueError("TP quantity exceeds open quantity")
    return [open_qty * close_pct / 100 for close_pct in close_percentages]


def tp_prices(actual_avg_fill: Decimal, side: str, move_percentages: list[Decimal], tick_size: Decimal) -> list[Decimal]:
    return [((actual_avg_fill * (Decimal("1") + move / 100 if side == "long" else Decimal("1") - move / 100)) / tick_size).quantize(Decimal("1")) * tick_size for move in move_percentages]
