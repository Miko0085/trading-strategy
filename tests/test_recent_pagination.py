import pytest

from recorder.storage.sqlite import SQLiteStore
from recorder.telegram.bot import TelegramBot


@pytest.fixture
def store(tmp_path):
    db = SQLiteStore(tmp_path / "db.sqlite")
    db.initialize()
    yield db
    db.close()


def make_bot(store):
    bot = TelegramBot("fake", {42}, store)
    messages = []
    next_id = [100]

    async def call(method, payload):
        messages.append((method, payload))
        if method == "sendMessage":
            next_id[0] += 1
            return {"ok": True, "result": {"message_id": next_id[0]}}
        return {"ok": True, "result": {}}

    bot.call = call
    return bot, messages


def insert_event(store, day, seq, event_type="ORDER"):
    return store.insert_timeline(
        {
            "event_type": event_type,
            "source": "test",
            "summary_ru": "Заявка: New",
            "symbol": "UAIUSDT",
            "timestamp_received": f"{day}T{seq:02d}:00:00+00:00",
        }
    )


async def cb(bot, data, user=42, chat=42, message_id=100):
    await bot.handle_callback(
        {
            "id": "cb",
            "data": data,
            "from": {"id": user},
            "message": {"chat": {"id": chat}, "message_id": message_id},
        }
    )


async def send(bot, text, user=42, chat=42, update_id=1):
    await bot.handle(
        {
            "update_id": update_id,
            "message": {"chat": {"id": chat}, "from": {"id": user}, "text": text},
        }
    )


def keyboard_of(messages):
    return messages[-1][1]["reply_markup"]["inline_keyboard"]


@pytest.mark.asyncio
async def test_recent_shows_only_last_ten_with_older_page_button(store):
    bot, messages = make_bot(store)
    ids = [insert_event(store, "2026-09-16", i) for i in range(12)]
    await send(bot, "/recent")
    kb = keyboard_of(messages)
    event_rows = kb[:-2]  # last two rows are "показать раньше" + "сохранить"
    assert len(event_rows) == 10
    assert event_rows[0][0]["callback_data"] == f"note:{ids[-1]}"
    assert kb[-2][0]["callback_data"] == f"page:{ids[2]}"


@pytest.mark.asyncio
async def test_toggling_a_selection_edits_in_place_instead_of_spamming(store):
    bot, messages = make_bot(store)
    ids = [insert_event(store, "2026-09-16", i) for i in range(3)]
    await send(bot, "/recent")
    assert messages[-1][0] == "sendMessage"
    sent_message_id = 101  # first (and only) sendMessage in this fixture returns id 101

    await cb(bot, f"note:{ids[-1]}", message_id=sent_message_id)
    method, payload = messages[-1]
    assert method == "editMessageText"
    assert payload["message_id"] == sent_message_id
    assert payload["chat_id"] == 42
    assert sum(1 for m, _ in messages if m == "sendMessage") == 1


@pytest.mark.asyncio
async def test_page_button_reveals_older_events_without_losing_selection(store):
    bot, messages = make_bot(store)
    ids = [insert_event(store, "2026-09-16", i) for i in range(12)]
    await send(bot, "/recent")
    mid = 101  # the one message this whole flow edits in place
    await cb(bot, f"note:{ids[-1]}", message_id=mid)  # select the newest event
    page_button = keyboard_of(messages)[-2][0]["callback_data"]
    await cb(bot, page_button, message_id=mid)
    kb = keyboard_of(messages)
    # a "show newer" button appears now that we've paged backward
    assert kb[-2][0]["callback_data"] == "page_prev"
    event_rows = kb[:-2]
    shown_ids = {int(row[0]["callback_data"].split(":")[1]) for row in event_rows}
    assert shown_ids == set(ids[:2])
    # select one more on this page too (order is DESC, so ids[0] is the second row)
    await cb(bot, f"note:{ids[0]}", message_id=mid)
    kb = keyboard_of(messages)
    assert kb[1][0]["text"].startswith("✓")
    # still editing the same message, never spamming a new one
    assert sum(1 for m, _ in messages if m == "sendMessage") == 1


@pytest.mark.asyncio
async def test_page_prev_returns_to_the_newer_page(store):
    bot, messages = make_bot(store)
    ids = [insert_event(store, "2026-09-16", i) for i in range(12)]
    await send(bot, "/recent")
    mid = 101
    page_button = keyboard_of(messages)[-2][0]["callback_data"]
    await cb(bot, page_button, message_id=mid)
    older_shown = {int(r[0]["callback_data"].split(":")[1]) for r in keyboard_of(messages)[:-2]}
    assert older_shown == set(ids[:2])

    await cb(bot, "page_prev", message_id=mid)
    newer_shown = {int(r[0]["callback_data"].split(":")[1]) for r in keyboard_of(messages)[:-2]}
    assert newer_shown == set(ids[2:])
    # back on the latest page: no more "show newer" button
    assert keyboard_of(messages)[-2][0]["callback_data"].startswith("page:")


@pytest.mark.asyncio
async def test_recent_with_date_filters_to_that_day_only(store):
    bot, messages = make_bot(store)
    old_ids = [insert_event(store, "2026-09-14", i) for i in range(3)]
    new_ids = [insert_event(store, "2026-09-16", i) for i in range(3)]
    await send(bot, "/recent 2026-09-14")
    kb = keyboard_of(messages)
    shown_ids = {int(row[0]["callback_data"].split(":")[1]) for row in kb[:-1]}
    assert shown_ids == set(old_ids)
    assert shown_ids.isdisjoint(new_ids)
    assert "за 2026-09-14" in messages[-1][1]["text"]


@pytest.mark.asyncio
async def test_recent_rejects_bad_date_format(store):
    bot, messages = make_bot(store)
    await send(bot, "/recent not-a-date")
    assert "Некорректная дата" in messages[-1][1]["text"]
