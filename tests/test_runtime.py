import asyncio
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from recorder.config import RecorderConfig, SymbolsConfig
from recorder.events.models import RawEvent
from recorder.export.verifier import verify_raw
from recorder.storage.lifecycle import DatabaseLease
from recorder.storage.raw_jsonl import RawJsonlWriter


@pytest.mark.parametrize(
    "script",
    [
        "reconcile.py",
        "backfill_market.py",
        "replay_raw.py",
        "retry_transcription.py",
        "export_dataset.py",
        "verify_dataset.py",
        "inspect.py",
    ],
)
def test_cli_help_has_no_import_side_effects(script):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / script), "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


@pytest.mark.asyncio
async def test_runner_public_only_graceful_shutdown_and_drain(tmp_path, monkeypatch):
    from recorder import main

    cfg = RecorderConfig(
        storage={
            "sqlite": {"path": str(tmp_path / "db.sqlite")},
            "raw_jsonl": {"directory": str(tmp_path / "raw")},
            "parquet": {"directory": str(tmp_path / "exports")},
        },
        market={},
        reconciliation={},
        telegram={"enabled": False},
        transcription={"enabled": False},
        dataset={},
    )
    symbols = SymbolsConfig(symbols=["SUIUSDT"], market={"kline_intervals": ["1"]})
    monkeypatch.setattr(main, "load_config", lambda: (symbols, cfg))
    monkeypatch.setattr(main, "credentials", lambda: ("", ""))
    callbacks = []
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "add_signal_handler", lambda sig, cb: callbacks.append(cb))
    monkeypatch.setattr(loop, "remove_signal_handler", lambda sig: None)

    class Rest:
        def __init__(self, *args):
            pass

        async def klines(self, *args):
            return []

    monkeypatch.setattr(main, "ReadOnlyBybitRest", Rest)

    class Collector:
        def __init__(self, raw, on_event, session, on_connect):
            self.raw, self.on_event, self.session, self.on_connect = (
                raw,
                on_event,
                session,
                on_connect,
            )

        async def run(self):
            from datetime import UTC, datetime

            stamp = datetime.now(UTC).isoformat()
            await self.session(
                {
                    "status": "connected",
                    "session_id": "fake",
                    "source": "bybit_public",
                    "timestamp": stamp,
                    "reconnect_count": 0,
                }
            )
            await self.on_connect(0)
            event = await self.raw.capture(
                RawEvent(
                    source="bybit_public",
                    topic="kline.1.SUIUSDT",
                    payload={
                        "topic": "kline.1.SUIUSDT",
                        "ts": 60000,
                        "data": [
                            {
                                "start": 0,
                                "end": 59999,
                                "interval": "1",
                                "open": "1",
                                "high": "2",
                                "low": "0",
                                "close": "1",
                                "volume": "1",
                                "turnover": "1",
                                "confirm": True,
                            }
                        ],
                    },
                )
            )
            await self.on_event(event)
            callbacks[0]()
            try:
                await asyncio.Future()
            finally:
                await self.session(
                    {
                        "status": "disconnected",
                        "session_id": "fake",
                        "source": "bybit_public",
                        "timestamp": stamp,
                        "reason": "shutdown",
                        "reconnect_count": 0,
                    }
                )

        async def stop(self):
            pass

    def build(symbols, intervals, testnet, raw, on_event, **kwargs):
        return Collector(raw, on_event, kwargs["session_callback"], kwargs["on_connect"])

    monkeypatch.setattr(main, "build_public_collector", build)
    await asyncio.wait_for(main.run(), 3)
    db = sqlite3.connect(tmp_path / "db.sqlite")
    try:
        assert db.execute("SELECT COUNT(*) FROM market_candles").fetchone()[0] == 1
        assert (
            db.execute(
                "SELECT COUNT(*) FROM websocket_sessions WHERE disconnected_at IS NULL"
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute("SELECT COUNT(*) FROM raw_events_index WHERE status='pending'").fetchone()[0]
            == 0
        )
    finally:
        db.close()
    DatabaseLease(tmp_path / "db.sqlite").acquire().close()


@pytest.mark.asyncio
async def test_interrupted_raw_tail_kept_but_next_record_valid(tmp_path):
    from datetime import UTC, datetime

    path = tmp_path / (datetime.now(UTC).strftime("%Y-%m-%d") + ".jsonl")
    path.write_bytes(b'{"interrupted":')
    writer = RawJsonlWriter(tmp_path)
    envelope = await writer.capture(RawEvent(source="test", payload={"valid": True}))
    import json

    with path.open("rb") as handle:
        handle.seek(envelope["byte_offset"])
        assert json.loads(handle.read(envelope["byte_length"]))["payload"] == {"valid": True}
    assert any("FAIL:" in p for p in verify_raw(tmp_path))
