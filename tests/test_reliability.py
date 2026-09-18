import asyncio
import hashlib
import hmac
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from recorder.bybit.rest import BybitError, ReadOnlyBybitRest
from recorder.bybit.ws_common import BybitWebSocketCollector
from recorder.events.ingestion import EventIngestor
from recorder.events.models import RawEvent
from recorder.events.queue import ControlledWriter
from recorder.events.replay import replay
from recorder.export.bundle import export_bundle
from recorder.export.verifier import verify_bundle, verify_sqlite
from recorder.storage.raw_jsonl import RawJsonlWriter
from recorder.storage.schema import SCHEMA
from recorder.storage.sqlite import SQLiteStore
from recorder.telegram.notes import edit_note, save_text_note, verify_note
from recorder.telegram.voice import VoiceService


@pytest.fixture
def store(tmp_path):
    db = SQLiteStore(tmp_path / "db.sqlite")
    db.initialize()
    yield db
    db.close()


async def captured(tmp_path, topic, data, **extra):
    return await RawJsonlWriter(tmp_path / "raw").capture(
        RawEvent(
            source="bybit_private",
            topic=topic,
            payload={"topic": topic, "creationTime": 1720000000000, "data": data, **extra},
        )
    )


@pytest.mark.asyncio
async def test_atomic_message_rollback_raw_survives_and_replay(store, tmp_path, monkeypatch):
    event = await captured(
        tmp_path,
        "execution",
        [
            {
                "execId": "e1",
                "orderId": "o1",
                "symbol": "SUIUSDT",
                "execTime": "1720000000000",
                "execPrice": "1.123456789123456789",
                "execQty": "0.1",
            },
            {
                "execId": "e2",
                "orderId": "o1",
                "symbol": "SUIUSDT",
                "execTime": "1720000000001",
                "execQty": "0.2",
            },
        ],
    )
    ingestor = EventIngestor(store)
    original = store.insert_timeline

    def broken(row):
        raise RuntimeError("injected timeline failure")

    monkeypatch.setattr(store, "insert_timeline", broken)
    with pytest.raises(RuntimeError):
        await ingestor.handle(event)
    assert store.db.execute("SELECT COUNT(*) FROM executions").fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
    assert Path(event["raw_path"]).exists()
    monkeypatch.setattr(store, "insert_timeline", original)
    assert await ingestor.handle(event) == 2
    assert await ingestor.handle(event) == 0
    assert store.db.execute("SELECT COUNT(*) FROM timeline").fetchone()[0] == 2
    rebuilt = SQLiteStore(tmp_path / "replayed.sqlite")
    rebuilt.initialize()
    try:
        result = await replay(tmp_path / "raw", EventIngestor(rebuilt))
        assert result["failed"] == 0 and result["processed"] == 2
        assert await replay(tmp_path / "raw", EventIngestor(rebuilt)) == {
            "processed": 0,
            "failed": 0,
            "unsupported": 0,
        }
        assert rebuilt.table_rows("executions") == store.table_rows("executions")
    finally:
        rebuilt.close()


@pytest.mark.asyncio
async def test_writer_continues_and_fatal_unblocks():
    seen = []

    async def handler(item):
        if item == "bad":
            raise ValueError("bad")
        seen.append(item)
        return item

    writer = ControlledWriter(handler)
    task = asyncio.create_task(writer.run())
    with pytest.raises(ValueError):
        await writer.submit("bad")
    assert await writer.submit("good") == "good"
    await asyncio.wait_for(writer.drain(), 1)
    await task
    assert seen == ["good"]

    def fatal(item, exc):
        raise OSError("storage offline")

    writer = ControlledWriter(handler, on_error=fatal)
    task = asyncio.create_task(writer.run())
    with pytest.raises(ValueError):
        await asyncio.wait_for(writer.submit("bad"), 1)
    with pytest.raises(OSError):
        await asyncio.wait_for(writer.drain(), 1)
    assert task.done()


