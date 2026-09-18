from __future__ import annotations

from typing import Any


def status_text(
    recorder: str,
    private_ws: str,
    public_ws: str,
    last_event: str = "нет данных",
    last_candle: str = "нет данных",
    last_reconciliation: str = "нет данных",
    data_gap: str = "нет данных",
) -> str:
    return "\n".join(
        [
            "📊 Статус recorder",
            f"Recorder: {recorder}",
            f"Bybit Private WS: {private_ws}",
            f"Bybit Public WS: {public_ws}",
            f"Последнее событие: {last_event}",
            f"Последняя свеча: {last_candle}",
            f"Последняя сверка: {last_reconciliation}",
            f"Data gap: {data_gap}",
        ]
    )


def event_text(event: dict[str, Any]) -> str:
    symbol = event.get("symbol") or "неизвестный символ"
    summary = event.get("summary_ru") or "Наблюдаемое событие"
    return f"🔔 {summary}\n\n{symbol}\n\nХотите пояснить это действие?"


def main_keyboard() -> dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "📊 Текущее состояние"}, {"text": "🕒 Последние действия"}],
            [{"text": "✍️ Пояснить действие"}, {"text": "🎙 Пояснить голосом"}],
        ],
        "resize_keyboard": True,
    }


def event_keyboard(event_id: int) -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": "✍️ Пояснить", "callback_data": f"note:{event_id}"}]]}


def confirmation_keyboard(note_id: int) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": "✅ Всё верно", "callback_data": f"verify:{note_id}"}],
            [
                {"text": "🔗 Исправить связь", "callback_data": f"relink:{note_id}"},
                {"text": "📝 Исправить текст", "callback_data": f"edit:{note_id}"},
            ],
        ]
    }
