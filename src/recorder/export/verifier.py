import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from recorder.market.candles import next_start


def timestamp(value):
    if value is None or value == "":
        raise ValueError("missing timestamp")
    if str(value).isdigit():
        value = int(value)
        if value < 0:
            raise ValueError("negative timestamp")
        return datetime.fromtimestamp(value / 1000, UTC)
    date = datetime.fromisoformat(str(value))
    if date.tzinfo is None:
        raise ValueError("timezone missing")
    return date


def verify_raw(directory, database=None):
    problems = []
    indexed = None
    unindexed = 0
    legacy = 0
    if database and Path(database).exists():
        with closing(
            sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
        ) as db:
            columns = [r[1] for r in db.execute("PRAGMA table_info(raw_events_index)")]
            if "capture_id" in columns:
                indexed = {
                    r[0] for r in db.execute("SELECT capture_id FROM raw_events_index") if r[0]
                }

    paths = list(Path(directory).glob("*.jsonl"))
    if not paths:
        return ["WARNING: RAW files absent"]
    for path in paths:
        try:
            with path.open(encoding="utf-8") as handle:
                for number, line in enumerate(handle, 1):
                    try:
                        item = json.loads(line)
                        if not isinstance(item, dict) or not isinstance(item.get("payload"), dict):
                            raise TypeError("invalid envelope")
                        timestamp(item.get("received_at"))
                        if indexed is not None:
                            if not item.get("capture_id"):
                                legacy += 1
                            elif item["capture_id"] not in indexed:
                                unindexed += 1
                    except (ValueError, TypeError, OverflowError):
                        problems.append(
                            f"FAIL: RAW {path.name}:{number} invalid JSON/envelope/timestamp"
                        )
        except (OSError, UnicodeError):
            problems.append(f"FAIL: RAW {path.name} unreadable")
    if unindexed:
        problems.append(f"WARNING: RAW captures not indexed in SQLite: {unindexed}")
    if legacy:
        problems.append(f"WARNING: legacy RAW without capture identity: {legacy}")
    return problems


