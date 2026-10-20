from types import SimpleNamespace

import pytest
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.helpers import entity_registry as er

from custom_components.nexhome.climate import NexhomeClimate
from custom_components.nexhome.cover import NexhomeCover
from custom_components.nexhome.errors import GatewayError
from custom_components.nexhome.fan import NexhomeFan
from custom_components.nexhome.light import NexhomeLight
from custom_components.nexhome.migration import plan_compatibility
from custom_components.nexhome.models import descriptions

from .conftest import device, runtime_for


@pytest.mark.parametrize(
    "type_id,domain",
    [
        ("1", "light"),
        ("2", "light"),
        ("51", "light"),
        ("133", "fan"),
        ("75", "fan"),
        ("3", "climate"),
        ("11", "climate"),
        ("6", "cover"),
        ("5", "sensor"),
        ("132", "switch"),
    ],
)
def test_fresh_semantics_are_protocol_driven_and_stable(type_id, domain):
    specs = descriptions([device(type_id)], "synthetic-gateway", "fresh")
    assert specs and all(s.domain == domain for s in specs)
    renamed = device(type_id) | {"name": "A completely different fixture label"}
    again = descriptions([renamed], "synthetic-gateway", "fresh")
    assert [(s.unique_id, s.device_identifier) for s in specs] == [
        (s.unique_id, s.device_identifier) for s in again
    ]


def row(spec, **kwargs):
    defaults = {
        "domain": "switch",
        "unique_id": spec.unique_id,
        "entity_id": "switch.fixture_legacy",
        "hidden_by": None,
        "disabled_by": None,
        "name": None,
        "icon": None,
        "area_id": None,
        "aliases": set(),
        "labels": set(),
    }
    return SimpleNamespace(**(defaults | kwargs))


def test_visible_legacy_preserved_and_semantic_predictable():
    spec = descriptions([device()], "synthetic-gateway", "compat")[0]
    legacy = row(spec)
    one = plan_compatibility([spec], [legacy], {})
    two = plan_compatibility([spec], [legacy], {})
    assert [s.domain for s in one.specs] == ["switch", "light"]
    assert one.specs == two.specs and one.specs[0].unique_id == spec.unique_id
    assert one.specs[0].device_identifier == one.specs[1].device_identifier


@pytest.mark.parametrize(
    "customization",
    [
        {"hidden_by": er.RegistryEntryHider.USER},
        {"name": "Fixture custom name"},
        {"disabled_by": er.RegistryEntryDisabler.USER},
        {"area_id": "fixture-area"},
        {"icon": "mdi:star"},
        {"hidden_by": er.RegistryEntryHider.INTEGRATION},
    ],
)
def test_manual_intent_never_creates_duplicate(customization):
    spec = descriptions([device()], "synthetic-gateway", "compat")[0]
    result = plan_compatibility([spec], [row(spec, **customization)], {})
    assert result.specs == [spec]


def test_explicit_wrapper_link_skips_semantic():
    spec = descriptions([device()], "synthetic-gateway", "compat")[0]
    result = plan_compatibility([spec], [row(spec)], {}, {"switch.fixture_legacy"})
    assert len(result.specs) == 1


def test_integration_owned_hidden_is_not_user_hidden():
    spec = descriptions([device()], "synthetic-gateway", "compat")[0]
    legacy = row(spec, hidden_by=er.RegistryEntryHider.INTEGRATION)
    uid = spec.unique_id + ":semantic:light:v1"
    semantic = row(spec, domain="light", unique_id=uid, entity_id="light.fixture_semantic")
    markers = {spec.unique_id: {"semantic_unique_id": uid, "owner": "nexhome"}}
    result = plan_compatibility([spec], [legacy, semantic], markers)
    assert len(result.specs) == 2 and result.records[spec.unique_id]["status"] == "owned_semantic_reused"
    markers[spec.unique_id]["owner"] = "unrelated"
    assert len(plan_compatibility([spec], [legacy, semantic], markers).specs) == 1


def test_existing_legacy_fan_has_same_compatibility_policy():
    spec = descriptions([device("133")], "synthetic-gateway", "compat")[0]
    result = plan_compatibility([spec], [row(spec)], {})
    assert [s.domain for s in result.specs] == ["switch", "fan"]
    skipped = plan_compatibility([spec], [row(spec, hidden_by=er.RegistryEntryHider.USER)], {})
    assert [s.domain for s in skipped.specs] == ["switch"]


async def test_explicit_lamp_on_is_not_skipped(coordinator, gateway):
    runtime, spec = runtime_for(coordinator)
    gateway.values[(spec.address, "PowerSwitch")] = "1"
    await coordinator.read()
    entity = NexhomeLight(runtime, spec)
    assert entity.is_on
    await entity.async_turn_on()
    await entity.async_turn_off()
    assert [c[1]["value"] for c in gateway.commands] == ["1", "0"]


@pytest.mark.parametrize("type_id,off", [("3", 0), ("11", "0"), ("73", "0"), ("35", "0")])
async def test_climate_optional_temperature_and_scoped_numeric_off(coordinator, gateway, type_id, off):
    runtime, spec = runtime_for(coordinator, type_id)
    for key, value in {"PowerSwitch": "1", "TemperatureSet": "24", "WorkMode": "0"}.items():
        gateway.values[(spec.address, key)] = value
    await coordinator.read()
    entity = NexhomeClimate(runtime, spec)
    assert entity.available and entity.current_temperature is None
    await entity.async_turn_off()
    assert gateway.commands[-1][1]["value"] == off
    assert type(gateway.commands[-1][1]["value"]) is type(off)


