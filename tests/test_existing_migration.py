"""Stage B: a single messy existing HA, actual HA registries, no real network."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nexhome.models import descriptions

from .conftest import device


def capture(hass, entry):
    registry = er.async_get(hass)
    return {r.entity_id: {k: getattr(r, k) for k in (
        'entity_id', 'unique_id', 'platform', 'original_name', 'name', 'hidden_by',
        'disabled_by', 'area_id', 'device_id',
    )} for r in er.async_entries_for_config_entry(registry, entry.entry_id)}


@pytest.mark.parametrize('old_minor', [1, 2])
async def test_composite_messy_existing_ha(hass, gateway, tmp_path, old_minor):
    entry = MockConfigEntry(domain='nexhome', version=1, minor_version=old_minor,
        title='User existing Hub', unique_id='synthetic-entry-identity',
        data={'ip_address': '192.0.2.10:8085', 'sn_input': 'synthetic-gateway',
              **({'identity_mode': 'compat'} if old_minor == 2 else {})},
        options={'udp_refresh': False})
    entry.add_to_hass(hass)
    names = ['untouched', 'wrapper', 'userhidden', 'owned', 'rename', 'idonly', 'area', 'manual', 'disabled', 'unknown']
    devices = [device('1', n) for n in names] + [device('133', 'fan')]
    specs = descriptions(devices, 'synthetic-gateway', 'compat')
    registry, devices_registry = er.async_get(hass), dr.async_get(hass)
    rows, markers = {}, {}
    for name, spec in zip(names + ['fan'], specs, strict=True):
        dev = devices_registry.async_get_or_create(config_entry_id=entry.entry_id,
            identifiers={('nexhome', spec.device_identifier)}, name=spec.device_name)
        rows[name] = registry.async_get_or_create('switch', 'nexhome', spec.unique_id,
            suggested_object_id='stageb_' + name, config_entry=entry,
            original_name=spec.config['name'], device_id=dev.id)
    area = ar.async_get(hass).async_create('Synthetic Stage B Area')
    registry.async_update_entity(rows['rename'].entity_id, name='USER NAME WINS')
    registry.async_update_entity(rows['idonly'].entity_id, new_entity_id='switch.user_custom_id')
    registry.async_update_entity(rows['userhidden'].entity_id, hidden_by=er.RegistryEntryHider.USER)
    registry.async_update_entity(rows['disabled'].entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    registry.async_update_entity(rows['area'].entity_id, area_id=area.id)
    wrapper = MockConfigEntry(domain='switch_as_x', data={'entity_id': rows['wrapper'].entity_id, 'target_domain': 'light'})
    wrapper.add_to_hass(hass)
    manual = MockConfigEntry(domain='switch_as_x', data={'entity_id': rows['manual'].entity_id, 'target_domain': 'fan'})
    manual.add_to_hass(hass)
    for name in ['untouched', 'fan']:
        row = rows[name]
        markers[row.unique_id] = {'owner': 'nexhome', 'approved_semantic': True, 'legacy_entity_id': row.entity_id}
    # An old approval does not authorize a subsequently renamed entity_id.
    markers[rows['idonly'].unique_id] = {'owner': 'nexhome', 'approved_semantic': True,
        'legacy_entity_id': rows['idonly'].entity_id}
    owned = rows['owned']
    semantic_uid = owned.unique_id + ':semantic:light:v1'
    registry.async_get_or_create('light', 'nexhome', semantic_uid, config_entry=entry,
        suggested_object_id='stageb_owned', original_name=owned.original_name, device_id=owned.device_id)
    registry.async_update_entity(owned.entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION)
    markers[owned.unique_id] = {'owner': 'nexhome', 'semantic_unique_id': semantic_uid,
        'legacy_entity_id': owned.entity_id, 'phase': 'COMPLETE'}
    await Store(hass, 1, f'nexhome.semantic.{entry.entry_id}').async_save(markers)
    refs = {'automation': rows['untouched'].entity_id, 'group': [r.entity_id for r in rows.values()],
            'dashboard': [rows['rename'].entity_id, 'switch.user_custom_id']}
    references_path = tmp_path / 'user-references.json'
    references_path.write_text(json.dumps(refs))
    before = capture(hass, entry)
    (tmp_path / 'identity-before.json').write_text(json.dumps(before))
    device_ids = {d.id for d in dr.async_entries_for_config_entry(devices_registry, entry.entry_id)}
    gateway.login = AsyncMock()
    gateway.devices = AsyncMock(return_value=devices)
    for dev in devices:
        gateway.values[(dev['address'], 'PowerSwitch')] = '0'
    with patch('custom_components.nexhome.GatewayClient', return_value=gateway), patch(
        'custom_components.nexhome.config_flow.async_discover', side_effect=AssertionError('NO DISCOVERY')
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        after = capture(hass, entry)
        assert entry.entry_id == next(e.entry_id for e in hass.config_entries.async_entries('nexhome'))
        assert entry.title == 'User existing Hub' and entry.unique_id == 'synthetic-entry-identity'
        assert entry.data['identity_mode'] == 'compat'
        assert entry.minor_version == 2
        assert set(before) <= set(after)
        for entity_id, original in before.items():
            expected = dict(original)
            if entity_id in [rows['untouched'].entity_id, rows['fan'].entity_id]:
                expected['hidden_by'] = er.RegistryEntryHider.INTEGRATION
            assert after[entity_id] == expected
        assert len(after) == len(before) + 2  # only explicitly approved untouched light/fan
        assert {d.id for d in dr.async_entries_for_config_entry(devices_registry, entry.entry_id)} == device_ids
        assert registry.async_get('switch.user_custom_id') is not None
        assert json.loads(references_path.read_text()) == refs
        assert not gateway.commands
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert capture(hass, entry) == after
        assert await hass.config_entries.async_unload(entry.entry_id)
    (tmp_path / 'identity-after.json').write_text(json.dumps(after))


async def test_unproven_entity_id_change_is_conservative(hass):
    from custom_components.nexhome.migration import plan_compatibility

    from .test_semantics import row
    spec = descriptions([device()], 'synthetic-gateway', 'compat')[0]
    assert len(plan_compatibility([spec], [row(spec, entity_id='switch.user_changed')], {}).specs) == 1


async def test_user_hidden_overrides_old_owned_marker(hass):
    from custom_components.nexhome.migration import plan_compatibility

    from .test_semantics import row
    spec = descriptions([device()], 'synthetic-gateway', 'compat')[0]
    semantic_uid = spec.unique_id + ':semantic:light:v1'
    plan = plan_compatibility([spec], [row(spec, hidden_by=er.RegistryEntryHider.USER),
        row(spec, domain='light', unique_id=semantic_uid)],
        {spec.unique_id: {'owner': 'nexhome', 'semantic_unique_id': semantic_uid}})
    assert len(plan.specs) == 1 and plan.records[spec.unique_id]['status'] == 'user_intent_skip'
