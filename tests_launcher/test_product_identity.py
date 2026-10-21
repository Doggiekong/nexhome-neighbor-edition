"""D.5 independent lineage, shared installer, rollback and identity guards."""
import hashlib
from pathlib import Path

import pytest

from neighbor_installer.artifact import Artifact
from neighbor_installer.files import InstallerError, inventory, load
from neighbor_installer.product import PRODUCT_ID, SCHEME, relation
from neighbor_launcher.bootstrap import deploy
from neighbor_launcher.controller import Controller
from tests_installer.test_installer import artifact, write
from tests_installer.test_installer import setup as base_setup
from tests_launcher.test_flows import install, step


def product(tmp, version='0.1.0'):
    b = artifact(tmp, version)
    info = dict(product_id=PRODUCT_ID, product_version=version,
                upstream_base_version='1.1.16', version_scheme=SCHEME)
    write(b.directory / 'nexhome/product.json', info)
    metadata = b.metadata | info | {'schema': 2, 'files': inventory(b.directory / 'nexhome')}
    write(b.directory / 'artifact.json', metadata)
    return Artifact.open(b.directory, hashlib.sha256((b.directory / 'artifact.json').read_bytes()).hexdigest())


@pytest.mark.parametrize('legacy', ['1.1.17.dev1', '1.1.17.dev2', '1.1.17.dev3', '1.1.17.dev4'])
def test_explicit_legacy_upgrade_and_noop(tmp_path, legacy):
    root, runtime, engine, _ = base_setup.__wrapped__(tmp_path)
    old = artifact(tmp_path, legacy) if legacy != '1.1.17.dev3' else _
    assert engine.apply(old)['status'] == 'COMMITTED'
    new = product(tmp_path)
    ui = Controller(engine, new, tmp_path / 'ui')
    assert step(ui, 'check')['screen'] == 'update'
    assert ui.view()['current_version'] == '早期内部 Candidate'
    assert install(ui)['screen'] == 'installed'
    assert engine.inspect()['product_version'] == '0.1.0'
    assert engine.inspect()['upstream_base_version'] == '1.1.16'
    assert engine.apply(new)['status'] == 'NO_OP'
    marker = load(engine.state / 'owner.json')
    assert marker['product_version'] == '0.1.0'
    assert marker['upstream_base_version'] == '1.1.16'
    assert step(ui, 'check')['screen'] == 'installed'


def test_new_version_upgrade_downgrade_and_rollback(tmp_path):
    _, runtime, engine, _ = base_setup.__wrapped__(tmp_path)
    first, second = product(tmp_path), product(tmp_path, '0.1.1')
    engine.apply(first)
    runtime.fail = True
    assert engine.apply(second)['status'] == 'ROLLED_BACK'
    assert engine.inspect()['product_version'] == '0.1.0'
    assert engine.apply(second)['status'] == 'COMMITTED'
    with pytest.raises(InstallerError, match='DOWNGRADE_REFUSED'):
        engine.apply(first)
    with pytest.raises(InstallerError, match='LEGACY_TARGET_REFUSED'):
        engine.apply(artifact(tmp_path, '1.1.17.dev4'))


@pytest.mark.parametrize('owner', ['OFFICIAL_HACS', 'COMMUNITY_HACS', 'MANUAL_UNKNOWN'])
def test_official_numbers_are_not_neighbor_lineage(tmp_path, owner):
    new = product(tmp_path)
    with pytest.raises(InstallerError, match='VERSION_LINEAGE_UNVERIFIED'):
        relation({'owner': owner, 'version': '1.1.16'}, new.metadata)


def test_unknown_installer_number_stops(tmp_path):
    with pytest.raises(InstallerError, match='VERSION_LINEAGE_UNVERIFIED'):
        relation({'owner':'NEIGHBOR_INSTALLER','version':'1.1.18'}, product(tmp_path).metadata)


def test_app_terminal_and_diagnostics_same_identity(tmp_path):
    states=[]
    for name in ('app','terminal'):
        p=tmp_path/name
        p.mkdir()
        root, runtime, engine, _ = base_setup.__wrapped__(p)
        b=product(p)
        ui=Controller(engine,b,p/'ui')
        if name=='app':
            install(ui)
        else:
            output=[]
            assert deploy(ui,confirm=True,output=output.append)==0
            assert any('0.1.0' in x and '1.1.16' in x for x in output)
        diagnostic=ui.diagnostics()
        assert diagnostic['technical']['product_version']=='0.1.0'
        assert diagnostic['technical']['upstream_base_version']=='1.1.16'
        assert ui.view()['new_version']=='0.1.0'
        states.append((inventory(engine.target),load(engine.state/'owner.json')))
    for _, marker in states:
        marker.pop('transaction_id')
    assert states[0]==states[1]


