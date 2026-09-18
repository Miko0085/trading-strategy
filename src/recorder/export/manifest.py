from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_manifest(directory: str | Path, values: dict[str, Any]) -> Path:
    """Manifest is the completion marker, published only as a complete file."""
    path = Path(directory) / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".manifest-", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(values, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return path
