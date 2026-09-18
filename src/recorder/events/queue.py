from __future__ import annotations

import asyncio
import inspect
import logging

log = logging.getLogger(__name__)


class ControlledWriter:
    """Serial owner; failed events don't kill ingestion, fatal storage failures unblock callers."""

    def __init__(self, handler, maxsize=1000, on_error=None):
        self.queue = asyncio.Queue(maxsize=maxsize)
        self.handler, self.on_error = handler, on_error
        self.closed = False
        self.task = None

    async def put(self, event):
        return await self._enqueue(event, False)

    async def submit(self, event):
        return await self._enqueue(event, True)

    async def call(self, operation):
        return await self._enqueue(operation, True)

    async def _enqueue(self, item, wait):
        if self.closed or (self.task and self.task.done()):
            raise RuntimeError("SQLite writer unavailable")
        future = asyncio.get_running_loop().create_future() if wait else None
        if future:
            # A cancelled producer may no longer observe the result, but the write still drains.
            future.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
        await self.queue.put((item, future))
        if self.task and self.task.done():
            self._fail_pending()
            raise RuntimeError("SQLite writer unavailable")
        return await asyncio.shield(future) if future else None

    def _fail_pending(self):
        while not self.queue.empty():
            _, future = self.queue.get_nowait()
            if future and not future.done():
                future.set_exception(RuntimeError("SQLite writer stopped"))
            self.queue.task_done()

    async def run(self):
        self.task = asyncio.current_task()
        try:
            while True:
                item, future = await self.queue.get()
                try:
                    if item is None:
                        return
                    try:
                        value = item() if callable(item) else self.handler(item)
                        if inspect.isawaitable(value):
                            value = await value
                    except Exception as exc:  # noqa: BLE001 -- isolate failed normalization
                        log.error("writer operation failed: %s", type(exc).__name__)
                        try:
                            if self.on_error:
                                self.on_error(item, exc)
                        finally:
                            if future and not future.done():
                                future.set_exception(exc)
                    else:
                        if future and not future.done():
                            future.set_result(value)
                finally:
                    if future and not future.done():
                        future.set_exception(RuntimeError("SQLite writer interrupted"))
                    self.queue.task_done()
        finally:
            self.closed = True
            self._fail_pending()

    async def drain(self):
        self.closed = True
        await self.queue.join()
        if self.task and self.task.done():
            await self.task
            return
        await self.queue.put((None, None))
        if self.task and self.task is not asyncio.current_task():
            await self.task
