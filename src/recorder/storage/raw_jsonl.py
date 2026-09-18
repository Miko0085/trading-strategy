from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC
from pathlib import Path
from uuid import uuid4

from recorder.events.models import RawEvent


class RawJsonlWriter:
    def __init__(self, directory):
        self.directory = Path(directory)
        self._lock = asyncio.Lock()

    async def capture(self, event: RawEvent):
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{event.received_at.astimezone(UTC):%Y-%m-%d}.jsonl"
        envelope = event.as_dict()
        envelope["capture_id"] = uuid4().hex
        async with self._lock:
            task = asyncio.create_task(
                asyncio.to_thread(self._append, path, json.dumps(envelope, ensure_ascii=False))
            )
            try:
                offset, length = await asyncio.shield(task)
            except asyncio.CancelledError:
                await task
                raise
        return {
            **envelope,
            "raw_path": str(path.resolve()),
            "byte_offset": offset,
            "byte_length": length,
        }

    async def write(self, event):
        return Path((await self.capture(event))["raw_path"])

    @staticmethod
    def _append(path, line):
        encoded = (line + "\n").encode("utf-8")
        with path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell():
                handle.seek(-1, os.SEEK_END)
                if handle.read(1) != b"\n":
                    # Preserve an interrupted tail for audit; never concatenate new JSON onto it.
                    handle.write(b"\n")
            offset = handle.tell()
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return offset, len(encoded)

    def read(self, path):
        with Path(path).open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]
