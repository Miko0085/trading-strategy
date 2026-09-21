from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from app.account_state import normalize_account, normalize_instrument
from app.shadow.engine import evaluate_restructuring, generate_grid
from app.shadow.pipeline import attribute_execution, process_live_executions, recover_latest_shadow_state


D = Decimal
INSTRUMENT = {"symbol": "BTCUSDT", "tick_size": "0.01", "qty_step": "0.01", "min_order_qty": "0.01", "min_notional_value": "1"}


def factual_account(*, long_upnl: str = "0", short_upnl: str = "0", total_upnl: str = "0") -> dict[str, object]:
    return {"mark_price": "100", "wallet_balance": "10000", "equity": "10000", "available_margin": "10000", "realized_pnl": "0", "unrealized_pnl": total_upnl, "long_unrealized_pnl": long_upnl, "short_unrealized_pnl": short_upnl, "position_mode": "HEDGE"}


def configuration() -> dict:
    side = {"enabled": True, "order_count": 4, "grid_depth_pct": "30", "first_order_offset_pct": "5", "distribution_coefficient": "1.5", "leverage": "2", "martingale_multiplier": "1.2", "active_order_count": 2, "tp_steps": [{"move_pct": "10", "close_pct": "50"}], "trailing_enabled": False, "realized_reinvest_pct": "50", "long_unrealized_reinvest_pct": "0", "short_unrealized_reinvest_pct": "0", "manual_overrides": []}
    return {"symbol": "BTCUSDT", "allocation": {"long_pct": "40", "short_pct": "40", "reserve_pct": "20"}, "long": deepcopy(side), "short": deepcopy(side)}


def shadow_state() -> tuple[dict, dict]:
    config = configuration()
    state = generate_grid(account=factual_account(), configuration=config, instrument=INSTRUMENT)
    for side, entry_action, close_action in (("long", "Buy", "Sell"), ("short", "Sell", "Buy")):
        order = state["sides"][side]["orders"][0]
        order.update({"order_id": f"{side}-entry", "order_link_id": f"{side}-entry-link", "qty": D("10"), "configured_qty": D("10"), "manual_qty_lock": True})
        order["planned_tp"][0].update({"order_id": f"{side}-tp", "order_link_id": f"{side}-tp-link", "entry_action": entry_action, "close_action": close_action})
    return state, config


def execution(execution_id: str, *, side: str = "Buy", position_idx: int = 1, qty: str = "1", price: str = "100", timestamp: str = "1", order_id: str = "long-entry", realized_pnl: str = "0", **extra) -> dict:
    return {"execution_id": execution_id, "order_id": order_id, "symbol": "BTCUSDT", "side": side, "position_idx": position_idx, "qty": qty, "price": price, "timestamp": timestamp, "realized_pnl": realized_pnl, "fee": "0", **extra}


def run(state: dict, config: dict, events: list[dict], repository=None) -> dict:
    return process_live_executions(state, events, account=factual_account(), configuration=config, instrument=INSTRUMENT, repository=repository)


def order(result: dict, side: str = "long") -> dict:
    return result["state"]["sides"][side]["orders"][0]


def assert_virtual_revision(revision: dict, trigger: str) -> None:
    assert revision["trigger"] == trigger
    assert revision["execution"] == "NOT_SENT"
    assert revision["before"] is not revision["after"]
    assert isinstance(revision["changes"], list)
    assert revision["revision_type"] == "DYNAMIC_SIZING"


class FakeShadowRepository:
    def __init__(self):
        self.rows: list[dict] = []

    def save_shadow_revision(self, symbol: str, evaluation: dict) -> dict:
        row = {"id": str(len(self.rows) + 1), "symbol": symbol, "trigger": evaluation["trigger"], "revision_type": evaluation["revision_type"], "status": "VIRTUAL", "payload": deepcopy(evaluation), "created_at": f"2026-01-01T00:00:0{len(self.rows)}Z"}
        self.rows.insert(0, row)
        return row

    def list_shadow_revisions(self, symbol: str | None = None) -> list[dict]:
        return [deepcopy(row) for row in self.rows if symbol is None or row["symbol"] == symbol]


