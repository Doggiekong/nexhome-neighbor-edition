"""Pinned native HACS 2.0.5 persistence version, checked against installed source."""

from neighbor_installer.hacs import OFFICIAL, detect_hacs
from tests_installer.test_installer import write


def test_native_hacs_storage_version_6(tmp_path):
    write(tmp_path / "custom_components/hacs/manifest.json", {"version": "2.0.5"})
    write(
        tmp_path / ".storage/hacs.repositories",
        {"version": "6", "data": {"1": {"domain": "nexhome", "installed": True, "full_name": OFFICIAL}}},
    )
    write(tmp_path / ".storage/hacs.data", {"version": "6", "data": {"repositories": {}}})
    result = detect_hacs(tmp_path)
    assert not result["uncertain"]
    assert result["claims"][0]["origin"] == OFFICIAL
    write(tmp_path / "custom_components/hacs/manifest.json", {"version": "99.0.0"})
    assert detect_hacs(tmp_path)["uncertain"]
