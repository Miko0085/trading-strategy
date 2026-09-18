"""Explicit maintenance retry; originals and trader corrections are preserved."""

import argparse
import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != _scripts_dir]

import asyncio

from recorder.config import load_config
from recorder.storage.lifecycle import DatabaseLease, backup_database
from recorder.storage.sqlite import SQLiteStore
from recorder.telegram.voice import VoiceService
from recorder.transcription.provider import build_provider


async def main(voice_id, reset):
    _, cfg = load_config()
    provider = build_provider()
    if getattr(provider, "configured", True) is False:
        raise SystemExit("Configure transcription provider credentials first")
    lease = DatabaseLease(cfg.storage["sqlite"]["path"]).acquire()
    store = None
    try:
        backup_database(cfg.storage["sqlite"]["path"])
        store = SQLiteStore(cfg.storage["sqlite"]["path"])
        store.initialize()
        if reset:
            store.db.execute(
                "UPDATE voice_messages SET attempt_count=0,next_attempt=NULL WHERE voice_id=? AND transcription_status!='completed'",
                (voice_id,),
            )
            store._commit()
        voice = VoiceService(
            cfg.transcription["directory"],
            store,
            provider,
            max_attempts=cfg.transcription["max_attempts"],
            retry_seconds=cfg.transcription["retry_seconds"],
        )
        _, status = await voice.transcribe(voice_id)
        print(f"Transcription status: {status}; original audio retained")
        return int(status != "completed")
    finally:
        if store:
            store.close()
        lease.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice-id", required=True)
    parser.add_argument("--reset-attempts", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.voice_id, args.reset_attempts)))
