"""Offline repository/model contract, not a production installation test."""

import ast
import json
from pathlib import Path

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from packaging.version import Version

from custom_components.nexhome.climate import NexhomeClimate
from custom_components.nexhome.const import VERSION
from custom_components.nexhome.cover import NexhomeCover
from custom_components.nexhome.fan import NexhomeFan
from custom_components.nexhome.light import NexhomeLight
from custom_components.nexhome.models import CATALOG
from custom_components.nexhome.sensor import NexhomeSensor
from custom_components.nexhome.switch import NexhomeSwitch

from .conftest import runtime_for

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("type_id", sorted(CATALOG))
async def test_all_catalog_models_handle_absent_properties(coordinator, type_id):
    runtime, _ = runtime_for(coordinator, type_id)
    classes = {
        "light": NexhomeLight,
        "fan": NexhomeFan,
        "climate": NexhomeClimate,
        "cover": NexhomeCover,
        "sensor": NexhomeSensor,
        "switch": NexhomeSwitch,
    }
    for spec in runtime.plan.specs:
        entity = classes[spec.domain](runtime, spec)
        assert not entity.available
        if spec.domain == "sensor":
            if entity.device_class:
                SensorDeviceClass(entity.device_class)
            assert entity.native_value is None
        elif spec.domain == "climate":
            assert entity.current_temperature is None and entity.hvac_mode is None
        elif spec.domain == "cover":
            assert entity.current_cover_position is None and entity.is_closed is None
        else:
            assert entity.is_on is None


def test_manifest_version_json_and_no_debug_print():
    manifest = json.loads((ROOT / "custom_components/nexhome/manifest.json").read_text())
    assert manifest["version"] == VERSION == "0.1.0" and Version(VERSION).release == (0, 1, 0)
    assert manifest["domain"] == "nexhome" and manifest["config_flow"]
    assert manifest["requirements"] == [] and manifest["dependencies"] == ["network"]
    for path in (ROOT / "custom_components").rglob("*.json"):
        json.loads(path.read_text())
    for path in (ROOT / "custom_components").rglob("*.py"):
        tree = ast.parse(path.read_text())
        assert not any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"
            for n in ast.walk(tree)
        ), path.name
