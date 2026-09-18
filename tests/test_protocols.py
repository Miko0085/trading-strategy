import asyncio
import logging

import aiohttp
import pytest

from recorder.bybit.reconciliation import Reconciler, backfill_klines
from recorder.bybit.rest import ReadOnlyBybitRest
from recorder.bybit.ws_common import BybitWebSocketCollector
from recorder.events.ingestion import EventIngestor
from recorder.events.queue import ControlledWriter
from recorder.logging_config import Redactor
from recorder.storage.lifecycle import DatabaseLease, backup_database
from recorder.storage.raw_jsonl import RawJsonlWriter
from recorder.storage.sqlite import SQLiteStore
from recorder.telegram.bot import TelegramBot
from recorder.telegram.notes import save_text_note


class MockSocket:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)

    async def receive_json(self, **kwargs):
        return next(self.replies)

    async def receive(self, **kwargs):
        return type("Message", (), {"type": aiohttp.WSMsgType.CLOSED})()

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockSession:
    def __init__(self, ws):
        self.ws = ws

    def ws_connect(self, *args, **kwargs):
        return self.ws

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("private", [False, True])
async def test_ws_rejects_subscription_and_finalizes_session(monkeypatch, tmp_path, private):
    replies = ([{"op": "auth", "success": True}] if private else []) + [
        {"op": "subscribe", "success": False}
    ]
    socket = MockSocket(replies)
    monkeypatch.setattr(
        "recorder.bybit.ws_common.aiohttp.ClientSession", lambda **_: MockSession(socket)
    )
    sessions, ready = [], []

    async def record(row):
        sessions.append(row)

    async def connected(count):
        ready.append(count)

    collector = BybitWebSocketCollector(
        "ws://unused",
        "test",
        ["position"],
        RawJsonlWriter(tmp_path),
        None,
        auth=(lambda: {"op": "auth"}) if private else None,
        on_connect=connected,
        session_callback=record,
    )
    with pytest.raises(RuntimeError, match="subscription rejected"):
        await collector._connect_once()
    assert not collector.ready.is_set()
    assert ready == []
    assert sessions[-1]["status"] == "disconnected"
    assert sessions[-1]["reason"] == "RuntimeError"


@pytest.mark.asyncio
async def test_ws_ack_reconnect_callback_each_connection(monkeypatch, tmp_path):
    sessions, ready = [], []

    def session(**kwargs):
        return MockSession(MockSocket([{"op": "subscribe", "success": True}]))

    monkeypatch.setattr("recorder.bybit.ws_common.aiohttp.ClientSession", session)

    async def record(row):
        sessions.append(row)

    async def connected(count):
        ready.append(count)
        if count == 1:
            collector._stop.set()

    collector = BybitWebSocketCollector(
        "ws://unused",
        "test",
        ["order"],
        RawJsonlWriter(tmp_path),
        None,
        on_connect=connected,
        session_callback=record,
    )
    await asyncio.wait_for(collector.run(), 3)
    assert ready == [0, 1]
    assert [s["status"] for s in sessions] == [
        "connected",
        "disconnected",
        "connected",
        "disconnected",
    ]
    assert not collector.ready.is_set()