def test_initial_bybit_factual_snapshot_is_normalized_without_trading_action():
    instrument = normalize_instrument({"list": [{"symbol": "BTCUSDT", "priceFilter": {"tickSize": "0.1"}, "lotSizeFilter": {"qtyStep": "0.001", "minOrderQty": "0.001", "minNotionalValue": "5"}}]})
    state = normalize_account(
        {"list": [{"totalWalletBalance": "100", "totalEquity": "110", "totalAvailableBalance": "80", "totalPerpUPL": "10"}]},
        {"list": [{"symbol": "BTCUSDT", "side": "Buy", "positionIdx": 1, "size": "2", "avgPrice": "90", "unrealisedPnl": "12"}, {"symbol": "BTCUSDT", "side": "Sell", "positionIdx": 2, "size": "1", "avgPrice": "110", "unrealisedPnl": "-2"}]},
        {"list": [{"orderId": "o1", "orderLinkId": "link-1", "symbol": "BTCUSDT", "side": "Buy", "positionIdx": 1, "reduceOnly": False}]},
        {"list": [{"symbol": "BTCUSDT", "markPrice": "100"}]}, instrument, "bybit_read_only",
        {"list": [{"execId": "e1", "orderId": "o1", "orderLinkId": "link-1", "symbol": "BTCUSDT", "side": "Buy", "positionIdx": 1, "execQty": "1", "execPrice": "99", "execPnl": "0"}]},
    )
    assert (state["symbol"], state["mark_price"], state["wallet_balance"], state["equity"], state["available_margin"]) == ("BTCUSDT", "100", "100", "110", "80")
    assert state["long"]["size"] == "2" and state["short"]["size"] == "1"
    assert state["long_unrealized_pnl"] == "12" and state["short_unrealized_pnl"] == "-2"
    assert state["position_mode"] == "HEDGE"
    assert state["executions"][0]["order_link_id"] == "link-1"
    assert state["instrument"] == instrument


def test_execution_attribution_proves_long_short_entry_and_close_directions():
    state, _ = shadow_state()
    assert attribute_execution(state, execution("le"))["kind"] == "ENTRY"
    assert attribute_execution(state, execution("lc", side="Sell", order_id="long-tp"))["kind"] == "TP_CLOSE"
    assert attribute_execution(state, execution("se", side="Sell", position_idx=2, order_id="short-entry"))["kind"] == "ENTRY"
    short_close = attribute_execution(state, execution("sc", side="Buy", position_idx=2, order_id="short-tp"))
    assert short_close["kind"] == "TP_CLOSE" and short_close["side"] == "short"


def test_normalized_bybit_execution_flows_into_shadow_revision_end_to_end():
    state, config = shadow_state()
    account_state = normalize_account(
        {"list": [{"totalWalletBalance": "10000", "totalEquity": "10000", "totalAvailableBalance": "10000"}]},
        {"list": [{"symbol": "BTCUSDT", "side": "Buy", "positionIdx": 1, "size": "4", "avgPrice": "100", "unrealisedPnl": "0"}, {"symbol": "BTCUSDT", "side": "Sell", "positionIdx": 2, "size": "0", "unrealisedPnl": "0"}]},
        {"list": []}, {"list": [{"symbol": "BTCUSDT", "markPrice": "100"}]}, INSTRUMENT, "bybit_read_only",
        {"list": [{"execId": "raw-entry", "orderId": "long-entry", "symbol": "BTCUSDT", "side": "Buy", "positionIdx": 1, "execQty": "4", "execPrice": "100", "execTime": "1000", "execPnl": "0", "execFee": "0"}]},
    )
    result = process_live_executions(state, account_state["executions"], account=account_state, configuration=config, instrument=INSTRUMENT)
    assert order(result)["filled_qty"] == D("4")
    assert result["events"][0]["trigger"] == "ENTRY_PARTIAL_FILL"
    assert result["revisions"][0]["factual_execution_id"] == "raw-entry"


