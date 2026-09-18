import pytest

from recorder.account.positions import semantic_position_change
from recorder.events.ingestion import EventIngestor
from recorder.events.models import RawEvent
from recorder.storage.raw_jsonl import RawJsonlWriter
from recorder.storage.sqlite import SQLiteStore

BASE = {
    "side": "Buy",
    "size": "147",
    "entryPrice": "0.34",
    "leverage": "10",
    "takeProfit": "0",
    "stopLoss": "0",
    "trailingStop": "0",
}


def test_unset_tp_sl_reported_as_zero_or_empty_is_not_a_semantic_change():
    quirked = {**BASE, "takeProfit": "", "stopLoss": ""}
    assert semantic_position_change(BASE, quirked) is False
    assert semantic_position_change(quirked, BASE) is False


def test_real_size_or_side_change_is_still_detected():
    assert semantic_position_change(BASE, {**BASE, "size": "200"}) is True
    assert semantic_position_change(BASE, {**BASE, "side": "Sell"}) is True
    assert semantic_position_change(BASE, {**BASE, "takeProfit": "0.5"}) is True


def test_no_previous_state_is_always_a_change():
    assert semantic_position_change(None, BASE) is True


@pytest.fixture
def store(tmp_path):
    db = SQLiteStore(tmp_path / "db.sqlite")
    db.initialize()
    yield db
    db.close()


async def captured(tmp_path, topic, data):
    return await RawJsonlWriter(tmp_path / "raw").capture(
        RawEvent(
            source="bybit_private",
            topic=topic,
            payload={"topic": topic, "creationTime": 1720000000000, "data": data},
        )
    )


@pytest.mark.asyncio
async def test_tp_sl_representation_quirk_does_not_spam_timeline(store, tmp_path):
    ingest = EventIngestor(store)
    position = {"symbol": "UAIUSDT", "positionIdx": 2, **BASE}
    await ingest.handle(await captured(tmp_path, "position", [position]))
    quirked = {**position, "takeProfit": "", "stopLoss": ""}
    await ingest.handle(await captured(tmp_path, "position", [quirked]))
    count = store.db.execute(
        "SELECT COUNT(*) FROM timeline WHERE event_type='POSITION' AND symbol='UAIUSDT'"
    ).fetchone()[0]
    assert count == 1
