from __future__ import annotations

import json
from typing import Any


class RevisionRepository:
    """Atomic PostgreSQL persistence for immutable revisions and their projections."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        import psycopg

        return psycopg.connect(self.database_url)

    def save(self, symbol: str, comment: str, payload: dict[str, Any], *, environment: str) -> dict[str, Any]:
        configuration = payload.get("configuration", payload)
        allocation = configuration.get("allocation", {})
        validation_state = payload.get("calculation", {}).get("validation_state", "BLOCKED")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (symbol,))
                cursor.execute("SELECT id FROM ui_accounts WHERE name=%s AND environment=%s FOR UPDATE", ("Manual Grid", environment))
                account = cursor.fetchone()
                if account is None:
                    cursor.execute("INSERT INTO ui_accounts(name,environment) VALUES(%s,%s) RETURNING id", ("Manual Grid", environment))
                    account = cursor.fetchone()
                cursor.execute("SELECT id FROM grids WHERE account_id=%s AND symbol=%s FOR UPDATE", (account[0], symbol))
                grid = cursor.fetchone()
                if grid is None:
                    cursor.execute("INSERT INTO grids(account_id,symbol) VALUES(%s,%s) RETURNING id", (account[0], symbol))
                    grid = cursor.fetchone()
                cursor.execute("SELECT id,revision_no,payload FROM grid_revisions WHERE grid_id=%s ORDER BY revision_no DESC LIMIT 1 FOR UPDATE", (grid[0],))
                previous = cursor.fetchone()
                number = (previous[1] if previous else 0) + 1
                market_snapshot = payload.get("market_snapshot", {})
                cursor.execute("INSERT INTO grid_revisions(grid_id,revision_no,payload,market_snapshot,comment,validation_state,validation_errors) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id,created_at", (grid[0], number, json.dumps(payload), json.dumps(market_snapshot), comment, validation_state, json.dumps(payload.get("calculation", {}).get("validation_errors", []))))
                revision_id, created_at = cursor.fetchone()
                for side in ("long", "short"):
                    for level, order in enumerate(configuration.get(side, []), start=1):
                        cursor.execute("INSERT INTO grid_order_configs(revision_id,side,level,entry_offset_pct,configured_qty,note) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id", (revision_id, side, level, order.get("offset_pct"), order.get("qty"), order.get("note", "")))
                        order_id = cursor.fetchone()[0]
                        for step, tp in enumerate(order.get("tps", []), start=1):
                            cursor.execute("INSERT INTO tp_step_configs(order_config_id,step_no,move_pct,close_pct) VALUES(%s,%s,%s,%s)", (order_id, step, tp.get("move_pct"), tp.get("close_pct")))
                cursor.execute("INSERT INTO allocation_configs(revision_id,long_pct,short_pct,reserve_pct,active_long_count,active_short_count) VALUES(%s,%s,%s,%s,%s,%s)", (revision_id, allocation.get("long_pct"), allocation.get("short_pct"), allocation.get("reserve_pct"), configuration.get("active_long_count", 1), configuration.get("active_short_count", 1)))
                cursor.execute("INSERT INTO account_snapshots(account_id,symbol,payload) VALUES(%s,%s,%s)", (account[0], symbol, json.dumps(market_snapshot)))
                cursor.execute("INSERT INTO audit_events(account_id,entity,entity_type,entity_id,side,action,before_payload,after_payload) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (account[0], symbol, "grid_revision", str(revision_id), None, "revision_saved", json.dumps(previous[2]) if previous else None, json.dumps(payload)))
                self._write_change_audits(cursor, account[0], symbol, previous[2] if previous else None, payload)
        return {"id": str(revision_id), "symbol": symbol, "comment": comment, "payload": payload, "validation_state": validation_state, "created_at": created_at.isoformat()}

    @staticmethod
    def _write_change_audits(cursor, account_id, symbol: str, previous: dict[str, Any] | None, current: dict[str, Any]) -> None:
        before = (previous or {}).get("configuration", previous or {})
        after = current.get("configuration", current)

        def event(entity_type: str, entity_id: str, side: str | None, action: str, old: Any, new: Any) -> None:
            cursor.execute("INSERT INTO audit_events(account_id,entity,entity_type,entity_id,side,action,before_payload,after_payload) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (account_id, symbol, entity_type, entity_id, side, action, json.dumps(old), json.dumps(new)))

        if previous and before.get("allocation") != after.get("allocation"):
            event("allocation", "allocation", None, "allocation_changed", before.get("allocation"), after.get("allocation"))
        for side in ("long", "short"):
            old_orders = {item.get("id") or f"level-{index}": item for index, item in enumerate(before.get(side, []), start=1)}
            new_orders = {item.get("id") or f"level-{index}": item for index, item in enumerate(after.get(side, []), start=1)}
            for entity_id in new_orders.keys() - old_orders.keys():
                event("grid_order", entity_id, side, "grid_order_added", None, new_orders[entity_id])
            for entity_id in old_orders.keys() - new_orders.keys():
                event("grid_order", entity_id, side, "grid_order_deleted", old_orders[entity_id], None)
            for entity_id in new_orders.keys() & old_orders.keys():
                old_order, new_order = old_orders[entity_id], new_orders[entity_id]
                for field, action in (("offset_pct", "grid_order_offset_changed"), ("qty", "grid_order_qty_changed"), ("note", "note_changed")):
                    if old_order.get(field) != new_order.get(field):
                        event("grid_order", entity_id, side, action, {field: old_order.get(field)}, {field: new_order.get(field)})
                if old_order.get("tps") != new_order.get("tps"):
                    event("tp_step", entity_id, side, "tp_changed", old_order.get("tps"), new_order.get("tps"))

    def list(self, symbol: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            query = "SELECT r.id,g.symbol,r.comment,r.payload,r.validation_state,r.created_at FROM grid_revisions r JOIN grids g ON g.id=r.grid_id"
            params: tuple[Any, ...] = ()
            if symbol:
                query += " WHERE g.symbol=%s"
                params = (symbol,)
            query += " ORDER BY r.created_at DESC"
            cursor.execute(query, params)
            return [{"id": str(row[0]), "symbol": row[1], "comment": row[2], "payload": row[3], "validation_state": row[4], "created_at": row[5].isoformat()} for row in cursor.fetchall()]

    def save_shadow_revision(self, symbol: str, evaluation: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO shadow_grid_revisions(symbol,trigger,revision_type,status,payload,capital_snapshot) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id,created_at", (symbol, evaluation["trigger"], evaluation["revision_type"], "VIRTUAL", json.dumps(evaluation), json.dumps(evaluation.get("after", {}).get("capital_snapshot", {}))))
            revision_id, created_at = cursor.fetchone()
        return {"id": str(revision_id), "symbol": symbol, "trigger": evaluation["trigger"], "revision_type": evaluation["revision_type"], "status": "VIRTUAL", "created_at": created_at.isoformat(), "payload": evaluation}

    def save_apply_audit(self, symbol: str, payload: dict[str, Any], *, environment: str) -> dict[str, Any]:
        """Persist a local generated-grid intention; this never talks to Bybit."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id FROM ui_accounts WHERE name=%s AND environment=%s FOR UPDATE", ("Manual Grid", environment))
            account = cursor.fetchone()
            if account is None:
                cursor.execute("INSERT INTO ui_accounts(name,environment) VALUES(%s,%s) RETURNING id", ("Manual Grid", environment))
                account = cursor.fetchone()
            entity_id = str(payload.get("event_id") or "generated-grid-apply")
            cursor.execute("INSERT INTO audit_events(account_id,entity,entity_type,entity_id,side,action,before_payload,after_payload) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (account[0], symbol, "grid_order", entity_id, payload.get("side"), "generated_grid_applied", json.dumps(payload.get("before")), json.dumps(payload.get("after"))))
        return {"symbol": symbol, "entity_id": entity_id, "action": "generated_grid_applied"}

    def list_shadow_revisions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            if symbol:
                cursor.execute("SELECT id,symbol,trigger,revision_type,status,payload,created_at FROM shadow_grid_revisions WHERE symbol=%s ORDER BY created_at DESC", (symbol,))
            else:
                cursor.execute("SELECT id,symbol,trigger,revision_type,status,payload,created_at FROM shadow_grid_revisions ORDER BY created_at DESC")
            return [{"id": str(row[0]), "symbol": row[1], "trigger": row[2], "revision_type": row[3], "status": row[4], "payload": row[5], "created_at": row[6].isoformat()} for row in cursor.fetchall()]

    def audit(self, filter_name: str = "all") -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            query = "SELECT id,created_at,entity_type,entity_id,side,action,before_payload,after_payload FROM audit_events"
            params: tuple[Any, ...] = ()
            if filter_name in {"long", "short"}:
                query += " WHERE side=%s"
                params = (filter_name,)
            elif filter_name == "orders":
                query += " WHERE entity_type='grid_order'"
            elif filter_name == "take_profit":
                query += " WHERE entity_type='tp_step'"
            elif filter_name == "capital":
                query += " WHERE entity_type='allocation'"
            elif filter_name == "grid":
                query += " WHERE entity_type IN ('grid_revision','grid_order')"
            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            return [{"id": str(row[0]), "created_at": row[1].isoformat(), "entity_type": row[2], "entity_id": row[3], "side": row[4], "action": row[5], "before": row[6], "after": row[7]} for row in cursor.fetchall()]
