"""Offline fixtures. Every device, identity and endpoint is synthetic."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.nexhome.coordinator import GatewayCoordinator
from custom_components.nexhome.errors import GatewayError
from custom_components.nexhome.migration import CompatibilityPlan
from custom_components.nexhome.models import descriptions

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


class Clock:
    now = 100.0

    def __call__(self):
        return self.now

    def advance(self, value=0.01):
        self.now += value


class FakeGateway:
    def __init__(self, clock):
        self.clock = clock
        self.values = {}
        self.reads = []
        self.commands = []
        self.failed = False
        self.stats = {"requests": 0, "errors": 0, "timeouts": 0}

    async def properties(self, params):
        self.reads.append(params)
        self.clock.advance()
        if self.failed:
            raise GatewayError("Synthetic timeout")
        return [{**p, "value": self.values.get((p["address"], p["identifier"]))} for p in params]

    async def control(self, address, command):
        self.commands.append((address, command))
        self.clock.advance()
        self.values[(address, command["identifier"])] = command["value"]

    async def close(self):
        pass


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def gateway(clock):
    return FakeGateway(clock)


@pytest.fixture
async def coordinator(hass, gateway, clock):
    obj = GatewayCoordinator(hass, gateway, clock=clock)
    yield obj
    await obj.async_shutdown()


def device(type_id="1", index="a"):
    return {
        "id": f"fixture-id-{index}",
        "address": f"fixture-address-{index}",
        "name": f"Fixture device {index}",
        "type": type_id,
    }


def runtime_for(coordinator, type_id="1", mode="fresh"):
    spec = descriptions([device(type_id)], "synthetic-gateway", mode)[0]
    coordinator.register(spec.address, spec.identifiers)
    return SimpleNamespace(
        coordinator=coordinator, mode=mode, plan=CompatibilityPlan([spec], {}), markers={}, store=AsyncMock()
    ), spec
