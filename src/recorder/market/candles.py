from datetime import UTC, datetime, timedelta

from recorder.config import VALID_INTERVALS


def next_start(start, interval):
    if interval not in VALID_INTERVALS:
        raise ValueError("unsupported interval")
    date = datetime.fromtimestamp(start / 1000, UTC)
    if interval == "M":
        return int(
            date.replace(
                year=date.year + (date.month == 12), month=date.month % 12 + 1, day=1
            ).timestamp()
            * 1000
        )
    delta = (
        timedelta(days=1 if interval == "D" else 7)
        if interval in {"D", "W"}
        else timedelta(minutes=int(interval))
    )
    return int((date + delta).timestamp() * 1000)


def floor_start(stamp, interval):
    date = datetime.fromtimestamp(stamp / 1000, UTC)
    if interval == "M":
        date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif interval == "W":
        date = (date - timedelta(days=date.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif interval == "D":
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        step = int(interval) * 60000
        return stamp // step * step
    return int(date.timestamp() * 1000)


def missing_candle_starts(starts, interval_ms):
    if interval_ms <= 0:
        raise ValueError("interval must be positive")
    values = sorted(set(starts))
    if not values:
        return []
    return sorted(set(range(values[0], values[-1] + interval_ms, interval_ms)) - set(values))
