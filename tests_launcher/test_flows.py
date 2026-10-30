"""Browser-facing state machines call real installer core on isolated fixtures."""

import json
import threading

import pytest

from neighbor_installer.detection import COMMUNITY, OFFICIAL
from neighbor_installer.files import digest, durable, inventory, load
from neighbor_launcher.controller import Controller
from tests_installer.test_installer import artifact, write
from tests_installer.test_installer import setup as base_setup


@pytest.fixture
def lab(tmp_path):
    root, runtime, engine, bundle = base_setup.__wrapped__(tmp_path)
    return Controller(engine, bundle, tmp_path / 'interface'), root, runtime, engine, bundle


def step(ui, action, **payload):
    assert ui.start(action, payload)
    ui.worker.join(5)
    assert not ui.worker.is_alive()
    return ui.view()


def install(ui):
    step(ui, 'check')
    plan = step(ui, 'prepare')['plan']
    return step(ui, 'confirm', plan=plan, confirmed=True)


def hacs(root, repo):
    write(root / 'custom_components/hacs/manifest.json', {'version': '2.0.5'})
    write(root / '.storage/hacs.repositories', {'version': 1, 'data': {'123': {
        'domain': 'nexhome', 'installed': True, 'full_name': repo,
    }}})


def test_d1_fresh(lab):
    ui, _, runtime, engine, _ = lab
    assert step(ui, 'check')['screen'] == 'fresh'
    plan = step(ui, 'prepare')['plan']
    assert runtime.calls == []
    assert step(ui, 'confirm', plan=plan, confirmed=True)['screen'] == 'installed'
    assert engine.inspect()['owner'] == 'NEIGHBOR_INSTALLER'


def test_d2_latest(lab):
    ui, _, runtime, engine, bundle = lab
    engine.apply(bundle)
    runtime.calls.clear()
    view = step(ui, 'check')
    assert view['screen'] == 'installed'
    assert '友邻加强版已经安装' in view['title']
    assert runtime.calls == []


def test_d3_update(lab, tmp_path):
    ui, _, _, engine, bundle = lab
    engine.apply(bundle)
    ui.artifact = artifact(tmp_path, '1.1.17.dev4')
    view = step(ui, 'check')
    assert view['screen'] == 'update'
    assert view['current_version'] == '早期版本'
    assert view['new_version'] == '1.1.17.dev4'
    assert install(ui)['screen'] == 'installed'
    assert engine.inspect()['version'] == '1.1.17.dev4'


def test_d4_hacs_requires_normal_user_step(lab):
    ui, root, runtime, engine, bundle = lab
    engine.apply(bundle)
    (engine.state / 'owner.json').unlink()
    hacs(root, OFFICIAL)
    engine.trusted_trees = {OFFICIAL: digest(bundle.metadata['files'])}
    runtime.calls.clear()
    assert step(ui, 'check')['screen'] == 'official'
    plan = step(ui, 'prepare')['plan']
    assert step(ui, 'confirm', plan=plan, confirmed=True)['screen'] == 'handoff'
    assert step(ui, 'handoff')['screen'] == 'handoff'
    assert runtime.calls == []
    # Test-only fixture: supported HACS UI removes its installed claim.
    write(root / '.storage/hacs.repositories', {'version': 1, 'data': {}})
    assert step(ui, 'handoff')['screen'] == 'installed'
    assert engine.inspect()['owner'] == 'NEIGHBOR_INSTALLER'


@pytest.mark.parametrize('owner,screen', [(COMMUNITY, 'hacs'), ('manual', 'unknown'), ('conflict', 'conflict')])
def test_d5_d6_d7_no_unsafe_write(lab, owner, screen):
    ui, root, runtime, engine, bundle = lab
    engine.apply(bundle)
    if owner != 'conflict':
        (engine.state / 'owner.json').unlink()
    if owner in {COMMUNITY, 'conflict'}:
        hacs(root, COMMUNITY)
        engine.trusted_trees = {COMMUNITY: digest(bundle.metadata['files'])}
    runtime.calls.clear()
    before = inventory(engine.target)
    assert step(ui, 'check')['screen'] == screen
    assert not ui.start('prepare')
    assert inventory(engine.target) == before and runtime.calls == []
    assert ui.plan is None


def test_d8_health_failure_restored(lab):
    ui, _, runtime, engine, _ = lab
    runtime.fail = True
    assert install(ui)['screen'] == 'restored'
    assert not engine.target.exists()