def test_identity_metadata_tampering_refused(tmp_path):
    b=product(tmp_path)
    raw=b.metadata|{'product_version':'9.0.0'}
    write(b.directory/'artifact.json',raw)
    pin=hashlib.sha256((b.directory/'artifact.json').read_bytes()).hexdigest()
    with pytest.raises(InstallerError,match='PRODUCT_IDENTITY_INVALID'):
        Artifact.open(b.directory,pin)


def test_source_identity_and_history_are_separate():
    root=Path(__file__).resolve().parents[1]
    manifest=load(root/'custom_components/nexhome/manifest.json')
    info=load(root/'custom_components/nexhome/product.json')
    assert manifest['version']==info['product_version']=='0.1.0'
    assert info['upstream_base_version']=='1.1.16'
    assert '1.1.17.dev4' not in (root/'neighbor_launcher/web/index.html').read_text()
    assert '1.1.17.dev4' in (root/'docs/phase2-staged-validation.md').read_text()


def test_official_hacs_transfer_to_independent_version(tmp_path):
    from neighbor_installer.detection import OFFICIAL
    from neighbor_installer.files import digest
    from tests_launcher.test_flows import hacs
    root, runtime, engine, _ = base_setup.__wrapped__(tmp_path)
    official=artifact(tmp_path,'1.1.16')
    engine.apply(official)
    (engine.state/'owner.json').unlink()
    hacs(root,OFFICIAL)
    engine.trusted_trees={OFFICIAL:digest(official.metadata['files'])}
    assert engine.inspect()['owner']=='OFFICIAL_HACS'
    assert 'product_version' not in engine.inspect()
    ui=Controller(engine,product(tmp_path),tmp_path/'ui')
    assert step(ui,'check')['screen']=='official'
    plan=step(ui,'prepare')['plan']
    assert step(ui,'confirm',plan=plan,confirmed=True)['screen']=='handoff'
    write(root/'.storage/hacs.repositories',{'version':1,'data':{}})
    assert step(ui,'handoff')['screen']=='installed'
    assert engine.inspect()['product_version']=='0.1.0'


def test_community_hacs_identity_uses_source_not_version(tmp_path):
    from neighbor_installer.detection import COMMUNITY
    from neighbor_installer.files import digest
    from tests_launcher.test_flows import hacs
    root, runtime, engine, _ = base_setup.__wrapped__(tmp_path)
    b=product(tmp_path)
    engine.apply(b)
    (engine.state/'owner.json').unlink()
    hacs(root,COMMUNITY)
    engine.trusted_trees={COMMUNITY:digest(b.metadata['files'])}
    assert engine.inspect()['owner']=='COMMUNITY_HACS'
    assert engine.inspect()['product_version']=='0.1.0'
    with pytest.raises(InstallerError,match='HACS_IS_UPDATE_OWNER'):
        engine.apply(b)


def test_invalid_owner_identity_fails_closed(tmp_path):
    _, runtime, engine, _ = base_setup.__wrapped__(tmp_path)
    b=product(tmp_path)
    engine.apply(b)
    marker=load(engine.state/'owner.json')
    marker['upstream_base_version']='9.0.0'
    write(engine.state/'owner.json',marker)
    assert engine.inspect()['owner']=='OWNERSHIP_CONFLICT'
    with pytest.raises(InstallerError,match='OWNERSHIP_CONFLICT_REFUSED'):
        engine.apply(b)


def test_product_cannot_strip_identity_to_schema1(tmp_path):
    from neighbor_installer.product import FIELDS
    b=product(tmp_path)
    raw={k:v for k,v in b.metadata.items() if k not in FIELDS}
    raw['schema']=1
    write(b.directory/'artifact.json',raw)
    pin=hashlib.sha256((b.directory/'artifact.json').read_bytes()).hexdigest()
    with pytest.raises(InstallerError,match='ARTIFACT_PRODUCT_SCHEMA_REQUIRED'):
        Artifact.open(b.directory,pin)
