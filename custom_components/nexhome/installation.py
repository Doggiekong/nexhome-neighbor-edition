"""Admin-only completion evidence; never sends commands or reveals Hub identity."""
from homeassistant.components import websocket_api
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


def installation_status(hass):
    entries=hass.config_entries.async_entries(DOMAIN)
    registry=er.async_get(hass)
    rows=[row for entry in entries for row in er.async_entries_for_config_entry(registry,entry.entry_id) if row.disabled_by is None]
    available=sum((state:=hass.states.get(row.entity_id)) is not None and state.state not in {'unavailable','unknown'} for row in rows)
    loaded=[e for e in entries if e.state.value=='loaded' and getattr(e,'runtime_data',None)]
    verified=any(getattr(e.runtime_data,'completion_verified',False) for e in loaded)
    evidence=bool(loaded and rows and available and verified)
    return {'stage':'CONTROL_VERIFIED' if evidence else 'CONFIGURED' if entries else 'DEPLOYED',
            'configured_entries':len(entries),'loaded_entries':len(loaded),'entities':len(rows),
            'available_entities':available,'control_readback_verified':verified}


@websocket_api.require_admin
@websocket_api.websocket_command({'type':'nexhome/installation_status'})
@websocket_api.async_response
async def websocket_installation_status(hass,connection,msg):
    connection.send_result(msg['id'],installation_status(hass))
