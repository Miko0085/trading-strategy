from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .migrations import ADDITIONS, SCHEMA_V2, SCHEMA_V3
from .schema import SCHEMA


class SQLiteStore:
    def __init__(self, path: str | Path, wal: bool = True):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._depth = 0
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("PRAGMA synchronous=FULL")
        if wal:
            self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")

    def _apply_additions(self) -> None:
        for table, columns in ADDITIONS.items():
            if not self.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone():
                continue
            existing = {row[1] for row in self.db.execute(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in existing:
                    self.db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def initialize(self) -> None:
        self.db.executescript(SCHEMA)
        with self.transaction():
            # raw_events_index gets capture_id here so SCHEMA_V2's index on it can be created.
            self._apply_additions()
            for statement in SCHEMA_V2.split(";"):
                if statement.strip():
                    self.db.execute(statement)
            self.db.execute(
                "INSERT OR IGNORE INTO schema_versions VALUES(2,?)",
                (datetime.now(UTC).isoformat(),),
            )
            for statement in SCHEMA_V3.split(";"):
                if statement.strip():
                    self.db.execute(statement)
            self.db.execute(
                "INSERT OR IGNORE INTO schema_versions VALUES(3,?)",
                (datetime.now(UTC).isoformat(),),
            )
            # Second pass covers additions targeting tables SCHEMA_V3 just created.
            self._apply_additions()

    def insert_execution(self, item: dict[str, Any]) -> bool:
        exec_id = item.get("execId")
        if not exec_id:
            raise ValueError("execution requires official execId")
        cur = self.db.execute(
            """INSERT OR IGNORE INTO executions(exec_id,order_id,symbol,exec_ts,exec_price,exec_qty,exec_pnl,raw_json) VALUES(?,?,?,?,?,?,?,?)""",
            (
                exec_id,
                item.get("orderId"),
                item.get("symbol"),
                item.get("execTime"),
                item.get("execPrice"),
                item.get("execQty"),
                item.get("execPnl"),
                json.dumps(item, ensure_ascii=False),
            ),
        )
        self._commit()
        return cur.rowcount == 1

    def insert_candle(self, item: dict[str, Any], source: str | None = None) -> bool:
        cur = self.db.execute(
            """INSERT INTO market_candles(symbol,interval,start_ms,end_ms,open,high,low,close,volume,turnover,confirm,exchange_ts,received_at,source)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(symbol,interval,start_ms) DO UPDATE SET end_ms=excluded.end_ms,open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,volume=excluded.volume,turnover=excluded.turnover,confirm=excluded.confirm,exchange_ts=excluded.exchange_ts,received_at=excluded.received_at,source=excluded.source""",
            (
                item.get("symbol"),
                str(item.get("interval")),
                item.get("start"),
                item.get("end"),
                item.get("open"),
                item.get("high"),
                item.get("low"),
                item.get("close"),
                item.get("volume"),
                item.get("turnover"),
                int(bool(item.get("confirm"))),
                item.get("timestamp", item.get("exchange_ts")),
                datetime.now(UTC).isoformat(),
                source or item.get("source", "WS"),
            ),
        )
        self._commit()
        return cur.rowcount > 0

    def insert_order_event(
        self, item: dict[str, Any], raw_message: dict[str, Any] | None = None
    ) -> bool:
        order_id = item.get("orderId")
        if not order_id:
            raise ValueError("order requires official orderId")
        raw = raw_message or item
        event_key = sha256(
            json.dumps(item, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        now = datetime.now(UTC).isoformat()
        self.db.execute(
            "INSERT OR IGNORE INTO orders(order_id,symbol,category,position_idx,first_seen,last_seen,raw_json) VALUES(?,?,?,?,?,?,?) ON CONFLICT(order_id) DO UPDATE SET last_seen=excluded.last_seen,raw_json=excluded.raw_json",
            (
                order_id,
                item.get("symbol"),
                item.get("category"),
                item.get("positionIdx"),
                now,
                now,
                json.dumps(raw, ensure_ascii=False),
            ),
        )
        cur = self.db.execute(
            "INSERT OR IGNORE INTO order_events(order_id,event_key,event_ts,order_status,raw_json) VALUES(?,?,?,?,?)",
            (
                order_id,
                event_key,
                item.get("updatedTime", item.get("createdTime")),
                item.get("orderStatus"),
                json.dumps(raw, ensure_ascii=False),
            ),
        )
        self._commit()
        return cur.rowcount == 1

    def insert_position(
        self, item: dict[str, Any], semantic_change: bool, raw_message: dict[str, Any] | None = None
    ) -> int:
        now = datetime.now(UTC).isoformat()
        cur = self.db.execute(
            "INSERT INTO positions(symbol,position_idx,event_ts,side,size,entry_price,mark_price,unrealised_pnl,raw_json) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                item.get("symbol"),
                item.get("positionIdx"),
                item.get("updatedTime", item.get("creationTime", now)),
                item.get("side"),
                item.get("size"),
                item.get("entryPrice"),
                item.get("markPrice"),
                item.get("unrealisedPnl", item.get("unrealizedPnl")),
                json.dumps(raw_message or item, ensure_ascii=False),
            ),
        )
        position_id = int(cur.lastrowid)
        self.db.execute(
            "INSERT INTO position_events(position_id,semantic_change,event_ts,raw_json) VALUES(?,?,?,?)",
            (
                position_id,
                int(semantic_change),
                item.get("updatedTime", now),
                json.dumps(raw_message or item, ensure_ascii=False),
            ),
        )
        self._commit()
        return position_id

    def insert_timeline(self, row: dict[str, Any]) -> int:
        cur = self.db.execute(
            "INSERT INTO timeline(timestamp_exchange,timestamp_received,event_type,symbol,source,source_id,summary_ru,linked_raw_event_id) VALUES(?,?,?,?,?,?,?,?)",
            (
                row.get("timestamp_exchange"),
                row.get("timestamp_received", datetime.now(UTC).isoformat()),
                row["event_type"],
                row.get("symbol"),
                row["source"],
                row.get("source_id"),
                row.get("summary_ru"),
                row.get("linked_raw_event_id"),
            ),
        )
        self._commit()
        return int(cur.lastrowid)

    def record_reconciliation(self, result: Any) -> int:
        cur = self.db.execute(
            "INSERT INTO reconciliation_runs(reason,started_at,finished_at,records_checked,missing_found,recovered,duplicates,errors,status) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                result.reason,
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat(),
                result.records_checked,
                result.missing_found,
                result.recovered,
                result.duplicates,
                json.dumps(result.errors or [], ensure_ascii=False),
                result.status,
            ),
        )
        self._commit()
        return int(cur.lastrowid)

    def start_websocket_session(self, session_id: str, source: str, connected_at: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO websocket_sessions(session_id,source,connected_at,reconnect_count) VALUES(?,?,?,COALESCE((SELECT reconnect_count FROM websocket_sessions WHERE session_id=?),0))",
            (session_id, source, connected_at, session_id),
        )
        self._commit()

    def finish_websocket_session(self, session_id: str, disconnected_at: str, reason: str) -> None:
        self.db.execute(
            "UPDATE websocket_sessions SET disconnected_at=?,reason=? WHERE session_id=?",
            (disconnected_at, reason, session_id),
        )
        self._commit()

    def table_rows(self, table: str) -> list[dict[str, Any]]:
        if not table.replace("_", "").isalnum():
            raise ValueError("invalid table name")
        return [dict(row) for row in self.db.execute(f"SELECT * FROM {table}")]

    def insert_voice_message(
        self,
        voice_id: str,
        telegram_message_id: str,
        telegram_file_id: str,
        received_at: str,
        duration: float | None,
        local_path: str,
        file_size: int,
        status: str,
    ) -> None:
        self.db.execute(
            "INSERT INTO voice_messages(voice_id,telegram_message_id,telegram_file_id,received_at,duration,local_path,file_size,transcription_status) VALUES(?,?,?,?,?,?,?,?)",
            (
                voice_id,
                telegram_message_id,
                telegram_file_id,
                received_at,
                duration,
                local_path,
                file_size,
                status,
            ),
        )
        self._commit()

    def insert_transcription(
        self, voice_id: str, transcript: str | None, language: str, status: str, error: str | None
    ) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO transcriptions(voice_id,transcript,language,status,error) VALUES(?,?,?,?,?)",
            (voice_id, transcript, language, status, error),
        )
        self._commit()

    def set_voice_status(self, voice_id: str, status: str) -> None:
        self.db.execute(
            "UPDATE voice_messages SET transcription_status=? WHERE voice_id=?", (status, voice_id)
        )
        self._commit()

    def close(self) -> None:
        self._commit()
        self.db.close()

    def _commit(self):
        if not self._depth:
            self.db.commit()

    @contextmanager
    def transaction(self):
        """No awaits inside: one message and its derived rows commit together."""
        outer = self._depth == 0
        if outer:
            self.db.execute("BEGIN IMMEDIATE")
        self._depth += 1
        try:
            yield
        except BaseException:
            if outer:
                self.db.rollback()
            raise
        else:
            if outer:
                self.db.commit()
        finally:
            self._depth -= 1

    def set_state(self, key, value):
        self.db.execute(
            "INSERT INTO collector_state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        self._commit()

    def get_state(self, key, default=None):
        row = self.db.execute("SELECT value FROM collector_state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def gap(self, kind, details, start_ms=None, end_ms=None):
        cur = self.db.execute(
            "INSERT INTO data_gaps(kind,start_ms,end_ms,details,created_at) VALUES(?,?,?,?,?)",
            (kind, start_ms, end_ms, details, datetime.now(UTC).isoformat()),
        )
        self._commit()
        return cur.lastrowid
