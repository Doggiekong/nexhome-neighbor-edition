"""One bounded, fair request worker per gateway; no HA executor threads."""

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable

from .const import CONTROL_BURST, QUEUE_LIMIT
from .errors import GatewayError, QueueFull


class GatewayScheduler:
    def __init__(self, limit=QUEUE_LIMIT):
        self.limit = limit
        self.control = deque()
        self.poll = deque()
        self.worker = None
        self.closed = False
        self.inflight = 0
        self.burst = 0
        self.rejected = 0

    async def call(self, operation: Callable[[], Awaitable], *, control=False):
        if self.closed:
            raise GatewayError("Gateway session is closed")
        if len(self.control) + len(self.poll) + self.inflight >= self.limit:
            self.rejected += 1
            raise QueueFull("Gateway queue full; request not sent")
        future = asyncio.get_running_loop().create_future()
        (self.control if control else self.poll).append((future, operation))
        if self.worker is None or self.worker.done():
            self.worker = asyncio.create_task(self._run())
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            future.cancel()  # Never send a cancelled operation still waiting in queue.
            raise

    async def _run(self):
        while self.control or self.poll:
            if self.control and (self.burst < CONTROL_BURST or not self.poll):
                future, operation = self.control.popleft()
                self.burst += 1
            else:
                future, operation = self.poll.popleft()
                self.burst = 0
            if future.cancelled():
                continue
            self.inflight = 1
            try:
                value = await operation()
            except asyncio.CancelledError:
                if not future.done():
                    future.set_exception(GatewayError("Request interrupted; outcome unknown"))
                raise
            except Exception as err:
                if not future.done():
                    future.set_exception(err)
            else:
                if not future.done():
                    future.set_result(value)
            finally:
                self.inflight = 0

    async def close(self):
        self.closed = True
        for queue in (self.control, self.poll):
            while queue:
                future, _ = queue.popleft()
                if not future.done():
                    future.set_exception(GatewayError("Session closed; queued request not sent"))
        if self.worker and not self.worker.done():
            self.worker.cancel()
            await asyncio.gather(self.worker, return_exceptions=True)