def test_unknown_execution_is_preserved_without_strategy_mutation_or_reinvest():
    state, config = shadow_state()
    repository = FakeShadowRepository()
    before = deepcopy(state["sides"])
    unknown = execution("unknown", order_id="external-order")
    result = run(state, config, [unknown], repository)
    assert result["state"]["sides"] == before
    assert result["events"][0]["attribution"] == "UNATTRIBUTED_EXECUTION"
    assert result["state"]["strategy_state"]["unattributed_executions"][0]["execution_id"] == "unknown"
    assert result["state"]["strategy_state"]["reinvest_audit"] == []
    assert result["revisions"][0]["revision_type"] == "FACTUAL_DIAGNOSTIC"
    assert result["revisions"][0]["execution"] == "NOT_SENT"
    recovered = recover_latest_shadow_state(repository, "BTCUSDT", state)
    replay = run(recovered, config, [unknown], repository)
    assert replay["events"] == [] and len(replay["state"]["strategy_state"]["unattributed_executions"]) == 1


def test_entry_partial_fill_pipeline_is_idempotent_and_keeps_one_logical_lot():
    state, config = shadow_state()
    result = run(state, config, [execution("entry-1", qty="4"), execution("entry-1", qty="4")])
    factual = order(result)
    assert factual["filled_qty"] == factual["open_qty"] == D("4")
    assert factual["actual_avg_fill"] == D("100")
    assert factual["remaining_entry_qty"] == D("6")
    assert len(factual["strategy_lots"]) == 1 and factual["strategy_lots"][0]["filled_qty"] == D("4")
    assert len(factual["executions"]) == 1 and len(result["events"]) == 1
    assert result["state"]["strategy_state"]["reinvest_audit"] == []
    assert_virtual_revision(result["revisions"][0], "ENTRY_PARTIAL_FILL")


def test_entry_full_fill_and_weighted_multiple_partials_update_one_order_and_lot():
    state, config = shadow_state()
    events = [execution("fill-3", qty="5", price="98", timestamp="3"), execution("fill-1", qty="2", price="100", timestamp="1"), execution("fill-2", qty="3", price="102", timestamp="2")]
    result = run(state, config, events)
    factual = order(result)
    assert factual["filled_qty"] == factual["open_qty"] == D("10")
    assert factual["actual_avg_fill"] == D("99.6")
    assert factual["remaining_entry_qty"] == 0
    assert len(factual["strategy_lots"]) == 1
    assert factual["strategy_lots"][0]["execution_ids"] == ["fill-1", "fill-2", "fill-3"]
    assert [item["trigger"] for item in result["events"]] == ["ENTRY_PARTIAL_FILL", "ENTRY_PARTIAL_FILL", "ENTRY_FULL_FILL"]
    assert_virtual_revision(result["revisions"][-1], "ENTRY_FULL_FILL")


def test_out_of_order_duplicate_delivery_has_deterministic_final_state():
    state, config = shadow_state()
    first = run(state, config, [execution("exec-2", qty="6", price="102", timestamp="2"), execution("exec-1", qty="4", price="99", timestamp="1"), execution("exec-2", qty="6", price="102", timestamp="2")])
    second = run(state, config, [execution("exec-1", qty="4", price="99", timestamp="1"), execution("exec-2", qty="6", price="102", timestamp="2")])
    assert order(first) == order(second)
    assert first["state"]["strategy_state"]["applied_factual_execution_ids"] == ["exec-1", "exec-2"]


