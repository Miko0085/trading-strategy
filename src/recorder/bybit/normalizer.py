from __future__ import annotations

from typing import Any


def topic_items(message: dict[str, Any]) -> list[dict[str, Any]]:
    data = message.get("data", [])
    return data if isinstance(data, list) else [data]


def normalize_kline(message: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for item in topic_items(message):
        result.append(
            {
                "symbol": message.get("topic", "").split(".")[-1],
                **item,
                "exchange_ts": message.get("ts"),
                "source": "WS",
            }
        )
    return result


def execution_identity(item: dict[str, Any]) -> str:
    if not item.get("execId"):
        raise ValueError("Bybit execution has no execId")
    return str(item["execId"])
