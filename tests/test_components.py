import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from recorder.bybit.reconciliation import reconcile_executions
from recorder.bybit.rest import ReadOnlyBybitRest
from recorder.events.queue import ControlledWriter
from recorder.export.manifest import write_manifest
from recorder.export.verifier import verify_raw, verify_sqlite
from recorder.market.candles import missing_candle_starts
from recorder.storage.sqlite import SQLiteStore
from recorder.telegram.bot import TelegramBot
from recorder.telegram.linking import candidate_event_ids
from recorder.telegram.notes import replace_note_links, save_text_note, verify_note


def test_missing_candles_and_time_window():
    assert missing_candle_starts([0, 60_000, 180_000], 60_000) == [120_000]
    now = datetime.now(UTC)
    assert candidate_event_ids(
        now, [(1, now - timedelta(minutes=2)), (2, now + timedelta(minutes=2))], 3, 3
    ) == [1, 2]


def test_controlled_writer_drains_in_order():
    seen = []

    async def handler(event):
        seen.append(event["id"])

    async def run():
        writer = ControlledWriter(handler)
        task = asyncio.create_task(writer.run())
        for value in range(3):
            await writer.put({"id": value})
        await writer.drain()
        await task

    asyncio.run(run())
    assert seen == [0, 1, 2]


def test_reconciliation_failure_is_data_gap():
    async def broken():
        raise RuntimeError("REST unavailable")

    result = asyncio.run(reconcile_executions(broken, set(), lambda _: None, "reconnect"))
    assert result.status == "data_gap"
    assert result.errors == ["RuntimeError"]  # External exception text can contain credentials.


def test_telegram_allowlist_supports_group_and_user():
    bot = TelegramBot("token", set(), None, allowed_chat_ids={-1001})
    assert bot.allowed({"message": {"chat": {"id": -1001}, "from": {"id": 42}}})
    assert not bot.allowed({"message": {"chat": {"id": -1002}, "from": {"id": 42}}})


def test_note_verification_and_relinking(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    event_id = store.insert_timeline(
        {"event_type": "EXECUTION", "source": "test", "source_id": "e1"}
    )
    note_id = save_text_note(store, "Пояснение", [event_id])
    verify_note(store, note_id)
    assert (
        store.db.execute("SELECT verified FROM trader_notes WHERE id=?", (note_id,)).fetchone()[0]
        == 1
    )
    replace_note_links(store, note_id, [])
    assert (
        store.db.execute("SELECT verified FROM trader_notes WHERE id=?", (note_id,)).fetchone()[0]
        == 0
    )
    assert (
        store.db.execute(
            "SELECT COUNT(*) FROM trader_note_links WHERE note_id=?", (note_id,)
        ).fetchone()[0]
        == 0
    )
    store.close()


def test_manifest_raw_and_sqlite_verifier(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "day.jsonl").write_text(
        '{"received_at":"2026-09-14T00:00:00+00:00","payload": {"ok": true}}\n', encoding="utf-8"
    )
    assert verify_raw(raw) == []
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    store.close()
    assert any("no closed candles" in p for p in verify_sqlite(tmp_path / "db.sqlite"))
    manifest = write_manifest(tmp_path / "export", {"dataset_verification_status": "PASS"})
    assert manifest.exists()


def test_rest_write_paths_are_rejected():
    client = ReadOnlyBybitRest("key", "secret")
    with pytest.raises(ValueError):
        asyncio.run(client.get("/v5/order/create", {}))
