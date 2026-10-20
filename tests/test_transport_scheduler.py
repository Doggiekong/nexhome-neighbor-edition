import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from custom_components.nexhome.api import HTTP_TIMEOUT, GatewayClient, authentication_headers
from custom_components.nexhome.errors import GatewayError, QueueFull
from custom_components.nexhome.scheduler import GatewayScheduler


class Response:
    status = 200

    def __init__(self, body):
        self.content = type("Content", (), {"read": AsyncMock(side_effect=[body, b""])})()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class Session:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.kwargs = response, error, None

    def request(self, *args, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


@pytest.mark.parametrize(
    "body,status",
    [
        (b"not-json", 200),
        (b'{"code":"denied","result":"private"}', 200),
        (b'{"code":0}', 200),
        (b'{"code":0,"result":{}}', 500),
        (b"[]", 200),
    ],
)
async def test_http_errors_redacted(body, status):
    response = Response(body)
    response.status = status
    client = GatewayClient("192.0.2.10:8085", "synthetic-identity", Session(response))
    with pytest.raises(GatewayError) as err:
        await client.request("GET", "devices")
    assert "private" not in str(err.value) and "synthetic-identity" not in str(err.value)
    await client.close()


async def test_timeout_and_nonblocking_isolation():
    session = Session(error=TimeoutError())
    client = GatewayClient("192.0.2.10:8085", "synthetic-identity", session)
    with pytest.raises(GatewayError):
        await client.properties([])
    assert session.kwargs["timeout"] is HTTP_TIMEOUT
    assert HTTP_TIMEOUT.sock_connect == 3 and HTTP_TIMEOUT.sock_read == 8 and HTTP_TIMEOUT.total == 11
    assert not session.kwargs["allow_redirects"]
    assert client.stats["timeouts"] == 1
    await client.close()


async def test_valid_json_and_response_schema():
    session = Session(Response(json.dumps({"code": "0", "result": {"elements": []}}).encode()))
    client = GatewayClient("192.0.2.10:8085", "synthetic-identity", session)
    assert await client.devices() == []
    session.response = Response(b'{"code":0,"result":{}}')
    with pytest.raises(GatewayError):
        await client.properties([])
    headers = authentication_headers("synthetic-identity", 100)
    assert len(headers["Password"]) == 32 and headers["Time"] == "100000"
    await client.close()


async def test_queue_bound_and_cancel_before_send():
    scheduler = GatewayScheduler(limit=2)
    gate = asyncio.Event()

    async def blocked():
        await gate.wait()

    first = asyncio.create_task(scheduler.call(blocked))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    calls = []

    async def next_call():
        calls.append("sent")

    second = asyncio.create_task(scheduler.call(next_call))
    await asyncio.sleep(0)
    with pytest.raises(QueueFull):
        await scheduler.call(next_call)
    second.cancel()
    await asyncio.gather(second, return_exceptions=True)
    gate.set()
    await first
    await asyncio.sleep(0)
    assert not calls
    await scheduler.close()


async def test_priority_is_fair_and_single_inflight():
    scheduler = GatewayScheduler()
    gate = asyncio.Event()
    order = []
    running = 0
    maximum = 0

    async def operation(name):
        nonlocal running, maximum
        running += 1
        maximum = max(maximum, running)
        if name == "first":
            await gate.wait()
        order.append(name)
        running -= 1

    first = asyncio.create_task(scheduler.call(lambda: operation("first")))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    queued = [
        asyncio.create_task(scheduler.call(lambda i=i: operation(f"control-{i}"), control=True))
        for i in range(5)
    ]
    poll = asyncio.create_task(scheduler.call(lambda: operation("poll")))
    await asyncio.sleep(0)
    gate.set()
    await asyncio.gather(first, *queued, poll)
    assert maximum == 1
    assert order.index("poll") <= 4
    await scheduler.close()


async def test_slow_gateway_does_not_block_event_loop():
    scheduler = GatewayScheduler()
    gate = asyncio.Event()
    task = asyncio.create_task(scheduler.call(gate.wait))
    alive = False

    async def tick():
        nonlocal alive
        await asyncio.sleep(0)
        alive = True

    await tick()
    assert alive and not task.done()
    gate.set()
    await task
    await scheduler.close()


async def test_fragmented_body_and_size_limit():
    response = Response(b"")
    response.content.read.side_effect = [b'{"code":', b'0,"result":{"elements":[]}}', b""]
    session = Session(response)
    client = GatewayClient("192.0.2.10:8085", "synthetic-identity", session)
    assert await client.devices() == []
    session.response = Response(b"x" * (1024 * 1024 + 1))
    with pytest.raises(GatewayError, match="size limit"):
        await client.devices()
    await client.close()
