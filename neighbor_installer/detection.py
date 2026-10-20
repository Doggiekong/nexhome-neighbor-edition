"""Conservative environment, source and exclusive update-owner classification."""

from enum import StrEnum

from .files import InstallerError, digest, guarded_root, inventory, load


class Owner(StrEnum):
    OFFICIAL_HACS = "OFFICIAL_HACS"
    COMMUNITY_HACS = "COMMUNITY_HACS"
    NEIGHBOR_INSTALLER = "NEIGHBOR_INSTALLER"
    MANUAL_UNKNOWN = "MANUAL_UNKNOWN"


OFFICIAL = "nexhome-org/nexhome-homeassistant-component"
COMMUNITY = "Doggiekong/nexhome-neighbor-edition"


def detect(root, trusted_trees=None):
    root = guarded_root(root)
    target = root / "custom_components/nexhome"
    files = inventory(target)
    exists = target.exists()
    fingerprint = digest(files)
    hacs_present = (root / "custom_components/hacs").exists()
    raw = load(root / ".storage/hacs.repositories")
    claims = []
    uncertain = raw is not None
    # Read-only format adapter. Unknown schema/fields never establish ownership.
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        repositories = raw["data"].get("repositories", raw["data"])
        if isinstance(repositories, dict):
            uncertain = False
            for repo in repositories.values():
                if not isinstance(repo, dict):
                    uncertain = True
                    continue
                if repo.get("domain") == "nexhome" and repo.get("installed") is True:
                    claims.append(repo.get("full_name"))
    marker = load(root / ".nexhome-installer/owner.json")
    owner = None
    reason = "ABSENT"
    if claims:
        matched = len(claims) == 1 and (trusted_trees or {}).get(claims[0]) == fingerprint
        if matched and not marker and not uncertain and hacs_present:
            owner = {OFFICIAL: Owner.OFFICIAL_HACS, COMMUNITY: Owner.COMMUNITY_HACS}.get(claims[0])
        reason = "HACS_OWNER" if owner else "HACS_CONFLICT_OR_UNVERIFIED_TREE"
    elif marker and not uncertain:
        if (
            marker.get("owner") == Owner.NEIGHBOR_INSTALLER
            and marker.get("files") == files
            and exists
        ):
            owner = Owner.NEIGHBOR_INSTALLER
            reason = "INSTALLER_MARKER_AND_HASHES"
        else:
            reason = "MARKER_TREE_MISMATCH"
    elif exists or uncertain:
        reason = "UNVERIFIED_EXISTING_FILES_OR_HACS_SCHEMA"
    if owner is None and (exists or claims or marker or uncertain):
        owner = Owner.MANUAL_UNKNOWN
    entries = load(root / ".storage/core.config_entries", {"data": {"entries": []}})
    rows = entries.get("data", {}).get("entries", [])
    if not isinstance(rows, list):
        raise InstallerError("ENTRY_METADATA_INVALID")
    nexhome = [row for row in rows if row.get("domain") == "nexhome"]
    manifest = load(target / "manifest.json", {}) if exists else {}
    return {
        "installed": exists,
        "version": manifest.get("version"),
        "owner": owner,
        "reason": reason,
        "tree_sha256": fingerprint,
        "file_count": len(files),
        "hacs_present": hacs_present,
        "hacs_claim_count": len(claims),
        "hacs_schema_uncertain": uncertain,
        "entry_count": len(nexhome),
        "enabled_entries": sum(row.get("disabled_by") is None for row in nexhome),
        "entry_repair": "EXPLICIT_DIAGNOSIS_REQUIRED" if nexhome else "NOT_NEEDED",
    }


def identity_fingerprint(root):
    """Do not save any registry contents or sensitive configuration values."""
    storage = root / ".storage"
    selected = {}
    specifications = {
        "core.config_entries": ("entries", ("entry_id", "domain", "unique_id", "title", "disabled_by", "options")),
        "core.entity_registry": (
            "entities",
            ("entity_id", "unique_id", "device_id", "config_entry_id", "name", "icon", "area_id", "hidden_by", "disabled_by"),
        ),
        "core.device_registry": (
            "devices", ("id", "identifiers", "config_entries", "name_by_user", "area_id", "disabled_by")
        ),
        "core.area_registry": ("areas", ("id", "name", "icon", "floor_id")),
    }
    for name, (collection, keys) in specifications.items():
        data = load(storage / name, {"data": {collection: []}}).get("data", {}).get(collection, [])
        selected[name] = [{key: row.get(key) for key in keys} for row in data]
        if name == 'core.config_entries':
            for row, safe in zip(data, selected[name], strict=True):
                if row.get('domain') == 'nexhome':
                    safe['data_sha256'] = digest(row.get('data', {}))
    for path in sorted(storage.glob("lovelace*")):
        if path.is_file():
            selected[path.name] = digest(load(path))
    for name in ("automations.yaml", "groups.yaml", "scripts.yaml", "scenes.yaml", "configuration.yaml"):
        path = root / name
        if path.is_symlink():
            raise InstallerError("IDENTITY_SYMLINK")
        if path.is_file():
            selected[name] = digest(path.read_bytes().hex())
    return digest(selected)
