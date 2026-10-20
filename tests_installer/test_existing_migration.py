"""Stage B installer contract: explicit preview, references and recovery boundaries."""

import json

import pytest

from neighbor_installer.engine import Installer
from neighbor_installer.files import InstallerError, inventory
from neighbor_installer.identity import baseline, preview, validate

from .test_installer import Runtime, artifact, write


def existing(tmp_path):
    root = tmp_path / 'config'
    root.mkdir()
    runtime = Runtime()
    engine = Installer(root, runtime)
    engine.apply(artifact(tmp_path, '1.1.17.dev2'))
    write(root / '.storage/core.config_entries', {'data': {'entries': [{
        'entry_id': 'fixture-entry', 'domain': 'nexhome', 'unique_id': 'fixture-hub',
        'title': 'User title', 'disabled_by': None, 'version': 1, 'minor_version': 1,
        'data': {'ip_address': '192.0.2.1:8085', 'sn_input': 'SYNTHETIC_ONLY'}, 'options': {},
    }]}})
    write(root / '.storage/core.device_registry', {'data': {'devices': [{
        'id': 'fixture-device', 'identifiers': [['nexhome', 'fixture-device']],
        'config_entries': ['fixture-entry'], 'name_by_user': 'User device', 'area_id': 'fixture-area',
    }]}})
    write(root / '.storage/core.entity_registry', {'data': {'entities': [{
        'id': 'fixture-registry-id', 'entity_id': 'switch.fixture', 'unique_id': 'fixture-uid',
        'platform': 'nexhome', 'config_entry_id': 'fixture-entry', 'device_id': 'fixture-device',
        'name': None, 'original_name': 'Fixture light', 'hidden_by': None,
        'disabled_by': None, 'area_id': None,
    }]}})
    for name in ['automations.yaml', 'groups.yaml']:
        (root / name).write_text('fixture: switch.fixture\n')
    write(root / '.storage/lovelace.fixture', {'data': {'entity': 'switch.fixture'}})
    runtime.entries = {'fixture-entry': 'loaded'}
    return root, runtime, engine


def additive(root):
    path = root / '.storage/core.config_entries'
    data = json.loads(path.read_text())
    data['data']['entries'][0]['data']['identity_mode'] = 'compat'
    data['data']['entries'][0]['minor_version'] = 2
    write(path, data)


def test_existing_upgrade_explicit_preview(tmp_path):
    root, runtime, engine = existing(tmp_path)
    plan = preview(root)
    runtime.restart = lambda: additive(root)
    result = engine.apply(artifact(tmp_path), migration_preview=plan)
    assert result['status'] == 'COMMITTED'
    assert validate(root, plan) == 'FORWARD_ONLY_BUT_COMPATIBLE'
    assert 'SYNTHETIC_ONLY' not in json.dumps(plan)
    assert baseline(root)['entries']['fixture-entry']['entry_id'] == 'fixture-entry'


@pytest.mark.parametrize('field,value', [('entity_id', 'light.changed'), ('unique_id', 'changed'),
    ('name', 'Lost user name'), ('area_id', 'changed'), ('hidden_by', 'user'),
    ('disabled_by', 'integration'), ('device_id', 'changed')])
def test_unapproved_identity_mutation_refused(tmp_path, field, value):
    root, _, _ = existing(tmp_path)
    plan = preview(root)
    path = root / '.storage/core.entity_registry'
    data = json.loads(path.read_text())
    data['data']['entities'][0][field] = value
    write(path, data)
    with pytest.raises(InstallerError):
        validate(root, plan)


@pytest.mark.parametrize('name', ['automations.yaml', 'groups.yaml', '.storage/lovelace.fixture'])
def test_reference_change_refused(tmp_path, name):
    root, _, _ = existing(tmp_path)
    plan = preview(root)
    (root / name).write_text('changed reference')
    with pytest.raises(InstallerError, match='REFERENCES_CHANGED'):
        validate(root, plan)


def test_stale_preview_refuses_before_deploy(tmp_path):
    root, _, engine = existing(tmp_path)
    plan = preview(root)
    (root / 'groups.yaml').write_text('new user change')
    before = inventory(engine.target)
    with pytest.raises(InstallerError, match='PREVIEW_STALE'):
        engine.apply(artifact(tmp_path), migration_preview=plan)
    assert inventory(engine.target) == before


def test_forward_only_failure_reports_recovery_not_registry_rollback(tmp_path):
    root, runtime, engine = existing(tmp_path)
    before = inventory(engine.target)
    plan = preview(root)
    runtime.restart = lambda: additive(root)
    runtime.fail = True
    with pytest.raises(InstallerError, match='RECOVERY_REQUIRED'):
        engine.apply(artifact(tmp_path), migration_preview=plan)
    assert inventory(engine.target) == before
    active = json.loads((engine.state / 'active.json').read_text())
    assert active['phase'] == 'RECOVERY_REQUIRED'
    record = json.loads((engine.state / 'transactions' / active['id'] / 'record.json').read_text())
    assert record['code_restored'] and record['identity_result'] == 'FORWARD_ONLY_BUT_COMPATIBLE'
    assert baseline(root)['entries']['fixture-entry']['minor_version'] == 2


def test_unchanged_identity_failure_fully_reversible(tmp_path):
    root, runtime, engine = existing(tmp_path)
    plan = preview(root)
    runtime.fail = True
    result = engine.apply(artifact(tmp_path), migration_preview=plan)
    assert result['status'] == 'ROLLED_BACK' and result['identity_unchanged']
    assert validate(root, plan) == 'REVERSIBLE'


def test_unavailable_entry_does_not_mutate_or_discover(tmp_path):
    root, runtime, engine = existing(tmp_path)
    before = baseline(root)
    runtime.entries = {'fixture-entry': 'setup_retry'}
    runtime.calls.clear()
    with pytest.raises(InstallerError, match='REQUIRES_DIAGNOSIS_NO_AUTODISCOVERY'):
        engine.apply(artifact(tmp_path), migration_preview=preview(root))
    assert baseline(root) == before and not runtime.calls


def test_manual_unknown_refuses_even_with_identity_preview(tmp_path):
    root, _, engine = existing(tmp_path)
    (engine.state / 'owner.json').unlink()
    before = inventory(engine.target)
    assert engine.inspect()['owner'] == 'MANUAL_UNKNOWN'
    assert engine.backup_only()['status'] == 'BACKUP_ONLY'
    with pytest.raises(InstallerError, match='UNKNOWN_OWNER'):
        engine.apply(artifact(tmp_path), migration_preview=preview(root))
    assert inventory(engine.target) == before


def test_interrupted_migration_restores_without_recreating_entry(tmp_path, monkeypatch):
    root, _, engine = existing(tmp_path)
    plan = preview(root)
    record = engine._record
    def interrupt(tx, phase, error=None):
        record(tx, phase, error)
        if phase == 'ACTIVATE':
            raise KeyboardInterrupt
    monkeypatch.setattr(engine, '_record', interrupt)
    with pytest.raises(KeyboardInterrupt):
        engine.apply(artifact(tmp_path), migration_preview=plan)
    monkeypatch.setattr(engine, '_record', record)
    assert engine.recover()['status'] == 'ROLLED_BACK'
    assert baseline(root) == plan['baseline']
