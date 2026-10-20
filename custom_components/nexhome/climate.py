"""Climate core/optional fields and model-scoped OFF compatibility."""

import math

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from .entity import NexhomeEntity, platform_entities
from .errors import GatewayError

MODES = {
    "0": HVACMode.COOL,
    "1": HVACMode.HEAT,
    "2": HVACMode.DRY,
    "3": HVACMode.FAN_ONLY,
    "4": HVACMode.AUTO,
}
FANS = {
    "0": "自动",
    "1": "低速",
    "2": "中速",
    "3": "高速",
    "4": "超静",
    "5": "超强",
    "6": "中低",
    "7": "中高",
}
DIRECTIONS = {"10": "摆动", "11": "上", "12": "中", "13": "下"}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(platform_entities(entry, "climate", NexhomeClimate))


class NexhomeClimate(NexhomeEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 16
    _attr_max_temp = 30
    _attr_target_temperature_step = 1

    @property
    def heating_only(self):
        return self.spec.type_id in {"11", "35"}

    @property
    def fan_map(self):
        if self.heating_only or not self.has_property("Windspeed"):
            return {}
        allowed = {
            "100": {"0", "1", "3"},
            "101": {"0", "1", "2", "3", "4", "5"},
            "107": {"0", "1", "2", "3"},
        }.get(self.spec.type_id, set(FANS))
        return {k: v for k, v in FANS.items() if k in allowed}

    @property
    def required(self):
        return ["PowerSwitch", "TemperatureSet"] + ([] if self.heating_only else ["WorkMode"])

    @property
    def available(self):
        return (
            self.coordinator.is_fresh(self.spec.address, self.required)
            and str(self.value("PowerSwitch")) in ("0", "1")
            and self.number("TemperatureSet") is not None
            and (self.heating_only or str(self.value("WorkMode")) in self.mode_map)
        )

    @property
    def mode_map(self):
        return MODES | ({"11": HVACMode.HEAT, "12": HVACMode.HEAT} if self.spec.type_id == "107" else {})

    @property
    def supported_features(self):
        flags = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        if self.fan_map:
            flags |= ClimateEntityFeature.FAN_MODE
        if self.spec.type_id == "73" and self.has_property("WindDirection"):
            flags |= ClimateEntityFeature.SWING_MODE
        if self.spec.type_id == "107":
            flags |= ClimateEntityFeature.PRESET_MODE
        return flags

    @property
    def hvac_modes(self):
        return ([HVACMode.HEAT] if self.heating_only else list(MODES.values())) + [HVACMode.OFF]

    @property
    def hvac_mode(self):
        power = self.value("PowerSwitch")
        if str(power) == "0":
            return HVACMode.OFF
        if str(power) != "1":
            return None
        return HVACMode.HEAT if self.heating_only else self.mode_map.get(str(self.value("WorkMode")))

    @property
    def target_temperature(self):
        return self.number("TemperatureSet")

    @property
    def current_temperature(self):
        return self.number("Temperature")

    @property
    def fan_modes(self):
        return list(self.fan_map.values()) or None

    @property
    def fan_mode(self):
        return self.fan_map.get(str(self.value("Windspeed")))

    @property
    def swing_modes(self):
        return (
            list(DIRECTIONS.values())
            if self.spec.type_id == "73" and self.has_property("WindDirection")
            else None
        )

    @property
    def swing_mode(self):
        return DIRECTIONS.get(str(self.value("WindDirection"))) if self.spec.type_id == "73" else None

    @property
    def preset_modes(self):
        return ["none", "floor_heating", "heat_and_floor"] if self.spec.type_id == "107" else None

    @property
    def preset_mode(self):
        if self.spec.type_id != "107":
            return None
        value = self.value("WorkMode")
        return (
            {"11": "floor_heating", "12": "heat_and_floor"}.get(str(value), "none")
            if value is not None
            else None
        )

    async def _control(self, commands):
        await self.send(commands, attempts=6, interval=0.8, confirmation_timeout=5)

    async def async_turn_on(self):
        await self._control([{"identifier": "PowerSwitch", "value": "1"}])

    async def async_turn_off(self):
        await self._control([{"identifier": "PowerSwitch", "value": 0 if self.spec.type_id == "3" else "0"}])

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
            return
        if hvac_mode not in self.hvac_modes:
            raise GatewayError("Unsupported climate mode")
        commands = [{"identifier": "PowerSwitch", "value": "1"}]
        if not self.heating_only:
            commands.append(
                {"identifier": "WorkMode", "value": next(k for k, v in MODES.items() if v == hvac_mode)}
            )
        await self._control(commands)

    async def async_set_temperature(self, **kwargs):
        value = kwargs.get(ATTR_TEMPERATURE)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 16 <= value <= 30
            or int(value) != value
        ):
            raise GatewayError("Temperature must be an integer within the supported range")
        await self._control([{"identifier": "TemperatureSet", "value": int(value)}])

    async def async_set_fan_mode(self, fan_mode):
        await self._set_mapped("Windspeed", self.fan_map, fan_mode)

    async def async_set_swing_mode(self, swing_mode):
        await self._set_mapped("WindDirection", DIRECTIONS if self.swing_modes else {}, swing_mode)

    async def async_set_preset_mode(self, preset_mode):
        if self.spec.type_id != "107" or preset_mode not in self.preset_modes:
            raise GatewayError("Unsupported climate preset")
        value = {"floor_heating": "11", "heat_and_floor": "12"}.get(preset_mode)
        if value is None:
            value = str(self.value("WorkMode"))
            if value in ("11", "12"):
                value = "1"
            if value not in MODES:
                raise GatewayError("No fresh standard mode to restore")
        await self._control([{"identifier": "WorkMode", "value": value}])

    async def _set_mapped(self, identifier, mapping, requested):
        value = next((k for k, v in mapping.items() if v == requested), None)
        if value is None:
            raise GatewayError("Unsupported climate setting")
        await self._control([{"identifier": identifier, "value": value}])
