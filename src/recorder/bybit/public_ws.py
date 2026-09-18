from __future__ import annotations

from collections.abc import Iterable

PUBLIC_TOPICS = ("kline.{interval}.{symbol}", "tickers.{symbol}")


def public_topics(symbols: Iterable[str], intervals: Iterable[str]) -> list[str]:
    return [f"kline.{interval}.{symbol}" for symbol in symbols for interval in intervals] + [
        f"tickers.{s}" for s in symbols
    ]
