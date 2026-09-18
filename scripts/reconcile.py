"""GET-only full reconciliation. Stop recorder before using this maintenance CLI."""

import argparse
import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != _scripts_dir]

import asyncio

from recorder.bybit.reconciliation import Reconciler
from recorder.bybit.rest import ReadOnlyBybitRest
from recorder.config import credentials, load_config
from recorder.events.ingestion import EventIngestor
from recorder.events.queue import ControlledWriter
from recorder.market.discovery import bootstrap
from recorder.storage.lifecycle import DatabaseLease, backup_database
from recorder.storage.raw_jsonl import RawJsonlWriter
from recorder.storage.sqlite import SQLiteStore


async def main(reason):
    symbols, cfg = load_config()
    key, secret = credentials()
    if not key or not secret:
        raise SystemExit("BYBIT_API_KEY and BYBIT_API_SECRET required")
    lease = DatabaseLease(cfg.storage["sqlite"]["path"]).acquire()
    store = None
    writer = None
    try:
        rest = ReadOnlyBybitRest(key, secret, cfg.environment == "testnet")
        await rest.validate_read_only()
        backup_database(cfg.storage["sqlite"]["path"])
        store = SQLiteStore(cfg.storage["sqlite"]["path"])
        store.initialize()
        bootstrap(store, symbols.category, symbols.symbols)
        ingestor = EventIngestor(store, symbols.symbols, category=symbols.category)
        writer = ControlledWriter(ingestor.handle, on_error=ingestor.failure)
        task = asyncio.create_task(writer.run())
        raw = RawJsonlWriter(cfg.storage["raw_jsonl"]["directory"])
        rest.capture = raw.capture
        result = await Reconciler(
            rest, writer, store, symbols.symbols, symbols.category, raw, cfg.reconciliation
        ).run(reason)
        print(result)
        return int(result.status == "data_gap")
    finally:
        if writer:
            await writer.drain()
            await task
        if store:
            store.close()
        lease.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reason", default="manual")
    raise SystemExit(asyncio.run(main(parser.parse_args().reason)))
