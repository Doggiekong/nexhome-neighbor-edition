"""Exclusive writer policy and explicit HACS UI handoff fixtures (no network)."""

import pytest

from neighbor_installer.detection import COMMUNITY, OFFICIAL, Owner
from neighbor_installer.files import InstallerError, digest, inventory
from neighbor_installer.hacs import detect_hacs, detect_installed_version, detect_repository_origin
from neighbor_installer.ownership import verify_expected_owner, verify_post_migration_state
from neighbor_installer.transfer import Transfer
from tests_installer.test_installer import setup as base_setup
from tests_installer.test_installer import write


@pytest.fixture
def setup(tmp_path):
    return base_setup.__wrapped__(tmp_path)


def hacs(root, repo=OFFICIAL):
    write(root / 'custom_components/hacs/manifest.json', {'version': '2.0.5'})
    write(root / '.storage/hacs.repositories', {'version': 1, 'data': {'123': {
        'domain': 'nexhome', 'category': 'integration', 'installed': True,
        'full_name': repo, 'version_installed': 'v1.1.16',
    }}})


def official(setup):
    root, runtime, engine, bundle = setup
    engine.apply(bundle)
    (root / '.nexhome-installer/owner.json').unlink()
    hacs(root)
    engine.trusted_trees = {OFFICIAL: digest(bundle.metadata['files'])}
    return root, runtime, engine, bundle


@pytest.mark.parametrize('repo,owner', [(OFFICIAL, Owner.OFFICIAL_HACS), (COMMUNITY, Owner.COMMUNITY_HACS)])
def test_real_shape_owner(setup, repo, owner):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    (root / '.nexhome-installer/owner.json').unlink()
    hacs(root, repo)
    engine.trusted_trees = {repo: digest(bundle.metadata['files'])}
    evidence = detect_hacs(root)
    assert detect_repository_origin(evidence) == repo
    assert detect_installed_version(evidence) == 'v1.1.16'
    assert verify_expected_owner(engine.inspect(), owner)
    assert verify_post_migration_state(engine.inspect(), owner)
    assert engine.inspect() == engine.inspect()
    with pytest.raises(InstallerError, match='HACS_IS_UPDATE_OWNER'):
        engine.apply(bundle)


def test_unrelated_hacs_keeps_installer(setup):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    hacs(root, 'example/other')
    write(root / '.storage/hacs.repositories', {'data': {'123': {
        'domain': 'other', 'installed': True, 'full_name': 'example/other',
    }}})
    assert engine.inspect()['owner'] == Owner.NEIGHBOR_INSTALLER
    assert engine.apply(bundle)['status'] == 'NO_OP'


def test_hash_disagreement_conflict(setup):
    root, _, engine, _ = official(setup)
    (root / 'custom_components/nexhome/__init__.py').write_text('CHANGED = True')
    assert engine.inspect()['owner'] == Owner.OWNERSHIP_CONFLICT


def test_stale_installer_marker_conflict(setup):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    (root / 'custom_components/nexhome/__init__.py').write_text('CHANGED = True')
    assert engine.inspect()['owner'] == Owner.OWNERSHIP_CONFLICT
    with pytest.raises(InstallerError, match='OWNERSHIP_CONFLICT'):
        engine.apply(bundle)


def test_manual_unknown_with_hacs(setup):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    (root / '.nexhome-installer/owner.json').unlink()
    write(root / 'custom_components/hacs/manifest.json', {'version': '2.0.5'})
    assert engine.inspect()['owner'] == Owner.MANUAL_UNKNOWN


def test_fallback_hacs_data(setup):
    root, _, _, _ = setup
    write(root / '.storage/hacs.data', {'data': {'repositories': {'integration': [{
        'domain': 'nexhome', 'installed': True, 'full_name': OFFICIAL,
    }]}}})
    assert detect_repository_origin(detect_hacs(root)) == OFFICIAL


def test_transfer_explicit_confirmation(setup):
    _, _, engine, _ = official(setup)
    transfer = Transfer(engine)
    proposal = transfer.preview(Owner.NEIGHBOR_INSTALLER)
    with pytest.raises(InstallerError, match='CONFIRMATION'):
        transfer.begin(proposal, 'wrong')
    assert not (engine.state / 'transfer-active.json').exists()


def test_official_transfer_release_resume_commit(setup):
    root, _, engine, bundle = official(setup)
    transfer = Transfer(engine)
    proposal = transfer.preview(Owner.NEIGHBOR_INSTALLER)
    transfer.begin(proposal, proposal['confirmation_sha256'])
    with pytest.raises(InstallerError, match='PENDING_OWNER_TRANSFER'):
        engine.apply(bundle)
    with pytest.raises(InstallerError, match='NOT_RELEASED'):
        transfer.verify_release()
    # Simulate supported HACS UI Remove; fixtures alone manipulate HACS metadata.
    write(root / '.storage/hacs.repositories', {'data': {}})
    transfer.verify_release()
    assert Transfer(engine).resume()['phase'] == 'SOURCE_RELEASED'
    assert transfer.deploy_installer(bundle)['status'] == 'COMMITTED'
    assert engine.inspect()['owner'] == Owner.NEIGHBOR_INSTALLER


