"""Failure injection at directory-swap boundaries and lifecycle security boundary."""

import json

import pytest

from neighbor_installer.engine import Installer
from neighbor_installer.environment import inspect_environment
from neighbor_installer.files import InstallerError, durable, inventory
from neighbor_installer.lifecycle import NoRedirect, SupervisorLifecycle

from .test_installer import Runtime, artifact


@pytest.mark.parametrize('boundary', ['partial_stage', 'retired_original', 'new_deployed'])
def test_mid_swap_power_interruption(tmp_path, monkeypatch, boundary):
    root = tmp_path / 'config'
    root.mkdir()
    engine = Installer(root, Runtime())
    old = artifact(tmp_path, '1.1.17.dev2')
    new = artifact(tmp_path)
    engine.apply(old)
    original = engine._swap

    def crash(files, source, tx):
        parent = engine.target.parent
        stage = parent / ('.nexhome-stage-' + tx['id'])
        retired = parent / ('.nexhome-retired-' + tx['id'])
        if boundary == 'partial_stage':
            stage.mkdir()
            (stage / '__init__.py').write_bytes((source / '__init__.py').read_bytes())
        elif boundary == 'retired_original':
            engine.target.rename(retired)
        else:
            original(files, source, tx)
        raise KeyboardInterrupt

    monkeypatch.setattr(engine, '_swap', crash)
    with pytest.raises(KeyboardInterrupt):
        engine.apply(new)
    assert engine.recover()['status'] == 'ROLLED_BACK'
    assert inventory(engine.target) == old.metadata['files']


def test_concurrent_edit_recovery_stops_before_core_stop(tmp_path, monkeypatch):
    root = tmp_path / 'config'
    root.mkdir()
    runtime = Runtime()
    engine = Installer(root, runtime)
    bundle = artifact(tmp_path)

    def crash(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(engine, '_swap', crash)
    with pytest.raises(KeyboardInterrupt):
        engine.apply(bundle)
    engine.target.mkdir(parents=True)
    (engine.target / 'user-file.txt').write_text('unrelated user change')
    with pytest.raises(InstallerError, match='RECOVERY_REQUIRED'):
        engine.recover()
    assert not runtime.calls
    assert (engine.target / 'user-file.txt').exists()


def test_invalid_transaction_id(tmp_path):
    durable(tmp_path / '.nexhome-installer/active.json', {'id': '../escape', 'phase': 'DEPLOY'})
    with pytest.raises(InstallerError, match='TRANSACTION_ID_INVALID'):
        Installer(tmp_path, Runtime()).recover()


@pytest.mark.parametrize('origin', ['file:///tmp', 'https://user:secret@example.com', 'http://example.com/path'])
def test_lifecycle_origin_validation(origin):
    with pytest.raises(InstallerError, match='HA_ORIGIN_INVALID'):
        SupervisorLifecycle('fixture', ha_url=origin)


def test_redirect_does_not_forward_token():
    with pytest.raises(InstallerError, match='REDIRECT_REFUSED'):
        NoRedirect().redirect_request(None, None, 302, '', {}, 'http://elsewhere')


def test_lifecycle_tokens_separated():
    runtime = SupervisorLifecycle('supervisor-fixture', ha_token='ha-fixture')
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{}'

    class Opener:
        def open(self, request, **kwargs):
            requests.append(request)
            return Response()

    runtime._opener = Opener()
    runtime.request('GET', '/core/api/config')
    runtime.request('GET', '/supervisor/info')
    assert requests[0].get_header('Authorization') == 'Bearer ha-fixture'
    assert requests[1].get_header('Authorization') == 'Bearer supervisor-fixture'
    assert requests[0].full_url == 'http://homeassistant:80/api/config'


def test_artifact_rejects_unexpected_private_metadata(tmp_path):
    bundle = artifact(tmp_path)
    raw = json.loads((bundle.directory / 'artifact.json').read_text())
    raw['password'] = 'not-allowed'
    (bundle.directory / 'artifact.json').write_text(json.dumps(raw))
    import hashlib

    from neighbor_installer.artifact import Artifact
    pin = hashlib.sha256((bundle.directory / 'artifact.json').read_bytes()).hexdigest()
    with pytest.raises(InstallerError, match='METADATA_INVALID'):
        Artifact.open(bundle.directory, pin)


def test_environment_no_implied_privilege(tmp_path):
    info = inspect_environment(tmp_path)
    assert info['runtime_adapter'] == 'EXPLICIT_ADAPTER_REQUIRED'
    assert not info['api_alone_can_deploy']
    assert inspect_environment(tmp_path, supervisor_authorized=True)['runtime_adapter'] == 'SUPERVISOR'


def test_backup_tamper_stops_before_core_stop(tmp_path):
    root = tmp_path / 'config'
    root.mkdir()
    runtime = Runtime()
    engine = Installer(root, runtime)
    first = engine.apply(artifact(tmp_path, '1.1.17.dev2'))
    second = engine.apply(artifact(tmp_path))
    tx = root / '.nexhome-installer/transactions' / second['transaction_id']
    (tx / 'backup/__init__.py').write_text('tampered')
    runtime.calls.clear()
    with pytest.raises(InstallerError, match='RECOVERY_REQUIRED'):
        engine.rollback(second['transaction_id'])
    assert not runtime.calls
    assert first['status'] == 'COMMITTED'


def test_old_transaction_rollback_refused(tmp_path):
    root = tmp_path / 'config'
    root.mkdir()
    engine = Installer(root, Runtime())
    first = engine.apply(artifact(tmp_path, '1.1.17.dev2'))
    engine.apply(artifact(tmp_path))
    with pytest.raises(InstallerError, match='ONLY_LATEST'):
        engine.rollback(first['transaction_id'])


def test_builder_requires_full_pin(tmp_path):
    import subprocess

    from neighbor_installer.build import build
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    bundle = artifact(tmp_path)
    import shutil
    shutil.copytree(bundle.directory / 'nexhome', repo / 'custom_components/nexhome')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid',
                    'commit', '-qm', 'Fixture'], check=True)
    with pytest.raises(InstallerError, match='FULL_COMMIT_PIN'):
        build(repo, 'HEAD', tmp_path / 'bad', ['2026.10.2'])
    revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip()
    pin = build(repo, revision, tmp_path / 'output', ['2026.10.2'])
    from neighbor_installer.artifact import Artifact
    assert Artifact.open(tmp_path / 'output', pin).metadata['revision'] == revision
