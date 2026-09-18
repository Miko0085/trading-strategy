from __future__ import annotations

import asyncio
import logging
import os
import signal
from datetime import UTC, datetime
from pathlib import Path

from recorder.bybit.private_collector import build_private_collector
from recorder.bybit.public_collector import build_public_collector
from recorder.bybit.reconciliation import Reconciler, backfill_klines
from recorder.bybit.rest import ReadOnlyBybitRest
from recorder.config import credentials, load_config
from recorder.events.ingestion import EventIngestor
from recorder.events.interpreter import Notifier
from recorder.events.models import RawEvent
from recorder.events.queue import ControlledWriter
from recorder.logging_config import configure_logging
from recorder.market.automatic import AutomaticMarkets
from recorder.market.discovery import bootstrap
from recorder.storage.lifecycle import DatabaseLease, backup_database
from recorder.storage.raw_jsonl import RawJsonlWriter
from recorder.storage.sqlite import SQLiteStore
from recorder.telegram.bot import TelegramBot
from recorder.telegram.voice import VoiceService
from recorder.transcription.provider import build_provider

log = logging.getLogger(__name__)


async def run():
    symbols, cfg = load_config()
    path = Path(cfg.storage["sqlite"]["path"])
    lease = DatabaseLease(path).acquire()
    try:
        backup_database(path)
        store = SQLiteStore(path)
        store.initialize()
    except BaseException:
        lease.close()
        raise
    snapshot_cfg = cfg.market["snapshots"]
    ingestor = EventIngestor(
        store,
        symbols.symbols,
        snapshot_cfg["enabled"] and snapshot_cfg["on_account_event"],
        category=symbols.category,
    )
    writer = ControlledWriter(ingestor.handle, on_error=ingestor.failure)
    writer_task = asyncio.create_task(writer.run())
    raw = RawJsonlWriter(cfg.storage["raw_jsonl"]["directory"])
    tasks = []
    collectors = []
    shutdown = asyncio.Event()
    loop = asyncio.get_running_loop()
    registered = []
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown.set)
            registered.append(sig)
        except NotImplementedError:
            pass

    async def capture(event):
        envelope = await raw.capture(event)

        def register():
            with store.transaction():
                raw_id = ingestor.index(envelope)
                if event.source == "SYSTEM" or event.payload.get("retCode"):
                    store.db.execute(
                        "UPDATE raw_events_index SET status=? WHERE id=?",
                        ("captured" if event.source == "SYSTEM" else "source_error", raw_id),
                    )

        await writer.call(register)
        return envelope

    async def system(text):
        envelope = await capture(RawEvent(source="SYSTEM", topic="system", payload={"text": text}))
        await writer.call(
            lambda: store.insert_timeline(
                {
                    "event_type": "SYSTEM",
                    "source": "SYSTEM",
                    "summary_ru": text,
                    "linked_raw_event_id": ingestor.index(envelope),
                }
            )
        )

    async def session(row):
        await capture(RawEvent(source="SYSTEM", topic="websocket_session", payload=row))

        def persist():
            with store.transaction():
                if row["status"] == "connected":
                    store.start_websocket_session(
                        row["session_id"], row["source"], row["timestamp"]
                    )
                    store.db.execute(
                        "UPDATE websocket_sessions SET reconnect_count=? WHERE session_id=?",
                        (row["reconnect_count"], row["session_id"]),
                    )
                else:
                    store.db.execute(
                        "INSERT OR IGNORE INTO websocket_sessions(session_id,source,connected_at) VALUES(?,?,?)",
                        (row["session_id"], row["source"], row["timestamp"]),
                    )
                    store.finish_websocket_session(
                        row["session_id"], row["timestamp"], row["reason"]
                    )
                    if not shutdown.is_set():
                        store.gap("websocket_disconnect", row["source"] + ": " + str(row["reason"]))

        await writer.call(persist)

    try:

        def recover_sessions():
            rows = store.db.execute(
                "SELECT session_id FROM websocket_sessions WHERE disconnected_at IS NULL"
            ).fetchall()
            with store.transaction():
                for row in rows:
                    store.finish_websocket_session(
                        row[0], datetime.now(UTC).isoformat(), "unclean_previous_shutdown"
                    )
                    store.gap("unclean_shutdown", f"session={row[0]}")

        await writer.call(recover_sessions)
        await writer.call(lambda: bootstrap(store, symbols.category, symbols.symbols))
        await system("Recorder запущен")
        key, secret = credentials()
        if bool(key) != bool(secret):
            raise ValueError("Both Bybit credential variables are required")
        rest = ReadOnlyBybitRest(key or "", secret or "", cfg.environment == "testnet", capture)
        market_rest = ReadOnlyBybitRest("", "", cfg.environment == "testnet", capture)
        rec = Reconciler(
            rest, writer, store, symbols.symbols, symbols.category, raw, cfg.reconciliation
        )
        triggers = asyncio.Queue()

        async def private_ready(reconnect):
            if cfg.reconciliation["enabled"] and cfg.reconciliation["on_reconnect"] and reconnect:
                await triggers.put("reconnect")

        async def recovery_loop():
            while True:
                reason = await triggers.get()
                try:
                    await rec.run(reason)
                finally:
                    triggers.task_done()

        async def periodic():
            while True:
                await asyncio.sleep(cfg.reconciliation["interval_seconds"])
                await triggers.put("periodic")

        async def market_backfill(targets=None):
            import time

            end = int(time.time() * 1000) - 1
            for symbol in targets if targets is not None else symbols.symbols:
                for interval in symbols.market["kline_intervals"]:
                    latest = await writer.call(
                        lambda symbol=symbol, interval=interval: store.db.execute(
                            "SELECT MAX(start_ms) FROM market_candles WHERE symbol=? AND interval=?",
                            (symbol, interval),
                        ).fetchone()[0]
                    )
                    start = latest if latest is not None else end - 3600000
                    try:
                        await backfill_klines(
                            market_rest,
                            store,
                            symbols.category,
                            symbol,
                            interval,
                            start,
                            end,
                            writer,
                            raw,
                        )
                    except Exception as exc:  # noqa: BLE001 -- isolate recoverable backfill errors
                        error_type = type(exc).__name__
                        await writer.call(
                            lambda start=start, error_type=error_type: store.gap(
                                "market_backfill", error_type, start, end
                            )
                        )

        market_trigger = asyncio.Event()

        async def public_ready(reconnect):
            market_trigger.set()

        async def market_loop():
            while True:
                await market_trigger.wait()
                market_trigger.clear()
                await market_backfill()

        public = build_public_collector(
            symbols.symbols,
            symbols.market["kline_intervals"],
            cfg.environment == "testnet",
            raw,
            writer.put,
            category=symbols.category,
            ticker=symbols.market["ticker"],
            public_trades=symbols.market["public_trades"]["enabled"],
            orderbook=symbols.market["orderbook"],
            save_open_kline_updates_raw=cfg.market["save_open_kline_updates_raw"],
            session_callback=session,
            on_connect=public_ready,
        )
        collectors.append(public)
        tasks.extend([asyncio.create_task(public.run()), asyncio.create_task(market_loop())])
        if cfg.market["auto_discovery"]:
            automatic = AutomaticMarkets(store, writer, raw, symbols, cfg, session, market_backfill)
            tasks.append(asyncio.create_task(automatic.run()))
        if key:
            await rest.validate_read_only()
            private = build_private_collector(
                key,
                secret,
                cfg.environment == "testnet",
                raw,
                writer.put,
                session_callback=session,
                on_connect=private_ready,
            )
            collectors.append(private)
            tasks.extend([asyncio.create_task(private.run()), asyncio.create_task(recovery_loop())])
            if cfg.reconciliation["enabled"]:
                if cfg.reconciliation["on_startup"]:
                    await triggers.put("startup")
                if cfg.reconciliation["periodic"]:
                    tasks.append(asyncio.create_task(periodic()))
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        users = {
            int(s.strip())
            for s in os.getenv("TELEGRAM_ALLOWED_USER_ID", "").split(",")
            if s.strip()
        }
        chats = {
            int(s.strip())
            for s in os.getenv("TELEGRAM_ALLOWED_CHAT_ID", "").split(",")
            if s.strip()
        }
        if cfg.telegram["enabled"] and token and (users or chats):
            voice = VoiceService(
                cfg.transcription["directory"],
                store,
                build_provider(),
                writer,
                cfg.transcription["max_attempts"],
                cfg.transcription["retry_seconds"],
            )
            bot = TelegramBot(
                token, users, store, cfg.telegram["event_linking"], voice, chats, writer, raw
            )
            tasks.append(asyncio.create_task(bot.run()))
            if cfg.transcription["enabled"]:
                tasks.append(asyncio.create_task(voice.retry_loop()))
            tasks.append(
                asyncio.create_task(
                    Notifier(
                        store,
                        writer,
                        bot,
                        cfg.telegram["notifications"],
                        cfg.telegram["aggregation_seconds"],
                    ).run()
                )
            )
        stop_task = asyncio.create_task(shutdown.wait())
        done, _ = await asyncio.wait(
            [writer_task, stop_task, *tasks], return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            if task is not stop_task:
                if task.cancelled():
                    continue
                error = task.exception()
                if error:
                    raise RuntimeError(
                        f"Background service failed: {type(error).__name__}"
                    ) from None
                raise RuntimeError("Background service stopped unexpectedly")
    finally:
        shutdown.set()
        for collector in collectors:
            await collector.stop()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if not writer_task.done():
            await system("Recorder остановлен")
            await writer.drain()
        else:
            await asyncio.gather(writer_task, return_exceptions=True)
        if "stop_task" in locals():
            stop_task.cancel()
            await asyncio.gather(stop_task, return_exceptions=True)
        store.close()
        lease.close()
        for sig in registered:
            loop.remove_signal_handler(sig)


def main():
    configure_logging()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
