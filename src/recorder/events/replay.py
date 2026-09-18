"""Rebuild normalized exchange data from immutable capture envelopes."""

import hashlib
import json
from pathlib import Path

from recorder.market.candles import next_start


def prepare(event):
    event = dict(event)
    context = event.get("context", {})
    if context.get("normalized_data") is not None:
        event.setdefault("normalized_data", context["normalized_data"])
    path = event.get("topic", "")
    topics = {
        "/v5/order/history": "order",
        "/v5/order/realtime": "order",
        "/v5/execution/list": "execution",
        "/v5/position/list": "position",
        "/v5/account/wallet-balance": "wallet",
        "/v5/account/info": "account",
        "/v5/position/closed-pnl": "closed_pnl",
        "/v5/account/transaction-log": "funding",
    }
    payload = event["payload"]
    if path in topics and not payload.get("retCode"):
        event.setdefault("normalized_topic", topics[path])
        result = payload.get("result", {})
        event.setdefault(
            "normalized_data", [result] if topics[path] == "account" else result.get("list", [])
        )
    if path == "/v5/market/kline" and "normalized_data" not in event:
        params = context.get("request", {})
        if not {"symbol", "interval"} <= params.keys():
            raise ValueError("Legacy REST kline lacks request context")
        from datetime import datetime

        ceiling = min(
            int(params.get("end", 2**63 - 1)) + 1,
            int(datetime.fromisoformat(event["received_at"]).timestamp() * 1000),
        )
        data = []
        for row in payload.get("result", {}).get("list", []):
            start = int(row[0])
            stop = next_start(start, str(params["interval"]))
            if start < int(params.get("start", 0)) or stop > ceiling:
                continue
            data.append(
                {
                    "symbol": params["symbol"],
                    "interval": str(params["interval"]),
                    "start": start,
                    "end": stop - 1,
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                    "turnover": row[6],
                    "confirm": True,
                }
            )
        event["normalized_topic"] = f"kline.{params['interval']}.{params['symbol']}"
        event["normalized_data"] = data
    return event


async def replay(directory, ingestor):
    counts = {"processed": 0, "failed": 0, "unsupported": 0}
    for path in sorted(Path(directory).glob("*.jsonl")):
        with path.open("rb") as handle:
            while True:
                offset = handle.tell()
                line = handle.readline()
                if not line:
                    break
                event = None
                try:
                    event = json.loads(line)
                    event.setdefault(
                        "capture_id",
                        hashlib.sha256(
                            str(path.resolve()).encode() + str(offset).encode() + line
                        ).hexdigest(),
                    )
                    event.update(
                        raw_path=str(path.resolve()), byte_offset=offset, byte_length=len(line)
                    )
                    if event.get("source") in {"TELEGRAM", "SYSTEM"}:
                        counts["unsupported"] += 1
                        continue
                    counts["processed"] += await ingestor.handle(event)
                except (ValueError, TypeError, KeyError) as exc:
                    counts["failed"] += 1
                    if (
                        isinstance(event, dict)
                        and event.get("received_at")
                        and event.get("raw_path")
                    ):
                        ingestor.failure(event, exc)
    return counts
