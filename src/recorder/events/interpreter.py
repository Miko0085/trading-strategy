"""Descriptive grouping, never strategy decisions."""

import asyncio
import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

ORDER_STATUS_RU = {
    "New": "выставлена",
    "Cancelled": "отменена",
    "Filled": "исполнена",
    "PartiallyFilled": "частично исполнена",
    "PartiallyFilledCanceled": "частично исполнена, остаток отменён",
    "Untriggered": "условная (не сработала)",
    "Triggered": "сработал триггер",
    "Rejected": "отклонена",
    "Deactivated": "деактивирована",
}


def _show(value):
    return str(value) if value not in (None, "") else "нет данных"


def _decimal(value):
    try:
        return Decimal(str(value)) if value not in (None, "") else Decimal(0)
    except InvalidOperation:
        return None


def _order_line(item):
    status = ORDER_STATUS_RU.get(item.get("orderStatus"), item.get("orderStatus") or "изменение")
    return f"{item.get('side', '')} {_show(item.get('qty'))} @ {_show(item.get('price'))} — {status}"


def _execution_line(item):
    if item.get("execType") == "Funding":
        return f"начисление funding по {_show(item.get('execQty'))} @ {_show(item.get('execPrice'))} — не сделка"
    line = f"{item.get('side', '')} {_show(item.get('execQty'))} @ {_show(item.get('execPrice'))}"
    pnl = _decimal(item.get("execPnl"))
    if pnl:
        line += f", PnL {item['execPnl']}"
    return line


def _bulleted(lines, single_header, plural_header):
    if len(lines) == 1:
        return single_header + lines[0]
    return plural_header + "\n".join(f"• {line}" for line in lines)


def _position_line(before, current):
    before_size = _decimal((before or {}).get("size"))
    after_size = _decimal(current.get("size"))
    if before_size is None or after_size is None:
        label = "Позиция изменена"
    elif before_size == 0 and after_size != 0:
        label = "Позиция открыта"
    elif before_size != 0 and after_size == 0:
        label = "Позиция закрыта"
    elif after_size > before_size:
        label = "Позиция увеличена"
    elif after_size < before_size:
        label = "Позиция уменьшена"
    else:
        label = "Позиция изменена"
    avg = current.get("avgPrice") or current.get("entryPrice")
    line = (
        f"{label}: {_show((before or {}).get('size'))} "
        f"→ {_show(current.get('size'))}, средняя {_show(avg)}"
    )
    if after_size == 0:
        line += f", реализованный PnL {_show(current.get('curRealisedPnl'))}"
    else:
        line += f", uPnL {_show(current.get('unrealisedPnl'))}"
    return line


def _wallet_line(before, current):
    b_equity, a_equity = (before or {}).get("totalEquity"), current.get("totalEquity")
    b_avail, a_avail = (before or {}).get("totalAvailableBalance"), current.get(
        "totalAvailableBalance"
    )
    equity = f"{_show(b_equity)} → {_show(a_equity)}" if b_equity != a_equity else _show(a_equity)
    avail = f"{_show(b_avail)} → {_show(a_avail)}" if b_avail != a_avail else _show(a_avail)
    return f"Баланс: equity {equity}, доступно {avail}"


def meaningful_summary(events):
    if not events:
        return None
    kind = events[0].get("event_type", "").upper()
    if kind == "EXECUTION":
        lines = [_execution_line(e["data"]) for e in events]
        return _bulleted(lines, "Исполнение: ", "Исполнения:\n")
    if kind == "ORDER":
        lines = [_order_line(e["data"]) for e in events]
        return _bulleted(lines, "Заявка ", "Заявки:\n")
    if kind == "POSITION":
        return _position_line(events[0].get("before_position"), events[-1]["data"])
    if kind == "WALLET":
        return _wallet_line(events[0].get("before_wallet"), events[-1]["data"])
    return "Изменение состояния аккаунта"


