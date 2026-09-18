import json
from datetime import UTC, datetime, timedelta

import pytest

from recorder.account.status import account_text
from recorder.storage.sqlite import SQLiteStore


@pytest.fixture
def store(tmp_path):
    db = SQLiteStore(tmp_path / "db.sqlite")
    db.initialize()
    yield db
    db.close()


def set_current(store, kind, key, symbol, received_at, data):
    store.db.execute(
        "INSERT INTO current_states VALUES(?,?,?,?,?,?)",
        (kind, key, symbol, 0, received_at, json.dumps(data)),
    )
    store._commit()


NOW = datetime.now(UTC).isoformat()
YESTERDAY = (datetime.now(UTC) - timedelta(days=1)).isoformat()


def test_report_groups_wallet_ticker_positions_and_orders_into_sections(store):
    set_current(
        store,
        "WALLET",
        "UNIFIED",
        None,
        NOW,
        {"totalEquity": "116.27", "totalAvailableBalance": "80.89", "totalPerpUPL": "8.30"},
    )
    set_current(
        store, "TICKER", "UAIUSDT", "UAIUSDT", NOW, {"lastPrice": "0.396", "markPrice": "0.397"}
    )
    set_current(
        store,
        "POSITION",
        "UAIUSDT:1",
        "UAIUSDT",
        NOW,
        {
            "positionIdx": 1,
            "size": "147",
            "entryPrice": "0.34",
            "unrealisedPnl": "8.31",
            "curRealisedPnl": "-0.03",
        },
    )
    set_current(
        store,
        "POSITION",
        "UAIUSDT:2",
        "UAIUSDT",
        NOW,
        {"positionIdx": 2, "size": "0", "entryPrice": "0", "curRealisedPnl": "0"},
    )
    set_current(
        store,
        "ORDER",
        "o1",
        "UAIUSDT",
        NOW,
        {"orderId": "fe220964-abcd", "side": "Buy", "qty": "185", "price": "0.27",
         "positionIdx": 1, "orderStatus": "New"},
    )

    text = account_text(store)

    assert text.index("💰 Баланс") < text.index("📈 UAIUSDT") < text.index("📋 Активные заявки")
    assert "Equity: 116.27" in text
    # LONG (idx 1) is listed before SHORT (idx 2), matching hedge-mode relevance order
    assert text.index("LONG:") < text.index("SHORT:")
    assert "Buy 185 @ 0.27 · LONG · #fe220964" in text


def test_report_omits_empty_sections_when_nothing_to_show(store):
    text = account_text(store)
    assert "📋 Активные заявки" not in text
    assert "💰 Баланс" not in text
    assert "Состояние аккаунта: нет данных" in text


def test_recent_actions_hide_market_noise_but_keep_real_events(store):
    store.insert_timeline(
        {"event_type": "MARKET", "source": "test", "symbol": "UAIUSDT", "summary_ru": "MARKET"}
    )
    store.insert_timeline(
        {
            "event_type": "WALLET",
            "source": "test",
            "summary_ru": "Обновление баланса",
        }
    )
    text = account_text(store)
    assert "MARKET" not in text.split("🕒 Последние действия")[1]
    assert "WALLET: Обновление баланса" in text


def test_timestamp_shown_as_time_only_for_today_and_full_date_for_older(store):
    set_current(
        store, "TICKER", "UAIUSDT", "UAIUSDT", NOW, {"lastPrice": "1", "markPrice": "1"}
    )
    set_current(
        store,
        "POSITION",
        "UAIUSDT:0",
        "UAIUSDT",
        YESTERDAY,
        {"positionIdx": 0, "size": "0", "entryPrice": "0"},
    )
    text = account_text(store)
    assert NOW[11:19] in text
    assert YESTERDAY[:10] in text