def test_exact_rest_signature_and_no_public_credentials(monkeypatch):
    monkeypatch.setattr("recorder.bybit.rest.time.time", lambda: 1720000000)
    rest = ReadOnlyBybitRest("key", "secret")
    url, headers = rest.request_parts(
        "/v5/execution/list", {"symbol": None, "category": "linear", "cursor": "a+/=& b"}
    )
    query = str(url).split("?", 1)[1]
    assert query == "category=linear&cursor=a%2B%2F%3D%26+b"
    assert (
        headers["X-BAPI-SIGN"]
        == hmac.new(
            b"secret", ("1720000000000key5000" + query).encode(), hashlib.sha256
        ).hexdigest()
    )
    assert rest.request_parts("/v5/market/time", {})[1] == {}
    with pytest.raises(ValueError):
        rest.request_parts("/v5/order/cancel", {})


@pytest.mark.asyncio
async def test_rest_error_captured_readonly_and_cursor_validation(tmp_path):
    raw = RawJsonlWriter(tmp_path / "raw")
    rest = ReadOnlyBybitRest(capture=raw.capture)

    async def response(url, headers):
        return {"retCode": 10003, "result": {}}

    rest._request = response
    with pytest.raises(BybitError):
        await rest.get("/v5/position/list", {})
    assert rest.last_capture["payload"]["retCode"] == 10003

    async def writable(url, headers):
        return {"retCode": 0, "result": {"readOnly": 0}}

    rest._request = writable
    with pytest.raises(PermissionError):
        await rest.validate_read_only()

    async def repeating(url, headers):
        return {"retCode": 0, "result": {"list": [], "nextPageCursor": "same"}}

    rest._request = repeating
    with pytest.raises(BybitError, match="REPEATED_CURSOR"):
        async for _ in rest.pages("/v5/execution/list", {}):
            pass


@pytest.mark.asyncio
async def test_wallet_hedge_pnl_and_snapshot(store, tmp_path):
    ingestor = EventIngestor(store)
    await ingestor.handle(
        await captured(
            tmp_path,
            "tickers.SUIUSDT",
            {"symbol": "SUIUSDT", "lastPrice": "1.20", "markPrice": "1.21"},
            type="snapshot",
        )
    )
    await ingestor.handle(
        await captured(
            tmp_path,
            "wallet",
            [
                {
                    "accountType": "UNIFIED",
                    "totalEquity": "100.00000000000001",
                    "totalWalletBalance": "90",
                    "totalAvailableBalance": "",
                    "totalPerpUPL": "10",
                    "coin": [
                        {
                            "coin": "USDT",
                            "walletBalance": "90",
                            "unrealisedPnl": "10",
                            "cumRealisedPnl": "2",
                        }
                    ],
                }
            ],
        )
    )
    await ingestor.handle(
        await captured(
            tmp_path,
            "wallet",
            [{"accountType": "UNIFIED", "coin": [{"coin": "BTC", "walletBalance": "0.01"}]}],
        )
    )
    wallet, _ = ingestor.state("WALLET", "UNIFIED")
    assert {c["coin"] for c in wallet["coin"]} == {"USDT", "BTC"}
    assert wallet["totalEquity"] == "100.00000000000001"
    assert (
        store.db.execute("SELECT available_margin FROM account_balances LIMIT 1").fetchone()[0]
        is None
    )
    for idx, side in ((1, "Buy"), (2, "Sell")):
        await ingestor.handle(
            await captured(
                tmp_path,
                "position",
                [
                    {
                        "symbol": "SUIUSDT",
                        "positionIdx": idx,
                        "side": side,
                        "size": "2",
                        "avgPrice": "1.1",
                        "markPrice": "1.2",
                        "unrealisedPnl": "0.2",
                        "curRealisedPnl": "0.05",
                        "updatedTime": "1720000000000",
                    }
                ],
            )
        )
    assert store.db.execute("SELECT COUNT(*) FROM position_balances").fetchone()[0] == 2
    assert (
        store.db.execute("SELECT COUNT(*) FROM current_states WHERE kind='POSITION'").fetchone()[0]
        == 2
    )
    await ingestor.handle(
        await captured(
            tmp_path,
            "position",
            [
                {
                    "symbol": "SUIUSDT",
                    "positionIdx": 1,
                    "side": "Buy",
                    "size": "2",
                    "avgPrice": "1.1",
                    "markPrice": "1.3",
                    "unrealisedPnl": "0.4",
                    "updatedTime": "1720000001000",
                }
            ],
        )
    )
    assert (
        store.db.execute("SELECT COUNT(*) FROM timeline WHERE event_type='POSITION'").fetchone()[0]
        == 2
    )
    snapshot = store.db.execute("SELECT * FROM market_snapshots LIMIT 1").fetchone()
    assert snapshot["last_price"] == "1.20" and snapshot["ticker_age_ms"] >= 0
    await ingestor.handle(
        await captured(
            tmp_path,
            "funding",
            [
                {
                    "id": "f1",
                    "symbol": "SUIUSDT",
                    "currency": "USDT",
                    "funding": "-0.003",
                    "cashFlow": "0",
                    "transactionTime": "1720000002000",
                }
            ],
        )
    )
    await ingestor.handle(
        await captured(
            tmp_path,
            "closed_pnl",
            [
                {
                    "orderId": "c1",
                    "symbol": "SUIUSDT",
                    "closedPnl": "0.05",
                    "updatedTime": "1720000002000",
                }
            ],
        )
    )
    assert (
        store.db.execute("SELECT funding FROM pnl_records WHERE kind='FUNDING'").fetchone()[0]
        == "-0.003"
    )


