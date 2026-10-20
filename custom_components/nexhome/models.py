"""Protocol metadata, stable identities and entity descriptions, never household names."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .const import DOMAIN

CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class EntitySpec:
    device_id: str
    address: str
    type_id: str
    device_name: str
    key: str
    domain: str
    identifiers: tuple[str, ...]
    unique_id: str
    device_identifier: str
    semantic: bool = False
    legacy_unique_id: str | None = None

    @property
    def config(self):
        return CATALOG[self.type_id]["entities"][self.key]

    @property
    def required_groups(self):
        """Alternative complete core-property sets; everything else is optional."""
        if self.domain == "climate":
            return [
                {"PowerSwitch", "TemperatureSet"} | (set() if self.type_id in {"11", "35"} else {"WorkMode"})
            ]
        if self.domain == "cover":
            core = {"Open", "Close"} | (set() if self.type_id == "30" else {"Stop"})
            return [{"Location"}, core] if self.type_id == "6" else [core]
        return [{"PowerSwitch"}] if "PowerSwitch" in self.identifiers else [set(self.identifiers)]


def descriptions(devices, serial, mode):
    specs = []
    seen = set()
    hub_key = hashlib.sha256(serial.encode()).hexdigest()[:20]
    for device in devices:
        if not isinstance(device, dict):
            continue
        type_id = str(device.get("type", ""))
        address, device_id = device.get("address"), device.get("id")
        if type_id not in CATALOG or not isinstance(address, str) or not isinstance(device_id, str):
            continue
        if not address or len(address) > 256 or not device_id or address in seen:
            continue
        seen.add(address)
        for key, config in CATALOG[type_id]["entities"].items():
            identifiers = tuple(config["identifiers"])
            domain = config["type"]
            if type_id == "6":
                identifiers = tuple(dict.fromkeys((*identifiers, "Open", "Close", "Stop")))
            # Only a protocol-classified lamp changes domain; not a name heuristic.
            if mode == "fresh" and type_id == "1":
                domain = "light"
            unique = (
                f"{DOMAIN}.{device_id}_{key}" if mode == "compat" else f"gateway-{hub_key}:{address}:{key}"
            )
            physical = device_id if mode == "compat" else f"gateway-{hub_key}:{address}"
            specs.append(
                EntitySpec(
                    device_id,
                    address,
                    type_id,
                    str(device.get("name") or "NEXhome"),
                    key,
                    domain,
                    identifiers,
                    unique,
                    physical,
                )
            )
    return specs


def model_status(type_id):
    if type_id in {"1", "2", "3", "6"}:
        return "FIELD_VERIFIED_BASELINE"
    if type_id == "11":
        return "FIELD_VERIFIED_AVAILABILITY_ONLY"
    return "IMPLEMENTED_NOT_FIELD_VERIFIED" if type_id in CATALOG else "UNSUPPORTED_UNKNOWN"
