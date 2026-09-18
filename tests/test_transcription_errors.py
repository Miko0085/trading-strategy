import asyncio
import json

import pytest

from recorder.storage.sqlite import SQLiteStore
from recorder.telegram.voice import VoiceService
from recorder.transcription.provider import TranscriptionError, upload_metadata


def test_telegram_oga_upload_does_not_change_original(tmp_path):
    path = tmp_path / "voice.oga"
    original = b"OggS\x00original"
    path.write_bytes(original)
    assert upload_metadata(str(path), original) == ("voice.ogg", "audio/ogg")
    assert path.read_bytes() == original
    assert upload_metadata(str(path), b"not ogg")[0] == "voice.oga"


@pytest.mark.parametrize(
    "status,code,retryable",
    [
        (400, "unsupported_format", False),
        (401, "invalid_api_key", False),
        (429, "insufficient_quota", False),
        (429, "rate_limit_exceeded", True),
        (503, None, True),
    ],
)
def test_error_policy(status, code, retryable):
    error = TranscriptionError(status, code)
    assert json.loads(error.diagnostic())["retryable"] is retryable
    assert "secret" not in TranscriptionError(400, "secret response body").diagnostic()


@pytest.mark.asyncio
async def test_permanent_error_keeps_audio_and_is_not_auto_retried(tmp_path, monkeypatch):
    class Provider:
        calls = 0

        async def transcribe(self, *args):
            self.calls += 1
            raise TranscriptionError(400, "unsupported_format")

    store = SQLiteStore(tmp_path / "test.db")
    store.initialize()
    audio = tmp_path / "voice.oga"
    audio.write_bytes(b"OggSoriginal")
    store.insert_voice_message(
        "v", "m", "f", "2026-09-14T00:00:00+00:00", 1, str(audio), audio.stat().st_size, "pending"
    )
    provider = Provider()
    service = VoiceService(tmp_path, store, provider)
    try:
        assert await service.transcribe("v") == (None, "failed")
        row = store.db.execute("SELECT error FROM transcriptions").fetchone()
        assert json.loads(row[0])["http_status"] == 400

        async def stop(*args):
            raise asyncio.CancelledError

        monkeypatch.setattr("recorder.telegram.voice.asyncio.sleep", stop)
        with pytest.raises(asyncio.CancelledError):
            await service.retry_loop()
        assert provider.calls == 1
        assert audio.read_bytes() == b"OggSoriginal"
    finally:
        store.close()
