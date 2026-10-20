import asyncio

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.nexhome.errors import GatewayError, QueueFull


async def test_shared_chunking_partial_and_recovery(coordinator, gateway):
    for n in range(150):
        coordinator.register("fixture-address", [f"field-{n}"])
        gateway.values[("fixture-address", f"field-{n}")] = n
    data = await coordinator._async_update_data()
    assert len(data) == 150 and [len(p) for p in gateway.reads] == [64, 64, 22]
    gateway.failed = True
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    gateway.failed = False
    assert len(await coordinator._async_update_data()) == 150


async def test_missing_optional_still_publishes_valid_subset(coordinator, gateway):
    coordinator.register("fixture-address", ["PowerSwitch", "Temperature"], required_groups=[{"PowerSwitch"}])
    gateway.values[("fixture-address", "PowerSwitch")] = "1"
    for _ in range(2):
        await coordinator._async_update_data()
    assert coordinator.is_fresh("fixture-address", ["PowerSwitch"])
    assert not coordinator.is_fresh("fixture-address", ["Temperature"])
    assert coordinator.data[("fixture-address", "PowerSwitch")] == "1"


async def test_stale_query_and_bad_rows_rejected(coordinator, clock):
    coordinator.register("fixture-address", ["PowerSwitch"])
    params = [{"address": "fixture-address", "identifier": "PowerSwitch"}]
    coordinator.protected["fixture-address"] = 101
    coordinator.apply_rows([{**params[0], "value": "1"}], params, 100)
    assert not coordinator.values
    coordinator.apply_rows(
        [{"address": [], "identifier": "PowerSwitch", "value": 1}, {**params[0], "value": "bad"}], params, 102
    )
    assert not coordinator.values
    clock.advance(2)
    coordinator.apply_rows([{**params[0], "value": "0"}], params, 102)
    assert coordinator.values[("fixture-address", "PowerSwitch")] == "0"


async def test_pending_expiry_is_not_permanent_prediction(coordinator, clock):
    key = ("fixture-address", "PowerSwitch")
    coordinator.values[key] = "0"
    coordinator.pending[key] = ("1", clock() + 5)
    assert coordinator.state(*key) == "1"
    clock.advance(6)
    coordinator.expire_pending()
    assert coordinator.state(*key) == "0" and not coordinator.pending


async def test_same_device_commands_order_and_directed_readback(coordinator, gateway):
    coordinator.register("fixture-address", ["PowerSwitch"])
    await asyncio.gather(
        coordinator.command("fixture-address", [{"identifier": "PowerSwitch", "value": "1"}]),
        coordinator.command("fixture-address", [{"identifier": "PowerSwitch", "value": "0"}]),
    )
    assert [c[1]["value"] for c in gateway.commands] == ["1", "0"]
    assert len(gateway.reads) == 2 and coordinator.values[("fixture-address", "PowerSwitch")] == "0"
    assert not coordinator.pending and coordinator.waiting == 0


async def test_confirmation_failure_never_resends(coordinator, gateway):
    coordinator.register("fixture-address", ["PowerSwitch"])
    gateway.failed = True
    with pytest.raises(GatewayError):
        await coordinator.command("fixture-address", [{"identifier": "PowerSwitch", "value": "1"}])
    assert len(gateway.commands) == 1 and not coordinator.pending


async def test_command_queue_bound(coordinator):
    coordinator.register("fixture-address", ["PowerSwitch"])
    coordinator.waiting = 32
    with pytest.raises(QueueFull):
        await coordinator.command("fixture-address", [{"identifier": "PowerSwitch", "value": "1"}])


async def test_push_debounce_never_applies_payload(coordinator, gateway):
    coordinator.register("fixture-address", ["PowerSwitch"])
    gateway.values[("fixture-address", "PowerSwitch")] = "0"
    for _ in range(10):
        coordinator.request_refresh("fixture-address")
    await asyncio.gather(*list(coordinator.push_tasks.values()))
    assert len(gateway.reads) == 1 and coordinator.state("fixture-address", "PowerSwitch") == "0"


async def test_required_missing_fails_then_recovers(coordinator, gateway):
    coordinator.register("fixture-address", ["PowerSwitch", "Temperature"], required_groups=[{"PowerSwitch"}])
    gateway.values[("fixture-address", "Temperature")] = 20
    with pytest.raises(UpdateFailed, match="Required"):
        await coordinator._async_update_data()
    gateway.values[("fixture-address", "PowerSwitch")] = "1"
    assert await coordinator._async_update_data()


async def test_cover_alternative_core_sets_and_separate_sensor_requirements(coordinator, gateway):
    coordinator.register(
        "cover",
        ["Location", "Open", "Close", "Stop"],
        required_groups=[{"Location"}, {"Open", "Close", "Stop"}],
    )
    gateway.values[("cover", "Location")] = 50
    assert await coordinator._async_update_data()
    gateway.values.pop(("cover", "Location"))
    for key in ("Open", "Close", "Stop"):
        gateway.values[("cover", key)] = 1
    assert await coordinator._async_update_data()
    coordinator.register("sensor", ["Temperature"], required_groups=[{"Temperature"}])
    coordinator.register("sensor", ["Humidity"], required_groups=[{"Humidity"}])
    gateway.values[("sensor", "Temperature")] = 20
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_cancelled_command_clears_pending_and_releases_device_lock(coordinator, gateway):
    coordinator.register("fixture-address", ["PowerSwitch"])
    entered, gate = asyncio.Event(), asyncio.Event()
    original = gateway.properties

    async def blocked(params):
        entered.set()
        await gate.wait()
        return await original(params)

    gateway.properties = blocked
    task = asyncio.create_task(
        coordinator.command("fixture-address", [{"identifier": "PowerSwitch", "value": "1"}])
    )
    await entered.wait()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert not coordinator.pending and coordinator.waiting == 0
    gateway.properties = original
    await coordinator.command("fixture-address", [{"identifier": "PowerSwitch", "value": "0"}])
    assert coordinator.state("fixture-address", "PowerSwitch") == "0"
