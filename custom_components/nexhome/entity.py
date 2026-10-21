"""Shared state/control base; registry customization remains authoritative."""

import math

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .migration import async_complete_semantic


class NexhomeEntity(CoordinatorEntity):
    def __init__(self, runtime, spec):
        super().__init__(runtime.coordinator)
        self.runtime = runtime
        self.spec = spec
        self._attr_unique_id = spec.unique_id
        self._attr_name = spec.config.get("name")
        self._attr_has_entity_name = runtime.mode == "fresh"
        self._attr_icon = spec.config.get("icon")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, spec.device_identifier)},
            "manufacturer": "NEXhome",
            "model": f"Type {spec.type_id}",
            "name": spec.device_name,
        }
        record = runtime.plan.records.get(spec.legacy_unique_id, {})
        if spec.semantic and record.get("legacy_entity_id"):
            self._attr_suggested_object_id = record["legacy_entity_id"].split(".", 1)[1]

    def value(self, identifier, *, predicted=True):
        if not self.coordinator.is_fresh(self.spec.address, [identifier]):
            return None
        return self.coordinator.state(self.spec.address, identifier, predicted=predicted)

    def has_property(self, identifier):
        """A catalog capability is exposed only after a valid actual value was seen.

        Keep capability stable during temporary staleness; state still expires.
        """
        return (
            identifier in self.spec.identifiers and (self.spec.address, identifier) in self.coordinator.values
        )

    def number(self, identifier, *, predicted=True):
        try:
            value = float(self.value(identifier, predicted=predicted))
            return value if math.isfinite(value) else None
        except ValueError, TypeError:
            return None

    @property
    def available(self):
        fields = ("PowerSwitch",) if "PowerSwitch" in self.spec.identifiers else self.spec.identifiers
        return self.coordinator.is_fresh(self.spec.address, fields)

    @property
    def is_on(self):
        value = self.value("PowerSwitch")
        return str(value) == "1" if value is not None else None

    async def send(self, commands, **kwargs):
        before = self.coordinator.confirmed_controls
        await self.coordinator.command(self.spec.address, commands, **kwargs)
        if self.coordinator.confirmed_controls > before and not getattr(self.runtime, 'completion_verified', False):
            self.runtime.completion_verified = True
            store = getattr(self.runtime, 'completion_store', None)
            if store is not None:
                try:
                    await store.async_save({'control_readback_verified': True})
                except OSError:
                    # Evidence persistence must never turn a successful device command into failure.
                    pass

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await async_complete_semantic(self.hass, self.runtime, self.spec)


def platform_entities(entry, domain, cls):
    runtime = entry.runtime_data
    return [cls(runtime, spec) for spec in runtime.plan.specs if spec.domain == domain]
