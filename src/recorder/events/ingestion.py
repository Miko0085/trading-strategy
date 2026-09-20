from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256

from recorder.account.normalization import persist_financial
from recorder.account.positions import semantic_position_change
from recorder.bybit.normalizer import normalize_kline, topic_items
from recorder.market.discovery import track


def now_iso():
    return datetime.now(UTC).isoformat()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


class EventIngestor:
    def __init__(self, store, symbols=None, snapshots=True, category="linear"):
        self.store = store
        self.symbols = set(symbols or [])
        self.snapshots = snapshots
        self.category = category

    def index(self, event):
        if not event.get("capture_id"):
            return None
        self.store.db.execute(
            "INSERT OR IGNORE INTO raw_events_index(received_at,source,topic,path,capture_id,byte_offset,byte_length,status) VALUES(?,?,?,?,?,?,?,'pending')",
            (
                event["received_at"],
                event["source"],
                event.get("topic"),
                event["raw_path"],
                event["capture_id"],
                event["byte_offset"],
                event["byte_length"],
            ),
        )
        self.store._commit()
        return self.store.db.execute(
            "SELECT id FROM raw_events_index WHERE capture_id=?", (event["capture_id"],)
        ).fetchone()[0]

    def failure(self, event, exc):
        if callable(event):
            self.store.gap("storage_command", type(exc).__name__)
            return
        raw_id = self.index(event)
        with self.store.transaction():
            if raw_id:
                self.store.db.execute(
                    "UPDATE raw_events_index SET status='failed',error=? WHERE id=?",
                    (type(exc).__name__, raw_id),
                )
            self.store.gap("normalization", f"raw_id={raw_id}; error={type(exc).__name__}")

    def state(self, kind, key):
        row = self.store.db.execute(
            "SELECT data_json,version_ms FROM current_states WHERE kind=? AND state_key=?",
            (kind, key),
        ).fetchone()
        return (json.loads(row[0]), row[1]) if row else (None, -1)

    def set_current(self, kind, key, symbol, stamp, received, data):
        self.store.db.execute(
            "INSERT INTO current_states VALUES(?,?,?,?,?,?) ON CONFLICT(kind,state_key) DO UPDATE SET symbol=excluded.symbol,version_ms=excluded.version_ms,received_at=excluded.received_at,data_json=excluded.data_json WHERE excluded.version_ms>=current_states.version_ms",
            (kind, key, symbol, stamp, received, encoded(data)),
        )

    def context(self, symbol=None):
        rows = self.store.db.execute(
            "SELECT kind,state_key,symbol,received_at,data_json FROM current_states WHERE (? IS NULL OR symbol=? OR symbol IS NULL)",
            (symbol, symbol),
        ).fetchall()
        return [
            {
                "kind": r[0],
                "key": r[1],
                "symbol": r[2],
                "received_at": r[3],
                "data": json.loads(r[4]),
            }
            for r in rows
        ]

    async def handle(self, event):
        raw_id = self.index(event)
        from recorder.events.replay import prepare

        event = prepare(event)
        received = event.get("received_at", now_iso())
        message = event["payload"]
        topic = event.get("normalized_topic") or message.get("topic", "")
        data = event.get("normalized_data")
        count = 0
        with self.store.transaction():
            if raw_id:
                status = self.store.db.execute(
                    "SELECT status FROM raw_events_index WHERE id=?", (raw_id,)
                ).fetchone()[0]
                if status == "processed":
                    return 0
            if topic.startswith("kline."):
                data = normalize_kline(message) if data is None else data
                kind = "MARKET"
            else:
                kind = {
                    "tickers": "TICKER",
                    "order": "ORDER",
                    "execution": "EXECUTION",
                    "position": "POSITION",
                    "wallet": "WALLET",
                    "closed_pnl": "CLOSED_PNL",
                    "funding": "FUNDING",
                    "account": "ACCOUNT",
                }.get(topic.split(".")[0])
                data = topic_items(message) if data is None else data
            if kind:
                for original in data:
                    item = dict(original)
                    symbol = item.get("symbol")
                    if symbol and kind in {
                        "ORDER",
                        "EXECUTION",
                        "POSITION",
                        "CLOSED_PNL",
                        "FUNDING",
                    }:
                        category = (
                            item.get("category")
                            or event.get("context", {}).get("request", {}).get("category")
                            or message.get("result", {}).get("category")
                            or self.category
                        )
                        # The watchlist never filters private account data.
                        added = track(
                            self.store,
                            category,
                            symbol,
                            "configured"
                            if category == self.category and symbol in self.symbols
                            else event["source"],
                            received,
                            raw_id,
                        )
                        if added and category != self.category:
                            self.store.gap(
                                "unsupported_market_category",
                                f"{category}/{symbol}: private event retained; automatic market/REST coverage is configured for {self.category}",
                            )
                    stamp = int(
                        item.get("execTime")
                        or item.get("updatedTime")
                        or item.get("transactionTime")
                        or message.get("creationTime")
                        or message.get("ts")
                        or message.get("time")
                        or int(datetime.fromisoformat(received).timestamp() * 1000)
                    )
                    key = str(
                        item.get("orderId")
                        or item.get("execId")
                        or symbol
                        or item.get("accountType")
                        or kind
                    )
                    if kind == "EXECUTION":
                        key = str(item["execId"])
                    if kind == "POSITION":
                        item["entryPrice"] = item.get("entryPrice", item.get("avgPrice"))
                        key = f"{symbol}:{item.get('positionIdx', 0)}"
                    if kind == "FUNDING":
                        key = str(item["id"])
                    if kind == "MARKET":
                        if not item.get("confirm"):
                            continue
                        key = f"{symbol}:{item['interval']}:{item['start']}"
                    before, previous_ms = self.state(kind, key)
                    context_before = (
                        self.context(symbol)
                        if kind in {"ORDER", "EXECUTION", "POSITION", "WALLET"}
                        else None
                    )
                    version = (
                        key
                        if kind in {"EXECUTION", "FUNDING", "MARKET"}
                        else key + ":" + sha256(encoded(item).encode()).hexdigest()
                    )
                    version = kind + ":" + version
                    if kind in {"WALLET", "TICKER", "ACCOUNT"}:
                        version += ":" + str(stamp)
                    exists = self.store.db.execute(
                        "SELECT id,timeline_id FROM observations WHERE version_key=?", (version,)
                    ).fetchone()
                    if exists:
                        continue
                    changed = True
                    if kind == "TICKER":
                        item = (
                            {**(before or {}), **item}
                            if message.get("type") != "snapshot"
                            else item
                        )
                    elif kind == "ORDER":
                        latest = self.store.db.execute(
                            "SELECT version_ms,raw_json FROM orders WHERE order_id=?", (key,)
                        ).fetchone()
                        self.store.insert_order_event(item)
                        if latest and latest[0] > stamp:
                            self.store.db.execute(
                                "UPDATE orders SET raw_json=? WHERE order_id=?", (latest[1], key)
                            )
                        else:
                            self.store.db.execute(
                                "UPDATE orders SET version_ms=? WHERE order_id=?", (stamp, key)
                            )
                    elif kind == "EXECUTION":
                        self.store.insert_execution(item)
                    elif kind == "POSITION":
                        changed = semantic_position_change(before, item) and stamp >= previous_ms
                        self.store.insert_position(item, changed)
                    elif kind == "WALLET":
                        if before and not event.get("topic", "").startswith("/v5/"):
                            coins = {c["coin"]: c for c in before.get("coin", [])}
                            for coin in item.get("coin", []):
                                coins[coin["coin"]] = {**coins.get(coin["coin"], {}), **coin}
                            item = {**before, **item, "coin": list(coins.values())}
                        self.store.db.execute(
                            "INSERT INTO wallet_snapshots(event_ts,raw_json) VALUES(?,?)",
                            (str(stamp), encoded(item)),
                        )
                    elif kind == "MARKET":
                        item["source"] = event["source"]
                        self.store.insert_candle(item, event["source"])
                        self.store.db.execute(
                            "UPDATE market_candles SET received_at=? WHERE symbol=? AND interval=? AND start_ms=?",
                            (received, symbol, str(item["interval"]), item["start"]),
                        )
                    elif kind in {"CLOSED_PNL", "FUNDING"}:
                        table = "closed_pnl" if kind == "CLOSED_PNL" else "funding"
                        column = "exec_id" if kind == "CLOSED_PNL" else "event_ts"
                        self.store.db.execute(
                            f"INSERT INTO {table}(symbol,{column},raw_json) VALUES(?,?,?)",
                            (
                                symbol,
                                item.get("execId") if kind == "CLOSED_PNL" else str(stamp),
                                encoded(item),
                            ),
                        )
                    if kind in {"ORDER", "POSITION", "WALLET", "TICKER", "ACCOUNT"}:
                        self.set_current(kind, key, symbol, stamp, received, item)
                    summary = {
                        "ORDER": "Заявка: " + str(item.get("orderStatus", "изменение")),
                        "EXECUTION": "Фактическое исполнение",
                        "POSITION": "Изменение позиции",
                        "WALLET": "Обновление баланса",
                        "FUNDING": "Начисление funding",
                        "CLOSED_PNL": "Реализация PnL по закрытой сделке",
                    }.get(kind, kind)
                    if kind == "EXECUTION" and item.get("execType") == "Funding":
                        summary = "Начисление funding (не сделка)"
                    elif kind == "EXECUTION" and Decimal(item.get("closedSize") or "0") > 0:
                        summary = "Исполнение с сокращением позиции"
                    timeline_id = None
                    if kind != "TICKER" and (kind != "POSITION" or changed):
                        timeline_id = self.store.insert_timeline(
                            {
                                "timestamp_exchange": datetime.fromtimestamp(
                                    stamp / 1000, UTC
                                ).isoformat(),
                                "timestamp_received": received,
                                "event_type": kind,
                                "symbol": symbol,
                                "source": event["source"],
                                "source_id": key,
                                "summary_ru": summary,
                                "linked_raw_event_id": raw_id,
                            }
                        )
                        if self.snapshots and symbol and kind in {"ORDER", "EXECUTION", "POSITION"}:
                            ticker, _ = self.state("TICKER", symbol)
                            ticker = ticker or {}
                            ticker_row = self.store.db.execute(
                                "SELECT received_at FROM current_states WHERE kind='TICKER' AND state_key=?",
                                (symbol,),
                            ).fetchone()
                            if category != self.category:
                                # Never attach a linear ticker to an identically named spot instrument.
                                ticker, ticker_row = {}, None
                            self.store.db.execute(
                                "INSERT INTO market_snapshots(symbol,timestamp,last_price,mark_price,index_price,bid,ask,account_event_id,ticker_received_at,ticker_age_ms) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                (
                                    symbol,
                                    received,
                                    ticker.get("lastPrice"),
                                    ticker.get("markPrice"),
                                    ticker.get("indexPrice"),
                                    ticker.get("bid1Price"),
                                    ticker.get("ask1Price"),
                                    timeline_id,
                                    ticker_row[0] if ticker_row else None,
                                    int(
                                        (
                                            datetime.fromisoformat(received)
                                            - datetime.fromisoformat(ticker_row[0])
                                        ).total_seconds()
                                        * 1000
                                    )
                                    if ticker_row
                                    else None,
                                ),
                            )
                    observation = self.store.db.execute(
                        "INSERT INTO observations(kind,entity_key,version_key,symbol,exchange_ms,received_at,raw_id,timeline_id,data_json,before_json,after_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            kind,
                            key,
                            version,
                            symbol,
                            stamp,
                            received,
                            raw_id,
                            timeline_id,
                            encoded(item),
                            encoded(context_before),
                            encoded(self.context(symbol)) if context_before is not None else None,
                        ),
                    )
                    persist_financial(self.store, observation.lastrowid, kind, item, stamp)
                    count += 1
            if raw_id:
                self.store.db.execute(
                    "UPDATE raw_events_index SET status='processed',error=NULL WHERE id=?",
                    (raw_id,),
                )
            self.store.set_state("last_event", received)
        return count
