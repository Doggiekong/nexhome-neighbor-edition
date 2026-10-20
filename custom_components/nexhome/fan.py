"""Protocol-classified fans; no invented percentage range."""

from homeassistant.components.fan import FanEntity, FanEntityFeature

from .entity import NexhomeEntity, platform_entities
from .errors import GatewayError

FAN_MODES = {"0": "自动", "1": "低速", "2": "中速", "3": "高速"}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(platform_entities(entry, "fan", NexhomeFan))


class NexhomeFan(NexhomeEntity, FanEntity):
    @property
    def modes(self):
        if not self.has_property("Windspeed"):
            return {}
        return {"1": "低速", "3": "高速"} if self.spec.type_id == "133" else FAN_MODES

    @property
    def supported_features(self):
        flags = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        return flags | FanEntityFeature.PRESET_MODE if self.modes else flags

    @property
    def preset_modes(self):
        return list(self.modes.values()) or None

    @property
    def preset_mode(self):
        return self.modes.get(str(self.value("Windspeed")))

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        if percentage is not None:
            raise GatewayError("This fan does not provide percentage speed")
        commands = [{"identifier": "PowerSwitch", "value": "1"}]
        if preset_mode is not None:
            commands.append(self._mode_command(preset_mode))
        await self.send(commands)

    async def async_turn_off(self, **kwargs):
        await self.send([{"identifier": "PowerSwitch", "value": "0"}])

    def _mode_command(self, mode):
        code = next((k for k, v in self.modes.items() if v == mode), None)
        if code is None:
            raise GatewayError("Unsupported fan preset")
        return {"identifier": "Windspeed", "value": code}

    async def async_set_preset_mode(self, preset_mode):
        await self.send([self._mode_command(preset_mode)])