def test_tp_partial_then_full_close_updates_capital_and_realized_reinvest_once():
    state, config = shadow_state()
    entered = run(state, config, [execution("entry-full", qty="10")])["state"]
    entered["strategy_state"]["long_strategy_deposit"] = "300"
    entry_price = entered["sides"]["long"]["orders"][0]["entry_price"]
    avg_fill = entered["sides"]["long"]["orders"][0]["actual_avg_fill"]
    partial = run(entered, config, [execution("tp-1", side="Sell", qty="4", price="110", order_id="long-tp", realized_pnl="100")])
    partial_order = order(partial)
    assert partial_order["closed_qty"] == D("4") and partial_order["open_qty"] == D("6")
    assert partial_order["entry_price"] == entry_price and partial_order["actual_avg_fill"] == avg_fill
    assert partial["state"]["strategy_state"]["long_strategy_deposit"] == "350"
    assert partial["state"]["sides"]["long"]["factual_used_capital"] == D("300")
    assert_virtual_revision(partial["revisions"][0], "TP_PARTIAL_FILL")

    closed = run(partial["state"], config, [execution("tp-2", side="Sell", qty="6", price="111", order_id="long-tp", realized_pnl="100"), execution("tp-2", side="Sell", qty="6", price="111", order_id="long-tp", realized_pnl="100")])
    assert order(closed)["open_qty"] == 0
    assert order(closed)["strategy_lots"][0]["state"] == "CLOSED"
    assert closed["state"]["strategy_state"]["long_strategy_deposit"] == "400"
    assert closed["state"]["sides"]["long"]["factual_used_capital"] == 0
    assert_virtual_revision(closed["revisions"][0], "TP_FULL_FILL")


def test_manual_partial_and_full_close_require_explicit_external_attribution():
    state, config = shadow_state()
    entered = run(state, config, [execution("entry-full", qty="10")])["state"]
    partial_event = execution("manual-1", side="Sell", qty="4", order_id="external", attribution_hint="MANUAL_CLOSE", grid_order_level=1)
    partial = run(entered, config, [partial_event])
    assert order(partial)["open_qty"] == D("6")
    assert_virtual_revision(partial["revisions"][0], "MANUAL_PARTIAL_CLOSE")
    full_event = execution("manual-2", side="Sell", qty="6", order_id="external", attribution_hint="MANUAL_CLOSE", grid_order_level=1)
    closed = run(partial["state"], config, [full_event])
    assert order(closed)["open_qty"] == 0
    assert_virtual_revision(closed["revisions"][0], "MANUAL_FULL_CLOSE")


def test_unrealized_boost_tracks_opposite_side_snapshot_and_never_uses_total_fallback():
    state, config = shadow_state()
    config["allocation"] = {"long_pct": "30", "short_pct": "30", "reserve_pct": "20"}
    config["long"]["long_unrealized_reinvest_pct"] = "10"
    state = generate_grid(account=factual_account(), configuration=config, instrument=INSTRUMENT)
    deposits = state["strategy_state"].copy()
    boosted = evaluate_restructuring(state, trigger="CAPITAL_STATE_CHANGE", account=factual_account(short_upnl="500", total_upnl="999"), configuration=config, instrument=INSTRUMENT)["after"]
    reduced = evaluate_restructuring(boosted, trigger="CAPITAL_STATE_CHANGE", account=factual_account(short_upnl="200", total_upnl="999"), configuration=config, instrument=INSTRUMENT)["after"]
    absent = evaluate_restructuring(reduced, trigger="CAPITAL_STATE_CHANGE", account=factual_account(short_upnl=None, total_upnl="999"), configuration=config, instrument=INSTRUMENT)["after"]
    assert boosted["shadow_summary"]["long"]["current_unrealized_boost"] == "50"
    assert reduced["shadow_summary"]["long"]["current_unrealized_boost"] == "20"
    assert absent["shadow_summary"]["long"]["current_unrealized_boost"] == "0"
    assert absent["strategy_state"]["long_strategy_deposit"] == deposits["long_strategy_deposit"]