async def test_climate_required_stale_unavailable(coordinator, gateway, clock):
    runtime, spec = runtime_for(coordinator, "3")
    for key, value in {"PowerSwitch": "1", "TemperatureSet": "24", "WorkMode": "0"}.items():
        gateway.values[(spec.address, key)] = value
    await coordinator.read()
    entity = NexhomeClimate(runtime, spec)
    assert entity.available
    clock.advance(16)
    assert not entity.available and entity.current_temperature is None


async def test_cover_without_location_honest_unknown_and_readback_only(coordinator, gateway):
    runtime, spec = runtime_for(coordinator, "6")
    for key in ["Open", "Close", "Stop"]:
        gateway.values[(spec.address, key)] = "1"
    await coordinator.read()
    entity = NexhomeCover(runtime, spec)
    assert entity.available and entity.current_cover_position is None and entity.is_closed is None
    assert not entity.supported_features & CoverEntityFeature.SET_POSITION
    await entity.async_open_cover()
    await entity.async_close_cover()
    await entity.async_stop_cover()
    assert entity.confirmation == "core_readback_only" and entity.is_closed is None
    with pytest.raises(GatewayError):
        await entity.async_set_cover_position(position=50)


async def test_cover_real_position_and_unsupported_stop(coordinator, gateway):
    runtime, spec = runtime_for(coordinator, "6")
    gateway.values[(spec.address, "Location")] = 100
    await coordinator.read()
    entity = NexhomeCover(runtime, spec)
    assert entity.current_cover_position == 100 and not entity.is_closed
    await entity.async_set_cover_position(position=50)
    assert entity.current_cover_position == 50 and entity.confirmation == "position_observed"
    other_runtime, other_spec = runtime_for(coordinator, "30")
    other = NexhomeCover(other_runtime, other_spec)
    with pytest.raises(GatewayError):
        await other.async_stop_cover()


async def test_cover_wrong_direction_is_not_confirmation(coordinator, gateway):
    runtime, spec = runtime_for(coordinator, "6")
    gateway.values[(spec.address, "Location")] = 50
    await coordinator.read()
    entity = NexhomeCover(runtime, spec)
    outcomes = []

    async def inspect_send(commands, **kwargs):
        for position in (49, 51):
            gateway.values[(spec.address, "Location")] = position
            await coordinator.read()
            outcomes.append(kwargs["verdict"](0))

    entity.send = inspect_send
    await entity.async_open_cover()
    assert outcomes == [False, True]


async def test_optional_capabilities_require_actual_properties(coordinator, gateway):
    runtime, spec = runtime_for(coordinator, "51")
    gateway.values[(spec.address, "PowerSwitch")] = "1"
    await coordinator.read()
    light = NexhomeLight(runtime, spec)
    assert {mode.value for mode in light.supported_color_modes} == {"onoff"}
    with pytest.raises(GatewayError):
        await light.async_turn_on(brightness=100)
    assert not gateway.commands
    gateway.values[(spec.address, "Brightness")] = 100
    gateway.values[(spec.address, "ColorTem")] = 3000
    await coordinator.read()
    assert {mode.value for mode in light.supported_color_modes} == {"color_temp"}
    await light.async_turn_on(brightness=200, color_temp_kelvin=4000)
    assert light.brightness == 200 and light.color_temp_kelvin == 4000


async def test_fan_ordered_control_and_no_fake_percentage(coordinator, gateway):
    runtime, spec = runtime_for(coordinator, "133")
    gateway.values[(spec.address, "PowerSwitch")] = "0"
    gateway.values[(spec.address, "Windspeed")] = "1"
    await coordinator.read()
    fan = NexhomeFan(runtime, spec)
    await fan.async_turn_on(preset_mode="高速")
    assert fan.is_on and fan.preset_mode == "高速"
    await fan.async_set_preset_mode("低速")
    await fan.async_turn_off()
    assert not fan.is_on
    count = len(gateway.commands)
    with pytest.raises(GatewayError):
        await fan.async_turn_on(percentage=50)
    assert len(gateway.commands) == count


async def test_climate_setting_controls_and_optional_swing(coordinator, gateway):
    runtime, spec = runtime_for(coordinator, "73")
    for key, value in {
        "PowerSwitch": "1",
        "TemperatureSet": "24",
        "WorkMode": "0",
        "Windspeed": "1",
        "WindDirection": "10",
    }.items():
        gateway.values[(spec.address, key)] = value
    await coordinator.read()
    entity = NexhomeClimate(runtime, spec)
    await entity.async_set_temperature(temperature=25)
    await entity.async_set_hvac_mode("heat")
    await entity.async_set_fan_mode("高速")
    await entity.async_set_swing_mode("下")
    assert entity.target_temperature == 25 and entity.hvac_mode == "heat"
    assert entity.fan_mode == "高速" and entity.swing_mode == "下"
    with pytest.raises(GatewayError):
        await entity.async_set_temperature(temperature=float("nan"))
