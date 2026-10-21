from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nexhome import async_migrate_entry
from custom_components.nexhome.diagnostics import async_get_config_entry_diagnostics
from custom_components.nexhome.errors import GatewayError
from custom_components.nexhome.models import descriptions

from .conftest import device


def config_entry(**kwargs):
    return MockConfigEntry(
        domain="nexhome",
        version=1,
        minor_version=2,
        data={"ip_address": "192.0.2.10:8085", "sn_input": "synthetic-gateway", "identity_mode": "fresh"},
        options={"udp_refresh": False},
        **kwargs,
    )


async def test_real_ha_setup_reload_no_duplicate_and_no_diagnostics_secrets(hass, gateway):
    entry = config_entry()
    entry.add_to_hass(hass)
    gateway.login = AsyncMock()
    gateway.devices = AsyncMock(
        return_value=[device("1"), device("133", "b"), device("3", "c"), device("6", "d"), device("5", "e")]
    )
    gateway.endpoint = "192.0.2.10:8085"
    gateway.scheduler = SimpleNamespace(control=[], poll=[], inflight=0, rejected=0)
    gateway.stats["token"] = "synthetic-private-value"
    for d in await gateway.devices():
        for key, value in {
            "PowerSwitch": "0",
            "TemperatureSet": "24",
            "WorkMode": "0",
            "Temperature": "20",
            "Humidity": "40",
            "Open": "1",
            "Close": "1",
            "Stop": "1",
        }.items():
            gateway.values[(d["address"], key)] = value
    with patch("custom_components.nexhome.GatewayClient", return_value=gateway):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        before = {
            (r.entity_id, r.unique_id, r.device_id)
            for r in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        assert {
            r.entity_id.split(".")[0] for r in er.async_entries_for_config_entry(registry, entry.entry_id)
        } == {"light", "fan", "climate", "cover", "sensor"}
        diag = await async_get_config_entry_diagnostics(hass, entry)
        assert diag["product_version"] == "0.1.0"
        assert diag["upstream_base_version"] == "1.1.16"
        encoded = str(diag)
        for sensitive in [
            "synthetic-gateway",
            "192.0.2.10",
            "fixture-address",
            "fixture-id",
            "Fixture device",
            "synthetic-private-value",
        ]:
            assert sensitive not in encoded
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        after = {
            (r.entity_id, r.unique_id, r.device_id)
            for r in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        assert before == after
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_migration_additive_idempotent_failure_safe(hass):
    entry = MockConfigEntry(
        domain="nexhome",
        version=1,
        minor_version=1,
        data={"ip_address": "192.0.2.10:8085", "sn_input": "synthetic-gateway", "custom": "keep"},
    )
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    first = dict(entry.data)
    assert first["custom"] == "keep" and first["identity_mode"] == "compat"
    assert await async_migrate_entry(hass, entry) and dict(entry.data) == first
    bad = MockConfigEntry(domain="nexhome", version=1, minor_version=1, data={"custom": "untouched"})
    bad.add_to_hass(hass)
    assert not await async_migrate_entry(hass, bad)
    assert dict(bad.data) == {"custom": "untouched"} and bad.minor_version == 1


async def test_real_registry_legacy_owned_hidden_and_user_customization(hass, gateway):
    entry = MockConfigEntry(
        domain="nexhome",
        version=1,
        minor_version=2,
        data={"ip_address": "192.0.2.10:8085", "sn_input": "synthetic-gateway", "identity_mode": "compat"},
        options={"udp_refresh": False},
    )
    entry.add_to_hass(hass)
    devices = [device("1", index) for index in ("a", "b", "c")]
    specs = descriptions(devices, "synthetic-gateway", "compat")
    registry = er.async_get(hass)
    rows = [
        registry.async_get_or_create(
            "switch", "nexhome", spec.unique_id, suggested_object_id=f"fixture_{i}", config_entry=entry
        )
        for i, spec in enumerate(specs)
    ]
    registry.async_update_entity(rows[1].entity_id, hidden_by=er.RegistryEntryHider.USER)
    registry.async_update_entity(rows[2].entity_id, name="User fixture name")
    gateway.login = AsyncMock()
    gateway.devices = AsyncMock(return_value=devices)
    await Store(hass, 1, f'nexhome.semantic.{entry.entry_id}').async_save({
        specs[0].unique_id: {'owner': 'nexhome', 'approved_semantic': True,
                             'legacy_entity_id': rows[0].entity_id}
    })
    for d in devices:
        gateway.values[(d["address"], "PowerSwitch")] = "0"
    with patch("custom_components.nexhome.GatewayClient", return_value=gateway):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        loaded = er.async_entries_for_config_entry(registry, entry.entry_id)
        assert len(loaded) == 4 and sum(r.domain == "light" for r in loaded) == 1, (
            entry.runtime_data.plan.records
        )
        assert registry.async_get(rows[0].entity_id).hidden_by == er.RegistryEntryHider.INTEGRATION
        assert registry.async_get(rows[0].entity_id).disabled_by is None
        assert registry.async_get(rows[1].entity_id).hidden_by == er.RegistryEntryHider.USER
        assert registry.async_get(rows[2].entity_id).name == "User fixture name"
        before = {(r.entity_id, r.unique_id) for r in loaded}
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert before == {
            (r.entity_id, r.unique_id) for r in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        assert entry.runtime_data.plan.records[specs[0].unique_id]["status"] == "owned_semantic_reused"
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_invalid_endpoint_does_not_reserve_gateway(hass):
    entry = MockConfigEntry(
        domain="nexhome",
        version=1,
        minor_version=2,
        data={"ip_address": "invalid", "sn_input": "synthetic-gateway"},
    )
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert not hass.data.get("nexhome", {}).get("gateways")


async def test_failed_setup_cleans_gateway_and_client(hass, gateway):
    entry = config_entry()
    entry.add_to_hass(hass)
    gateway.login = AsyncMock(side_effect=GatewayError("Synthetic unavailable"))
    gateway.close = AsyncMock()
    with patch("custom_components.nexhome.GatewayClient", return_value=gateway):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    gateway.close.assert_awaited_once()
    assert not hass.data["nexhome"]["gateways"]