def test_transfer_cancel_before_release(setup):
    _, _, engine, _ = official(setup)
    transfer = Transfer(engine)
    proposal = transfer.preview(Owner.COMMUNITY_HACS)
    transfer.begin(proposal, proposal['confirmation_sha256'])
    assert transfer.cancel_before_release()['no_files_written']


def test_release_cannot_fake_full_rollback(setup):
    root, _, engine, _ = official(setup)
    transfer = Transfer(engine)
    proposal = transfer.preview(Owner.COMMUNITY_HACS)
    transfer.begin(proposal, proposal['confirmation_sha256'])
    write(root / '.storage/hacs.repositories', {'data': {}})
    with pytest.raises(InstallerError, match='RECOVERY_REQUIRED'):
        transfer.cancel_before_release()
    with pytest.raises(InstallerError):
        transfer.finish()
    assert transfer.resume()['phase'] == 'RECOVERY_REQUIRED'


def test_hacs_rollback_write_refused(setup):
    root, runtime, engine, bundle = setup
    tx = engine.apply(bundle)['transaction_id']
    hacs(root)
    before = inventory(engine.target)
    runtime.calls.clear()
    with pytest.raises(InstallerError, match='HACS_OWNERSHIP_PREVENTS'):
        engine.rollback(tx)
    assert inventory(engine.target) == before
    assert runtime.calls == []


def test_conflict_not_transferable(setup):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    hacs(root)
    with pytest.raises(InstallerError, match='TRANSITION_REFUSED'):
        Transfer(engine).preview(Owner.COMMUNITY_HACS)


def test_privacy_safe_evidence(setup):
    root, _, engine, _ = official(setup)
    write(root / '.storage/core.config_entries', {'data': {'entries': [{
        'entry_id': 'fixture', 'domain': 'nexhome', 'data': {'sn_input': 'SECRET_NOT_FOR_REPORT'},
    }]}})
    proposal = Transfer(engine).preview(Owner.COMMUNITY_HACS)
    assert 'SECRET_NOT_FOR_REPORT' not in repr(proposal)


def test_installer_to_community_ui_handoff(setup):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    transfer = Transfer(engine)
    proposal = transfer.preview(Owner.COMMUNITY_HACS)
    transfer.begin(proposal, proposal['confirmation_sha256'])
    transfer.release_installer()
    assert not (engine.state / 'owner.json').exists()
    with pytest.raises(InstallerError, match='PENDING_OWNER_TRANSFER'):
        engine.apply(bundle)
    hacs(root, COMMUNITY)  # Simulated supported UI install, no production/private API.
    engine.trusted_trees = {COMMUNITY: digest(bundle.metadata['files'])}
    assert transfer.finish()['owner'] == Owner.COMMUNITY_HACS
    with pytest.raises(InstallerError, match='HACS_IS_UPDATE_OWNER'):
        engine.apply(bundle)


def test_official_to_community_ui_handoff(setup):
    root, _, engine, bundle = official(setup)
    transfer = Transfer(engine)
    proposal = transfer.preview(Owner.COMMUNITY_HACS)
    transfer.begin(proposal, proposal['confirmation_sha256'])
    write(root / '.storage/hacs.repositories', {'data': {}})
    transfer.verify_release()
    hacs(root, COMMUNITY)
    engine.trusted_trees = {COMMUNITY: digest(bundle.metadata['files'])}
    assert transfer.finish()['status'] == 'COMMITTED'


def test_transfer_failed_health_requires_recovery(setup):
    root, runtime, engine, bundle = official(setup)
    transfer = Transfer(engine)
    proposal = transfer.preview(Owner.NEIGHBOR_INSTALLER)
    transfer.begin(proposal, proposal['confirmation_sha256'])
    write(root / '.storage/hacs.repositories', {'data': {}})
    transfer.verify_release()
    runtime.fail = True
    with pytest.raises(InstallerError, match='RECOVERY_REQUIRED'):
        transfer.deploy_installer(bundle)
    assert transfer.resume()['phase'] == 'RECOVERY_REQUIRED'


def test_forged_marker_without_history_refused(setup):
    root, _, engine, bundle = setup
    engine.apply(bundle)
    import shutil
    shutil.rmtree(root / '.nexhome-installer/transactions')
    assert engine.inspect()['owner'] == Owner.OWNERSHIP_CONFLICT


def test_update_requires_confirmation_and_pinned_artifact(setup, tmp_path):
    from neighbor_installer.update import apply_update, preview_update
    from tests_installer.test_installer import artifact
    _, _, engine, bundle = setup
    engine.apply(bundle)
    newer = artifact(tmp_path, '1.1.17.dev4')
    proposal = preview_update(engine, newer)
    assert proposal['from_version'] == '1.1.17.dev3'
    with pytest.raises(InstallerError, match='CONFIRMATION'):
        apply_update(engine, newer, proposal, 'wrong')
    assert apply_update(engine, newer, proposal, proposal['confirmation_sha256'])['status'] == 'COMMITTED'