def test_d9_recovery_required(lab):
    ui, _, runtime, engine, _ = lab
    runtime.fail = True
    runtime.restart = lambda: (engine.target / '__init__.py').write_text('CONCURRENT_CHANGE = True')
    view = install(ui)
    assert view['screen'] == 'recovery'
    assert '停止' in view['description']
    assert 'Traceback' not in json.dumps(ui.diagnostics())


def test_d10_interrupted_core_journal_not_repeated(lab):
    ui, _, _, engine, _ = lab
    install(ui)
    active = load(engine.state / 'active.json')
    tx = load(engine.state / 'transactions' / active['id'] / 'record.json')
    engine._record(tx, 'ACTIVATE')  # Crash fixture: saved after swap, before health.
    ui._save('running', status='RUNNING')
    reopened = Controller(engine, ui.artifact, ui.data)
    assert reopened.view()['screen'] == 'interrupted'
    assert step(reopened, 'recover')['screen'] == 'restored'
    assert len(list((engine.state / 'transactions').iterdir())) == 1


def test_d11_duplicate_confirmation(lab):
    ui, _, runtime, engine, _ = lab
    step(ui, 'check')
    plan = step(ui, 'prepare')['plan']
    held = threading.Event()
    runtime.wait = lambda *args: held.wait(3)
    assert ui.start('confirm', {'plan': plan, 'confirmed': True})
    assert not ui.start('confirm', {'plan': plan, 'confirmed': True})
    held.set()
    ui.worker.join(5)
    assert not ui.start('confirm', {'plan': plan, 'confirmed': True})
    assert len(list((engine.state / 'transactions').iterdir())) == 1
    assert ui.view()['screen'] == 'installed'


def test_d12_reopen_completed_state(lab):
    ui, _, runtime, engine, _ = lab
    install(ui)
    runtime.calls.clear()
    reopened = Controller(engine, ui.artifact, ui.data)
    assert reopened.view()['screen'] == 'installed'
    assert runtime.calls == []


def test_no_secret_in_export(lab):
    ui, root, _, _, _ = lab
    write(root / '.storage/core.config_entries', {'data': {'entries': [{
        'domain': 'nexhome', 'entry_id': 'synthetic',
        'data': {'sn_input': 'PRIVATE_SN_VALUE', 'password': 'PRIVATE_PASSWORD'},
    }]}})
    step(ui, 'check')
    exported = json.dumps(ui.diagnostics())
    assert 'PRIVATE_SN_VALUE' not in exported and 'PRIVATE_PASSWORD' not in exported
    assert 'confirmation' not in exported


def test_observer_cannot_break_transaction(lab):
    _, _, _, engine, bundle = lab
    def broken(_event):
        raise RuntimeError('observer unavailable')
    engine.observer = broken
    assert engine.apply(bundle)['status'] == 'COMMITTED'


def test_pending_transfer_remains_waiting_after_reopen(lab):
    ui, _, _, engine, _ = lab
    durable(engine.state / 'transfer-active.json', {'id': 'a' * 32, 'phase': 'SOURCE_RELEASED'})
    assert Controller(engine, ui.artifact, ui.data).view()['screen'] == 'handoff'


@pytest.mark.parametrize('change_wrapper', [False, True])
def test_old_official_schema_uses_stageb_policy_not_strict_false_failure(lab, change_wrapper):
    ui, root, runtime, engine, bundle = lab
    entries = {'data': {'entries': [
        {'entry_id': 'legacy', 'domain': 'nexhome', 'version': 1, 'minor_version': 1,
         'data': {'sn': 'TEST_ONLY'}, 'options': {}},
        {'entry_id': 'wrapper', 'domain': 'switch_as_x', 'data': {'entity_id': 'switch.legacy'}},
    ]}}
    write(root / '.storage/core.config_entries', entries)
    runtime.entries = {'legacy': 'not_loaded'}
    engine.apply(bundle)
    (engine.state / 'owner.json').unlink()
    hacs(root, OFFICIAL)
    engine.trusted_trees = {OFFICIAL: digest(bundle.metadata['files'])}
    step(ui, 'check')
    plan = step(ui, 'prepare')['plan']
    step(ui, 'confirm', plan=plan, confirmed=True)
    write(root / '.storage/hacs.repositories', {'version': 1, 'data': {}})
    def restart():
        entries['data']['entries'][0]['minor_version'] = 2
        entries['data']['entries'][0]['data'].update(identity_mode='compat', sn_input='TEST_ONLY')
        if change_wrapper:
            entries['data']['entries'][1]['data']['entity_id'] = 'switch.WRONG'
        write(root / '.storage/core.config_entries', entries)
    runtime.restart = restart
    view = step(ui, 'handoff')
    assert view['screen'] == ('recovery' if change_wrapper else 'configured')
