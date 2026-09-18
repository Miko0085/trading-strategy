"""Export without migrating or writing the running recorder database."""

import argparse
import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != _scripts_dir]

from recorder.config import load_config
from recorder.export.bundle import export_bundle

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export self-contained recorder dataset")
    parser.add_argument("--experiment-id", required=True)
    args = parser.parse_args()
    symbols, cfg = load_config()
    output = export_bundle(
        cfg.storage["sqlite"]["path"],
        cfg.storage["raw_jsonl"]["directory"],
        cfg.storage["parquet"]["directory"],
        args.experiment_id,
        symbols.model_dump(),
        cfg.model_dump(),
    )
    print(f"Exported dataset to {output}")
