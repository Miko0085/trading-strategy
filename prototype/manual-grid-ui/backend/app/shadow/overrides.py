from __future__ import annotations

from decimal import Decimal
from copy import deepcopy


def apply_field_overrides(orders: list[dict], overrides: list[dict], *, leverage: Decimal, budget: Decimal) -> dict:
    """Apply explicit field locks after generation and report budget violations."""
    by_level = {int(item["level"]): item for item in orders}
    locked_fields = []
    for override in overrides:
        order = by_level.get(int(override["level"]))
        if order is None or override.get("field") not in {"entry_price", "qty", "planned_tp"}:
            continue
        field = str(override["field"])
        order[field] = Decimal(str(override["value"])) if field != "planned_tp" else deepcopy(override["value"])
        order[f"manual_{'price' if field == 'entry_price' else field}_lock"] = True
        locked_fields.append({"level": order["level"], "field": field, "source": "MANUAL_OVERRIDE"})
    planned = sum((Decimal(str(item["entry_price"])) * Decimal(str(item["qty"])) / leverage for item in orders), Decimal("0"))
    errors = ["Ручные настройки превышают доступный side allocation."] if planned > budget else []
    return {"orders": orders, "locked_fields": locked_fields, "planned_margin": planned, "validation_errors": errors, "status": "BLOCKED" if errors else "VALID"}
