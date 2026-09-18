import asyncio

from recorder.bybit.reconciliation import backfill_klines, reconcile_account
from recorder.storage.sqlite import SQLiteStore


class FakeRest:
    async def executions(self, category, symbol, start_ms=None, end_ms=None):
        return [
            {"execId": "missing", "orderId": "o", "symbol": symbol, "execQty": "1"},
            {"execId": "known", "orderId": "o", "symbol": symbol},
        ]

    async def klines(self, category, symbol, interval, start_ms, end_ms):
        return [["0", "1", "2", "0.5", "1.5", "10", "15"]] if end_ms >= 0 else []


def test_reconciliation_recovers_missing_execution(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    store.insert_execution({"execId": "known", "orderId": "o", "symbol": "SUIUSDT"})
    result = asyncio.run(reconcile_account(FakeRest(), store, "linear", ["SUIUSDT"], "reconnect"))
    assert (result.records_checked, result.missing_found, result.recovered, result.duplicates) == (
        2,
        1,
        1,
        1,
    )
    assert store.db.execute("SELECT COUNT(*) FROM reconciliation_runs").fetchone()[0] == 1
    store.close()


def test_backfill_marks_source(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    assert asyncio.run(backfill_klines(FakeRest(), store, "linear", "SUIUSDT", "1", 0, 59999)) == 1
    assert store.db.execute("SELECT source FROM market_candles").fetchone()[0] == "REST_BACKFILL"
    store.close()
