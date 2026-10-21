"""Deployment UI must not own a second configuration flow."""

import pytest

from neighbor_installer.files import InstallerError
from tests_launcher.test_flows import install
from tests_launcher.test_flows import lab as base_lab


@pytest.fixture
def lab(tmp_path):
    return base_lab.__wrapped__(tmp_path)


def test_install_hands_off_to_native_ha(lab):
    ui, *_ = lab
    result = install(ui)
    assert result["screen"] == "installed"
    assert result["button"] == "开始连接 NexHome"
    assert "Home Assistant" in result["description"]
    assert not result["can_connect"]


@pytest.mark.parametrize("action", ["connect", "connect_confirm", "connect_select"])
def test_parallel_configuration_actions_refused(lab, action):
    ui, *_ = lab
    install(ui)
    with pytest.raises(InstallerError, match="UI_ACTION_REFUSED"):
        ui.start(action)
    assert not ui.guard.locked()


def test_reopen_unconfirmed_preview_requires_new_plan(lab):
    from neighbor_launcher.controller import Controller
    from tests_launcher.test_flows import step
    ui, _, _, engine, bundle = lab
    step(ui, 'check')
    old = step(ui, 'prepare')['plan']
    reopened = Controller(engine, bundle, ui.data)
    assert reopened.view()['screen'] == 'welcome'
    assert not reopened.start('confirm', {'plan': old, 'confirmed': True})
    assert not engine.target.exists()
