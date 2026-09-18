from __future__ import annotations

import asyncio
import json
import logging
import ssl
from datetime import UTC, date, datetime

import aiohttp
import certifi

from recorder.account.status import account_text, health
from recorder.events.models import RawEvent
from recorder.telegram.notes import (
    edit_note,
    link_candidates,
    links,
    replace_note_links,
    revision,
    save_text_note,
    verify_note,
)
from recorder.telegram.notifications import main_keyboard

log = logging.getLogger(__name__)


class TelegramBot:
    def __init__(
        self,
        token,
        allowed_user_ids,
        store,
        link_config=None,
        voice_service=None,
        allowed_chat_ids=None,
        writer=None,
        raw=None,
    ):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_base_url = f"https://api.telegram.org/file/bot{token}"
        self.allowed_user_ids = allowed_user_ids
        self.allowed_chat_ids = allowed_chat_ids or set()
        self.store, self.writer, self.raw = store, writer, raw
        self.link_config = link_config or {}
        self.voice_service = voice_service
        self._stop = asyncio.Event()
        self.offset = 0
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())

    async def db(self, operation):
        return await self.writer.call(operation) if self.writer else operation()

    def allowed(self, update):
        msg = update.get("message", {})
        user = msg.get("from", {})
        uid = user.get("id")
        chat = msg.get("chat", {}).get("id")
        if user.get("is_bot") or msg.get("sender_chat"):
            return False
        # Group-only configuration retained for explicit group mode; state isolated per user.
        if self.allowed_chat_ids:
            return chat in self.allowed_chat_ids and (
                not self.allowed_user_ids or uid in self.allowed_user_ids
            )
        return uid in self.allowed_user_ids and chat == uid

    async def call(self, method, payload):
        try:
            async with (
                aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=self.ssl_context),
                    timeout=aiohttp.ClientTimeout(total=40),
                ) as session,
                session.post(
                    f"{self.base_url}/{method}", json=payload, allow_redirects=False
                ) as response,
            ):
                if response.status != 200:
                    raise RuntimeError(f"Telegram HTTP {response.status}")
                data = await response.json()
                if data.get("ok") is not True:
                    raise RuntimeError("Telegram request rejected")
                return data
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise RuntimeError(f"Telegram transport {type(exc).__name__}") from None

    async def send(self, chat_id, text, keyboard=None):
        chunks = [text[i : i + 3500] for i in range(0, len(text), 3500)] or [""]
        message_id = None
        for i, chunk in enumerate(chunks):
            payload = {"chat_id": chat_id, "text": chunk}
            if keyboard and i == len(chunks) - 1:
                payload["reply_markup"] = keyboard
            result = await self.call("sendMessage", payload)
            message_id = result.get("result", {}).get("message_id")
        return message_id

    async def edit(self, chat_id, message_id, text, keyboard=None):
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text[:4096]}
        if keyboard:
            payload["reply_markup"] = keyboard
        await self.call("editMessageText", payload)

    async def download_file(self, file_path):
        if file_path.startswith("/") or ".." in file_path.split("/"):
            raise ValueError("invalid Telegram file path")
        try:
            async with (
                aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=self.ssl_context),
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as session,
                session.get(f"{self.file_base_url}/{file_path}", allow_redirects=False) as response,
            ):
                if response.status != 200:
                    raise RuntimeError(f"Telegram file HTTP {response.status}")
                data = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    data.extend(chunk)
                    if len(data) > 25 * 1024 * 1024:
                        raise ValueError("audio too large")
                return bytes(data)
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise RuntimeError(type(exc).__name__) from None

    async def send_allowed(self, text):
        for chat in self.allowed_chat_ids or self.allowed_user_ids:
            try:
                await self.send(chat, text, main_keyboard())
            except RuntimeError:
                log.warning("Telegram notification unavailable")

    async def stop(self):
        self._stop.set()

    async def run(self):
        self.offset = await self.db(lambda: self.store.get_state("telegram_offset", 0))
        while not self._stop.is_set():
            try:
                response = await self.call(
                    "getUpdates",
                    {
                        "offset": self.offset,
                        "timeout": 25,
                        "allowed_updates": ["message", "callback_query"],
                    },
                )
                for update in response["result"]:
                    uid = update["update_id"]
                    done = await self.db(
                        lambda uid=uid: self.store.db.execute(
                            "SELECT status FROM telegram_updates WHERE update_id=?", (uid,)
                        ).fetchone()
                    )
                    if not done or done[0] != "done":
                        raw_id = None
                        if self.raw:
                            envelope = await self.raw.capture(
                                RawEvent(source="TELEGRAM", topic="update", payload=update)
                            )
                            from recorder.events.ingestion import EventIngestor

                            raw_id = await self.db(
                                lambda envelope=envelope: EventIngestor(self.store).index(envelope)
                            )
                        await self.handle(update)

                        def acknowledge(uid=uid, update=update, raw_id=raw_id):
                            with self.store.transaction():
                                if raw_id:
                                    self.store.db.execute(
                                        "UPDATE raw_events_index SET status='processed' WHERE id=?",
                                        (raw_id,),
                                    )
                                    self.store.db.execute(
                                        "UPDATE timeline SET linked_raw_event_id=? WHERE event_type IN ('TRADER_NOTE','VOICE_NOTE') AND source_id IN (SELECT CAST(id AS TEXT) FROM trader_notes WHERE telegram_update_id=?)",
                                        (raw_id, uid),
                                    )
                                self.store.db.execute(
                                    "INSERT OR REPLACE INTO telegram_updates VALUES(?,'done',?,?)",
                                    (
                                        uid,
                                        datetime.now(UTC).isoformat(),
                                        json.dumps(update, ensure_ascii=False),
                                    ),
                                )
                                self.store.set_state("telegram_offset", uid + 1)

                        await self.db(acknowledge)
                    self.offset = uid + 1
            except (RuntimeError, ValueError, KeyError) as exc:
                log.warning("Telegram polling retry: %s", type(exc).__name__)
                await asyncio.sleep(3)

    async def state(self, chat, user, value=None):
        def operation():
            if value is not None:
                self.store.db.execute(
                    "INSERT INTO telegram_state VALUES(?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET data_json=excluded.data_json",
                    (chat, user, json.dumps(value)),
                )
                self.store._commit()
            row = self.store.db.execute(
                "SELECT data_json FROM telegram_state WHERE chat_id=? AND user_id=?", (chat, user)
            ).fetchone()
            return json.loads(row[0]) if row else {}

        return await self.db(operation)

    async def recent(self, chat, selected=(), day=None, before_id=None, has_back=False, message_id=None):
        where = ["event_type IN ('ORDER','EXECUTION','POSITION')"]
        params = []
        if day:
            where.append("substr(timestamp_received,1,10)=?")
            params.append(day)
        if before_id:
            where.append("id<?")
            params.append(before_id)
        rows = await self.db(
            lambda: self.store.db.execute(
                f"SELECT id,timestamp_received,summary_ru,symbol FROM timeline WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 11",
                params,
            ).fetchall()
        )
        has_more = len(rows) > 10
        rows = rows[:10]
        keyboard_rows = [
            [
                {
                    "text": f"{'✓ ' if r[0] in selected else ''}{r[1][:10]} {r[1][11:19]} {r[3] or ''} {r[2] or ''}"[
                        :100
                    ],
                    "callback_data": f"note:{r[0]}",
                }
            ]
            for r in rows
        ]
        nav_row = []
        if has_back:
            nav_row.append({"text": "↑ Показать позже", "callback_data": "page_prev"})
        if has_more:
            nav_row.append({"text": "Показать раньше ↓", "callback_data": f"page:{rows[-1][0]}"})
        if nav_row:
            keyboard_rows.append(nav_row)
        keyboard_rows.append(
            [{"text": "Сохранить выбранные связи", "callback_data": "links_done"}]
        )
        label = f" за {day}" if day else ""
        if rows:
            text = f"Выберите события{label}; повторное нажатие снимает выбор. Затем отправьте пояснение."
        else:
            text = f"Нет действий{label}." if day else "Пока нет действий."
        keyboard = {"inline_keyboard": keyboard_rows}
        if message_id:
            try:
                await self.edit(chat, message_id, text, keyboard)
                return message_id
            except RuntimeError:
                pass  # message too old/deleted to edit; fall back to a fresh one
        return await self.send(chat, text, keyboard)

    async def review(self, chat, note_id):
        row = await self.db(
            lambda: self.store.db.execute(
                "SELECT text FROM trader_notes WHERE id=?", (note_id,)
            ).fetchone()
        )
        if row is None:
            return
        ids = await self.db(lambda: links(self.store, note_id))
        rev = await self.db(lambda: revision(self.store, note_id))
        labels = await self.db(
            lambda: [
                dict(
                    self.store.db.execute(
                        "SELECT id,summary_ru,symbol FROM timeline WHERE id=?", (i,)
                    ).fetchone()
                )
                for i in ids
            ]
        )
        body = (
            f"Пояснение #{note_id} записано ✓\n"
            + (
                "Пояснение к событиям. Проверьте связи:\n"
                if ids
                else "Общее пояснение — без привязки к событию.\n"
            )
            + (
                "\n".join(f"#{r['id']} {r['symbol'] or ''} {r['summary_ru']}" for r in labels)
                or "нет выбранных событий"
            )
            + "\n\nТекст:\n"
            + (row[0] or "Расшифровка ожидается")
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": label, "callback_data": f"{action}:{note_id}:{rev}"}]
                for action, label in (
                    ("verify", "✅ Подтвердить текст и события")
                    if ids
                    else ("verify_general", "✅ Подтвердить как общее пояснение"),
                    ("relink", "🔗 Исправить связь"),
                    ("edit", "📝 Исправить текст"),
                )
            ]
        }
        await self.send(chat, body, keyboard)

    async def handle(self, update):
        if "callback_query" in update:
            return await self.handle_callback(update["callback_query"])
        if not self.allowed(update):
            return
        msg = update["message"]
        chat = msg["chat"]["id"]
        user = msg["from"]["id"]
        state = await self.state(chat, user)
        text = (msg.get("text") or "").strip()
        command = text.split(" ", 1)[0].split("@", 1)[0]
        if command in {"/start", "/help"}:
            return await self.send(
                chat,
                "Команды: /status, /recent [ГГГГ-ММ-ДД], /note текст. Выберите несколько событий (кнопки «Показать раньше ↓» / «Показать позже ↑» листают историю, сообщение обновляется на месте), отправьте текст или голос и подтвердите пояснение.",
                main_keyboard(),
            )
        if command == "/status":
            return await self.send(chat, await self.db(lambda: health(self.store)))
        if command == "/recent" or text == "🕒 Последние действия":
            day = None
            if command == "/recent" and " " in text:
                candidate = text.split(" ", 1)[1].strip()
                try:
                    date.fromisoformat(candidate)
                except ValueError:
                    return await self.send(chat, "Некорректная дата. Формат: /recent ГГГГ-ММ-ДД")
                day = candidate
            state["recent_date"] = day
            state.pop("recent_before_id", None)
            state.pop("recent_stack", None)
            message_id = await self.recent(chat, state.get("events", []), day=day)
            state["recent_message_id"] = message_id
            await self.state(chat, user, state)
            return
        if text == "📊 Текущее состояние":
            return await self.send(chat, await self.db(lambda: account_text(self.store)))
        if text in {"/note", "✍️ Пояснить действие", "🎙 Пояснить голосом"}:
            state["mode"] = "note"
            await self.state(chat, user, state)
            return await self.send(
                chat, "Выберите события через /recent или отправьте текст/голосовое пояснение."
            )
        if text.startswith("/") and command != "/note":
            return await self.send(chat, "Неизвестная команда. /help")
        if command == "/note":
            text = text.split(" ", 1)[1].strip() if " " in text else ""
        if state.get("edit") and text:
            note_id = state["edit"]
            await self.db(lambda: edit_note(self.store, note_id, text))
            await self.state(chat, user, {})
            return await self.review(chat, note_id)
        ids = state.get("events")
        if ids is None:
            ids = await self.db(
                lambda: link_candidates(
                    self.store,
                    datetime.now(UTC),
                    self.link_config.get("lookback_minutes", 10),
                    self.link_config.get("lookforward_minutes", 3),
                )
            )
        if msg.get("voice") or msg.get("audio"):
            if not self.voice_service:
                return await self.send(chat, "Приём аудио не настроен.")
            _voice_id, note_id = await self.voice_service.save(
                self, msg, ids, update.get("update_id")
            )
            await self.send(
                chat, f"Оригинальное аудио сохранено ✓ Пояснение #{note_id}. Расшифровка ожидается."
            )
        elif text:
            note_id = await self.db(
                lambda: save_text_note(
                    self.store,
                    text,
                    ids,
                    owner_id=user,
                    chat_id=chat,
                    update_id=update.get("update_id"),
                )
            )
            await self.review(chat, note_id)
        await self.state(chat, user, {})

    async def handle_callback(self, cb):
        msg = {**cb.get("message", {}), "from": cb.get("from", {})}
        if not self.allowed({"message": msg}):
            return
        chat = msg["chat"]["id"]
        user = cb["from"]["id"]
        await self.call("answerCallbackQuery", {"callback_query_id": cb["id"]})
        data = cb.get("data", "")
        state = await self.state(chat, user)
        if data == "links_done":
            if state.get("relink"):
                note_id = state["relink"]
                await self.db(
                    lambda: replace_note_links(self.store, note_id, state.get("events", []))
                )
                await self.state(chat, user, {})
                await self.review(chat, note_id)
            else:
                await self.send(chat, "События выбраны. Отправьте текст или голосовое пояснение.")
            return
        if data == "page_prev":
            stack = state.get("recent_stack") or []
            before_id = stack.pop() if stack else None
            state["recent_stack"] = stack
            state["recent_before_id"] = before_id
            message_id = await self.recent(
                chat,
                state.get("events", []),
                day=state.get("recent_date"),
                before_id=before_id,
                has_back=bool(stack),
                message_id=state.get("recent_message_id"),
            )
            state["recent_message_id"] = message_id
            await self.state(chat, user, state)
            return
        try:
            pieces = data.split(":")
            action = pieces[0]
            entity = int(pieces[1])
        except (ValueError, IndexError):
            return await self.send(chat, "Кнопка устарела. Откройте /recent.")
        if action == "page":
            stack = state.get("recent_stack") or []
            stack.append(state.get("recent_before_id"))
            state["recent_stack"] = stack
            state["recent_before_id"] = entity
            message_id = await self.recent(
                chat,
                state.get("events", []),
                day=state.get("recent_date"),
                before_id=entity,
                has_back=True,
                message_id=state.get("recent_message_id"),
            )
            state["recent_message_id"] = message_id
            await self.state(chat, user, state)
            return
        if action == "note":
            row = await self.db(
                lambda: self.store.db.execute(
                    "SELECT 1 FROM timeline WHERE id=? AND event_type IN ('ORDER','EXECUTION','POSITION')",
                    (entity,),
                ).fetchone()
            )
            if not row:
                return
            selected = set(state.get("events", []))
            selected.symmetric_difference_update({entity})
            state["events"] = sorted(selected)
            message_id = await self.recent(
                chat,
                state["events"],
                day=state.get("recent_date"),
                before_id=state.get("recent_before_id"),
                has_back=bool(state.get("recent_stack")),
                message_id=state.get("recent_message_id"),
            )
            state["recent_message_id"] = message_id
            await self.state(chat, user, state)
            return
        owner = await self.db(
            lambda: self.store.db.execute(
                "SELECT owner_id,chat_id FROM trader_notes WHERE id=?", (entity,)
            ).fetchone()
        )
        if not owner or owner[0] != user or owner[1] != chat:
            return await self.send(chat, "Это пояснение другого пользователя.")
        rev = await self.db(lambda: revision(self.store, entity))
        if len(pieces) < 3 or pieces[2] != str(rev):
            return await self.review(chat, entity)
        if action in {"verify", "verify_general"}:
            try:
                await self.db(
                    lambda: verify_note(
                        self.store,
                        entity,
                        general=action == "verify_general",
                        expected_revision=rev,
                    )
                )
            except ValueError:
                await self.send(
                    chat,
                    "Подтверждение не выполнено: проверьте текст и связи. Для старой кнопки откройте актуальное пояснение ниже.",
                )
                await self.review(chat, entity)
                return
            await self.send(
                chat,
                "Общее пояснение подтверждено; связи с событием нет ✓"
                if action == "verify_general"
                else "Пояснение и связи подтверждены ✓",
            )
        elif action == "edit":
            await self.state(chat, user, {"edit": entity})
            await self.send(chat, "Отправьте исправленный текст. Исходная версия сохранится.")
        elif action == "relink":
            selected = await self.db(lambda: links(self.store, entity))
            message_id = await self.recent(chat, selected)
            await self.state(
                chat, user, {"relink": entity, "events": selected, "recent_message_id": message_id}
            )