def test_community_update_is_hacs_only(setup):
    from neighbor_installer.update import preview_update
    root, _, engine, bundle = official(setup)
    hacs(root, COMMUNITY)
    engine.trusted_trees = {COMMUNITY: digest(bundle.metadata['files'])}
    with pytest.raises(InstallerError, match='HACS_IS_UPDATE_OWNER'):
        preview_update(engine, bundle)


def test_empty_primary_uses_experimental_fallback(setup):
    root, _, _, _ = setup
    write(root / '.storage/hacs.repositories', {'data': {}})
    write(root / '.storage/hacs.data', {'data': {'repositories': {'integration': [{
        'domain': 'nexhome', 'installed': True, 'full_name': OFFICIAL,
    }]}}})
    assert detect_repository_origin(detect_hacs(root)) == OFFICIAL


def test_hacs_claim_appears_during_preflight_no_deploy(setup):
    root, runtime, engine, bundle = setup
    original_probe = runtime.probe
    def concurrent_probe():
        hacs(root)
        return original_probe()
    runtime.probe = concurrent_probe
    result = engine.apply(bundle)
    assert result['status'] == 'ROLLED_BACK'
    assert result['no_deploy_happened']
    assert not engine.target.exists()
    assert runtime.calls == []


def test_interrupted_deploy_resume_is_explicit_recovery(setup):
    from neighbor_installer.files import durable
    root, _, engine, _ = official(setup)
    transfer = Transfer(engine)
    proposal = transfer.preview(Owner.NEIGHBOR_INSTALLER)
    record = transfer.begin(proposal, proposal['confirmation_sha256'])
    record['phase'] = 'DEPLOY'
    durable(engine.state / 'transfers' / record['id'] / 'record.json', record)
    durable(engine.state / 'transfer-active.json', {'id': record['id'], 'phase': 'DEPLOY'})
    assert Transfer(engine).resume()['next'] == 'RECOVERY_REQUIRED'


def test_hacs_update_entity_churn_does_not_change_user_identity(setup):
    from neighbor_installer.identity import transfer_identity
    root, _, engine, bundle = setup
    engine.apply(bundle)
    write(root / '.storage/core.config_entries', {'data': {'entries': [{'entry_id': 'hacs-id', 'domain': 'hacs'}]}})
    before = transfer_identity(root)
    write(root / '.storage/core.entity_registry', {'data': {'entities': [{
        'entity_id': 'update.nexhome_hacs', 'config_entry_id': 'hacs-id', 'platform': 'hacs',
    }]}})
    assert transfer_identity(root) == before
    write(root / 'automations.yaml', {'automation': 'switch.user_legacy'})
    assert transfer_identity(root) != before


def test_file_rollback_after_transfer_requires_owner_recovery(setup):
    from neighbor_installer.files import load
    root, _, engine, bundle = official(setup)
    transfer = Transfer(engine)
    proposal = transfer.preview(Owner.NEIGHBOR_INSTALLER)
    transfer.begin(proposal, proposal['confirmation_sha256'])
    write(root / '.storage/hacs.repositories', {'data': {}})
    transfer.verify_release()
    transfer.deploy_installer(bundle)
    transaction = load(engine.state / 'owner.json')['transaction_id']
    with pytest.raises(InstallerError, match='RECOVERY_REQUIRED'):
        engine.rollback(transaction)
    assert transfer.resume()['phase'] == 'RECOVERY_REQUIRED'
    assert load(engine.state / 'transactions' / transaction / 'record.json')['code_restored']


@pytest.mark.parametrize('repo', [OFFICIAL, COMMUNITY])
def test_unknown_hacs_version_cannot_establish_trusted_owner(setup, repo):
    root, _, engine, bundle = official(setup)
    hacs(root, repo)
    write(root / 'custom_components/hacs/manifest.json', {'version': '999.0.0'})
    engine.trusted_trees = {repo: digest(bundle.metadata['files'])}
    assert engine.inspect()['owner'] == Owner.MANUAL_UNKNOWN
    with pytest.raises(InstallerError):
        engine.apply(bundle, manual_fingerprint=engine.inspect()['tree_sha256'])


def test_transfer_identifier_is_bounded_before_file_lookup(setup):
    _, runtime, engine, bundle = setup
    with pytest.raises(InstallerError, match='TRANSFER_ID_INVALID'):
        engine.apply(bundle, transfer_id='../../other')
    assert runtime.calls == []


def test_unknown_storage_version_fails_closed(setup):
    root, _, engine, _ = setup
    write(root / '.storage/hacs.repositories', {'version': 999, 'data': {}})
    assert engine.inspect()['hacs_schema_uncertain']
