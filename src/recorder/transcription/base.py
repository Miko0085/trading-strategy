from __future__ import annotations

from typing import Protocol


class TranscriptionProvider(Protocol):
    async def transcribe(self, file_path: str, language: str = "ru") -> str: ...
