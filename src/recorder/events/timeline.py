from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def timeline_row(
    event_type: str,
    source: str,
    source_id: str | None,
    symbol: str | None = None,
    summary_ru: str | None = None,
    exchange_ts: int | None = None,
) -> dict[str, Any]:
    return {
        "timestamp_exchange": datetime.fromtimestamp(int(exchange_ts) / 1000, UTC).isoformat()
        if exchange_ts
        else None,
        "timestamp_received": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "symbol": symbol,
        "source": source,
        "source_id": source_id,
        "summary_ru": summary_ru,
    }
