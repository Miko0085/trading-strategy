import json
from datetime import UTC, datetime


def health(store):
    sessions = []
    for source in ("bybit_public", "bybit_private"):
        row = store.db.execute(
            "SELECT disconnected_at,connected_at,reason FROM websocket_sessions WHERE source=? ORDER BY connected_at DESC LIMIT 1",
            (source,),
        ).fetchone()
        sessions.append(
            f"{source}: "
            + ("нет данных" if not row else ("подключён" if not row[0] else "отключён"))
        )
    candle = store.db.execute("SELECT MAX(end_ms) FROM market_candles").fetchone()[0]
    gaps = store.db.execute("SELECT COUNT(*) FROM data_gaps WHERE resolved=0").fetchone()[0]
    pending = store.db.execute(
        "SELECT COUNT(*) FROM voice_messages WHERE transcription_status!='completed'"
    ).fetchone()[0]
    automatic = store.db.execute(
        "SELECT COUNT(*) FROM websocket_sessions WHERE source LIKE 'bybit_public:auto:%' AND disconnected_at IS NULL"
    ).fetchone()[0]
    return "\n".join(
        [
            "📊 Состояние recorder",
            *sessions,
            f"Автоматические рыночные подключения: {automatic}",
            f"Последнее событие: {store.get_state('last_event', 'нет данных')}",
            f"Закрытая свеча: {datetime.fromtimestamp(candle / 1000, UTC).isoformat() if candle else 'нет данных'}",
            f"Последняя сверка: {store.get_state('last_reconciliation', 'нет данных')}",
            f"Неразрешённые пробелы данных: {gaps}",
            f"Аудио без готовой расшифровки: {pending}",
        ]
    )


_POSITION_LABELS = {0: "One-way", 1: "LONG", 2: "SHORT"}
_POSITION_ORDER = {1: 0, 2: 1, 0: 2}
_ACTIVE_ORDER_STATUSES = {"New", "PartiallyFilled", "Untriggered"}


def _show(value):
    return str(value) if value not in (None, "") else "нет данных"


def _clock(received_at):
    if not received_at:
        return "нет данных"
    today = datetime.now(UTC).date().isoformat()
    return received_at[11:19] if received_at[:10] == today else received_at[:16].replace("T", " ")


def account_text(store, symbol=None, since=None):
    rows = store.db.execute(
        "SELECT kind,state_key,symbol,received_at,data_json FROM current_states WHERE (? IS NULL OR symbol=? OR symbol IS NULL)",
        (symbol, symbol),
    ).fetchall()
    by_symbol = {}
    wallet = None
    active_orders = []
    for r in rows:
        data = json.loads(r["data_json"])
        if r["kind"] == "WALLET":
            wallet = (r["received_at"], data)
        elif r["kind"] == "TICKER":
            by_symbol.setdefault(r["symbol"], {})["ticker"] = (r["received_at"], data)
        elif r["kind"] == "POSITION":
            by_symbol.setdefault(r["symbol"], {}).setdefault("positions", []).append(
                (r["received_at"], data)
            )
        elif r["kind"] == "ORDER" and data.get("orderStatus") in _ACTIVE_ORDER_STATUSES:
            active_orders.append(data)

    header = f"📊 Текущее состояние — {symbol or 'все монеты'}"
    sections = [header]

    if wallet:
        received_at, data = wallet
        sections.append(
            "\n".join(
                [
                    f"💰 Баланс ({_clock(received_at)})",
                    f"Equity: {_show(data.get('totalEquity'))}",
                    f"Доступно: {_show(data.get('totalAvailableBalance'))}",
                    f"uPnL (перп.): {_show(data.get('totalPerpUPL'))}",
                ]
            )
        )

    for sym in sorted(by_symbol):
        block = by_symbol[sym]
        lines = []
        ticker = block.get("ticker")
        title = f"📈 {sym}"
        if ticker:
            received_at, data = ticker
            title += f" — Last {_show(data.get('lastPrice'))} / Mark {_show(data.get('markPrice'))} ({_clock(received_at)})"
        lines.append(title)
        positions = sorted(
            block.get("positions", []),
            key=lambda item: _POSITION_ORDER.get(item[1].get("positionIdx"), 9),
        )
        for received_at, data in positions:
            label = _POSITION_LABELS.get(data.get("positionIdx"), "неизвестно")
            lines.append(
                f"  {label}: размер {_show(data.get('size'))}, средняя {_show(data.get('entryPrice'))}, "
                f"uPnL {_show(data.get('unrealisedPnl'))}, реализ. PnL {_show(data.get('curRealisedPnl'))} "
                f"({_clock(received_at)})"
            )
        sections.append("\n".join(lines))

    if active_orders:
        lines = [f"📋 Активные заявки ({len(active_orders)})"]
        for data in active_orders:
            side_label = _POSITION_LABELS.get(data.get("positionIdx"), "")
            lines.append(
                f"  {data.get('side', '')} {_show(data.get('qty'))} @ {_show(data.get('price'))}"
                f"{' · ' + side_label if side_label else ''} · #{str(data.get('orderId'))[:8]}"
            )
        sections.append("\n".join(lines))

    if not rows:
        sections.append("Состояние аккаунта: нет данных")

    events = store.db.execute(
        "SELECT event_type,symbol,summary_ru,timestamp_received FROM timeline "
        "WHERE event_type!='MARKET' AND (? IS NULL OR symbol=?) AND (? IS NULL OR timestamp_received>=?) "
        "ORDER BY id DESC LIMIT 10",
        (symbol, symbol, since, since),
    ).fetchall()
    recent = ["🕒 Последние действия"]
    recent.extend(
        f"{_clock(r[3])} {r[0]}{' ' + r[1] if r[1] else ''}: {r[2]}" for r in events
    )
    if len(recent) == 1:
        recent.append("нет данных")
    sections.append("\n".join(recent))

    return "\n\n".join(sections)
