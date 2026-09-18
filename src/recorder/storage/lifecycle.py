"""One process owns a writable recorder DB; inspection/export use read-only connections."""

import fcntl
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path


class DatabaseLease:
    def __init__(self, path):
        self.path = Path(path)
        self.handle = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.with_suffix(self.path.suffix + ".lock").open("a")
        try:
            fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.handle.close()
            self.handle = None
            raise RuntimeError(
                "Recorder database is already in use; stop its writer first"
            ) from None
        return self

    def close(self):
        if self.handle:
            fcntl.flock(self.handle, fcntl.LOCK_UN)
            self.handle.close()
            self.handle = None


def backup_database(path):
    path = Path(path)
    if not path.exists():
        return None
    backup = path.parent / "backups" / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + ".db")
    backup.parent.mkdir(parents=True, exist_ok=True)
    with (
        closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as source,
        closing(sqlite3.connect(backup)) as target,
    ):
        source.backup(target)
    return backup