def verify_sqlite(path):
    path = Path(path)
    if not path.is_file():
        return ["FAIL: SQLite file missing"]
    problems = []
    try:
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            problems.append("FAIL: SQLite integrity")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        def count(sql):
            return db.execute(sql).fetchone()[0]

        checks = [
            (
                "executions",
                "SELECT COUNT(*) FROM executions e WHERE NOT EXISTS(SELECT 1 FROM timeline t WHERE t.event_type='EXECUTION' AND t.source_id=e.exec_id)",
                "FAIL: executions without timeline",
            ),
            (
                "market_snapshots",
                "SELECT COUNT(*) FROM market_snapshots s LEFT JOIN timeline t ON t.id=s.account_event_id WHERE t.id IS NULL",
                "FAIL: orphan market snapshot",
            ),
            (
                "market_snapshots",
                "SELECT COUNT(*) FROM market_snapshots WHERE last_price IS NULL OR mark_price IS NULL",
                "WARNING: incomplete market snapshots",
            ),
            (
                "transcriptions",
                "SELECT COUNT(*) FROM transcriptions t LEFT JOIN voice_messages v ON v.voice_id=t.voice_id WHERE v.voice_id IS NULL",
                "FAIL: orphan transcription",
            ),
            (
                "executions",
                "SELECT COUNT(*) FROM (SELECT exec_id FROM executions GROUP BY exec_id HAVING COUNT(*)>1)",
                "FAIL: duplicate executions",
            ),
            (
                "executions",
                "SELECT COUNT(*) FROM executions e LEFT JOIN orders o ON o.order_id=e.order_id WHERE o.order_id IS NULL",
                "WARNING: orphan executions",
            ),
            (
                "trader_note_links",
                "SELECT COUNT(*) FROM trader_note_links l LEFT JOIN trader_notes n ON n.id=l.note_id LEFT JOIN timeline t ON t.id=l.timeline_id WHERE n.id IS NULL OR t.id IS NULL",
                "FAIL: orphan note links",
            ),
            (
                "transcriptions",
                "SELECT COUNT(*) FROM transcriptions WHERE status IN ('pending','failed')",
                "WARNING: pending/failed transcriptions",
            ),
            (
                "reconciliation_runs",
                "SELECT COUNT(*) FROM reconciliation_runs WHERE status!='ok' OR status IS NULL",
                "WARNING: incomplete reconciliation",
            ),
            (
                "data_gaps",
                "SELECT COUNT(*) FROM data_gaps WHERE resolved=0",
                "WARNING: unresolved data gaps",
            ),
            (
                "websocket_sessions",
                "SELECT COUNT(*) FROM websocket_sessions WHERE disconnected_at IS NOT NULL",
                "WARNING: websocket disconnect history; review recovery",
            ),
        ]
        for table, sql, label in checks:
            if table in tables:
                n = count(sql)
                if n:
                    problems.append(f"{label}: {n}")
        if "data_gaps" not in tables:
            problems.append("WARNING: legacy schema lacks data-gap audit")
        if "executions" in tables:
            for row in db.execute("SELECT exec_id,exec_ts FROM executions"):
                try:
                    timestamp(row["exec_ts"])
                except (ValueError, TypeError, OverflowError):
                    problems.append(f"FAIL: execution {row['exec_id']} invalid timestamp")
        if "timeline" in tables:
            for row in db.execute("SELECT id,timestamp_received,timestamp_exchange FROM timeline"):
                try:
                    timestamp(row["timestamp_received"])
                    if row["timestamp_exchange"]:
                        timestamp(row["timestamp_exchange"])
                except (ValueError, TypeError, OverflowError):
                    problems.append(f"FAIL: timeline {row['id']} invalid timestamp")
        if "voice_messages" in tables:
            for row in db.execute("SELECT * FROM voice_messages"):
                media = Path(row["local_path"] or "")
                if not media.is_absolute():
                    media = path.parent / media
                if not media.is_file():
                    problems.append(f"FAIL: missing voice file {row['voice_id']}")
                elif media.stat().st_size != row["file_size"]:
                    problems.append(f"FAIL: voice file size mismatch {row['voice_id']}")
                if row["transcription_status"] != "completed":
                    problems.append(f"WARNING: voice {row['voice_id']} transcription incomplete")
                if "note_id" in list(row.keys()) and (
                    not row["note_id"]
                    or not db.execute(
                        "SELECT 1 FROM trader_notes WHERE id=?", (row["note_id"],)
                    ).fetchone()
                ):
                    problems.append(f"FAIL: voice {row['voice_id']} note link missing")
        if "market_candles" in tables:
            previous = {}
            for row in db.execute("SELECT * FROM market_candles ORDER BY symbol,interval,start_ms"):
                key = (row["symbol"], row["interval"])
                try:
                    expected = next_start(row["start_ms"], row["interval"]) - 1
                    if row["end_ms"] != expected or row["confirm"] != 1:
                        problems.append(f"FAIL: candle bounds/confirm {key} {row['start_ms']}")
                    if key in previous and previous[key] != row["start_ms"]:
                        problems.append(
                            f"WARNING: candle gap {key} {previous[key]}..{row['start_ms']}"
                        )
                    previous[key] = expected + 1
                except (ValueError, TypeError, OverflowError):
                    problems.append(f"FAIL: invalid candle {key}")
            if not previous:
                problems.append("WARNING: no closed candles; continuity unverified")
        if "observations" in tables:
            n = count(
                "SELECT COUNT(*) FROM observations o LEFT JOIN raw_events_index r ON r.id=o.raw_id WHERE r.id IS NULL"
            )
            if n:
                problems.append(f"WARNING: observations without RAW provenance: {n}")
        if "raw_events_index" in tables:
            for row in db.execute("SELECT * FROM raw_events_index"):
                raw = Path(row["path"])
                if not raw.is_absolute():
                    raw = path.parent / raw
                if not raw.is_file():
                    problems.append(f"FAIL: indexed RAW absent #{row['id']}")
                elif "byte_offset" in list(row.keys()) and row["byte_offset"] is not None:
                    with raw.open("rb") as handle:
                        handle.seek(row["byte_offset"])
                        data = handle.read(row["byte_length"])
                    try:
                        payload = json.loads(data)
                        if payload.get("capture_id") != row["capture_id"]:
                            raise ValueError()
                    except ValueError:
                        problems.append(f"FAIL: RAW index mismatch #{row['id']}")
                if "status" in list(row.keys()) and row["status"] in {
                    "pending",
                    "failed",
                    "legacy",
                    "source_error",
                }:
                    problems.append(f"WARNING: RAW #{row['id']} ingestion {row['status']}")
    except (sqlite3.Error, OSError) as exc:
        problems.append(f"FAIL: dataset read error {type(exc).__name__}")
    finally:
        if "db" in locals():
            db.close()
    return problems


def report(problems):
    return {
        "status": "FAIL"
        if any(p.startswith("FAIL:") for p in problems)
        else "WARNING"
        if problems
        else "PASS",
        "problems": problems,
    }


def verify_bundle(directory):
    root = Path(directory)
    problems = verify_sqlite(root / "snapshot.sqlite") + verify_raw(
        root / "raw", root / "snapshot.sqlite"
    )
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for name, digest in manifest["sha256"].items():
            path = root / name
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("unsafe manifest path")
            if not path.is_file():
                problems.append(f"FAIL: export checksum {name}")
            else:
                with path.open("rb") as handle:
                    if hashlib.file_digest(handle, "sha256").hexdigest() != digest:
                        problems.append(f"FAIL: export checksum {name}")
        import pyarrow.parquet as pq

        for path in root.glob("*.parquet"):
            metadata = pq.read_metadata(path)
            if path.name not in manifest["sha256"]:
                problems.append(f"FAIL: unlisted export file {path.name}")
            expected = manifest.get("table_counts", {}).get(path.stem)
            if expected is not None and metadata.num_rows != expected:
                problems.append(f"FAIL: export row count {path.name}")
            for _ in pq.ParquetFile(path).iter_batches(batch_size=10000):
                pass
        for table in manifest.get("table_counts", {}):
            if f"{table}.parquet" not in manifest["sha256"]:
                problems.append(f"FAIL: missing manifest table {table}")
        for required in ("snapshot.sqlite", "config.json", "market_1m.parquet", "wallet.parquet"):
            if required not in manifest["sha256"]:
                problems.append(f"FAIL: missing manifest artifact {required}")
    except Exception as exc:  # noqa: BLE001 -- failure boundary records errors and preserves source data
        problems.append(f"FAIL: export verification {type(exc).__name__}")
    return report(problems)