class Notifier:
    def __init__(self, store, writer, bot, policy, interval=5):
        self.store, self.writer, self.bot, self.policy, self.interval = (
            store,
            writer,
            bot,
            policy,
            interval,
        )

    def collect(self):
        previous = self.store.get_state("notification_timeline", 0)
        rows = self.store.db.execute(
            "SELECT t.*,o.data_json,o.before_json FROM timeline t LEFT JOIN observations o ON o.timeline_id=t.id WHERE t.id>? ORDER BY t.id LIMIT 500",
            (previous,),
        ).fetchall()
        groups = defaultdict(list)
        for row in rows:
            kind = row["event_type"]
            flag = {
                "EXECUTION": "executions",
                "ORDER": "grid_activity",
                "POSITION": "position_changes",
                "WALLET": "wallet_changes",
            }.get(kind, "technical_events")
            data = json.loads(row["data_json"]) if row["data_json"] else {}
            if kind == "EXECUTION" and data.get("execType") == "Funding":
                flag = "funding"
            elif kind == "EXECUTION" and data.get("leavesQty") not in (None, "", "0"):
                flag = "partial_fills"
            if self.policy.get(flag):
                group = (
                    row["symbol"],
                    data.get("positionIdx"),
                    data.get("orderId") if kind == "EXECUTION" else kind,
                )
                event = {**dict(row), "order_status": data.get("orderStatus"), "data": data}
                if kind in ("POSITION", "WALLET") and row["before_json"]:
                    before_ctx = json.loads(row["before_json"])
                    before_key = (
                        f"{row['symbol']}:{data.get('positionIdx', 0)}"
                        if kind == "POSITION"
                        else "UNIFIED"
                    )
                    match = next(
                        (
                            c["data"]
                            for c in before_ctx
                            if c.get("kind") == kind and c.get("key") == before_key
                        ),
                        None,
                    )
                    event[f"before_{kind.lower()}"] = match
                groups[group].append(event)
        with self.store.transaction():
            for (symbol, position, _), events in groups.items():
                text = (
                    f"{symbol or 'Аккаунт'} { {1: 'Long', 2: 'Short'}.get(position, '') }\n"
                    + meaningful_summary(events)
                )
                if any("сокращением" in (e.get("summary_ru") or "") for e in events):
                    text += "\nЕсть исполнение с сокращением позиции"
                keyboard = {
                    "inline_keyboard": [
                        [{"text": f"Пояснить #{e['id']}", "callback_data": f"note:{e['id']}"}]
                        for e in events[:10]
                    ]
                }
                for chat in self.bot.allowed_chat_ids or self.bot.allowed_user_ids:
                    self.store.db.execute(
                        "INSERT INTO notification_outbox(destination,payload_json) VALUES(?,?)",
                        (
                            chat,
                            json.dumps({"text": text, "keyboard": keyboard}, ensure_ascii=False),
                        ),
                    )
            if rows:
                self.store.set_state("notification_timeline", rows[-1]["id"])

    async def run(self):
        while True:
            await asyncio.sleep(self.interval)
            await self.writer.call(self.collect)
            rows = await self.writer.call(
                lambda: self.store.db.execute(
                    "SELECT * FROM notification_outbox WHERE sent_at IS NULL ORDER BY id LIMIT 10"
                ).fetchall()
            )
            for row in rows:
                payload = json.loads(row["payload_json"])
                try:
                    if "review_note" in payload:
                        await self.bot.review(row["destination"], payload["review_note"])
                    else:
                        await self.bot.send(
                            row["destination"], payload["text"], payload["keyboard"]
                        )
                except RuntimeError:

                    def failed(row_id=row["id"]):
                        self.store.db.execute(
                            "UPDATE notification_outbox SET attempts=attempts+1,last_error='delivery failed' WHERE id=?",
                            (row_id,),
                        )
                        self.store._commit()

                    await self.writer.call(failed)
                    break

                def mark(row_id=row["id"]):
                    self.store.db.execute(
                        "UPDATE notification_outbox SET sent_at=?,attempts=attempts+1 WHERE id=?",
                        (datetime.now(UTC).isoformat(), row_id),
                    )
                    self.store._commit()

                await self.writer.call(mark)
