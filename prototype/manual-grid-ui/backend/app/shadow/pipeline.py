from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Protocol

from .engine import apply_realized_execution, evaluate_restructuring
from .lots import apply_close_to_shadow_order, apply_execution_to_shadow_order
from .triggers import classify_restructuring_trigger


class ShadowRevisionRepository(Protocol):
    def save_shadow_revision(self, symbol: str, evaluation: dict[str, Any]) -> dict[str, Any]: ...

    def list_shadow_revisions(self, symbol: str | None = None) -> list[dict[str, Any]]: ...


def execution_identity(execution: dict[str, Any]) -> str:
    """Return a replay-stable identity without inventing strategy attribution."""
    explicit = execution.get("execution_id") or execution.get("execId")
    if explicit:
        return str(explicit)
    factual = "|".join(str(execution.get(key, "")) for key in ("symbol", "order_id", "orderId", "side", "position_idx", "positionIdx", "price", "execPrice", "qty", "execQty", "timestamp", "execTime"))
    return f"missing-id:{sha256(factual.encode()).hexdigest()}"


def execution_sort_key(execution: dict[str, Any]) -> tuple[Decimal, str]:
    """Chronological order, then execution id as a stable tie-break."""
    raw = execution.get("timestamp", execution.get("execTime"))
    try:
        timestamp = Decimal(str(raw)) if raw not in (None, "") else Decimal("Infinity")
    except InvalidOperation:
        timestamp = Decimal("Infinity")
    return timestamp, execution_identity(execution)


def _position_side(execution: dict[str, Any]) -> str | None:
    position_idx = str(execution.get("position_idx", execution.get("positionIdx", "")))
    if position_idx == "1":
        return "long"
    if position_idx == "2":
        return "short"
    return None


def _direction_matches(side: str, action: str, *, close: bool) -> bool:
    expected = {("long", False): "buy", ("long", True): "sell", ("short", False): "sell", ("short", True): "buy"}
    return action.lower() == expected[(side, close)]


def _linked(execution: dict[str, Any], candidate: dict[str, Any]) -> bool:
    execution_ids = {str(value) for value in (execution.get("order_id"), execution.get("orderId"), execution.get("order_link_id"), execution.get("orderLinkId")) if value not in (None, "")}
    candidate_ids = {str(value) for value in (candidate.get("order_id"), candidate.get("orderId"), candidate.get("order_link_id"), candidate.get("orderLinkId")) if value not in (None, "")}
    return bool(execution_ids & candidate_ids)


