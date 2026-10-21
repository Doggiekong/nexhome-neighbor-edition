"""Shared polling, per-property freshness and ordered command/readback pipeline."""

import asyncio
import logging
import math
import time
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CHUNK_SIZE, FRESH_SECONDS, PENDING_SECONDS, POLL_SECONDS, QUEUE_LIMIT
from .errors import GatewayError, QueueFull

LOGGER = logging.getLogger(__name__)


def valid_value(identifier, value):
    if value is None or isinstance(value, (dict, list, bool)):
        return False
    if identifier == "PowerSwitch":
        return str(value) in ("0", "1")
    try:
        return math.isfinite(float(value))
    except ValueError, TypeError:
        return False


class GatewayCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, client, *, entry=None, clock=time.monotonic):
        super().__init__(
            hass, LOGGER, name="nexhome", config_entry=entry, update_interval=timedelta(seconds=POLL_SECONDS)
        )
        self.client = client
        self.clock = clock
        self.targets = {}
        self.requirements = {}
        self.read_received = set()
        self.values = {}
        self.fresh = {}
        self.pending = {}
        self.protected = {}
        self.device_locks = {}
        self.read_lock = asyncio.Lock()
        self.waiting = 0
        self.expiry = None
        self.push_tasks = {}
        self.missing_count = 0
        self.closed = False
        self.confirmed_controls = 0

    def register(self, address, identifiers, *, required_groups=None):
        self.targets.setdefault(address, set()).update(identifiers)
        groups = required_groups if required_groups is not None else [set(identifiers)]
        alternatives = tuple(frozenset(group) for group in groups)
        if alternatives not in self.requirements.setdefault(address, []):
            self.requirements[address].append(alternatives)

    def is_fresh(self, address, identifiers, *, after=0):
        now = self.clock()
        return bool(identifiers) and all(
            after <= self.fresh.get((address, i), -math.inf)
            and now - self.fresh.get((address, i), -math.inf) < FRESH_SECONDS
            for i in identifiers
        )

    def state(self, address, identifier, *, predicted=True):
        key = (address, identifier)
        pending = self.pending.get(key)
        if predicted and pending and pending[1] > self.clock():
            return pending[0]
        return self.values.get(key)

    def _notify(self):
        self.data = dict(self.values)
        self.async_update_listeners()

    def _schedule_expiry(self):
        if self.expiry:
            self.expiry.cancel()
        if self.pending:
            delay = max(0, min(v[1] for v in self.pending.values()) - self.clock())
            self.expiry = self.hass.loop.call_later(delay, self.expire_pending)

    def expire_pending(self):
        self.expiry = None
        now = self.clock()
        self.pending = {k: v for k, v in self.pending.items() if v[1] > now}
        self._notify()
        self._schedule_expiry()

    def apply_rows(self, rows, params, started, accepted=None):
        wanted = {(p["address"], p["identifier"]) for p in params}
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            if not isinstance(row.get("address"), str) or not isinstance(row.get("identifier"), str):
                continue
            key = (row.get("address"), row.get("identifier"))
            if key not in wanted or key in seen or not valid_value(key[1], row.get("value")):
                continue
            seen.add(key)
            if started < self.protected.get(key[0], 0):
                continue
            if accepted is not None:
                accepted.add(key)
            self.values[key] = row["value"]
            self.fresh[key] = self.clock()
            self.pending.pop(key, None)
        return len(wanted - seen)

    async def read(self, address=None):
        async with self.read_lock:
            params = [
                {"address": a, "identifier": i}
                for a, ids in sorted(self.targets.items())
                if address is None or a == address
                for i in sorted(ids)
            ]
            missing = 0
            received = set()
            try:
                for offset in range(0, len(params), CHUNK_SIZE):
                    chunk = params[offset : offset + CHUNK_SIZE]
                    started = self.clock()
                    rows = await self.client.properties(chunk)
                    missing += self.apply_rows(rows, chunk, started, received)
            finally:
                self.missing_count = missing
                self.read_received = received
                self._notify()  # Valid partial data stays visible even on consecutive failures.
            return missing

    async def _async_update_data(self):
        try:
            await self.read()
        except GatewayError:
            raise UpdateFailed("Gateway polling failed") from None
        if any(
            not any(all((address, field) in self.read_received for field in group) for group in alternatives)
            for address, groups in self.requirements.items()
            for alternatives in groups
        ):
            raise UpdateFailed("Required gateway properties are missing or invalid")
        return dict(self.values)

    async def command(
        self, address, commands, *, attempts=2, interval=0.5, verdict=None, confirmation_timeout=None
    ):
        if self.closed or address not in self.targets:
            raise GatewayError("Device session unavailable")
        if self.waiting >= QUEUE_LIMIT:
            raise QueueFull("Device command queue full; command not sent")
        self.waiting += 1
        keys = [(address, c["identifier"]) for c in commands]
        try:
            async with self.device_locks.setdefault(address, asyncio.Lock()):
                self.protected[address] = math.inf
                try:
                    for command in commands:
                        await self.client.control(address, command)
                    self.protected[address] = self.clock()
                    for c in commands:
                        self.pending[(address, c["identifier"])] = (
                            c["value"],
                            self.clock() + PENDING_SECONDS,
                        )
                    self._schedule_expiry()
                    self._notify()
                    deadline = (
                        self.clock() + confirmation_timeout if confirmation_timeout is not None else None
                    )
                    for attempt in range(attempts):
                        if attempt and deadline is not None and self.clock() >= deadline:
                            break
                        await self.read(address)  # No blind resend, even after transport failure.
                        if verdict:
                            confirmed = verdict(self.protected[address])
                        else:
                            confirmed = all(
                                self.is_fresh(address, [c["identifier"]], after=self.protected[address])
                                and str(self.values.get(k)) == str(c["value"])
                                for k, c in zip(keys, commands)
                            )
                        if confirmed is True or confirmed is None:
                            if confirmed is True:
                                self.confirmed_controls += 1
                            return
                        if attempt + 1 < attempts:
                            delay = (
                                interval
                                if deadline is None
                                else max(0, min(interval, deadline - self.clock()))
                            )
                            await asyncio.sleep(delay)
                    raise GatewayError("Command accepted but physical state not confirmed")
                finally:
                    self.protected[address] = self.clock()
                    for key in keys:
                        self.pending.pop(key, None)
                    self._notify()
        finally:
            self.waiting -= 1

    def request_refresh(self, address):
        if not self.closed and address in self.targets and address not in self.push_tasks:
            self.push_tasks[address] = asyncio.create_task(self._push_refresh(address))

    async def _push_refresh(self, address):
        try:
            await asyncio.sleep(0.15)
            await self.read(address)
        except GatewayError:
            LOGGER.debug("UDP refresh failed; polling remains active")
        finally:
            self.push_tasks.pop(address, None)

    async def async_shutdown(self):
        if self.closed:
            return
        self.closed = True
        if self.expiry:
            self.expiry.cancel()
        for task in self.push_tasks.values():
            task.cancel()
        await asyncio.gather(*list(self.push_tasks.values()), return_exceptions=True)
        self.push_tasks.clear()
        self.pending.clear()
        await self.client.close()
        await super().async_shutdown()
