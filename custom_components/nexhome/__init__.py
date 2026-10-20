"""NEXhome Community Candidate. No installer, updater or household customization."""

import asyncio
import hashlib
import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import GatewayClient, validate_endpoint
from .const import DOMAIN, IP_CONFIG, PLATFORMS, SN_CONFIG
from .coordinator import GatewayCoordinator
from .discovery import PushDispatcher
from .errors import GatewayError
from .migration import plan_compatibility, related_wrappers
from .models import descriptions

LOGGER = logging.getLogger(__name__)


@dataclass
class Runtime:
    client: GatewayClient
    coordinator: GatewayCoordinator
    mode: str
    plan: object
    markers: dict
    store: Store
    gateway_key: str


async def async_migrate_entry(hass, entry):
    """Only additive, version-checked metadata. Never delete user fields/options."""
    if entry.version != 1 or entry.minor_version > 2:
        return False
    if entry.minor_version == 2:
        return True
    data = dict(entry.data)
    if SN_CONFIG not in data and isinstance(data.get("sn"), str):
        data[SN_CONFIG] = data["sn"]
    if not isinstance(data.get(SN_CONFIG), str) or not isinstance(data.get(IP_CONFIG), str):
        return False
    data.setdefault("identity_mode", "compat")
    hass.config_entries.async_update_entry(entry, data=data, minor_version=2)
    return True


async def async_setup_entry(hass, entry: ConfigEntry):
    serial, endpoint = entry.data.get(SN_CONFIG), entry.data.get(IP_CONFIG)
    if not isinstance(serial, str) or not serial or not isinstance(endpoint, str):
        raise ConfigEntryError("Missing local gateway configuration")
    try:
        endpoint = validate_endpoint(endpoint)
    except GatewayError:
        raise ConfigEntryError("Invalid local gateway endpoint") from None
    root = hass.data.setdefault(DOMAIN, {"gateways": {}, "push": None, "push_lock": asyncio.Lock()})
    key = hashlib.sha256(serial.encode()).hexdigest()
    if key in root["gateways"]:
        raise ConfigEntryError("This gateway is already loaded by another entry")
    root["gateways"][key] = entry.entry_id
    client = GatewayClient(endpoint, serial, async_get_clientsession(hass))
    coordinator = GatewayCoordinator(hass, client, entry=entry)
    try:
        await client.login()
        devices = await client.devices()
        mode = entry.data.get("identity_mode", "compat")
        if mode not in {"fresh", "compat"}:
            raise ConfigEntryError("Unknown identity mode; refusing an implicit migration")
        selected = set(entry.data.get("filter_devices", []))
        filter_mode = entry.data.get("filter_mode", "exclude")
        if selected:
            devices = [
                d
                for d in devices
                if isinstance(d, dict) and ((d.get("id") in selected) == (filter_mode == "include"))
            ]
        specs = descriptions(devices, serial, mode)
        registry = er.async_get(hass)
        rows = er.async_entries_for_config_entry(registry, entry.entry_id)
        store = Store(hass, 1, f"nexhome.semantic.{entry.entry_id}")
        markers = await store.async_load() or {}
        if not isinstance(markers, dict) or any(not isinstance(v, dict) for v in markers.values()):
            raise ConfigEntryError("Invalid local migration metadata")
        plan = (
            plan_compatibility(specs, rows, markers, related_wrappers(hass))
            if mode == "compat"
            else plan_compatibility(specs, [], {})
        )
        devices_registry = dr.async_get(hass)
        for spec in plan.specs:
            existing = devices_registry.async_get_devices(identifiers={(DOMAIN, spec.device_identifier)})
            if any(device.config_entries - {entry.entry_id} for device in existing):
                raise ConfigEntryError("Device identity conflicts with another entry; manual review needed")
            coordinator.register(spec.address, spec.identifiers)
        await coordinator.async_refresh()
        if specs and not coordinator.values:
            raise ConfigEntryNotReady("No valid gateway properties available")
        entry.runtime_data = Runtime(client, coordinator, mode, plan, markers, store, key)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        if entry.options.get("udp_refresh", True):
            async with root["push_lock"]:
                if root["push"] is None:
                    dispatcher = PushDispatcher()
                    try:
                        await hass.loop.create_datagram_endpoint(
                            lambda: dispatcher, local_addr=("0.0.0.0", 1912)
                        )
                    except OSError:
                        LOGGER.warning("UDP refresh listener unavailable; polling remains active")
                    else:
                        root["push"] = dispatcher
                if root["push"] is not None:
                    root["push"].entries[entry.entry_id] = (client.endpoint.rsplit(":", 1)[0], coordinator)
        return True
    except GatewayError:
        await coordinator.async_shutdown()
        root["gateways"].pop(key, None)
        raise ConfigEntryNotReady("Gateway initialization failed") from None
    except BaseException:
        await coordinator.async_shutdown()
        root["gateways"].pop(key, None)
        raise


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    runtime = entry.runtime_data
    await runtime.coordinator.async_shutdown()
    root = hass.data[DOMAIN]
    async with root["push_lock"]:
        if root["push"]:
            root["push"].entries.pop(entry.entry_id, None)
            if not root["push"].entries:
                root["push"].close()
                root["push"] = None
    root["gateways"].pop(runtime.gateway_key, None)
    return True
