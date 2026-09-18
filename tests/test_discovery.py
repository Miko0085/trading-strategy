import asyncio
import json

import pytest

from recorder.bybit.reconciliation import Reconciler
from recorder.bybit.rest import ReadOnlyBybitRest
from recorder.config import RecorderConfig, SymbolsConfig
from recorder.events.ingestion import EventIngestor
from recorder.events.models import RawEvent
from recorder.events.queue import ControlledWriter
from recorder.export.bundle import export_bundle
from recorder.market.automatic import AutomaticMarkets
from recorder.market.discovery import bootstrap, is_flat, stop_tracking, track, tracked_symbols
from recorder.storage.raw_jsonl import RawJsonlWriter
from recorder.storage.sqlite import SQLiteStore


@pytest.fixture
def store(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")
    store.initialize()
    yield store
    store.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "topic,item",
    [
        ("order", {"orderId": "o1", "symbol": "ETHUSDT", "orderStatus": "New"}),
        (
            "execution",
            {"execId": "e1", "orderId": "o1", "symbol": "ETHUSDT", "execTime": "1720000000000"},
        ),
        ("position", {"symbol": "ETHUSDT", "positionIdx": 1, "side": "Buy", "size": "1"}),
    ],
)
async def test_unconfigured_account_symbol_is_not_filtered(store, tmp_path, topic, item):
    ingest = EventIngestor(store, ["SUIUSDT"])
    raw = RawJsonlWriter(tmp_path / "raw")
    event = await raw.capture(
        RawEvent(
            source="bybit_private",
            topic=topic,
            payload={
                "topic": topic,
                "creationTime": 1720000000000,
                "data": [{**item, "category": "linear"}],
            },
        )
    )
    assert await ingest.handle(event) == 1
    assert await ingest.handle(event) == 0
    assert tracked_symbols(store, "linear") == ["ETHUSDT"]
    assert (
        store.db.execute("SELECT COUNT(*) FROM timeline WHERE symbol='ETHUSDT'").fetchone()[0] == 1
    )
    assert (
        store.db.execute(
            "SELECT COUNT(*) FROM data_gaps WHERE kind='market_before_discovery'"
        ).fetchone()[0]
        == 1
    )
    bootstrap(store, "linear", ["SUIUSDT"])
    assert tracked_symbols(store, "linear") == ["ETHUSDT", "SUIUSDT"]
    root = export_bundle(
        store.path,
        tmp_path / "raw",
        tmp_path / "exports",
        "discovery",
        {"category": "linear", "symbols": ["SUIUSDT"]},
        {},
    )
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["symbols"] == ["ETHUSDT", "SUIUSDT"]
    assert manifest["configured_symbols"] == ["SUIUSDT"]


@pytest.mark.asyncio
async def test_other_category_kept_but_wrong_ticker_not_used(store):
    ingest = EventIngestor(store, ["SUIUSDT"])
    await ingest.handle(
        {
            "source": "bybit_public",
            "payload": {
                "topic": "tickers.ETHUSDT",
                "type": "snapshot",
                "ts": 1720000000000,
                "data": {"symbol": "ETHUSDT", "lastPrice": "123"},
            },
        }
    )
    await ingest.handle(
        {
            "source": "bybit_private",
            "payload": {
                "topic": "order",
                "creationTime": 1720000000001,
                "data": [
                    {
                        "category": "spot",
                        "orderId": "spot1",
                        "symbol": "ETHUSDT",
                        "orderStatus": "New",
                    }
                ],
            },
        }
    )
    assert tracked_symbols(store, "spot") == ["ETHUSDT"]
    assert tracked_symbols(store, "linear") == []
    assert store.db.execute("SELECT last_price FROM market_snapshots").fetchone()[0] is None
    assert (
        store.db.execute(
            "SELECT COUNT(*) FROM data_gaps WHERE kind='unsupported_market_category'"
        ).fetchone()[0]
        == 1
    )


@pytest.mark.asyncio
async def test_discovery_rolls_back_with_failed_message(store, monkeypatch):
    ingest = EventIngestor(store, ["SUIUSDT"])

    def fail(row):
        raise ValueError("injected")

    monkeypatch.setattr(store, "insert_timeline", fail)
    with pytest.raises(ValueError):
        await ingest.handle(
            {
                "source": "bybit_private",
                "payload": {
                    "topic": "order",
                    "data": [{"orderId": "o1", "symbol": "ETHUSDT", "category": "linear"}],
                },
            }
        )
    assert tracked_symbols(store, "linear") == []


