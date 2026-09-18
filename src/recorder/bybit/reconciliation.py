from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from recorder.events.ingestion import EventIngestor
from recorder.events.models import RawEvent
from recorder.market.candles import floor_start, next_start
from recorder.storage.raw_jsonl import RawJsonlWriter


@dataclass
class ReconciliationResult:
    reason: str
    records_checked: int = 0
    missing_found: int = 0
    recovered: int = 0
    duplicates: int = 0
    errors: list[str] = field(default_factory=list)
    status: str = "ok"


async def reconcile_executions(fetch, known, ingest, reason):
    result = ReconciliationResult(reason)
    try:
        for item in await fetch():
            result.records_checked += 1
            key = item["execId"]
            if key in known:
                result.duplicates += 1
            else:
                result.missing_found += 1
                if await ingest(item):
                    result.recovered += 1
                    known.add(key)
    except Exception as exc:  # noqa: BLE001 -- failure boundary records errors and preserves source data
        result.status, result.errors = "data_gap", [type(exc).__name__]
    return result


class Reconciler:
    def __init__(self, rest, writer, store, symbols, category, raw, config):
        self.rest, self.writer, self.store = rest, writer, store
        self.symbols, self.category, self.raw, self.config = symbols, category, raw, config
        self.lock = asyncio.Lock()

    async def run(self, reason):
        async with self.lock:
            return await self._run(reason)

    async def _run(self, reason):
        end = int(time.time() * 1000)
        scope = (
            "all_symbols:"
            + self.category
            + ":"
            + ",".join(sorted(self.config.get("settle_coins", ["USDT", "USDC"])))
        )
        old_scope = await self.writer.call(lambda: self.store.get_state("reconciliation_scope"))
        previous = (
            await self.writer.call(lambda: self.store.get_state("reconciled_until"))
            if old_scope == scope
            else None
        )
        start = (
            previous or end - self.config.get("startup_lookback_hours", 24) * 3600000
        ) - self.config.get("overlap_seconds", 120) * 1000
        result = ReconciliationResult(reason)
        started = datetime.now(UTC).isoformat()

        async def read(path, params, topic):
            async for rows, event in self.rest.pages(path, params):
                if event is None:
                    raise RuntimeError("REST source capture is required")
                result.records_checked += len(rows)
                changed = await self.writer.submit(
                    {**event, "normalized_topic": topic, "normalized_data": rows}
                )
                result.recovered += changed
                result.duplicates += len(rows) - changed

        try:
            # All historical windows <= 24h, stricter than V5's seven-day limits.
            # Query history across the entire configured category, not the watchlist.
            left = start
            while left <= end:
                right = min(left + 86400000 - 1, end)
                params = {
                    "category": self.category,
                    "startTime": left,
                    "endTime": right,
                    "limit": 50,
                }
                for path, topic in (
                    ("/v5/order/history", "order"),
                    ("/v5/execution/list", "execution"),
                    ("/v5/position/closed-pnl", "closed_pnl"),
                ):
                    await read(path, params, topic)
                left = right + 1
            settlements = (
                self.config.get("settle_coins", ["USDT", "USDC"])
                if self.category == "linear"
                else [None]
            )
            for settlement in settlements:
                params = {"category": self.category, "limit": 50}
                if settlement:
                    params["settleCoin"] = settlement
                await read("/v5/order/realtime", {**params, "openOnly": 0}, "order")
                await read("/v5/position/list", params, "position")
            # Symbol-scoped queries also return flat positions, preventing stale open sizes.
            from recorder.market.discovery import tracked_symbols

            known = await self.writer.call(lambda: tracked_symbols(self.store, self.category))
            for symbol in sorted(set(self.symbols) | set(known)):
                await read(
                    "/v5/position/list", {"category": self.category, "symbol": symbol}, "position"
                )
            left = start
            while left <= end:
                right = min(left + 86400000 - 1, end)
                await read(
                    "/v5/account/transaction-log",
                    {
                        "accountType": "UNIFIED",
                        "category": self.category,
                        "type": "SETTLEMENT",
                        "startTime": left,
                        "endTime": right,
                        "limit": 50,
                    },
                    "funding",
                )
                left = right + 1
            await read("/v5/account/wallet-balance", {"accountType": "UNIFIED"}, "wallet")
            response = await self.rest.get("/v5/account/info", {})
            await self.writer.submit(
                {
                    **self.rest.last_capture,
                    "normalized_topic": "account",
                    "normalized_data": [response["result"]],
                }
            )

            def checkpoint():
                with self.store.transaction():
                    self.store.set_state("reconciled_until", end)
                    self.store.set_state("reconciliation_scope", scope)

            await self.writer.call(checkpoint)
            # History can recover fills and final states, not every intermediate WS transition.
            if reason in {"startup", "reconnect"}:
                result.status = "warning"
                await self.writer.call(
                    lambda: self.store.gap(
                        "state_history_unprovable",
                        "REST recovery cannot prove every intermediate order/wallet/position state",
                        start,
                        end,
                    )
                )
        except Exception as exc:  # noqa: BLE001 -- failure boundary records errors and preserves source data
            result.status = "data_gap"
            result.errors = [type(exc).__name__]
            await self.writer.call(
                lambda: self.store.gap("reconciliation", result.errors[0], start, end)
            )
        result.missing_found = result.recovered

        def finish():
            with self.store.transaction():
                run_id = self.store.record_reconciliation(result)
                self.store.db.execute(
                    "UPDATE reconciliation_runs SET started_at=?,finished_at=? WHERE id=?",
                    (started, datetime.now(UTC).isoformat(), run_id),
                )
                self.store.db.execute(
                    "INSERT INTO reconciliation_findings(run_id,kind,details) VALUES(?,?,?)",
                    (
                        run_id,
                        result.status,
                        f"window={start}:{end}; recovered includes new states, not inferred executions",
                    ),
                )
                self.store.set_state(
                    "last_reconciliation",
                    {
                        "status": result.status,
                        "finished_at": datetime.now(UTC).isoformat(),
                        "start_ms": start,
                        "end_ms": end,
                    },
                )
            return run_id

        await self.writer.call(finish)
        return result


