from typing import ClassVar

import pytest

from recorder.events.ingestion import EventIngestor
from recorder.events.interpreter import Notifier, meaningful_summary
from recorder.events.models import RawEvent
from recorder.storage.raw_jsonl import RawJsonlWriter
from recorder.storage.sqlite import SQLiteStore


@pytest.fixture
def store(tmp_path):
    db = SQLiteStore(tmp_path / "db.sqlite")
    db.initialize()
    yield db
    db.close()


async def captured(tmp_path, topic, data, **extra):
    return await RawJsonlWriter(tmp_path / "raw").capture(
        RawEvent(
            source="bybit_private",
            topic=topic,
            payload={"topic": topic, "creationTime": 1720000000000, "data": data, **extra},
        )
    )


class FakeBot:
    allowed_chat_ids: ClassVar = {1}
    allowed_user_ids: ClassVar = set()


def event(kind, **fields):
    return {"event_type": kind, "data": fields, "order_status": fields.get("orderStatus")}


def test_single_order_line_names_side_price_and_status():
    text = meaningful_summary([event("ORDER", side="Buy", qty="350", price="0.2", orderStatus="New")])
    assert text == "Заявка Buy 350 @ 0.2 — выставлена"


def test_multiple_orders_bulleted_with_status_each():
    events = [
        event("ORDER", side="Buy", qty="350", price="0.2", orderStatus="New"),
        event("ORDER", side="Buy", qty="185", price="0.27", orderStatus="Cancelled"),
    ]
    text = meaningful_summary(events)
    assert text == "Заявки:\n• Buy 350 @ 0.2 — выставлена\n• Buy 185 @ 0.27 — отменена"


def test_execution_line_includes_pnl_only_when_nonzero():
    no_pnl = meaningful_summary(
        [event("EXECUTION", side="Buy", execQty="147", execPrice="0.34", execPnl="0")]
    )
    assert no_pnl == "Исполнение: Buy 147 @ 0.34"
    with_pnl = meaningful_summary(
        [event("EXECUTION", side="Sell", execQty="50", execPrice="0.36", execPnl="1.23")]
    )
    assert with_pnl == "Исполнение: Sell 50 @ 0.36, PnL 1.23"


def test_position_open_close_increase_decrease_labels():
    def line(before_size, after_size, **after_fields):
        e = event("POSITION", size=str(after_size), avgPrice="0.3", unrealisedPnl="1", **after_fields)
        e["before_position"] = {"size": str(before_size)} if before_size is not None else None
        return meaningful_summary([e])

    assert line(0, 230).startswith("Позиция открыта: 0 → 230")
    assert line(147, 0, curRealisedPnl="2.86").startswith("Позиция закрыта: 147 → 0")
    assert "реализованный PnL 2.86" in line(147, 0, curRealisedPnl="2.86")
    assert line(100, 200).startswith("Позиция увеличена: 100 → 200")
    assert line(200, 100).startswith("Позиция уменьшена: 200 → 100")
    assert "uPnL 1" in line(100, 200)


def test_wallet_line_shows_delta_only_when_changed():
    e = event("WALLET", totalEquity="110.9", totalAvailableBalance="93.3")
    e["before_wallet"] = {"totalEquity": "108.0", "totalAvailableBalance": "93.3"}
    text = meaningful_summary([e])
    assert text == "Баланс: equity 108.0 → 110.9, доступно 93.3"


@pytest.mark.asyncio
async def test_notifier_collect_reports_position_open_end_to_end(store, tmp_path):
    import json

    ingest = EventIngestor(store)
    notifier = Notifier(store, writer=None, bot=FakeBot(), policy={"position_changes": True})

    # Baseline discovery (e.g. from reconciliation) lands in its own notification cycle,
    # well before the trader actually opens a position minutes/hours later.
    await ingest.handle(
        await captured(
            tmp_path,
            "position",
            [
                {
                    "symbol": "ETHUSDT",
                    "positionIdx": 1,
                    "side": "",
                    "size": "0",
                    "avgPrice": "",
                    "unrealisedPnl": "",
                }
            ],
        )
    )
    notifier.collect()

    await ingest.handle(
        await captured(
            tmp_path,
            "position",
            [
                {
                    "symbol": "ETHUSDT",
                    "positionIdx": 1,
                    "side": "Buy",
                    "size": "230",
                    "avgPrice": "0.288",
                    "unrealisedPnl": "1.15",
                }
            ],
        )
    )
    notifier.collect()

    row = store.db.execute(
        "SELECT payload_json FROM notification_outbox ORDER BY id DESC LIMIT 1"
    ).fetchone()
    payload = json.loads(row[0])
    assert payload["text"] == "ETHUSDT Long\nПозиция открыта: 0 → 230, средняя 0.288, uPnL 1.15"