@pytest.mark.asyncio
async def test_auto_market_restores_and_never_reconnects_watchlist(store, tmp_path, monkeypatch):
    bootstrap(store, "linear", ["SUIUSDT"])
    with store.transaction():
        track(store, "linear", "ETHUSDT", "test", "2026-09-15T00:00:00+00:00")
    # A fresh repository connection sees the registry, not an in-memory-only list.
    reopened = SQLiteStore(store.path)
    try:
        assert tracked_symbols(reopened, "linear") == ["ETHUSDT", "SUIUSDT"]
    finally:
        reopened.close()
    cfg = RecorderConfig(
        storage={},
        market={"discovery_interval_seconds": 0.01},
        reconciliation={},
        telegram={},
        transcription={},
        dataset={},
    )
    symbols = SymbolsConfig(symbols=["SUIUSDT"], market={"kline_intervals": ["1", "15"]})
    ingest = EventIngestor(store, symbols.symbols)
    writer = ControlledWriter(ingest.handle, on_error=ingest.failure)
    wt = asyncio.create_task(writer.run())
    built = []
    backfilled = asyncio.Event()

    class FakeCollector:
        async def run(self):
            await self.ready(0)
            await asyncio.Future()

        async def stop(self):
            self.stopped = True

    def build(watch, intervals, testnet, raw, handler, **kwargs):
        collector = FakeCollector()
        collector.ready = kwargs["on_connect"]
        collector.stopped = False
        built.append((watch, intervals, collector))
        return collector

    monkeypatch.setattr("recorder.market.automatic.build_public_collector", build)

    async def backfill(targets):
        assert targets == ["ETHUSDT"]
        backfilled.set()

    manager = AutomaticMarkets(
        store, writer, RawJsonlWriter(tmp_path / "raw"), symbols, cfg, None, backfill
    )
    task = asyncio.create_task(manager.run())
    try:
        await asyncio.wait_for(backfilled.wait(), 1)
        await manager.refresh()
        assert len(built) == 1
        assert built[0][:2] == (["ETHUSDT"], ["1", "15"])
        assert store.db.execute(
            "SELECT market_started_at FROM tracked_instruments WHERE symbol='ETHUSDT'"
        ).fetchone()[0]
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await writer.drain()
        await wt
    assert built[0][2].stopped


def test_is_flat_requires_observed_zero_position_and_reactivation_keeps_history(store):
    with store.transaction():
        track(store, "linear", "ETHUSDT", "test", "2026-09-15T00:00:00+00:00")
    # No POSITION observation yet: unknown, not flat.
    assert not is_flat(store, "ETHUSDT")
    store.db.execute(
        "INSERT INTO current_states VALUES('POSITION','ETHUSDT:1','ETHUSDT',0,'t',?)",
        (json.dumps({"size": "1"}),),
    )
    assert not is_flat(store, "ETHUSDT")
    store.db.execute(
        "UPDATE current_states SET data_json=? WHERE kind='POSITION' AND state_key='ETHUSDT:1'",
        (json.dumps({"size": "0"}),),
    )
    assert is_flat(store, "ETHUSDT")
    store.db.execute(
        "INSERT INTO current_states VALUES('ORDER','o1','ETHUSDT',0,'t',?)",
        (json.dumps({"orderStatus": "New"}),),
    )
    assert not is_flat(store, "ETHUSDT")
    store.db.execute(
        "UPDATE current_states SET data_json=? WHERE kind='ORDER' AND state_key='o1'",
        (json.dumps({"orderStatus": "Filled"}),),
    )
    assert is_flat(store, "ETHUSDT")
    stop_tracking(store, "linear", "ETHUSDT", "2026-09-16T00:00:00+00:00")
    assert tracked_symbols(store, "linear") == []
    assert (
        store.db.execute(
            "SELECT COUNT(*) FROM tracked_instruments WHERE symbol='ETHUSDT'"
        ).fetchone()[0]
        == 1
    )
    track(store, "linear", "ETHUSDT", "test", "2026-09-16T00:01:00+00:00")
    assert tracked_symbols(store, "linear") == ["ETHUSDT"]


