from __future__ import annotations

import hashlib
import hmac
import time

from recorder.bybit.private_ws import PRIVATE_TOPICS
from recorder.bybit.ws_common import BybitWebSocketCollector
from recorder.storage.raw_jsonl import RawJsonlWriter


def build_private_collector(
    api_key: str,
    api_secret: str,
    testnet: bool,
    raw_writer: RawJsonlWriter,
    on_event,
    session_store=None,
    **kwargs,
):
    host = "stream-testnet.bybit.com" if testnet else "stream.bybit.com"

    def auth():
        expires = int(time.time() * 1000) + 10_000
        signature = hmac.new(
            api_secret.encode(), f"GET/realtime{expires}".encode(), hashlib.sha256
        ).hexdigest()
        return {"op": "auth", "args": [api_key, expires, signature]}

    return BybitWebSocketCollector(
        f"wss://{host}/v5/private",
        "bybit_private",
        list(PRIVATE_TOPICS),
        raw_writer,
        on_event,
        session_store,
        auth,
        **kwargs,
    )
