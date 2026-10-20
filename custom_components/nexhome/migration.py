"""Conservative, idempotent compatibility planning. User intent wins."""

from dataclasses import dataclass, replace

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


@dataclass
class CompatibilityPlan:
    specs: list
    records: dict


def user_customized(row):
    """HA computed-name alias sentinels are defaults, not user-assigned aliases."""
    return any((row.name, row.icon, row.area_id, getattr(row, "labels", None))) or any(
        isinstance(alias, str) and bool(alias) for alias in getattr(row, "aliases", ())
    )


def plan_compatibility(specs, rows, markers, wrappers=frozenset()):
    """Read registry metadata only; never inspect or rewrite user YAML/templates."""
    records = {}
    output = []
    registry = {(row.domain, row.unique_id): row for row in rows}
    for spec in specs:
        target_domain = (
            "light"
            if spec.domain == "switch" and spec.type_id == "1"
            else "fan"
            if spec.domain == "fan"
            else None
        )
        if target_domain is None:
            output.append(spec)
            continue
        legacy = registry.get(("switch", spec.unique_id))
        if legacy is None:
            output.append(spec)
            records[spec.unique_id] = {"status": "legacy_registry_absent"}
            continue  # Existing entry without a proven legacy identity stays compatible.
        output.append(replace(spec, domain="switch"))
        owned = markers.get(spec.unique_id, {})
        semantic_uid = f"{spec.unique_id}:semantic:{target_domain}:v1"
        existing_semantic = registry.get((target_domain, semantic_uid))
        hidden_by = getattr(legacy.hidden_by, "value", legacy.hidden_by)
        disabled_by = getattr(legacy.disabled_by, "value", legacy.disabled_by)
        customized = user_customized(legacy)
        if (
            owned.get("owner") == DOMAIN
            and owned.get("semantic_unique_id") == semantic_uid
            and existing_semantic
        ):
            reason = "owned_semantic_reused"
        elif hidden_by == "user" or disabled_by:
            records[spec.unique_id] = {"status": "user_intent_skip"}
            continue
        elif customized or legacy.entity_id in wrappers:
            records[spec.unique_id] = {"status": "customization_or_wrapper_skip"}
            continue
        elif hidden_by is not None:
            # An unowned integration-hidden row might belong to earlier customization.
            records[spec.unique_id] = {"status": "unowned_hidden_skip"}
            continue
        else:
            reason = "semantic_candidate"
        output.append(
            replace(
                spec,
                domain=target_domain,
                unique_id=semantic_uid,
                semantic=True,
                legacy_unique_id=spec.unique_id,
            )
        )
        records[spec.unique_id] = {
            "status": reason,
            "semantic_unique_id": semantic_uid,
            "legacy_entity_id": legacy.entity_id,
        }
    return CompatibilityPlan(output, records)


def related_wrappers(hass):
    """Only HA's explicit switch-as-X link is reliable; do not guess template names."""
    return frozenset(
        e.data.get("entity_id")
        for e in hass.config_entries.async_entries("switch_as_x")
        if isinstance(e.data.get("entity_id"), str)
    )


async def async_complete_semantic(hass, runtime, spec):
    """Hide, never disable, the old switch only after the new entity exists."""
    if not spec.semantic:
        return
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", DOMAIN, spec.legacy_unique_id)
    legacy = registry.async_get(entity_id) if entity_id else None
    if not legacy or legacy.hidden_by == er.RegistryEntryHider.USER or legacy.disabled_by:
        return
    if user_customized(legacy):
        return
    record = runtime.plan.records[spec.legacy_unique_id]
    if record["status"] == "semantic_candidate" and legacy.hidden_by is None:
        registry.async_update_entity(entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION)
    runtime.markers[spec.legacy_unique_id] = {"semantic_unique_id": spec.unique_id, "owner": "nexhome"}
    await runtime.store.async_save(runtime.markers)