@pytest.mark.asyncio
async def test_automatic_market_stops_flat_symbol_and_reconnects_on_new_activity(
    store, tmp_path, monkeypatch
):
    with store.transaction():
        track(store, "linear", "ETHUSDT", "test", "2026-09-15T00:00:00+00:00")
        store.db.execute(
            "INSERT INTO current_states VALUES('POSITION','ETHUSDT:1','ETHUSDT',0,'t',?)",
            (json.dumps({"size": "1"}),),
        )
    cfg = RecorderConfig(
        storage={},
        market={"discovery_interval_seconds": 0.01},
        reconciliation={},
        telegram={},
        transcription={},
        dataset={},
    )
    symbols = SymbolsConfig(symbols=[], market={"kline_intervals": ["1", "15"]})
    ingest = EventIngestor(store, symbols.symbols)
    writer = ControlledWriter(ingest.handle, on_error=ingest.failure)
    wt = asyncio.create_task(writer.run())
    built = []
    backfilled = asyncio.Event()

    class FakeCollector:
        async def run(self):
            await self.ready(0)
            await asyncio.Future()

        async def stop(self):
            self.stopped = True

    def build(watch, intervals, testnet, raw, handler, **kwargs):
        collector = FakeCollector()
        collector.ready = kwargs["on_connect"]
        collector.stopped = False
        built.append(collector)
        return collector

    monkeypatch.setattr("recorder.market.automatic.build_public_collector", build)

    async def backfill(targets):
        backfilled.set()

    manager = AutomaticMarkets(
        store, writer, RawJsonlWriter(tmp_path / "raw"), symbols, cfg, None, backfill
    )
    task = asyncio.create_task(manager.run())
    try:
        await asyncio.wait_for(backfilled.wait(), 1)
        assert len(built) == 1
        assert not built[0].stopped

        def flatten():
            store.db.execute(
                "UPDATE current_states SET data_json=? WHERE kind='POSITION' AND state_key='ETHUSDT:1'",
                (json.dumps({"size": "0"}),),
            )
            store._commit()

        await writer.call(flatten)
        await manager.refresh()
        assert built[0].stopped
        assert tracked_symbols(store, "linear") == []

        backfilled.clear()
        with store.transaction():
            track(store, "linear", "ETHUSDT", "test", "2026-09-16T00:01:00+00:00")
        await asyncio.wait_for(backfilled.wait(), 1)
        assert len(built) == 2
        assert tracked_symbols(store, "linear") == ["ETHUSDT"]
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await writer.drain()
        await wt


@pytest.mark.asyncio
async def test_reconciliation_discovers_history_open_orders_and_positions(store, tmp_path):
    raw = RawJsonlWriter(tmp_path / "raw")
    ingest = EventIngestor(store, ["SUIUSDT"])
    writer = ControlledWriter(ingest.handle, on_error=ingest.failure)
    task = asyncio.create_task(writer.run())
    rest = ReadOnlyBybitRest(capture=raw.capture)
    calls = []

    async def request(url, headers):
        params = dict(url.query)
        calls.append((url.path, params))
        rows = []
        if url.path == "/v5/execution/list":
            rows = [
                {"execId": "e1", "orderId": "o1", "symbol": "ETHUSDT", "execTime": "1720000000000"}
            ]
        elif url.path == "/v5/order/realtime" and params.get("settleCoin") == "USDC":
            rows = [{"orderId": "o2", "symbol": "BTCPERP", "orderStatus": "New"}]
        elif url.path == "/v5/position/list" and params.get("settleCoin") == "USDT":
            rows = [{"symbol": "SOLUSDT", "size": "1", "side": "Buy", "positionIdx": 1}]
        result = {"list": rows, "nextPageCursor": "", "category": "linear"}
        if url.path == "/v5/account/info":
            result = {"marginMode": "REGULAR_MARGIN"}
        return {"retCode": 0, "time": 1720000000000, "result": result}

    rest._request = request
    rec = Reconciler(rest, writer, store, ["SUIUSDT"], "linear", raw, {"startup_lookback_hours": 1})
    try:
        assert (await rec.run("startup")).errors == []
        assert set(tracked_symbols(store, "linear")) == {"ETHUSDT", "BTCPERP", "SOLUSDT"}
        histories = [
            q
            for path, q in calls
            if path in {"/v5/execution/list", "/v5/order/history", "/v5/position/closed-pnl"}
        ]
        assert histories and all("symbol" not in q for q in histories)
        assert {q.get("settleCoin") for path, q in calls if path == "/v5/order/realtime"} == {
            "USDT",
            "USDC",
        }
        specific = {
            q["symbol"] for path, q in calls if path == "/v5/position/list" and "symbol" in q
        }
        assert {"SUIUSDT", "ETHUSDT", "SOLUSDT", "BTCPERP"} <= specific
        await rec.run("periodic")
        assert store.db.execute("SELECT COUNT(*) FROM executions").fetchone()[0] == 1
    finally:
        await writer.drain()
        await task
