from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.nexhome.discovery import Hub, PushDispatcher, async_discover, parse_discovery


def packet(serial="synthetic-a", host="192.0.2.10", model=None):
    model = model if model is not None else f"sn={serial}&productId=fixture"
    return (
        f"HTTP/1.1 200 OK\r\nST: nsdp:all\r\nLOCATION: http://{host}:8085\r\nMODEL: {model}\r\n\r\n".encode()
    )


def test_location_and_model_identity_exact():
    hub = parse_discovery(packet(model="sn=synthetic%2DCase&productId=fixture"), ("192.0.2.10", 1912))
    assert hub == Hub("192.0.2.10:8085", "synthetic-Case")
    assert "synthetic-Case" not in repr(hub)


@pytest.mark.parametrize(
    "body",
    [
        b"garbage",
        b"x" * 9000,
        packet(model="sn=one&sn=two"),
        packet(host="example.com"),
        packet().replace(b"http://", b"file://"),
        packet().replace(b":8085", b":8085?token=fixture"),
        packet().replace(b"MODEL:", b"LOCATION: duplicate\r\nMODEL:"),
    ],
)
def test_malformed_discovery(body):
    with pytest.raises((ValueError, KeyError)):
        parse_discovery(body, ("192.0.2.10", 1912))


class FakeSocket:
    def __init__(self):
        self.sends = []
        self.closed = False

    def setsockopt(self, *args):
        pass

    def bind(self, address):
        self.address = address

    def getsockname(self):
        return self.address[0], 45000

    def setblocking(self, value):
        pass

    def sendto(self, data, destination):
        self.sends.append((data, destination))

    def close(self):
        self.closed = True


@pytest.mark.parametrize("count", [0, 1, 2])
async def test_discovery_zero_one_multiple_and_broadcast_only(hass, count):
    sockets = []

    def factory(*args):
        obj = FakeSocket()
        sockets.append(obj)
        return obj

    received = [
        (packet(f"synthetic-{i}", f"192.0.2.{10 + i}"), (f"192.0.2.{10 + i}", 1912)) for i in range(count)
    ]
    received.extend([TimeoutError()] * 3)
    fake_module = SimpleNamespace(AF_INET=2, SOCK_DGRAM=2, SOL_SOCKET=1, SO_BROADCAST=6, socket=factory)
    adapters = [{"enabled": True, "ipv4": [{"address": "192.0.2.2", "network_prefix": 24}]}]
    with (
        patch(
            "custom_components.nexhome.discovery.network.async_get_adapters", AsyncMock(return_value=adapters)
        ),
        patch("custom_components.nexhome.discovery.socket", fake_module),
        patch.object(hass.loop, "sock_recvfrom", AsyncMock(side_effect=received)),
    ):
        hubs = await async_discover(hass)
    assert len(hubs) == count
    assert len(sockets) == (3 if not count else 1)
    assert all(s.closed and s.sends[0][1] == ("192.0.2.255", 1912) for s in sockets)
    assert all(b"MODEL:sn=" not in s.sends[0][0] for s in sockets)


def test_push_validation_and_source_filter():
    coordinator = SimpleNamespace(
        targets={"fixture-device": {"PowerSwitch"}}, request_refresh=lambda address: calls.append(address)
    )
    calls = []
    dispatcher = PushDispatcher()
    dispatcher.entries["fixture-entry"] = ("192.0.2.10", coordinator)
    push = b"NOTIFY * HTTP/1.1\r\nMODEL: value=1&identifier=PowerSwitch&address=fixture-device\r\n\r\n"
    dispatcher.datagram_received(b"bad", ("192.0.2.10", 1912))
    dispatcher.datagram_received(push, ("192.0.2.11", 1912))
    dispatcher.datagram_received(push.replace(b"value=1", b"value=1&value=2"), ("192.0.2.10", 1912))
    assert calls == []
    dispatcher.datagram_received(push, ("192.0.2.10", 1912))
    assert calls == ["fixture-device"]