def test_revision_persistence_and_restart_recovery_prevent_replay():
    state, config = shadow_state()
    repository = FakeShadowRepository()
    entered = run(state, config, [execution("entry-full", qty="10")], repository)["state"]
    entered["strategy_state"]["long_strategy_deposit"] = "300"
    first = run(entered, config, [execution("persisted-close", side="Sell", qty="4", order_id="long-tp", realized_pnl="100")], repository)
    persisted = repository.rows[0]
    assert persisted["symbol"] == "BTCUSDT" and persisted["trigger"] == "TP_PARTIAL_FILL"
    assert persisted["payload"]["before"] and persisted["payload"]["after"] and persisted["payload"]["changes"] is not None
    assert persisted["payload"]["after"]["capital_snapshot"]
    assert persisted["payload"]["after"]["strategy_state"]["long_strategy_deposit"] == "350"
    assert "persisted-close" in persisted["payload"]["after"]["strategy_state"]["applied_factual_execution_ids"]
    assert persisted["id"] and persisted["created_at"]

    recovered = recover_latest_shadow_state(repository, "BTCUSDT", state)
    replay = run(recovered, config, [execution("persisted-close", side="Sell", qty="4", order_id="long-tp", realized_pnl="100")], repository)
    assert replay["revisions"] == [] and replay["events"] == []
    assert replay["state"]["strategy_state"]["long_strategy_deposit"] == "350"
    assert order(replay)["closed_qty"] == D("4")


def test_multiple_executions_in_one_poll_are_all_applied_in_chronological_order():
    state, config = shadow_state()
    events = [execution("tp", side="Sell", qty="4", price="110", timestamp="3", order_id="long-tp", realized_pnl="20"), execution("entry-b", qty="6", timestamp="2"), execution("entry-a", qty="4", timestamp="1")]
    result = run(state, config, events)
    assert [event["execution_id"] for event in result["events"]] == ["entry-a", "entry-b", "tp"]
    assert [event["trigger"] for event in result["events"]] == ["ENTRY_PARTIAL_FILL", "ENTRY_FULL_FILL", "TP_PARTIAL_FILL"]
    assert len(result["revisions"]) == 3
    assert order(result)["filled_qty"] == D("10") and order(result)["open_qty"] == D("6")
    assert result["ordering_policy"] == "execTime ascending; execution_id ascending for equal timestamps"


def test_only_explicit_trailing_moves_prices_and_live_factual_levels_stay_fixed():
    state, config = shadow_state()
    long_orders = state["sides"]["long"]["orders"]
    long_orders[1].update({"order_id": "long-entry-2", "qty": D("10"), "configured_qty": D("10"), "manual_qty_lock": True})
    factual = run(state, config, [execution("l1", qty="10"), execution("l2", order_id="long-entry-2", qty="4")])["state"]
    before = [item["entry_price"] for item in factual["sides"]["long"]["orders"]]
    ordinary = evaluate_restructuring(factual, trigger="CAPITAL_STATE_CHANGE", account=factual_account(), configuration=config, instrument=INSTRUMENT)["after"]
    assert [item["entry_price"] for item in ordinary["sides"]["long"]["orders"]] == before
    config["long"]["anchor_price"] = "110"
    trailed = evaluate_restructuring(ordinary, trigger="TRAILING_TRIGGER", account=factual_account(), configuration=config, instrument=INSTRUMENT)["after"]
    after = [item["entry_price"] for item in trailed["sides"]["long"]["orders"]]
    assert after[0] == before[0] and after[1] == before[1]
    assert after[2:] != before[2:]
    assert all(item["planned_tp"][0].get("price") is not None for item in trailed["sides"]["long"]["orders"][2:])
    assert trailed["sides"]["long"]["orders"][0]["actual_avg_fill"] == D("100")
    assert trailed["sides"]["long"]["orders"][1]["actual_avg_fill"] == D("100")
