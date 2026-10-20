"""Local-only, bounded asynchronous implementation of the upstream HTTP protocol."""

import asyncio
import hashlib
import ipaddress
import json
import time
from urllib.parse import quote

import aiohttp

from .errors import GatewayError
from .scheduler import GatewayScheduler

HTTP_TIMEOUT = aiohttp.ClientTimeout(total=11, sock_connect=3, sock_read=8)
MAX_BODY = 1024 * 1024


def validate_endpoint(value):
    try:
        host, port = value.rsplit(":", 1)
        address = ipaddress.IPv4Address(host)
        if address.is_loopback or address.is_multicast or address.is_unspecified:
            raise ValueError
        if not 0 < int(port) < 65536 or not address.is_private:
            raise ValueError
        return f"{address}:{int(port)}"
    except ValueError, AttributeError:
        raise GatewayError("Expected a local IPv4 address and port") from None


def authentication_headers(serial, now=None):
    if not isinstance(serial, str) or not serial or len(serial) > 256:
        raise GatewayError("Missing or invalid local gateway identity")
    stamp = str(int((time.time() if now is None else now) * 1000))

    def digest(text):
        return hashlib.md5(text.encode()).hexdigest()  # Protocol, not encryption.

    return {
        "Time": stamp,
        "Password": digest(digest(serial) + digest(stamp)),
        "Appid": "10000106",
        "Version": "v1",
    }


class GatewayClient:
    def __init__(self, endpoint, serial, session, scheduler=None):
        self.endpoint = validate_endpoint(endpoint)
        self.serial = serial
        self.session = session
        self.scheduler = scheduler or GatewayScheduler()
        self.stats = {"requests": 0, "errors": 0, "timeouts": 0}

    async def request(self, method, path, data=None, *, control=False):
        async def operation():
            self.stats["requests"] += 1
            try:
                async with self.session.request(
                    method,
                    f"http://{self.endpoint}/smarthome/{path}",
                    headers=authentication_headers(self.serial),
                    json=data,
                    timeout=HTTP_TIMEOUT,
                    allow_redirects=False,
                ) as response:
                    if not 200 <= response.status < 300:
                        raise GatewayError("Gateway HTTP response rejected")
                    body = bytearray()
                    while len(body) <= MAX_BODY:
                        fragment = await response.content.read(min(65536, MAX_BODY + 1 - len(body)))
                        if not fragment:
                            break
                        body.extend(fragment)
                    if len(body) > MAX_BODY:
                        raise GatewayError("Gateway response exceeded size limit")
                    payload = json.loads(body)
                    if not isinstance(payload, dict) or str(payload.get("code")) != "0":
                        raise GatewayError("Gateway business response rejected")
                    if "result" not in payload:
                        raise GatewayError("Gateway response result missing")
                    return payload["result"]
            except TimeoutError, asyncio.TimeoutError:
                self.stats["timeouts"] += 1
                self.stats["errors"] += 1
                raise GatewayError("Gateway timed out; command outcome may be unknown") from None
            except aiohttp.ClientError, ValueError, UnicodeError, RecursionError:
                self.stats["errors"] += 1
                raise GatewayError("Gateway transport or JSON failure") from None
            except GatewayError:
                self.stats["errors"] += 1
                raise

        return await self.scheduler.call(operation, control=control)

    async def login(self):
        await self.request("POST", "login", {"ip": "127.0.0.1"})

    async def devices(self):
        result = await self.request("GET", "devices")
        if not isinstance(result, dict) or not isinstance(result.get("elements"), list):
            raise GatewayError("Gateway device list malformed")
        return result["elements"]

    async def properties(self, params):
        result = await self.request("POST", "devices/properties/realtime", {"properties": params})
        if not isinstance(result, dict) or not isinstance(result.get("deviceProperty"), list):
            raise GatewayError("Gateway property list malformed")
        return result["deviceProperty"]

    async def control(self, address, command):
        await self.request("POST", f"devices/{quote(address, safe='')}/control", command, control=True)

    async def close(self):
        await self.scheduler.close()
