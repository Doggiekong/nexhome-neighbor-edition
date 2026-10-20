"""Momentary command acknowledgements are not physical curtain states."""

from homeassistant.components.cover import CoverEntity, CoverEntityFeature

from .entity import NexhomeEntity, platform_entities
from .errors import GatewayError


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(platform_entities(entry, "cover", NexhomeCover))


class NexhomeCover(NexhomeEntity, CoverEntity):
    confirmation = None

    @property
    def core_fields(self):
        return ["Open", "Close"] + ([] if self.spec.type_id == "30" else ["Stop"])

    @property
    def current_cover_position(self):
        value = self.number("Location", predicted=False) if self.spec.type_id == "6" else None
        return value if value is not None and 0 <= value <= 100 else None

    def _core_fresh(self, after=0):
        return self.coordinator.is_fresh(self.spec.address, self.core_fields, after=after) and all(
            str(self.value(i, predicted=False)) == "1" for i in self.core_fields
        )

    @property
    def available(self):
        return self.current_cover_position is not None or self._core_fresh()

    @property
    def is_closed(self):
        position = self.current_cover_position
        return position == 0 if position is not None else None

    @property
    def supported_features(self):
        flags = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        if self.spec.type_id != "30":
            flags |= CoverEntityFeature.STOP
        if self.current_cover_position is not None:
            flags |= CoverEntityFeature.SET_POSITION
        return flags

    async def _control(self, identifier, value):
        previous = self.current_cover_position
        target = {"Open": 100, "Close": 0}.get(identifier, value)
        self.confirmation = None

        def verdict(after):
            position = self.current_cover_position
            if (
                identifier != "Stop"
                and position is not None
                and self.coordinator.is_fresh(self.spec.address, ["Location"], after=after)
            ):
                if abs(position - target) <= 1 or (previous is not None and abs(position - previous) >= 1):
                    self.confirmation = "position_observed"
                    return True
            if self._core_fresh(after) and (previous is None or identifier == "Stop"):
                self.confirmation = "core_readback_only"
                return None  # Transport/readback only, explicitly not physical confirmation.
            return False

        await self.send(
            [{"identifier": identifier, "value": value}],
            attempts=6,
            interval=0.8,
            verdict=verdict,
            confirmation_timeout=5,
        )

    async def async_open_cover(self, **kwargs):
        await self._control("Open", 1)

    async def async_close_cover(self, **kwargs):
        await self._control("Close", 1)

    async def async_stop_cover(self, **kwargs):
        if self.spec.type_id == "30":
            raise GatewayError("This cover has no stop capability")
        await self._control("Stop", 1)

    async def async_set_cover_position(self, **kwargs):
        value = kwargs.get("position")
        if (
            self.current_cover_position is None
            or isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 100
        ):
            raise GatewayError("No readable position capability or invalid position")
        await self._control("Location", value)
