import asyncio

from recorder.events.models import RawEvent
from recorder.storage.raw_jsonl import RawJsonlWriter
from recorder.storage.sqlite import SQLiteStore


def test_raw_jsonl(tmp_path):
    writer = RawJsonlWriter(tmp_path / "raw")
    path = asyncio.run(
        writer.write(RawEvent(source="test", topic="execution", payload={"unknown": 1}))
    )
    assert writer.read(path)[0]["payload"]["unknown"] == 1


def test_sqlite_wal_and_execution_idempotency(tmp_path):
    store = SQLiteStore(tmp_path / "x.db")
    store.initialize()
    assert store.db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    item = {"execId": "e1", "orderId": "o1", "symbol": "SUIUSDT", "execQty": "1"}
    assert store.insert_execution(item) is True
    assert store.insert_execution(item) is False
    store.close()
