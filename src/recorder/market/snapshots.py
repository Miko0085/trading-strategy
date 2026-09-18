from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class MarketSnapshot:
    symbol: str
    timestamp: datetime
    last_price: str | None = None
    mark_price: str | None = None
    index_price: str | None = None
    bid: str | None = None
    ask: str | None = None
