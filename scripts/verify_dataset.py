import argparse
import json
import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != _scripts_dir]

from recorder.config import load_config
from recorder.export.verifier import report, verify_bundle, verify_raw, verify_sqlite

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failure")
    args = parser.parse_args()
    if args.bundle:
        result = verify_bundle(args.bundle)
    else:
        _, cfg = load_config()
        result = report(
            verify_raw(cfg.storage["raw_jsonl"]["directory"], cfg.storage["sqlite"]["path"])
            + verify_sqlite(cfg.storage["sqlite"]["path"])
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(
        1 if result["status"] == "FAIL" or args.strict and result["status"] != "PASS" else 0
    )
