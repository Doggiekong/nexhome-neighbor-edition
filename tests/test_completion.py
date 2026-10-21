from unittest.mock import AsyncMock, patch

from homeassistant.helpers import entity_registry as er

from custom_components.nexhome.installation import installation_status
from tests.conftest import device
from tests.test_ha_lifecycle import config_entry


async def test_real_hass_completion_readback_reload(hass,gateway):
    entry=config_entry()
    entry.add_to_hass(hass)
    gateway.login=AsyncMock()
    gateway.devices=AsyncMock(return_value=[device('1')])
    gateway.endpoint='192.0.2.10:8085'
    gateway.values[('fixture-address-a','PowerSwitch')]='0'
    with patch('custom_components.nexhome.GatewayClient',return_value=gateway):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert installation_status(hass)['stage']=='CONFIGURED'
        row=er.async_entries_for_config_entry(er.async_get(hass),entry.entry_id)[0]
        await hass.services.async_call('light','turn_on',{'entity_id':row.entity_id},blocking=True)
        assert installation_status(hass)['stage']=='CONTROL_VERIFIED'
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert installation_status(hass)['stage']=='CONTROL_VERIFIED'
        await hass.config_entries.async_unload(entry.entry_id)

async def test_existing_entry_does_not_discover(hass):
    entry=config_entry()
    entry.add_to_hass(hass)
    with patch('custom_components.nexhome.config_flow.async_discover',AsyncMock()) as discover:
        flow=await hass.config_entries.flow.async_init('nexhome',context={'source':'user'})
    assert flow['type']=='abort' and flow['reason']=='already_configured'
    discover.assert_not_called()
