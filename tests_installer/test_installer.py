"""Isolated filesystem/lifecycle fixtures; never connect to a real HA or Hub."""

import hashlib
import json

import pytest

from neighbor_installer.artifact import Artifact
from neighbor_installer.detection import COMMUNITY, OFFICIAL, Owner, identity_fingerprint
from neighbor_installer.engine import Installer
from neighbor_installer.files import InstallerError, digest, inventory, lock
from neighbor_installer.lifecycle import Probe


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def artifact(tmp, version='1.1.17.dev3'):
    directory = tmp / ('artifact-' + version)
    write(directory / 'nexhome/manifest.json', {'domain': 'nexhome', 'version': version})
    (directory / 'nexhome/__init__.py').write_text('VALUE = 1\n')
    metadata = {
        'schema': 1, 'version': version, 'revision': 'a' * 40,
        'origin': 'urn:nexhome:fixture:test', 'tested_ha_versions': ['2026.10.2'],
        'files': inventory(directory / 'nexhome'),
    }
    write(directory / 'artifact.json', metadata)
    pin = hashlib.sha256((directory / 'artifact.json').read_bytes()).hexdigest()
    return Artifact.open(directory, pin)


class Runtime:
    def __init__(self):
        self.entries = {}
        self.calls = []
        self.healthy = True
        self.fail = False

    def probe(self):
        return Probe('2026.10.2', True, self.healthy, True, self.entries.copy())

    def restart(self):
        self.calls.append('restart')

    def stop(self):
        self.calls.append('stop')

    def start(self):
        self.calls.append('start')

    def wait(self, present, baseline):
        if self.fail:
            self.fail = False
            return False
        return True


@pytest.fixture
def setup(tmp_path):
    root = tmp_path / 'config'
    root.mkdir()
    runtime = Runtime()
    return root, runtime, Installer(root, runtime), artifact(tmp_path)


def test_fresh_install(setup):
    root, runtime, engine, bundle = setup
    assert engine.inspect()['owner'] is None
    result = engine.apply(bundle)
    assert result['status'] == 'COMMITTED'
    assert engine.inspect()['owner'] == Owner.NEIGHBOR_INSTALLER
    assert inventory(root / 'custom_components/nexhome') == bundle.metadata['files']
    assert runtime.calls == ['restart']


def test_idempotency(setup):
    _, runtime, engine, bundle = setup
    engine.apply(bundle)
    for _ in range(3):
        assert engine.apply(bundle)['status'] == 'NO_OP'
    assert runtime.calls == ['restart']


def test_upgrade_backup_and_rollback(setup, tmp_path):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    newer = artifact(tmp_path, '1.1.17.dev4')
    result = engine.apply(newer)
    backup = root / '.nexhome-installer/transactions' / result['transaction_id'] / 'backup'
    assert inventory(backup) == bundle.metadata['files']
    assert engine.rollback(result['transaction_id'])['status'] == 'ROLLED_BACK'
    assert inventory(root / 'custom_components/nexhome') == bundle.metadata['files']


@pytest.mark.parametrize('existing', [False, True])
def test_failed_health_restores(setup, tmp_path, existing):
    root, runtime, engine, bundle = setup
    before = {}
    if existing:
        engine.apply(bundle)
        before = bundle.metadata['files']
        bundle = artifact(tmp_path, '1.1.17.dev4')
    runtime.fail = True
    result = engine.apply(bundle)
    assert result['status'] == 'ROLLED_BACK'
    assert inventory(root / 'custom_components/nexhome') == before
    assert runtime.calls[-2:] == ['stop', 'start']


def test_explicit_fresh_rollback(setup):
    root, _, engine, bundle = setup
    result = engine.apply(bundle)
    engine.rollback(result['transaction_id'])
    assert not (root / 'custom_components/nexhome').exists()
    assert engine.inspect()['owner'] is None


@pytest.mark.parametrize('repo,owner', [(OFFICIAL, Owner.OFFICIAL_HACS), (COMMUNITY, Owner.COMMUNITY_HACS)])
def test_hacs_exclusive_owner(setup, repo, owner):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    (root / '.nexhome-installer/owner.json').unlink()
    (root / 'custom_components/hacs').mkdir()
    write(root / '.storage/hacs.repositories', {'data': {'repositories': {'1': {
        'domain': 'nexhome', 'installed': True, 'full_name': repo,
    }}}})
    engine.trusted_trees = {repo: digest(bundle.metadata['files'])}
    assert engine.inspect()['owner'] == owner
    with pytest.raises(InstallerError, match='HACS_IS_UPDATE_OWNER'):
        engine.apply(bundle)


@pytest.mark.parametrize('raw', [{'data': []}, {'data': {'x': 3}}, []])
def test_unknown_hacs_schema_refuses(setup, raw):
    root, _, engine, bundle = setup
    write(root / '.storage/hacs.repositories', raw)
    assert engine.inspect()['owner'] == Owner.MANUAL_UNKNOWN
    with pytest.raises(InstallerError):
        engine.apply(bundle)


def test_manual_requires_exact_confirmation(setup):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    (root / '.nexhome-installer/owner.json').unlink()
    with pytest.raises(InstallerError, match='UNKNOWN_OWNER'):
        engine.apply(bundle)
    assert engine.backup_only()['status'] == 'BACKUP_ONLY'
    assert engine.apply(bundle, manual_fingerprint=engine.inspect()['tree_sha256'])['status'] == 'COMMITTED'


def test_conflicting_hacs_and_installer(setup):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    write(root / '.storage/hacs.repositories', {'data': {'1': {
        'domain': 'nexhome', 'installed': True, 'full_name': COMMUNITY,
    }}})
    assert engine.inspect()['owner'] == Owner.MANUAL_UNKNOWN
    with pytest.raises(InstallerError):
        engine.apply(bundle, manual_fingerprint=engine.inspect()['tree_sha256'])


