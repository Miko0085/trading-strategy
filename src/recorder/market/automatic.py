"""Add market collectors without reconnecting already observed instruments."""

import asyncio
from datetime import UTC, datetime

from recorder.bybit.public_collector import build_public_collector
from recorder.market.discovery import is_flat, stop_tracking, tracked_symbols


class AutomaticMarkets:
    def __init__(self, store, writer, raw, symbols, cfg, session_callback, backfill):
        self.store, self.writer, self.raw = store, writer, raw
        self.symbols, self.cfg = symbols, cfg
        self.session_callback, self.backfill = session_callback, backfill
        self.collectors = {}
        self.tasks = {}
        self.backfill_queue = asyncio.Queue()
        self.pending = set()

    async def stop_flat_symbols(self):
        for symbol in list(self.collectors):
            if not await self.writer.call(lambda symbol=symbol: is_flat(self.store, symbol)):
                continue

            def mark_stopped(symbol=symbol):
                stop_tracking(
                    self.store, self.symbols.category, symbol, datetime.now(UTC).isoformat()
                )
                self.store._commit()

            await self.writer.call(mark_stopped)
            await self.collectors.pop(symbol).stop()
            task = self.tasks.pop(symbol)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def refresh(self):
        await self.stop_flat_symbols()
        discovered = await self.writer.call(
            lambda: tracked_symbols(self.store, self.symbols.category)
        )
        for symbol in discovered:
            if symbol in self.symbols.symbols or symbol in self.collectors:
                continue

            async def ready(reconnect, symbol=symbol):
                def mark():
                    self.store.db.execute(
                        "UPDATE tracked_instruments SET market_started_at=COALESCE(market_started_at,?) WHERE category=? AND symbol=?",
                        (datetime.now(UTC).isoformat(), self.symbols.category, symbol),
                    )
                    self.store._commit()

                await self.writer.call(mark)
                if symbol not in self.pending:
                    self.pending.add(symbol)
                    self.backfill_queue.put_nowait(symbol)

            collector = build_public_collector(
                [symbol],
                self.symbols.market["kline_intervals"],
                self.cfg.environment == "testnet",
                self.raw,
                self.writer.put,
                category=self.symbols.category,
                ticker=self.symbols.market["ticker"],
                public_trades=self.symbols.market["public_trades"]["enabled"],
                orderbook=self.symbols.market["orderbook"],
                save_open_kline_updates_raw=self.cfg.market["save_open_kline_updates_raw"],
                session_callback=self.session_callback,
                on_connect=ready,
            )
            collector.source = f"bybit_public:auto:{self.symbols.category}:{symbol}"
            self.collectors[symbol] = collector
            self.tasks[symbol] = asyncio.create_task(collector.run())

    async def backfills(self):
        while True:
            symbol = await self.backfill_queue.get()
            self.pending.discard(symbol)
            try:
                await self.backfill([symbol])
            finally:
                self.backfill_queue.task_done()

    async def run(self):
        backfills = asyncio.create_task(self.backfills())
        try:
            while True:
                await self.refresh()
                for task in [backfills, *self.tasks.values()]:
                    if task.done():
                        await task
                        raise RuntimeError("Automatic market task stopped unexpectedly")
                await asyncio.sleep(self.cfg.market["discovery_interval_seconds"])
        finally:
            await asyncio.gather(
                *(c.stop() for c in self.collectors.values()), return_exceptions=True
            )
            backfills.cancel()
            for task in self.tasks.values():
                task.cancel()
            await asyncio.gather(backfills, *self.tasks.values(), return_exceptions=True)
