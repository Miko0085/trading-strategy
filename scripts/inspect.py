"""Read-only operational inspection; never initializes/migrates the database."""

import argparse
import re
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != _scripts_dir]

from recorder.account.status import account_text, health
from recorder.config import load_config
from recorder.storage.sqlite import SQLiteStore

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--last", default="2h")
    args = parser.parse_args()
    match = re.fullmatch(r"([1-9][0-9]*)(m|h|d)", args.last)
    if not match:
        parser.error("--last format: 30m, 2h, 1d")
    seconds = int(match[1]) * {"m": 60, "h": 3600, "d": 86400}[match[2]]
    _, cfg = load_config()
    path = Path(cfg.storage["sqlite"]["path"])
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    store = object.__new__(SQLiteStore)
    store.db = db
    try:
        since = (datetime.now(UTC) - timedelta(seconds=seconds)).isoformat()
        print(account_text(store, args.symbol, since))
        print(health(store))
    except sqlite3.OperationalError:
        raise SystemExit(
            "Database schema is older than v2; back up and migrate before inspection."
        ) from None
    finally:
        db.close()
