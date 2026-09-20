from __future__ import annotations

import json
from typing import Any


class RevisionRepository:
    """Small PostgreSQL repository kept inside the isolated UI module."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        import psycopg

        return psycopg.connect(self.database_url)

    def save(self, symbol: str, comment: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM ui_accounts ORDER BY created_at LIMIT 1")
                account = cursor.fetchone()
                if account is None:
                    cursor.execute("INSERT INTO ui_accounts(name,environment) VALUES(%s,%s) RETURNING id", ("Manual Grid", "testnet"))
                    account = cursor.fetchone()
                cursor.execute("SELECT id FROM grids WHERE account_id=%s AND symbol=%s", (account[0], symbol))
                grid = cursor.fetchone()
                if grid is None:
                    cursor.execute("INSERT INTO grids(account_id,symbol) VALUES(%s,%s) RETURNING id", (account[0], symbol))
                    grid = cursor.fetchone()
                cursor.execute("SELECT COALESCE(MAX(revision_no), 0) + 1 FROM grid_revisions WHERE grid_id=%s", (grid[0],))
                number = cursor.fetchone()[0]
                snapshot = payload.get("market_snapshot", {})
                cursor.execute("INSERT INTO grid_revisions(grid_id,revision_no,payload,market_snapshot,comment) VALUES(%s,%s,%s,%s,%s) RETURNING id,created_at", (grid[0], number, json.dumps(payload), json.dumps(snapshot), comment))
                revision_id, created_at = cursor.fetchone()
                cursor.execute("INSERT INTO audit_events(account_id,entity,action,after_payload) VALUES(%s,%s,%s,%s)", (account[0], symbol, "revision_saved", json.dumps(payload)))
        return {"id": str(revision_id), "symbol": symbol, "comment": comment, "payload": payload, "created_at": created_at.isoformat()}

    def list(self, symbol: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            query = "SELECT r.id,g.symbol,r.comment,r.payload,r.created_at FROM grid_revisions r JOIN grids g ON g.id=r.grid_id"
            params: tuple[Any, ...] = ()
            if symbol:
                query += " WHERE g.symbol=%s"
                params = (symbol,)
            query += " ORDER BY r.created_at DESC"
            cursor.execute(query, params)
            return [{"id": str(row[0]), "symbol": row[1], "comment": row[2], "payload": row[3], "created_at": row[4].isoformat()} for row in cursor.fetchall()]
