"""Bounded NSDP discovery and refresh hints; no device scanning or payload trust."""

import asyncio
import ipaddress
import socket
import uuid
from dataclasses import dataclass, field
from urllib.parse import unquote_plus, urlsplit

from homeassistant.components import network

from .api import validate_endpoint
from .errors import GatewayError

MAX_PACKET = 8192


def parse_headers(packet):
    if len(packet) > MAX_PACKET:
        raise ValueError("Oversized packet")
    lines = packet.decode("utf-8", errors="strict").split("\r\n")
    if not lines or not lines[0].startswith(("HTTP/1.", "NOTIFY ")):
        raise ValueError("Unsupported packet")
    headers = {}
    for line in lines[1:]:
        if not line:
            continue
        if ":" not in line:
            raise ValueError("Malformed header")
        key, value = line.split(":", 1)
        key = key.strip().upper()
        if key in headers:
            raise ValueError("Duplicate header")
        headers[key] = value.strip()
    return headers


def parse_model(value):
    result = {}
    for item in unquote_plus(value).split("&"):
        # Real NSDP senders may include empty query segments between fields.
        if not item:
            continue
        if "=" not in item:
            raise ValueError("Malformed model")
        key, value = item.split("=", 1)
        if key in result:
            raise ValueError("Duplicate model field")
        result[key] = value
    return result


@dataclass(frozen=True)
class Hub:
    endpoint: str
    serial: str = field(repr=False)


def parse_discovery(packet, source):
    headers = parse_headers(packet)
    location = urlsplit(headers["LOCATION"])
    if (
        location.scheme != "http"
        or location.username
        or location.password
        or location.query
        or location.fragment
        or location.path not in ("", "/")
        or location.hostname != source[0]
    ):
        raise ValueError("Invalid local discovery endpoint")
    try:
        endpoint = validate_endpoint(f"{location.hostname}:{location.port}")
    except GatewayError, ValueError:
        raise ValueError("Invalid endpoint") from None
    serial = parse_model(headers["MODEL"])["sn"]
    if not serial or len(serial) > 256 or any(ord(c) < 32 for c in serial):
        raise ValueError("Invalid gateway identity")
    return Hub(endpoint, serial)


def build_search(local_ip, port):
    return (
        f"M-SEARCH * HTTP/1.1\r\nHOST: {local_ip}:{port}\r\n"
        "ST: nsdp:all\r\nMAN: nsdp:discover\r\nFEATURES: productid-v2\r\n"
        f"USN: {uuid.uuid4().hex}\r\nSN: 1\r\n\r\n"
    ).encode()


async def async_discover(hass, *, attempts=3, window=3):
    adapters = [a for a in await network.async_get_adapters(hass) if a["enabled"]]
    interfaces = []
    for adapter in adapters:
        for item in adapter["ipv4"]:
            iface = ipaddress.IPv4Interface(f"{item['address']}/{item['network_prefix']}")
            if not iface.ip.is_loopback and not iface.ip.is_link_local:
                interfaces.append(iface)
    # Globally bounded sends, including multi-interface systems. No unicast fallback.
    hubs = {}
    loop = asyncio.get_running_loop()
    for index in range(min(max(attempts, 0), 3)):
        if not interfaces:
            break
        iface = interfaces[index % len(interfaces)]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((str(iface.ip), 0))
            sock.setblocking(False)
            sock.sendto(
                build_search(str(iface.ip), sock.getsockname()[1]),
                (str(iface.network.broadcast_address), 1912),
            )
            deadline = loop.time() + window
            while loop.time() < deadline:
                try:
                    packet, source = await asyncio.wait_for(
                        loop.sock_recvfrom(sock, MAX_PACKET + 1), deadline - loop.time()
                    )
                    hub = parse_discovery(packet, source)
                    if ipaddress.IPv4Address(source[0]) not in iface.network:
                        continue
                    hubs[(hub.serial, hub.endpoint)] = hub
                except ValueError, KeyError, UnicodeError:
                    continue
                except asyncio.TimeoutError:
                    break
        except OSError:
            continue
        finally:
            sock.close()
        if hubs and len(interfaces) == 1:
            break
    return list(hubs.values())


class PushDispatcher(asyncio.DatagramProtocol):
    """One optional UDP listener per HA instance, multiple registered entries."""

    def __init__(self):
        self.entries = {}
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, source):
        try:
            headers = parse_headers(data)
            model = parse_model(headers["MODEL"])
            address = model.get("address")
            identifier = model.get("identifier", model.get("id"))
            if not address or not identifier or "value" not in model:
                return
        except ValueError, KeyError, UnicodeError:
            return
        for host, coordinator in list(self.entries.values()):
            if source[0] == host and identifier in coordinator.targets.get(address, ()):
                coordinator.request_refresh(address)

    def close(self):
        if self.transport:
            self.transport.close()
        self.entries.clear()