@pytest.mark.asyncio
async def test_old_order_does_not_replace_current(store, tmp_path):
    ingestor = EventIngestor(store)
    for status, stamp in (("Filled", 2000), ("New", 1000)):
        await ingestor.handle(
            await captured(
                tmp_path,
                "order",
                [
                    {
                        "orderId": "o1",
                        "symbol": "SUIUSDT",
                        "orderStatus": status,
                        "updatedTime": str(stamp),
                    }
                ],
            )
        )
    assert ingestor.state("ORDER", "o1")[0]["orderStatus"] == "Filled"
    assert json.loads(store.table_rows("orders")[0]["raw_json"])["orderStatus"] == "Filled"
    assert store.db.execute("SELECT COUNT(*) FROM executions").fetchone()[0] == 0


def test_additive_legacy_migration_preserves_rows(tmp_path):
    path = tmp_path / "legacy.sqlite"
    with closing(sqlite3.connect(path)) as db:
        db.executescript(SCHEMA)
        db.execute("INSERT INTO trader_notes(text,verified) VALUES('legacy',1)")
        db.commit()
    store = SQLiteStore(path)
    try:
        store.initialize()
        store.initialize()
        assert store.db.execute("SELECT text,verified FROM trader_notes").fetchone()[:] == (
            "legacy",
            1,
        )
        assert (
            store.db.execute("SELECT COUNT(*) FROM schema_versions WHERE version=2").fetchone()[0]
            == 1
        )
    finally:
        store.close()


@pytest.mark.asyncio
async def test_sampled_ticker_replays_merged_delta(store, tmp_path, monkeypatch):
    ingestor = EventIngestor(store)
    clock = [100.0]
    monkeypatch.setattr("recorder.bybit.ws_common.time.monotonic", lambda: clock[0])
    collector = BybitWebSocketCollector(
        "unused",
        "bybit_public",
        [],
        RawJsonlWriter(tmp_path / "raw"),
        ingestor.handle,
        sample_seconds=1,
    )
    await collector.receive(
        {
            "topic": "tickers.SUIUSDT",
            "type": "snapshot",
            "ts": 1000,
            "data": {"symbol": "SUIUSDT", "lastPrice": "1", "markPrice": "1.1"},
        }
    )
    clock[0] += 0.1
    await collector.receive(
        {
            "topic": "tickers.SUIUSDT",
            "type": "delta",
            "ts": 1001,
            "data": {"symbol": "SUIUSDT", "markPrice": "1.2"},
        }
    )
    clock[0] += 2
    await collector.receive(
        {
            "topic": "tickers.SUIUSDT",
            "type": "delta",
            "ts": 1002,
            "data": {"symbol": "SUIUSDT", "lastPrice": "1.3"},
        }
    )
    assert ingestor.state("TICKER", "SUIUSDT")[0]["markPrice"] == "1.2"
    target = SQLiteStore(tmp_path / "replay.sqlite")
    target.initialize()
    try:
        await replay(tmp_path / "raw", EventIngestor(target))
        assert EventIngestor(target).state("TICKER", "SUIUSDT") == ingestor.state(
            "TICKER", "SUIUSDT"
        )
    finally:
        target.close()