def test_existing_identity_preserved(setup, tmp_path):
    root, runtime, engine, bundle = setup
    entries = {'data': {'entries': [{'entry_id': 'test-entry', 'domain': 'nexhome',
        'unique_id': 'test-id', 'title': 'Renamed', 'data': {'sn_input': 'SECRET_TEST_SN'},
        'options': {}, 'disabled_by': None}]}}
    write(root / '.storage/core.config_entries', entries)
    write(root / '.storage/core.entity_registry', {'data': {'entities': [{
        'entity_id': 'light.test', 'unique_id': 'test-uid', 'name': 'User name',
        'hidden_by': 'user', 'area_id': 'test-area', 'config_entry_id': 'test-entry',
    }]}})
    write(root / '.storage/core.area_registry', {'data': {'areas': [{'id': 'test-area', 'name': 'Test'}]}})
    write(root / '.storage/lovelace.test', {'cards': ['test']})
    runtime.entries = {'test-entry': 'loaded'}
    before = inventory(root / '.storage')
    identity = identity_fingerprint(root)
    engine.apply(bundle)
    engine.apply(artifact(tmp_path, '1.1.17.dev4'))
    assert inventory(root / '.storage') == before
    assert identity_fingerprint(root) == identity
    diagnostics = json.dumps(engine.inspect())
    evidence = ''.join(p.read_text() for p in (root / '.nexhome-installer').rglob('*.json'))
    assert 'SECRET_TEST_SN' not in diagnostics + evidence


@pytest.mark.parametrize('state', ['setup_error', 'setup_retry', 'migration_error', 'failed_unload'])
def test_stale_entry_no_discovery(setup, state):
    _, runtime, engine, bundle = setup
    runtime.entries = {'test': state}
    with pytest.raises(InstallerError, match='EXISTING_ENTRY_REQUIRES_DIAGNOSIS'):
        engine.apply(bundle)
    assert not runtime.calls


def test_lock_exclusive_and_stale_release(setup):
    root, _, engine, bundle = setup
    with lock(root), pytest.raises(InstallerError, match='BUSY'):
        engine.apply(bundle)
    assert engine.apply(bundle)['status'] == 'COMMITTED'


@pytest.mark.parametrize('phase', ['PRECHECK', 'BACKUP', 'DEPLOY', 'ACTIVATE', 'HEALTH_CHECK'])
def test_interrupted_recovery(setup, monkeypatch, phase):
    root, runtime, engine, bundle = setup
    original = engine._record

    def interrupt(tx, current, error=None):
        original(tx, current, error)
        if current == phase:
            raise KeyboardInterrupt

    monkeypatch.setattr(engine, '_record', interrupt)
    with pytest.raises(KeyboardInterrupt):
        engine.apply(bundle)
    monkeypatch.setattr(engine, '_record', original)
    with pytest.raises(InstallerError, match='PENDING_TRANSACTION'):
        engine.apply(bundle)
    assert engine.recover()['status'] == 'ROLLED_BACK'
    assert inventory(root / 'custom_components/nexhome') == {}
    assert engine.recover()['status'] == 'NO_PENDING_TRANSACTION'


def test_backup_failure_does_not_stop_core(setup, monkeypatch):
    _, runtime, engine, bundle = setup
    monkeypatch.setattr(engine, '_backup', lambda tx: (_ for _ in ()).throw(OSError('private detail')))
    assert engine.apply(bundle)['status'] == 'ROLLED_BACK'
    assert not runtime.calls


def test_source_pin_and_tampering(setup):
    _, _, engine, bundle = setup
    with pytest.raises(InstallerError, match='PIN_MISMATCH'):
        Artifact.open(bundle.directory, '0' * 64)
    (bundle.directory / 'nexhome/__init__.py').write_text('changed')
    with pytest.raises(InstallerError, match='FILES_MISMATCH'):
        engine.apply(bundle)


@pytest.mark.parametrize('relative', ['../escape', '/absolute', 'a\\b', './file'])
def test_artifact_path_traversal(setup, relative):
    _, _, _, bundle = setup
    metadata = bundle.metadata.copy()
    metadata['files'] = {relative: '0' * 64}
    write(bundle.directory / 'artifact.json', metadata)
    pin = hashlib.sha256((bundle.directory / 'artifact.json').read_bytes()).hexdigest()
    with pytest.raises(InstallerError, match='PATH_INVALID'):
        Artifact.open(bundle.directory, pin)


@pytest.mark.parametrize('child', ['custom_components', '.storage', '.nexhome-installer'])
def test_symlink_boundary(tmp_path, child):
    root = tmp_path / 'config'
    root.mkdir()
    (root / child).symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(InstallerError, match='CONFIG_CHILD_INVALID'):
        Installer(root, Runtime())


def test_unsupported_ha_and_unhealthy(setup, monkeypatch):
    _, runtime, engine, bundle = setup
    runtime.healthy = False
    with pytest.raises(InstallerError, match='HA_NOT_HEALTHY'):
        engine.apply(bundle)
    runtime.healthy = True
    monkeypatch.setattr(runtime, 'probe', lambda: Probe('2026.9.0', True, True, False, {}))
    with pytest.raises(InstallerError, match='HA_VERSION_OUTSIDE_TESTED_MATRIX'):
        engine.apply(bundle)


def test_downgrade_refused(setup, tmp_path):
    _, _, engine, bundle = setup
    engine.apply(bundle)
    with pytest.raises(InstallerError, match='DOWNGRADE_REFUSED'):
        engine.apply(artifact(tmp_path, '1.1.17.dev2'))
