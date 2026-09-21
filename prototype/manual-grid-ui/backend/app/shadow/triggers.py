from __future__ import annotations


def classify_restructuring_trigger(*, event_type: str, filled_qty: str | float, target_qty: str | float, realized_pnl: str | float | None = None) -> str:
    """Classify factual state changes without performing execution."""
    event = event_type.upper()
    if event in {"TP_PARTIAL", "TP_FULL", "MANUAL_PARTIAL_CLOSE", "MANUAL_FULL_CLOSE"}:
        return {"TP_PARTIAL": "TP_PARTIAL_FILL", "TP_FULL": "TP_FULL_FILL", "MANUAL_PARTIAL_CLOSE": "MANUAL_PARTIAL_CLOSE", "MANUAL_FULL_CLOSE": "MANUAL_FULL_CLOSE"}[event]
    filled = float(filled_qty)
    target = float(target_qty)
    if filled >= target:
        return "ENTRY_FULL_FILL"
    return "ENTRY_PARTIAL_FILL"
