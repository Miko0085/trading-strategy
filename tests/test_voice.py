import asyncio

from recorder.storage.sqlite import SQLiteStore
from recorder.telegram.voice import VoiceService


class FakeBot:
    async def call(self, method, payload):
        return {"result": {"file_path": "voice/test.ogg"}}

    async def download_file(self, file_path):
        return b"audio-bytes"


class FakeProvider:
    async def transcribe(self, file_path, language="ru"):
        return "Я поднял лимитки выше"


def test_voice_original_and_verbatim_transcript(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    service = VoiceService(tmp_path / "voice", store, FakeProvider())
    voice_id, transcript, status = asyncio.run(
        service.save_and_transcribe(
            FakeBot(), {"message_id": 7, "voice": {"file_id": "file-1", "duration": 3}}
        )
    )
    assert transcript == "Я поднял лимитки выше"
    assert status == "completed"
    row = store.db.execute(
        "SELECT local_path,transcription_status FROM voice_messages WHERE voice_id=?", (voice_id,)
    ).fetchone()
    assert row[1] == "completed"
    assert __import__("pathlib").Path(row[0]).read_bytes() == b"audio-bytes"
    store.close()


def test_voice_failure_keeps_original(tmp_path):
    class BrokenProvider:
        async def transcribe(self, file_path, language="ru"):
            raise RuntimeError("provider down")

    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    service = VoiceService(tmp_path / "voice", store, BrokenProvider())
    voice_id, transcript, status = asyncio.run(
        service.save_and_transcribe(FakeBot(), {"message_id": 8, "voice": {"file_id": "file-2"}})
    )
    assert transcript is None and status == "failed"
    assert (
        store.db.execute(
            "SELECT COUNT(*) FROM voice_messages WHERE voice_id=?", (voice_id,)
        ).fetchone()[0]
        == 1
    )
    store.close()
