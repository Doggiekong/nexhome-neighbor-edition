from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nexhome.config_flow import NexhomeConfigFlow
from custom_components.nexhome.discovery import Hub
from custom_components.nexhome.errors import GatewayError


@pytest.mark.parametrize("count,step", [(0, "no_hubs"), (1, "confirm"), (2, "select_hub")])
async def test_discovery_flow_zero_one_multiple(hass, count, step):
    hubs = [Hub(f"192.0.2.{10 + i}:8085", f"synthetic-{i}") for i in range(count)]
    with patch("custom_components.nexhome.config_flow.async_discover", AsyncMock(return_value=hubs)):
        result = await hass.config_entries.flow.async_init("nexhome", context={"source": "user"})
    assert result["step_id"] == step
    assert result["type"] == (FlowResultType.MENU if count == 0 else FlowResultType.FORM)


async def test_fresh_confirm_creates_entry_without_secrets_in_title(hass):
    client = AsyncMock()
    with (
        patch(
            "custom_components.nexhome.config_flow.async_discover",
            AsyncMock(return_value=[Hub("192.0.2.10:8085", "synthetic-identity")]),
        ),
        patch("custom_components.nexhome.config_flow.GatewayClient", return_value=client),
        patch.object(hass.config_entries, "async_setup", AsyncMock(return_value=True)),
    ):
        result = await hass.config_entries.flow.async_init("nexhome", context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["identity_mode"] == "fresh"
    assert result["data"]["sn_input"] == "synthetic-identity"
    assert "synthetic-identity" not in result["title"]
    client.login.assert_awaited_once()
    client.close.assert_awaited_once()


async def test_legacy_duplicate_aborts_before_login(hass):
    entry = MockConfigEntry(domain="nexhome", data={"sn_input": "synthetic-identity"})
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.nexhome.config_flow.async_discover",
            AsyncMock(return_value=[Hub("192.0.2.10:8085", "synthetic-identity")]),
        ),
        patch("custom_components.nexhome.config_flow.GatewayClient") as client,
    ):
        result = await hass.config_entries.flow.async_init("nexhome", context={"source": "user"})
    assert result["reason"] == "already_configured"
    client.assert_not_called()


async def test_failed_login_keeps_confirm_and_closes_client(hass):
    client = AsyncMock()
    client.login.side_effect = GatewayError("Synthetic failure")
    with (
        patch(
            "custom_components.nexhome.config_flow.async_discover",
            AsyncMock(return_value=[Hub("192.0.2.10:8085", "synthetic-identity")]),
        ),
        patch("custom_components.nexhome.config_flow.GatewayClient", return_value=client),
    ):
        result = await hass.config_entries.flow.async_init("nexhome", context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "confirm" and result["errors"] == {"base": "cannot_connect"}
    client.close.assert_awaited_once()


async def test_reconfigure_rejects_other_identity_before_login(hass):
    entry = MockConfigEntry(domain="nexhome", data={"sn_input": "synthetic-original"})
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.nexhome.config_flow.async_discover",
            AsyncMock(return_value=[Hub("192.0.2.11:8085", "synthetic-other")]),
        ),
        patch("custom_components.nexhome.config_flow.GatewayClient") as client,
    ):
        result = await hass.config_entries.flow.async_init(
            "nexhome", context={"source": "reconfigure", "entry_id": entry.entry_id}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["reason"] == "identity_mismatch"
    client.assert_not_called()


async def test_negative_selection_is_rejected(hass):
    flow = NexhomeConfigFlow()
    flow.hass = hass
    flow.hubs = [Hub("192.0.2.10:8085", "synthetic")]
    assert (await flow.async_step_select_hub({"hub": "-1"}))["reason"] == "invalid_selection"


async def test_manual_validation_stays_local(hass):
    flow = NexhomeConfigFlow()
    flow.hass = hass
    assert (await flow.async_step_manual({"ip_address": "invalid", "sn": "synthetic"}))["errors"] == {
        "base": "invalid_input"
    }
    result = await flow.async_step_manual({"ip_address": "192.0.2.10:8085", "sn": "synthetic"})
    assert result["step_id"] == "confirm"
