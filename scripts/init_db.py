import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != _scripts_dir]

from recorder.config import load_config
from recorder.storage.lifecycle import DatabaseLease, backup_database
from recorder.storage.sqlite import SQLiteStore

if __name__ == "__main__":
    _, cfg = load_config()
    path = cfg.storage["sqlite"]["path"]
    lease = DatabaseLease(path).acquire()
    store = None
    try:
        backup = backup_database(path)
        store = SQLiteStore(path)
        store.initialize()
        print("SQLite v2 initialized; backup: " + str(backup or "new database"))
    finally:
        if store:
            store.close()
        lease.close()
