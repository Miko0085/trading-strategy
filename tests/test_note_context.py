import json

import pytest

from recorder.storage.sqlite import SQLiteStore
from recorder.telegram.bot import TelegramBot
from recorder.telegram.notes import (
    edit_note,
    links,
    replace_note_links,
    revision,
    save_text_note,
    verify_note,
)


@pytest.fixture
def store(tmp_path):
    s = SQLiteStore(tmp_path / "test.db")
    s.initialize()
    yield s
    s.close()


def event(store, name):
    eid = store.insert_timeline({"event_type": "EXECUTION", "source": "test", "source_id": name})
    store.db.execute(
        "INSERT INTO observations(version_key,timeline_id,before_json,after_json) VALUES(?,?,?,?)",
        (name, eid, json.dumps({"before": name}), json.dumps({"after": name})),
    )
    store._commit()
    return eid


def context(store, note):
    return json.loads(
        store.db.execute("SELECT context_json FROM trader_notes WHERE id=?", (note,)).fetchone()[0]
    )


def test_relink_updates_context_preserves_original_and_clears_verification(store):
    a, b = event(store, "a"), event(store, "b")
    n = save_text_note(store, "explanation", [a])
    original = context(store, n)
    verify_note(store, n)
    replace_note_links(store, n, [b])
    c = context(store, n)
    assert links(store, n) == [b]
    assert c["event_contexts"] == [
        {"event_id": b, "before": {"before": "b"}, "after": {"after": "b"}}
    ]
    assert c["at_note_time"] == original["at_note_time"]
    assert c["link_context_history"][0]["event_contexts"] == original["event_contexts"]
    assert "confirmation_scope" not in c
    assert store.db.execute("SELECT verified FROM trader_notes WHERE id=?", (n,)).fetchone()[0] == 0
    verify_note(store, n)
    assert context(store, n)["confirmation_scope"] == "event"
    replace_note_links(store, n, [])
    assert context(store, n)["event_contexts"] == []
    with pytest.raises(ValueError):
        verify_note(store, n)
    verify_note(store, n, general=True)
    assert context(store, n)["confirmation_scope"] == "general"
    edit_note(store, n, "corrected")
    assert "confirmation_scope" not in context(store, n)


def test_failed_relink_rolls_back_everything(store, monkeypatch):
    a, b = event(store, "a"), event(store, "b")
    n = save_text_note(store, "text", [a])
    verify_note(store, n)
    original = context(store, n)

    def broken(*args):
        raise RuntimeError("injected")

    monkeypatch.setattr("recorder.telegram.notes.event_contexts", broken)
    with pytest.raises(RuntimeError):
        replace_note_links(store, n, [b])
    assert links(store, n) == [a]
    assert context(store, n) == original
    assert revision(store, n) == 0
    assert store.db.execute("SELECT verified FROM trader_notes WHERE id=?", (n,)).fetchone()[0] == 1


def test_wrong_scope_and_stale_revision_rejected(store):
    n = save_text_note(store, "text", [event(store, "a")])
    with pytest.raises(ValueError):
        verify_note(store, n, general=True)
    edit_note(store, n, "edited")
    with pytest.raises(ValueError):
        verify_note(store, n, expected_revision=0)
    verify_note(store, n, expected_revision=1)


@pytest.mark.asyncio
async def test_general_note_requires_explicit_button(store):
    bot = TelegramBot("fake", {42}, store)
    sent = []

    async def call(method, payload):
        sent.append((method, payload))
        return {"ok": True, "result": {}}

    bot.call = call
    n = save_text_note(store, "general text", owner_id=42, chat_id=42)
    await bot.review(42, n)
    keyboard = sent[-1][1]["reply_markup"]["inline_keyboard"]
    assert keyboard[0][0]["callback_data"] == f"verify_general:{n}:0"

    async def click(action):
        await bot.handle_callback(
            {
                "id": "c",
                "from": {"id": 42},
                "message": {"chat": {"id": 42}},
                "data": f"{action}:{n}:0",
            }
        )

    await click("verify")
    assert store.db.execute("SELECT verified FROM trader_notes WHERE id=?", (n,)).fetchone()[0] == 0
    await click("verify_general")
    assert context(store, n)["confirmation_scope"] == "general"
