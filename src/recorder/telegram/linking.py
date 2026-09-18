from collections.abc import Iterable
from datetime import datetime, timedelta


def candidate_event_ids(
    note_at: datetime,
    events: Iterable[tuple[int, datetime]],
    lookback_minutes: int,
    lookforward_minutes: int,
) -> list[int]:
    low, high = (
        note_at - timedelta(minutes=lookback_minutes),
        note_at + timedelta(minutes=lookforward_minutes),
    )
    return [event_id for event_id, when in events if low <= when <= high]
