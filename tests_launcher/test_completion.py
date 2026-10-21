"""COMMITTED is deployment only; READY requires native readback and user knowledge."""
import pytest

from neighbor_installer.files import InstallerError
from tests_launcher.test_flows import install, step
from tests_launcher.test_flows import lab as base_lab


@pytest.fixture
def lab(tmp_path):
    return base_lab.__wrapped__(tmp_path)

def test_deployed_not_ready_native_direct_link(lab):
    ui,_,_,_,_=lab
    view=install(ui)
    assert view['completion']['stage']=='DEPLOYED'
    assert view['native_url']=='/config/integrations/dashboard?config_flow_start=nexhome'
    assert not view['can_ack_ready']
    assert '安装完成' not in view['title']
    assert not ui.start('acknowledge_ready')

def test_existing_config_no_discovery_and_ready_guard(lab):
    from tests_installer.test_installer import write
    ui,root,runtime,engine,_=lab
    write(root/'.storage/core.config_entries',{'data':{'entries':[{'domain':'nexhome','entry_id':'fixture','data':{},'disabled_by':None}]}})
    evidence={'stage':'CONFIGURED','entities':1,'loaded_entries':1,'available_entities':1,'control_readback_verified':False}
    runtime.completion_status=lambda:evidence.copy()
    install(ui)
    assert ui.view()['screen']=='configured'
    assert 'config_flow_start' not in ui.view()['native_url']
    assert step(ui,'acknowledge_ready')['screen']=='failed'
    step(ui,'check')
    evidence.update(stage='CONTROL_VERIFIED',control_readback_verified=True)
    assert step(ui,'check_setup')['screen']=='configured'
    assert ui.view()['can_ack_ready']
    assert step(ui,'acknowledge_ready')['screen']=='ready'
    from neighbor_launcher.controller import Controller
    reopened=Controller(engine,ui.artifact,ui.data)
    assert step(reopened,'check_setup')['screen']=='ready'

def test_no_evidence_no_claim(lab):
    ui,_,runtime,_,_=lab
    install(ui)
    def fail():raise InstallerError('NO_PROOF')
    runtime.completion_status=fail
    view=step(ui,'check_setup')
    assert not view['can_ack_ready'] and view['completion']['stage']=='UNCONFIRMED'
