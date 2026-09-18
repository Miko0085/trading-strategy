from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import ssl
from pathlib import Path

import aiohttp
import certifi


class TranscriptionError(RuntimeError):
    """Safe structured diagnostics; never persist provider messages or request bodies."""

    def __init__(self, status: int, code: str | None = None):
        allowed = {
            "insufficient_quota",
            "rate_limit_exceeded",
            "invalid_api_key",
            "unsupported_format",
            "invalid_value",
            "model_not_found",
        }
        self.status = status
        self.code = code if isinstance(code, str) and code in allowed else None
        self.retryable = (
            status in {408, 429} or status >= 500
        ) and self.code != "insufficient_quota"
        super().__init__(f"Transcription HTTP {status}")

    def diagnostic(self):
        return json.dumps(
            {"http_status": self.status, "code": self.code, "retryable": self.retryable}
        )


def upload_metadata(path: str, audio: bytes) -> tuple[str, str]:
    name = Path(path).name
    if Path(path).suffix.lower() == ".oga" and audio.startswith(b"OggS"):
        return Path(name).with_suffix(".ogg").name, "audio/ogg"
    return name, mimetypes.guess_type(path)[0] or "application/octet-stream"


class UnavailableTranscriptionProvider:
    configured = False

    async def transcribe(self, file_path: str, language: str = "ru") -> str:
        raise RuntimeError("transcription provider is not configured")


class OpenAITranscriptionProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def transcribe(self, file_path: str, language: str = "ru") -> str:
        form = aiohttp.FormData()
        audio = await asyncio.to_thread(Path(file_path).read_bytes)
        filename, content_type = upload_metadata(file_path, audio)
        form.add_field(
            "file",
            audio,
            filename=filename,
            content_type=content_type,
        )
        form.add_field("model", "gpt-4o-mini-transcribe")
        form.add_field("language", language)
        async with (
            aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    ssl=ssl.create_default_context(cafile=certifi.where())
                ),
                timeout=aiohttp.ClientTimeout(total=180),
            ) as session,
            session.post(
                "https://api.openai.com/v1/audio/transcriptions",
                data=form,
                headers={"Authorization": f"Bearer {self.api_key}"},
                allow_redirects=False,
            ) as response,
        ):
            if response.status != 200:
                try:
                    failure = await response.json()
                    error = failure.get("error", {}) if isinstance(failure, dict) else {}
                    code = error.get("code") if isinstance(error, dict) else None
                except (ValueError, aiohttp.ContentTypeError):
                    code = None
                raise TranscriptionError(response.status, code)
            payload = await response.json()
        return payload["text"]


def build_provider():
    if os.getenv("TRANSCRIPTION_PROVIDER", "").lower() == "openai" and os.getenv(
        "TRANSCRIPTION_API_KEY"
    ):
        return OpenAITranscriptionProvider(os.environ["TRANSCRIPTION_API_KEY"])
    return UnavailableTranscriptionProvider()
