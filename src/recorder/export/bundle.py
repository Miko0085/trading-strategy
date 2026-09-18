import hashlib
import json
import re
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from recorder.export.manifest import write_manifest
from recorder.export.parquet import export_sqlite
from recorder.export.verifier import report, verify_raw, verify_sqlite


def export_bundle(db_path, raw_dir, destination, experiment_id, symbols, config):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", experiment_id):
        raise ValueError("experiment_id: only letters/digits/_/-")
    root = Path(destination) / experiment_id
    root.mkdir(parents=True, exist_ok=False)
    snapshot = root / "snapshot.sqlite"
    source = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    db = sqlite3.connect(snapshot)
    try:
        source.backup(db)
    finally:
        source.close()
    db.row_factory = sqlite3.Row
    try:
        (root / "raw").mkdir()
        (root / "voice").mkdir()
        # Copy a fixed complete-line prefix. Concurrent later RAW may be a superset of SQLite.
        paths = {
            Path(r[0]) for r in db.execute("SELECT DISTINCT path FROM raw_events_index")
        } | set(Path(raw_dir).glob("*.jsonl"))
        mapping = {}
        for path in paths:
            if not path.is_file():
                continue
            name = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:12] + "-" + path.name
            target = root / "raw" / name
            limit = path.stat().st_size
            with path.open("rb") as reader, target.open("xb") as writer:
                remaining = limit
                while remaining > 0:
                    line = reader.readline(remaining)
                    remaining -= len(line)
                    if not line or not line.endswith(b"\n"):
                        break
                    writer.write(line)
            mapping[str(path)] = str(Path("raw") / name)
        for origin, target in mapping.items():
            db.execute("UPDATE raw_events_index SET path=? WHERE path=?", (target, origin))
        for row in db.execute("SELECT voice_id,local_path FROM voice_messages").fetchall():
            path = Path(row["local_path"])
            if path.is_file():
                target = Path("voice") / (row["voice_id"] + path.suffix)
                shutil.copyfile(path, root / target)
                db.execute(
                    "UPDATE voice_messages SET local_path=? WHERE voice_id=?",
                    (str(target), row["voice_id"]),
                )
        db.commit()
        tables = [
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        export_sqlite(SimpleNamespace(db=db), root, tables)
        # Required analysis-friendly names; every interval remains in market_candles.
        import pyarrow.compute as pc
        import pyarrow.parquet as pq

        candles = pq.read_table(root / "market_candles.parquet")
        pq.write_table(
            candles.filter(pc.equal(candles["interval"], "1")), root / "market_1m.parquet"
        )
        shutil.copyfile(root / "wallet_snapshots.parquet", root / "wallet.parquet")

        def count(table, where=""):
            return db.execute(f"SELECT COUNT(*) FROM {table} " + where).fetchone()[0]

        times = db.execute(
            "SELECT MIN(timestamp_received),MAX(timestamp_received) FROM timeline"
        ).fetchone()
        gaps = (
            [dict(r) for r in db.execute("SELECT * FROM data_gaps WHERE resolved=0")]
            if "data_gaps" in tables
            else [{"kind": "legacy_unknown"}]
        )
        counts = {t: count(t) for t in tables}
        observed_symbols = {
            r[0]
            for r in db.execute("SELECT DISTINCT symbol FROM timeline WHERE symbol IS NOT NULL")
        }
        instruments = (
            [
                dict(r)
                for r in db.execute("SELECT * FROM tracked_instruments ORDER BY category,symbol")
            ]
            if "tracked_instruments" in tables
            else []
        )
        observed_symbols.update(i["symbol"] for i in instruments)
        config_snapshot = {"symbols": symbols, "recorder": config}
        (root / "config.json").write_text(
            json.dumps(config_snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        verification = report(verify_sqlite(snapshot) + verify_raw(root / "raw", snapshot))
        raw_count = 0
        for raw_path in (root / "raw").glob("*.jsonl"):
            with raw_path.open("rb") as handle:
                raw_count += sum(1 for _ in handle)
        manifest = {
            "dataset_version": "2",
            "schema_version": (
                db.execute("SELECT MAX(version) FROM schema_versions").fetchone()[0]
                if "schema_versions" in tables
                else None
            ),
            "experiment_id": experiment_id,
            "exchange": "bybit",
            "category": symbols["category"],
            "symbols": sorted(set(symbols["symbols"]) | observed_symbols),
            "configured_symbols": symbols["symbols"],
            "tracked_instruments": instruments,
            "account_capture_scope": "all private WS symbols; REST history in configured category",
            "timezone": "UTC",
            "collector_version": "0.2.0",
            "experiment_start": times[0],
            "experiment_end": times[1],
            "exported_at": datetime.now(UTC).isoformat(),
            "config_reference": "config.json",
            "table_counts": counts,
            "raw_event_count": raw_count,
            "order_event_count": counts.get("order_events", 0),
            "execution_count": counts.get("executions", 0),
            "position_event_count": counts.get("position_events", 0),
            "trader_note_count": counts.get("trader_notes", 0),
            "verified_note_count": count("trader_notes", "WHERE verified=1"),
            "voice_note_count": counts.get("voice_messages", 0),
            "websocket_disconnect_count": count(
                "websocket_sessions", "WHERE disconnected_at IS NOT NULL"
            ),
            "reconciliation_runs": counts.get("reconciliation_runs", 0),
            "reconciliation_failures": count("reconciliation_runs", "WHERE status='data_gap'"),
            "known_data_gaps": gaps,
            "dataset_verification_status": verification["status"],
            "verification": verification,
            "raw_scope": "Complete-line RAW prefix may include events received after the SQLite snapshot",
        }
    finally:
        db.close()
    hashes = {}
    for path in root.rglob("*"):
        if path.is_file():
            with path.open("rb") as handle:
                hashes[str(path.relative_to(root))] = hashlib.file_digest(
                    handle, "sha256"
                ).hexdigest()
    manifest["sha256"] = hashes
    write_manifest(root, manifest)
    return root
