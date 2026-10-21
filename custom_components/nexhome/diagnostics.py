"""User-exported allowlisted diagnostics. No network requests and no property values."""

from collections import Counter

from homeassistant.const import __version__ as HA_VERSION

from .const import PRODUCT_ID, PRODUCT_VERSION, UPSTREAM_BASE_VERSION, VERSION
from .installation import installation_status
from .models import model_status


async def async_get_config_entry_diagnostics(hass, entry):
    runtime = getattr(entry, "runtime_data", None)
    result = {"product_id": PRODUCT_ID, "product_version": PRODUCT_VERSION,
              "upstream_base_version": UPSTREAM_BASE_VERSION, "ha_version": HA_VERSION, "integration_version": VERSION, "entry_state": entry.state.value}
    result['installation'] = installation_status(hass)
    if runtime is None:
        return result | {"runtime_available": False}
    coordinator = runtime.coordinator
    result.update(
        {
            "runtime_available": True,
            "gateway_reachable": any(
                coordinator.is_fresh(address, [identifier]) for address, identifier in coordinator.values
            ),
            "transport": {
                key: runtime.client.stats.get(key, 0) for key in ("requests", "errors", "timeouts")
            },
            "queue": {
                "control_waiting": len(runtime.client.scheduler.control),
                "poll_waiting": len(runtime.client.scheduler.poll),
                "inflight": runtime.client.scheduler.inflight,
                "rejected": runtime.client.scheduler.rejected,
            },
            "coordinator": {
                "missing_properties": coordinator.missing_count,
                "pending_properties": len(coordinator.pending),
                "last_update_success": coordinator.last_update_success,
            },
            "identity_mode": runtime.mode,
            "migration": dict(Counter(r["status"] for r in runtime.plan.records.values())),
            "entities": [],
        }
    )
    aliases = {spec.unique_id: f"entity-{i + 1}" for i, spec in enumerate(runtime.plan.specs)}
    for index, spec in enumerate(runtime.plan.specs):
        properties = []
        for identifier in spec.identifiers:
            age = coordinator.clock() - coordinator.fresh.get((spec.address, identifier), -float("inf"))
            properties.append(
                {
                    "identifier": identifier,
                    "fresh": coordinator.is_fresh(spec.address, [identifier]),
                    "age_seconds": round(age, 1) if age != float("inf") else None,
                }
            )
        result["entities"].append(
            {
                "id": f"entity-{index + 1}",
                "device_type": spec.type_id,
                "domain": spec.domain,
                "semantic": spec.semantic,
                "legacy_link_present": spec.legacy_unique_id is not None,
                "legacy_entity": aliases.get(spec.legacy_unique_id),
                "validation": model_status(spec.type_id),
                "properties": properties,
            }
        )
    return result
