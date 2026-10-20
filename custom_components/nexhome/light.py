"""Native lights, including on/off lamps formerly exposed as switches."""

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN, ColorMode, LightEntity

from .entity import NexhomeEntity, platform_entities
from .errors import GatewayError


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(platform_entities(entry, "light", NexhomeLight))


class NexhomeLight(NexhomeEntity, LightEntity):
    @property
    def supported_color_modes(self):
        if self.has_property("ColorTem") and self.has_property("Brightness"):
            return {ColorMode.COLOR_TEMP}
        if self.has_property("Brightness"):
            return {ColorMode.BRIGHTNESS}
        return {ColorMode.ONOFF}

    @property
    def color_mode(self):
        return next(iter(self.supported_color_modes))

    @property
    def brightness(self):
        value = self.number("Brightness")
        return round(value) if value is not None and 0 <= value <= 255 else None

    @property
    def color_temp_kelvin(self):
        value = self.number("ColorTem")
        return int(value) if value is not None and 2000 <= value <= 6500 else None

    _attr_min_color_temp_kelvin = 2000
    _attr_max_color_temp_kelvin = 6500

    async def async_turn_on(self, **kwargs):
        commands = [{"identifier": "PowerSwitch", "value": "1"}]
        for key, identifier, low, high in [
            (ATTR_BRIGHTNESS, "Brightness", 0, 255),
            (ATTR_COLOR_TEMP_KELVIN, "ColorTem", 2000, 6500),
        ]:
            if key in kwargs:
                value = kwargs[key]
                if (
                    not self.has_property(identifier)
                    or isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not low <= value <= high
                ):
                    raise GatewayError("Unsupported or invalid light parameter")
                commands.append({"identifier": identifier, "value": int(value)})
        await self.send(commands)  # Explicit ON is never skipped because of cached state.

    async def async_turn_off(self, **kwargs):
        await self.send([{"identifier": "PowerSwitch", "value": "0"}])
