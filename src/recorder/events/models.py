from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class RawEvent:
    source: str
    payload: dict[str, Any]
    topic: str | None = None
    connection_id: str | None = None
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    exchange_timestamp: int | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "received_at": self.received_at.isoformat(),
            "source": self.source,
            "connection_id": self.connection_id,
            "topic": self.topic,
            "exchange_timestamp": self.exchange_timestamp,
            "payload": self.payload,
            "context": self.context,
        }

    def json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, separators=(",", ":"))