async def reconcile_account(rest, store, category, symbols, reason, start_ms=None, end_ms=None):
    """Compatibility helper for offline callers. Runtime uses Reconciler + one writer."""
    result = ReconciliationResult(reason)
    ingestor = EventIngestor(store)
    raw = RawJsonlWriter(store.path.parent / "recovery_raw")
    try:
        for symbol in symbols:
            records = await rest.executions(category, symbol, start_ms, end_ms)
            for item in records:
                known = store.db.execute(
                    "SELECT 1 FROM executions WHERE exec_id=?", (item["execId"],)
                ).fetchone()
                result.records_checked += 1
                event = await raw.capture(
                    RawEvent(
                        source="REST_RECONCILE",
                        topic="execution",
                        payload={"topic": "execution", "data": [item]},
                    )
                )
                await ingestor.handle(event)
                if known:
                    result.duplicates += 1
                else:
                    result.missing_found += 1
                    result.recovered += 1
    except Exception as exc:  # noqa: BLE001 -- failure boundary records errors and preserves source data
        result.status, result.errors = "data_gap", [type(exc).__name__]
        store.gap("reconciliation", type(exc).__name__, start_ms, end_ms)
    store.record_reconciliation(result)
    return result


async def backfill_klines(
    rest, store, category, symbol, interval, start_ms, end_ms, writer=None, raw=None
):
    raw = raw or RawJsonlWriter(store.path.parent / "recovery_raw")
    ingestor = EventIngestor(store)
    cursor = end_ms
    now = int(time.time() * 1000)
    found = set()
    while cursor >= start_ms:
        rows = await rest.klines(category, symbol, interval, start_ms, cursor)
        if not rows:
            break
        event = getattr(rest, "last_capture", None)
        if event is None:
            event = await raw.capture(
                RawEvent(
                    source="REST_BACKFILL",
                    topic="/v5/market/kline",
                    payload={"result": {"list": rows}},
                    context={
                        "request": {
                            "symbol": symbol,
                            "interval": interval,
                            "start": start_ms,
                            "end": cursor,
                        }
                    },
                )
            )
        candles = []
        for row in rows:
            start = int(row[0])
            stop = next_start(start, interval)
            if start < start_ms or start > cursor or stop > min(now, end_ms + 1):
                continue
            found.add(start)
            candles.append(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "start": start,
                    "end": stop - 1,
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                    "turnover": row[6],
                    "confirm": True,
                }
            )
        envelope = {
            **event,
            "source": "REST_BACKFILL",
            "normalized_topic": f"kline.{interval}.{symbol}",
            "normalized_data": candles,
        }
        if writer:
            await writer.submit(envelope)
        else:
            await ingestor.handle(envelope)
        oldest = min(int(row[0]) for row in rows)
        if oldest > cursor:
            raise RuntimeError("Kline pagination did not advance")
        cursor = oldest - 1
    left = floor_start(start_ms, interval)
    if left < start_ms:
        left = next_start(left, interval)
    missing = []
    while next_start(left, interval) <= min(now, end_ms + 1):
        if left not in found:
            missing.append(left)
        left = next_start(left, interval)
    if missing:
        operation = lambda: store.gap(
            "candles",
            f"{symbol}/{interval}: {len(missing)} candles absent from REST",
            missing[0],
            missing[-1],
        )
        if writer:
            await writer.call(operation)
        else:
            operation()
    return len(found)
