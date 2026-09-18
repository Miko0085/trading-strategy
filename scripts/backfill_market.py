"""Public closed-candle backfill, no private API key required."""

import argparse
import sys
import time
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != _scripts_dir]

import asyncio

from recorder.bybit.reconciliation import backfill_klines
from recorder.bybit.rest import ReadOnlyBybitRest
from recorder.config import load_config
from recorder.storage.lifecycle import DatabaseLease, backup_database
from recorder.storage.raw_jsonl import RawJsonlWriter
from recorder.storage.sqlite import SQLiteStore


async def main(symbol, interval, hours):
    symbols, cfg = load_config()
    if symbol not in symbols.symbols or interval not in symbols.market["kline_intervals"]:
        raise SystemExit("Symbol/interval must be configured")
    if not 1 <= hours <= 336:
        raise SystemExit("--hours must be 1..336")
    lease = DatabaseLease(cfg.storage["sqlite"]["path"]).acquire()
    store = None
    try:
        backup_database(cfg.storage["sqlite"]["path"])
        store = SQLiteStore(cfg.storage["sqlite"]["path"])
        store.initialize()
        raw = RawJsonlWriter(cfg.storage["raw_jsonl"]["directory"])
        client = ReadOnlyBybitRest(testnet=cfg.environment == "testnet", capture=raw.capture)
        end = int(time.time() * 1000) - 1
        count = await backfill_klines(
            client, store, symbols.category, symbol, interval, end - hours * 3600000, end, raw=raw
        )
        print(f"Backfilled {count} closed candles")
    finally:
        if store:
            store.close()
        lease.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--interval", default="1")
    parser.add_argument("--hours", type=int, default=2)
    args = parser.parse_args()
    asyncio.run(main(args.symbol, args.interval, args.hours))
