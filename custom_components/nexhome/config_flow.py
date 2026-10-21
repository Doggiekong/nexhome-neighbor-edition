"""User-invoked zero-parameter discovery, explicit selection and advanced manual entry."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GatewayClient, validate_endpoint
from .const import DOMAIN, IP_CONFIG, SN_CONFIG
from .discovery import Hub, async_discover
from .errors import GatewayError


class NexhomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self):
        self.hubs = []
        self.selected = None

    async def async_step_user(self, user_input=None):
        if self._async_current_entries() and self.source == "user":
            return self.async_abort(reason="already_configured")
        self.hubs = await async_discover(self.hass)
        if not self.hubs:
            return await self.async_step_no_hubs()
        if len(self.hubs) == 1:
            self.selected = self.hubs[0]
            return await self.async_step_confirm()
        return await self.async_step_select_hub()

    async def async_step_retry(self, user_input=None):
        return await self.async_step_user()

    async def async_step_no_hubs(self, user_input=None):
        return self.async_show_menu(step_id="no_hubs", menu_options=["retry", "manual"])

    async def async_step_select_hub(self, user_input=None):
        if user_input is not None:
            try:
                index = int(user_input["hub"])
                if index < 0:
                    raise IndexError
                self.selected = self.hubs[index]
            except ValueError, TypeError, IndexError, KeyError:
                return self.async_abort(reason="invalid_selection")
            return await self.async_step_confirm()
        choices = {str(i): f"Hub {i + 1} — {hub.endpoint}" for i, hub in enumerate(self.hubs)}
        return self.async_show_form(
            step_id="select_hub", data_schema=vol.Schema({vol.Required("hub"): vol.In(choices)})
        )

    async def async_step_manual(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                endpoint = validate_endpoint(user_input[IP_CONFIG])
                serial = user_input["sn"]
                if not isinstance(serial, str) or not serial or len(serial) > 256:
                    raise GatewayError("Invalid identity")
                self.selected = Hub(endpoint, serial)
                return await self.async_step_confirm()
            except GatewayError, KeyError:
                errors["base"] = "invalid_input"
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(IP_CONFIG): str, vol.Required("sn"): str}),
            errors=errors,
        )

    async def async_step_confirm(self, user_input=None):
        hub = self.selected
        if hub is None:
            return self.async_abort(reason="invalid_selection")
        # Include old entries with no config-flow unique_id; no duplicate HTTP login.
        if self.source != "reconfigure" and any(
            e.data.get(SN_CONFIG, e.data.get("sn")) == hub.serial for e in self._async_current_entries()
        ):
            return self.async_abort(reason="already_configured")
        errors = {}
        if user_input is not None:
            if self.source == "reconfigure":
                entry = self._get_reconfigure_entry()
                if entry.data.get(SN_CONFIG) != hub.serial:
                    return self.async_abort(reason="identity_mismatch")
            else:
                await self.async_set_unique_id(hub.serial)
                self._abort_if_unique_id_configured()
            client = GatewayClient(hub.endpoint, hub.serial, async_get_clientsession(self.hass))
            try:
                await client.login()
                await client.devices()
            except GatewayError:
                errors["base"] = "cannot_connect"
            else:
                if self.source == "reconfigure":
                    return self.async_update_reload_and_abort(entry, data_updates={IP_CONFIG: hub.endpoint})
                return self.async_create_entry(
                    title="NexHome 滨融府友邻加强版",
                    data={
                        IP_CONFIG: hub.endpoint,
                        SN_CONFIG: hub.serial,
                        "identity_mode": "fresh",
                        "filter_mode": "exclude",
                        "filter_devices": [],
                    },
                )
            finally:
                await client.close()
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"endpoint": hub.endpoint},
        )

    async def async_step_reconfigure(self, user_input=None):
        return await self.async_step_user(user_input)
