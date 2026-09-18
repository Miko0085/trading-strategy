"""Offline replay into an explicitly chosen, separate database."""

import argparse
import json
import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != _scripts_dir]

import asyncio

from recorder.events.ingestion import EventIngestor
from recorder.events.replay import replay
from recorder.storage.sqlite import SQLiteStore

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output-db", type=Path, required=True)
    args = parser.parse_args()
    if args.output_db.exists():
        parser.error("--output-db must be a new file; running database is never overwritten")
    if not args.raw.is_dir():
        parser.error("--raw must exist")
    store = SQLiteStore(args.output_db)
    store.initialize()
    try:
        result = asyncio.run(replay(args.raw, EventIngestor(store)))
        print(json.dumps(result))
    finally:
        store.close()
    raise SystemExit(bool(result["failed"]))
