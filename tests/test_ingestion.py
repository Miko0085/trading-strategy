import asyncio

from recorder.events.ingestion import EventIngestor
from recorder.storage.sqlite import SQLiteStore
from recorder.telegram.notes import save_text_note
from recorder.telegram.notifications import status_text


def test_one_order_multiple_executions_and_duplicate_order(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    ingestor = EventIngestor(store)
    order = {
        "topic": "order",
        "data": [{"orderId": "o1", "symbol": "SUIUSDT", "orderStatus": "Filled"}],
    }
    execution = lambda exec_id: {
        "topic": "execution",
        "data": [
            {
                "execId": exec_id,
                "orderId": "o1",
                "symbol": "SUIUSDT",
                "execQty": "1",
                "execTime": "1",
            }
        ],
    }
    asyncio.run(ingestor.handle({"source": "fixture", "payload": order}))
    asyncio.run(ingestor.handle({"source": "fixture", "payload": execution("e1")}))
    asyncio.run(ingestor.handle({"source": "fixture", "payload": execution("e2")}))
    asyncio.run(ingestor.handle({"source": "fixture", "payload": execution("e1")}))
    assert store.db.execute("SELECT COUNT(*) FROM executions").fetchone()[0] == 2
    assert store.db.execute("SELECT COUNT(*) FROM order_events").fetchone()[0] == 1
    store.close()


def test_position_event_without_change_is_not_semantic(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    ingestor = EventIngestor(store)
    position = {
        "topic": "position",
        "data": [
            {"symbol": "SUIUSDT", "positionIdx": 1, "side": "Buy", "size": "2", "entryPrice": "1"}
        ],
    }
    asyncio.run(ingestor.handle({"source": "fixture", "payload": position}))
    asyncio.run(ingestor.handle({"source": "fixture", "payload": position}))
    assert (
        store.db.execute("SELECT COUNT(*) FROM position_events WHERE semantic_change=1").fetchone()[
            0
        ]
        == 1
    )
    store.close()


def test_russian_note_and_status(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    note_id = save_text_note(store, "Поднял лимитки выше")
    assert note_id == 1
    assert "Recorder:" in status_text("работает", "подключён", "подключён")
    store.close()
