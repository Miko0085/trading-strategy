import pytest

from recorder.config import VALID_INTERVALS, Market, SymbolsConfig


def test_multiple_symbols_and_intervals():
    c = SymbolsConfig(
        exchange="bybit",
        category="linear",
        symbols=["SUIUSDT", "ETHUSDT"],
        market={"primary_kline_interval": "1", "kline_intervals": ["1", "15"]},
    )
    assert c.symbols == ["SUIUSDT", "ETHUSDT"]


def test_invalid_interval():
    with pytest.raises(ValueError):
        SymbolsConfig(
            exchange="bybit",
            category="linear",
            symbols=["SUIUSDT"],
            market={"primary_kline_interval": "2", "kline_intervals": ["2"]},
        )


def test_official_intervals_present():
    assert {"1", "60", "D", "W", "M"} <= VALID_INTERVALS


def test_empty_symbols_allowed_for_auto_discovery_only_mode():
    c = SymbolsConfig(
        exchange="bybit",
        category="linear",
        symbols=[],
        market={"primary_kline_interval": "1", "kline_intervals": ["1"]},
    )
    assert c.symbols == []


def test_save_open_kline_updates_raw_can_be_disabled():
    m = Market(save_open_kline_updates_raw=False)
    assert m.save_open_kline_updates_raw is False
    assert Market().save_open_kline_updates_raw is True