async def test_open_kline_updates_skipped_from_raw_when_disabled(tmp_path):
    events = []

    async def on_event(event):
        events.append(event)

    collector = BybitWebSocketCollector(
        "unused",
        "bybit_public",
        [],
        RawJsonlWriter(tmp_path / "raw"),
        on_event,
        save_open_kline_updates_raw=False,
    )
    await collector.receive(
        {
            "topic": "kline.1.SUIUSDT",
            "data": [{"symbol": "SUIUSDT", "interval": "1", "start": 1000, "confirm": False}],
        }
    )
    assert events == []
    await collector.receive(
        {
            "topic": "kline.1.SUIUSDT",
            "data": [{"symbol": "SUIUSDT", "interval": "1", "start": 1000, "confirm": True}],
        }
    )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_voice_retry_idempotent_and_corrections_preserved(store, tmp_path):
    class Bot:
        async def call(self, *args):
            return {"result": {"file_path": "voice/x.ogg"}}

        async def download_file(self, *args):
            return b"original"

    class Provider:
        fail = True

        async def transcribe(self, *args):
            if self.fail:
                raise RuntimeError("do not store secret exception content")
            return "verbatim original"

    provider = Provider()
    voice = VoiceService(tmp_path / "voice", store, provider)
    message = {"message_id": 1, "chat": {"id": 42}, "from": {"id": 42}, "voice": {"file_id": "f"}}
    voice_id, note = await voice.save(Bot(), message, update_id=7)
    assert await voice.save(Bot(), message, update_id=7) == (voice_id, note)
    with pytest.raises(ValueError):
        verify_note(store, note)
    assert (await voice.transcribe(voice_id))[1] == "failed"
    edit_note(store, note, "trader correction")
    provider.fail = False
    assert await voice.transcribe(voice_id) == ("verbatim original", "completed")
    row = store.db.execute(
        "SELECT text,original_text FROM trader_notes WHERE id=?", (note,)
    ).fetchone()
    assert row[:] == ("trader correction", "verbatim original")
    assert store.db.execute("SELECT attempt_count FROM voice_messages").fetchone()[0] == 2


@pytest.mark.asyncio
async def test_export_checksums_schema_and_source_unchanged(store, tmp_path):
    event = await captured(
        tmp_path,
        "order",
        [
            {
                "orderId": "o",
                "symbol": "SUIUSDT",
                "orderStatus": "New",
                "updatedTime": "1720000000000",
            }
        ],
    )
    await EventIngestor(store).handle(event)
    before = store.table_rows("raw_events_index")
    root = export_bundle(
        store.path,
        tmp_path / "raw",
        tmp_path / "exports",
        "test",
        {"category": "linear", "symbols": ["SUIUSDT"]},
        {},
    )
    assert store.table_rows("raw_events_index") == before
    result = verify_bundle(root)
    assert result["status"] == "WARNING", result
    import pyarrow.parquet as pq

    assert "exec_id" in pq.read_schema(root / "executions.parquet").names
    assert json.loads((root / "manifest.json").read_text())["table_counts"]["orders"] == 1
    with pytest.raises(FileExistsError):
        export_bundle(
            store.path,
            tmp_path / "raw",
            tmp_path / "exports",
            "test",
            {"category": "linear", "symbols": ["SUIUSDT"]},
            {},
        )
    (root / "orders.parquet").write_bytes(b"corrupt")
    assert verify_bundle(root)["status"] == "FAIL"


def test_verifier_catches_missing_media_orphans_and_gaps(store):
    note = save_text_note(store, "text")
    store.db.execute("INSERT INTO trader_note_links VALUES(?,999999)", (note,))
    store.insert_voice_message(
        "v", "1", "f", datetime.now(UTC).isoformat(), 1, "/nonexistent/audio", 3, "pending"
    )
    store.gap("reconciliation", "injected")
    problems = verify_sqlite(store.path)
    assert any("orphan note links" in p for p in problems)
    assert any("missing voice file" in p for p in problems)
    assert any("unresolved data gaps" in p for p in problems)