def attribute_execution(current: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    """Prove an execution relation or return UNATTRIBUTED_EXECUTION.

    Buy/Sell alone is never sufficient: positionIdx proves the position side,
    while an order/TP link (or explicit external manual-close attribution)
    proves the strategy object and entry/close role.
    """
    side = _position_side(execution)
    action = str(execution.get("side", ""))
    if side is None:
        return {"kind": "UNATTRIBUTED_EXECUTION", "reason": "positionIdx does not prove a strategy side"}
    orders = current.get("sides", {}).get(side, {}).get("orders", [])

    for order in orders:
        if _linked(execution, order) and _direction_matches(side, action, close=False):
            return {"kind": "ENTRY", "side": side, "order": order, "level": order.get("level")}

    for order in orders:
        for tp in order.get("planned_tp", []):
            if _linked(execution, tp) and _direction_matches(side, action, close=True):
                return {"kind": "TP_CLOSE", "side": side, "order": order, "level": order.get("level")}

    manual_hint = str(execution.get("attribution_hint", execution.get("close_source", ""))).upper()
    if manual_hint in {"MANUAL", "MANUAL_CLOSE"} and _direction_matches(side, action, close=True):
        requested_level = execution.get("grid_order_level")
        candidates = [order for order in orders if Decimal(str(order.get("open_qty", "0"))) > 0 and (requested_level is None or str(order.get("level")) == str(requested_level))]
        if len(candidates) == 1:
            order = candidates[0]
            return {"kind": "MANUAL_CLOSE", "side": side, "order": order, "level": order.get("level")}

    return {"kind": "UNATTRIBUTED_EXECUTION", "reason": "no proven shadow order, TP, or manual-close relation"}


def _record_event(state: dict[str, Any], execution: dict[str, Any], attribution: dict[str, Any], trigger: str | None) -> dict[str, Any]:
    event = {
        "execution_id": execution_identity(execution),
        "timestamp": execution.get("timestamp", execution.get("execTime")),
        "symbol": execution.get("symbol"),
        "side": attribution.get("side"),
        "level": attribution.get("level"),
        "attribution": attribution["kind"],
        "trigger": trigger,
        "reason": attribution.get("reason"),
    }
    state.setdefault("strategy_state", {}).setdefault("factual_event_audit", []).append(event)
    return event


def recover_latest_shadow_state(repository: ShadowRevisionRepository, symbol: str, fallback: dict[str, Any]) -> dict[str, Any]:
    revisions = repository.list_shadow_revisions(symbol)
    if not revisions:
        return deepcopy(fallback)
    payload = revisions[0].get("payload", {})
    return deepcopy(payload.get("after", fallback))


def process_live_executions(
    current: dict[str, Any],
    executions: list[dict[str, Any]],
    *,
    account: dict[str, object],
    configuration: dict[str, Any],
    instrument: dict[str, object],
    repository: ShadowRevisionRepository | None = None,
) -> dict[str, Any]:
    """Apply all factual events deterministically and persist virtual revisions.

    Every unique factual event is accounted for. Restructuring is performed
    after each attributed event; it remains simulation-only (NOT_SENT).
    """
    state = deepcopy(current)
    events: list[dict[str, Any]] = []
    revisions: list[dict[str, Any]] = []
    persisted: list[dict[str, Any]] = []

    for execution in sorted(executions, key=execution_sort_key):
        strategy_state = state.setdefault("strategy_state", {})
        applied = strategy_state.setdefault("applied_factual_execution_ids", [])
        unattributed = strategy_state.setdefault("unattributed_executions", [])
        execution_id = execution_identity(execution)
        if execution_id in applied:
            continue
        attribution = attribute_execution(state, execution)
        if attribution["kind"] == "UNATTRIBUTED_EXECUTION":
            before = deepcopy(state)
            applied.append(execution_id)
            unattributed.append({"execution_id": execution_id, "execution": deepcopy(execution), "reason": attribution["reason"]})
            event = _record_event(state, execution, attribution, None)
            events.append(event)
            diagnostic = {"mode": "SHADOW / SIMULATION", "trigger": "UNATTRIBUTED_EXECUTION", "source": "BYBIT_FACTUAL", "before": before, "after": deepcopy(state), "changes": [], "revision_type": "FACTUAL_DIAGNOSTIC", "execution": "NOT_SENT", "factual_event": deepcopy(event), "factual_execution_id": execution_id}
            revisions.append(diagnostic)
            if repository is not None:
                persisted.append(repository.save_shadow_revision(str(configuration["symbol"]), diagnostic))
            continue

        order = attribution["order"]
        if attribution["kind"] == "ENTRY":
            apply_execution_to_shadow_order(order, execution)
            trigger = classify_restructuring_trigger(event_type="entry", filled_qty=order["filled_qty"], target_qty=order.get("configured_qty", order.get("qty", "0")))
        else:
            apply_close_to_shadow_order(order, execution)
            is_full = Decimal(str(order.get("open_qty", "0"))) == 0
            event_type = "TP_FULL" if attribution["kind"] == "TP_CLOSE" and is_full else "TP_PARTIAL" if attribution["kind"] == "TP_CLOSE" else "MANUAL_FULL_CLOSE" if is_full else "MANUAL_PARTIAL_CLOSE"
            trigger = classify_restructuring_trigger(event_type=event_type, filled_qty=order.get("closed_qty", "0"), target_qty=order.get("filled_qty", "0"), realized_pnl=execution.get("realized_pnl"))

        applied.append(execution_id)
        event = _record_event(state, execution, attribution, trigger)
        events.append(event)
        if attribution["kind"] != "ENTRY":
            state = apply_realized_execution(state, execution={**execution, "execution_id": execution_id, "trigger": trigger}, configuration=configuration)
        evaluation = evaluate_restructuring(state, trigger=trigger, account=account, configuration=configuration, instrument=instrument)
        evaluation["factual_event"] = deepcopy(event)
        evaluation["factual_execution_id"] = execution_id
        revisions.append(evaluation)
        if repository is not None:
            persisted.append(repository.save_shadow_revision(str(configuration["symbol"]), evaluation))
        state = evaluation["after"]

    return {"state": state, "events": events, "revisions": revisions, "persisted": persisted, "ordering_policy": "execTime ascending; execution_id ascending for equal timestamps"}
