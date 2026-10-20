"""Read-only sensor properties with honest missing/stale values."""

from homeassistant.components.sensor import SensorEntity

from .entity import NexhomeEntity, platform_entities


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(platform_entities(entry, "sensor", NexhomeSensor))


class NexhomeSensor(NexhomeEntity, SensorEntity):
    def __init__(self, runtime, spec):
        super().__init__(runtime, spec)
        self._attr_native_unit_of_measurement = spec.config.get("unit")
        self._attr_device_class = spec.config.get("device_class")
        self._attr_state_class = spec.config.get("state_class")

    @property
    def native_value(self):
        return self.number(self.spec.identifiers[0], predicted=False)