@pytest.mark.asyncio
async def test_full_reconciliation_v5_shapes_replay_and_checkpoint(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    raw = RawJsonlWriter(tmp_path / "raw")
    ingestor = EventIngestor(store)
    writer = ControlledWriter(ingestor.handle, on_error=ingestor.failure)
    task = asyncio.create_task(writer.run())
    rest = ReadOnlyBybitRest(capture=raw.capture)
    fail = [False]

    async def request(url, headers):
        path = url.path
        if fail[0]:
            return {"retCode": 10003, "result": {}}
        forms = {
            "/v5/order/history": [
                {
                    "orderId": "o1",
                    "symbol": "SUIUSDT",
                    "orderStatus": "Filled",
                    "updatedTime": "1720000000001",
                }
            ],
            "/v5/execution/list": [
                {
                    "execId": "e1",
                    "orderId": "o1",
                    "symbol": "SUIUSDT",
                    "execTime": "1720000000001",
                    "execQty": "1",
                }
            ],
            "/v5/position/closed-pnl": [
                {
                    "orderId": "o1",
                    "symbol": "SUIUSDT",
                    "closedPnl": "0.2",
                    "updatedTime": "1720000000001",
                }
            ],
            "/v5/order/realtime": [],
            "/v5/position/list": [
                {
                    "symbol": "SUIUSDT",
                    "positionIdx": 1,
                    "side": "Buy",
                    "size": "1",
                    "avgPrice": "1.2",
                    "updatedTime": "1720000000001",
                }
            ],
            "/v5/account/transaction-log": [
                {
                    "id": "f1",
                    "symbol": "SUIUSDT",
                    "type": "SETTLEMENT",
                    "funding": "-0.01",
                    "transactionTime": "1720000000001",
                }
            ],
            "/v5/account/wallet-balance": [
                {
                    "accountType": "UNIFIED",
                    "totalWalletBalance": "100",
                    "totalEquity": "101",
                    "coin": [],
                }
            ],
        }
        result = (
            {"marginMode": "REGULAR_MARGIN", "unifiedMarginStatus": 6}
            if path == "/v5/account/info"
            else {"list": forms[path], "nextPageCursor": ""}
        )
        return {"retCode": 0, "time": 1720000000010, "result": result}

    rest._request = request
    rec = Reconciler(rest, writer, store, ["SUIUSDT"], "linear", raw, {"startup_lookback_hours": 1})
    try:
        first = await rec.run("reconnect")
        assert first.status == "warning"
        assert store.db.execute("SELECT COUNT(*) FROM executions").fetchone()[0] == 1
        assert store.db.execute("SELECT COUNT(*) FROM pnl_records").fetchone()[0] == 2
        assert store.db.execute("SELECT equity FROM account_balances").fetchone()[0] == "101"
        await rec.run("periodic")
        assert store.db.execute("SELECT COUNT(*) FROM executions").fetchone()[0] == 1
        checkpoint = store.get_state("reconciled_until")
        fail[0] = True
        failed = await rec.run("periodic")
        assert failed.status == "data_gap"
        assert store.get_state("reconciled_until") == checkpoint
        assert (
            store.db.execute(
                "SELECT COUNT(*) FROM data_gaps WHERE kind='reconciliation'"
            ).fetchone()[0]
            == 1
        )
    finally:
        await writer.drain()
        await task
        store.close()


@pytest.mark.asyncio
async def test_backfill_multiple_pages_excludes_open_and_flags_gap(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()

    class Rest:
        def __init__(self):
            self.calls = []

        async def klines(self, category, symbol, interval, start, end):
            self.calls.append(end)
            values = [s for s in (180000, 120000, 0) if start <= s <= end][:2]
            return [[str(s), "1", "2", "0", "1", "1", "1"] for s in values]

    rest = Rest()
    try:
        count = await backfill_klines(rest, store, "linear", "SUIUSDT", "1", 0, 180100)
        assert count == 2
        assert (
            store.db.execute("SELECT start_ms FROM market_candles ORDER BY start_ms").fetchall()[0][
                0
            ]
            == 0
        )
        assert len(rest.calls) == 2
        assert (
            store.db.execute("SELECT COUNT(*) FROM data_gaps WHERE kind='candles'").fetchone()[0]
            == 1
        )
    finally:
        store.close()


@pytest.mark.asyncio
async def test_telegram_buttons_real_ids_owner_and_edit_roundtrip(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    bot = TelegramBot("fake", {42}, store)
    messages = []

    async def call(method, payload):
        messages.append((method, payload))
        return {"ok": True, "result": {}}

    bot.call = call
    try:
        event_id = store.insert_timeline(
            {"event_type": "EXECUTION", "source": "test", "summary_ru": "Исполнение"}
        )
        await bot.recent(42)
        data = messages[-1][1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"]
        assert data == f"note:{event_id}"

        async def cb(data, user=42, chat=42):
            await bot.handle_callback(
                {"id": "cb", "data": data, "from": {"id": user}, "message": {"chat": {"id": chat}}}
            )

        await cb(data)
        await bot.handle(
            {
                "update_id": 1,
                "message": {"chat": {"id": 42}, "from": {"id": 42}, "text": "original"},
            }
        )
        note = store.db.execute("SELECT id FROM trader_notes").fetchone()[0]
        await cb(f"edit:{note}:0")
        await bot.handle(
            {
                "update_id": 2,
                "message": {"chat": {"id": 42}, "from": {"id": 42}, "text": "correction"},
            }
        )
        await cb(f"verify:{note}:0")  # stale button cannot verify revised text
        assert store.db.execute("SELECT verified FROM trader_notes").fetchone()[0] == 0
        await cb(f"verify:{note}:1")
        assert store.db.execute("SELECT text,original_text,verified FROM trader_notes").fetchone()[
            :
        ] == ("correction", "original", 1)
        bot.allowed_user_ids.add(43)
        await cb(f"edit:{note}:1", 43, 43)
        assert await bot.state(43, 43) == {}
        assert (
            store.db.execute("SELECT timeline_id FROM trader_note_links").fetchone()[0] == event_id
        )
    finally:
        store.close()


def test_database_lease_backup_and_log_redaction(tmp_path, monkeypatch):
    path = tmp_path / "db.sqlite"
    store = SQLiteStore(path)
    store.initialize()
    save_text_note(store, "retained")
    lease = DatabaseLease(path).acquire()
    try:
        with pytest.raises(RuntimeError, match="already in use"):
            DatabaseLease(path).acquire()
        backup = backup_database(path)
        assert backup.is_file()
    finally:
        lease.close()
        store.close()
    DatabaseLease(path).acquire().close()
    monkeypatch.setenv("BYBIT_API_SECRET", "sensitive-value")
    record = logging.LogRecord(
        "x",
        logging.ERROR,
        "",
        0,
        "sensitive-value https://api.telegram.org/bot123:secret/getUpdates",
        (),
        None,
    )
    output = Redactor().format(record)
    assert "sensitive-value" not in output and "123:secret" not in output
