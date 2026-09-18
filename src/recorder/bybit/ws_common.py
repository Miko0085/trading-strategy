from __future__ import annotations

import asyncio
import json
import logging
import ssl
import time
import uuid
from datetime import UTC, datetime

import aiohttp
import certifi

from recorder.events.models import RawEvent

log = logging.getLogger(__name__)


class BybitWebSocketCollector:
    def __init__(
        self,
        url,
        source,
        topics,
        raw_writer,
        on_event,
        session_store=None,
        auth=None,
        on_connect=None,
        session_callback=None,
        sample_seconds=0,
        save_open_kline_updates_raw=True,
    ):
        self.url, self.source, self.topics = url, source, topics
        self.raw_writer, self.on_event, self.auth = raw_writer, on_event, auth
        self.session_store, self.session_callback = session_store, session_callback
        self.on_connect = on_connect
        self.sample_seconds = sample_seconds
        self.save_open_kline_updates_raw = save_open_kline_updates_raw
        self.connection_id = ""
        self._stop = asyncio.Event()
        self.ready = asyncio.Event()
        self.ws = None
        self.reconnect_count = 0
        self.tickers = {}
        self.sampled_at = {}

    async def stop(self):
        self._stop.set()
        if self.ws:
            await self.ws.close()

    async def session(self, status, reason=None):
        row = {
            "session_id": self.connection_id,
            "source": self.source,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": reason,
            "reconnect_count": self.reconnect_count,
        }
        if self.session_callback:
            await self.session_callback(row)
        elif self.session_store:
            if status == "connected":
                self.session_store.start_websocket_session(
                    self.connection_id, self.source, row["timestamp"]
                )
            else:
                self.session_store.finish_websocket_session(
                    self.connection_id, row["timestamp"], reason
                )

    async def run(self):
        delay = 1
        while not self._stop.is_set():
            try:
                await self._connect_once()
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, TimeoutError, ValueError, RuntimeError) as exc:
                log.warning("%s reconnect: %s", self.source, type(exc).__name__)
            # Disk/storage failures propagate to supervisor; do not keep receiving.
            if not self._stop.is_set():
                self.reconnect_count += 1
                try:
                    await asyncio.wait_for(self._stop.wait(), delay)
                except TimeoutError:
                    pass
                delay = min(delay * 2, 30)

    async def _connect_once(self):
        self.connection_id = uuid.uuid4().hex
        self.tickers.clear()
        self.sampled_at.clear()
        reason = "closed"
        heartbeat = None
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            async with (
                aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=context)) as session,
                session.ws_connect(self.url, autoping=True) as ws,
            ):
                self.ws = ws
                if self.auth:
                    await ws.send_json(self.auth())
                    auth = await ws.receive_json(timeout=15)
                    if auth.get("op") != "auth" or auth.get("success") is not True:
                        raise RuntimeError("Private WS authentication rejected")
                # Small subscription batches respect per-request product limits.
                for start in range(0, len(self.topics), 10):
                    await ws.send_json({"op": "subscribe", "args": self.topics[start : start + 10]})
                    while True:
                        payload = await ws.receive_json(timeout=15)
                        if payload.get("op") == "subscribe":
                            if payload.get("success") is not True:
                                raise RuntimeError("WS subscription rejected")
                            break
                        await self.receive(payload)
                self.ready.set()
                await self.session("connected")
                if self.on_connect:
                    await self.on_connect(self.reconnect_count)

                async def ping():
                    while True:
                        await asyncio.sleep(20)
                        await ws.send_json({"op": "ping"})

                heartbeat = asyncio.create_task(ping())
                while not self._stop.is_set():
                    message = await ws.receive(timeout=65)
                    if message.type == aiohttp.WSMsgType.TEXT:
                        await self.receive(json.loads(message.data))
                    elif message.type in {
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.CLOSE,
                        aiohttp.WSMsgType.ERROR,
                    }:
                        break
        except BaseException as exc:
            reason = type(exc).__name__
            raise
        finally:
            self.ready.clear()
            self.ws = None
            if heartbeat:
                heartbeat.cancel()
                await asyncio.gather(heartbeat, return_exceptions=True)
            await self.session("disconnected", reason)

    async def receive(self, payload):
        topic = payload.get("topic", "")
        if not topic:
            return
        if topic.startswith("kline.") and not self.save_open_kline_updates_raw:
            items = payload.get("data") or []
            if not any(item.get("confirm") for item in items):
                return
        received = datetime.now(UTC)
        normalized = None
        if topic.startswith("tickers."):
            item = payload["data"]
            symbol = item["symbol"]
            current = {} if payload.get("type") == "snapshot" else self.tickers.get(symbol, {})
            self.tickers[symbol] = {**current, **item}
            if time.monotonic() - self.sampled_at.get(symbol, 0) < self.sample_seconds:
                return
            self.sampled_at[symbol] = time.monotonic()
            normalized = [self.tickers[symbol].copy()]
        event = await self.raw_writer.capture(
            RawEvent(
                source=self.source,
                payload=payload,
                topic=topic,
                connection_id=self.connection_id,
                received_at=received,
                exchange_timestamp=payload.get("ts", payload.get("creationTime")),
                context={"normalized_data": normalized} if normalized is not None else {},
            )
        )
        if normalized is not None:
            event["normalized_data"] = normalized
        await self.on_event(event)
