"""Two deployment entries share exactly the same core/artifact outcomes."""


import pytest

from neighbor_installer.files import InstallerError, inventory, load
from neighbor_launcher.bootstrap import deploy
from neighbor_launcher.container_lifecycle import ContainerLifecycle
from tests_launcher.test_flows import install
from tests_launcher.test_flows import lab as base_lab


@pytest.fixture
def lab(tmp_path):
    return base_lab.__wrapped__(tmp_path)


def test_terminal_preview_then_confirm_and_idempotence(lab):
    ui, root, runtime, engine, bundle = lab
    output = []
    assert deploy(ui, output=output.append) == 2
    assert runtime.calls == []
    assert not (root / "custom_components/nexhome").exists()
    assert deploy(ui, confirm=True, output=output.append) == 0
    assert inventory(root / "custom_components/nexhome") == bundle.metadata["files"]
    before = list(runtime.calls)
    assert deploy(ui, confirm=True, output=output.append) == 0
    assert runtime.calls == before
    assert engine.inspect()["owner"] == "NEIGHBOR_INSTALLER"


def test_terminal_and_app_identical_product(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = base_lab.__wrapped__(tmp_path / "a")
    b = base_lab.__wrapped__(tmp_path / "b")
    install(a[0])
    assert deploy(b[0], confirm=True, output=lambda *_: None) == 0
    assert inventory(a[1] / "custom_components/nexhome") == inventory(b[1] / "custom_components/nexhome")
    left = load(a[3].state / "owner.json")
    right = load(b[3].state / "owner.json")
    assert len(left.pop("transaction_id")) == len(right.pop("transaction_id")) == 32
    assert left == right
    assert a[3].inspect() == b[3].inspect()


def test_terminal_unknown_refuses(lab):
    ui, root, runtime, *_ = lab
    p = root / "custom_components/nexhome"
    p.mkdir(parents=True)
    (p / "manifest.json").write_text('{"domain":"nexhome","version":"9.1.2"}')
    assert deploy(ui, confirm=True, output=lambda *_: None) == 2
    assert runtime.calls == []


@pytest.mark.parametrize(
    "change,code",
    [
        ("mount", "CONTAINER_CONFIG_MOUNT_MISMATCH"),
        ("managed", "SUPERVISOR_MANAGED_CONTAINER_REFUSED"),
    ],
)
def test_container_validates_real_target_before_control(tmp_path, change, code):
    info = {
        "Config": {"Env": []},
        "Mounts": [{"Destination": "/config", "Type": "bind", "RW": True, "Source": str(tmp_path)}],
    }
    if change == "mount":
        info["Mounts"][0]["Source"] = str(tmp_path / "wrong")
    else:
        info["Config"]["Env"] = ["SUPERVISOR_TOKEN=SYNTHETIC_TEST_ONLY"]
    calls = []

    def request(method, path):
        calls.append((method, path))
        return {"ApiVersion": "1.53", "MinAPIVersion": "1.44"} if path == "/version" else info

    with pytest.raises(InstallerError, match=code):
        ContainerLifecycle("ha", tmp_path, "PRIVATE_TEST", "http://localhost:8123", request=request)
    assert calls == [("GET", "/version"), ("GET", "/v1.47/containers/ha/json")]


def test_container_lifecycle_local_api_only(tmp_path):
    info = {
        "Config": {"Labels": {"io.hass.type": "core"}, "Env": []},
        "Mounts": [{"Destination": "/config", "Type": "bind", "RW": True, "Source": str(tmp_path)}],
        "State": {"Running": True},
    }
    calls = []

    def request(method, path):
        calls.append((method, path))
        if path == "/version":
            return {"ApiVersion": "1.53", "MinAPIVersion": "1.44"}
        return info if method == "GET" else None

    runtime = ContainerLifecycle("ha", tmp_path, "PRIVATE_TEST", "http://localhost:8123", request=request)
    runtime.stop()
    runtime.start()
    assert ("POST", "/v1.47/containers/ha/stop?t=30") in calls
    assert ("POST", "/v1.47/containers/ha/start") in calls
    with pytest.raises(InstallerError, match="CONTAINER_NAME_INVALID"):
        ContainerLifecycle("ha;reboot", tmp_path, "PRIVATE_TEST", "http://localhost:8123", request=request)


def test_private_token_file_requires_exclusive_permissions(tmp_path):
    from neighbor_launcher.bootstrap import read_private_token

    p = tmp_path / "temporary-auth"
    p.write_text("SYNTHETIC_TEST_ONLY")
    p.chmod(0o600)
    assert read_private_token(p) == "SYNTHETIC_TEST_ONLY"
    p.chmod(0o644)
    with pytest.raises(InstallerError, match="TOKEN_FILE_PERMISSIONS"):
        read_private_token(p)
    p.chmod(0o600)
    p.write_text("bad whitespace")
    with pytest.raises(InstallerError, match="TOKEN_FILE_INVALID"):
        read_private_token(p)
