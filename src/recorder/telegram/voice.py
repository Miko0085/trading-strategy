import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from recorder.telegram.notes import save_text_note
from recorder.transcription.provider import TranscriptionError


class VoiceService:
    def __init__(
        self, base_directory, store, provider, writer=None, max_attempts=5, retry_seconds=60
    ):
        self.base_directory = Path(base_directory)
        self.store, self.provider, self.writer = store, provider, writer
        self.max_attempts, self.retry_seconds = max_attempts, retry_seconds

    async def db(self, operation):
        return await self.writer.call(operation) if self.writer else operation()

    async def save(self, bot, message, event_ids=(), update_id=None):
        if update_id is not None:
            existing = await self.db(
                lambda: self.store.db.execute(
                    "SELECT voice_id,id FROM trader_notes WHERE telegram_update_id=?", (update_id,)
                ).fetchone()
            )
            if existing:
                return existing[0], existing[1]
        media = message.get("voice") or message.get("audio")
        if not media:
            raise ValueError("voice/audio missing")
        received = datetime.now(UTC)
        voice_id = uuid4().hex
        info = await bot.call("getFile", {"file_id": media["file_id"]})
        remote = info["result"]["file_path"]
        audio = await bot.download_file(remote)
        directory = self.base_directory / f"{received:%Y-%m-%d}"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (voice_id + (Path(remote).suffix or ".ogg"))

        def persist():
            import os

            with path.open("xb") as handle:
                handle.write(audio)
                handle.flush()
                os.fsync(handle.fileno())

        task = asyncio.create_task(asyncio.to_thread(persist))
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            await task
            raise

        def record():
            with self.store.transaction():
                note_id = save_text_note(
                    self.store,
                    "",
                    event_ids,
                    owner_id=message.get("from", {}).get("id"),
                    chat_id=message.get("chat", {}).get("id"),
                    update_id=update_id,
                    voice_id=voice_id,
                )
                self.store.insert_voice_message(
                    voice_id,
                    str(message.get("message_id", "")),
                    media["file_id"],
                    received.isoformat(),
                    media.get("duration"),
                    str(path.resolve()),
                    len(audio),
                    "pending",
                )
                self.store.db.execute(
                    "UPDATE voice_messages SET note_id=?,chat_id=? WHERE voice_id=?",
                    (note_id, message.get("chat", {}).get("id"), voice_id),
                )
                return note_id

        note_id = await self.db(record)
        return voice_id, note_id

    async def transcribe(self, voice_id):
        row = await self.db(
            lambda: self.store.db.execute(
                "SELECT * FROM voice_messages WHERE voice_id=?", (voice_id,)
            ).fetchone()
        )
        if row is None:
            raise ValueError("unknown voice")
        if row["transcription_status"] == "completed":
            text = await self.db(
                lambda: self.store.db.execute(
                    "SELECT transcript FROM transcriptions WHERE voice_id=?", (voice_id,)
                ).fetchone()[0]
            )
            return text, "completed"
        if getattr(self.provider, "configured", True) is False:
            return None, "pending"
        attempt = row["attempt_count"] + 1
        if attempt > self.max_attempts:
            return None, "failed"

        def mark():
            self.store.db.execute(
                "UPDATE voice_messages SET attempt_count=?,last_attempt=? WHERE voice_id=?",
                (attempt, datetime.now(UTC).isoformat(), voice_id),
            )
            self.store._commit()

        await self.db(mark)
        try:
            transcript = await self.provider.transcribe(row["local_path"], "ru")
            if not isinstance(transcript, str) or not transcript.strip():
                raise ValueError("empty transcript")
        except Exception as exc:  # noqa: BLE001 -- persist STT failure without losing audio
            error_type = (
                exc.diagnostic() if isinstance(exc, TranscriptionError) else type(exc).__name__
            )
            retryable = not isinstance(exc, TranscriptionError) or exc.retryable

            def failed():
                with self.store.transaction():
                    self.store.insert_transcription(voice_id, None, "ru", "failed", error_type)
                    self.store.set_voice_status(voice_id, "failed")
                    self.store.db.execute(
                        "UPDATE voice_messages SET next_attempt=? WHERE voice_id=?",
                        (
                            (
                                datetime.now(UTC)
                                + timedelta(seconds=self.retry_seconds * 2 ** (attempt - 1))
                            ).isoformat()
                            if retryable
                            else None,
                            voice_id,
                        ),
                    )

            await self.db(failed)
            return None, "failed"

        def success():
            with self.store.transaction():
                self.store.insert_transcription(voice_id, transcript, "ru", "completed", None)
                self.store.set_voice_status(voice_id, "completed")
                # Never overwrite a trader correction.
                self.store.db.execute(
                    "UPDATE trader_notes SET original_text=?,text=CASE WHEN text='' THEN ? ELSE text END WHERE id=?",
                    (transcript, transcript, row["note_id"]),
                )
                if row["chat_id"] and row["note_id"]:
                    self.store.db.execute(
                        "INSERT INTO notification_outbox(destination,payload_json) VALUES(?,?)",
                        (row["chat_id"], json.dumps({"review_note": row["note_id"]})),
                    )

        await self.db(success)
        return transcript, "completed"

    async def save_and_transcribe(self, bot, message, event_ids=()):
        voice_id, _ = await self.save(bot, message, event_ids)
        transcript, status = await self.transcribe(voice_id)
        return voice_id, transcript, status

    async def retry_loop(self, notify=None):
        while True:
            rows = await self.db(
                lambda: self.store.db.execute(
                    "SELECT v.voice_id,v.note_id,v.chat_id,t.error FROM voice_messages v LEFT JOIN transcriptions t ON t.voice_id=v.voice_id WHERE v.transcription_status IN ('pending','failed') AND v.attempt_count<? AND (v.next_attempt IS NULL OR v.next_attempt<=?)",
                    (self.max_attempts, datetime.now(UTC).isoformat()),
                ).fetchall()
            )
            for row in rows:
                try:
                    diagnostic = json.loads(row["error"] or "null")
                except (ValueError, TypeError):
                    diagnostic = None
                if isinstance(diagnostic, dict) and diagnostic.get("retryable") is False:
                    continue
                _text, status = await self.transcribe(row["voice_id"])
                if status == "completed" and notify and row["chat_id"]:
                    await notify(row["chat_id"], row["note_id"])
            await asyncio.sleep(self.retry_seconds)
