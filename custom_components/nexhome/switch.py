"""Real switches and preserved legacy control endpoints, never disabled automatically."""

from homeassistant.components.switch import SwitchEntity

from .entity import NexhomeEntity, platform_entities


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(platform_entities(entry, "switch", NexhomeSwitch))


class NexhomeSwitch(NexhomeEntity, SwitchEntity):
    async def async_turn_on(self, **kwargs):
        await self.send([{"identifier": "PowerSwitch", "value": "1"}])

    async def async_turn_off(self, **kwargs):
        await self.send([{"identifier": "PowerSwitch", "value": "0"}])
