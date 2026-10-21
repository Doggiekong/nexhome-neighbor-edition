"""Conservative environment, source and exclusive update-owner classification."""

from enum import StrEnum

from .files import InstallerError, digest, guarded_root, inventory, load
from .hacs import COMMUNITY, OFFICIAL, detect_hacs
from .product import artifact_identity, installed_identity


class Owner(StrEnum):
    OFFICIAL_HACS = "OFFICIAL_HACS"
    COMMUNITY_HACS = "COMMUNITY_HACS"
    NEIGHBOR_INSTALLER = "NEIGHBOR_INSTALLER"
    MANUAL_UNKNOWN = "MANUAL_UNKNOWN"
    OWNERSHIP_CONFLICT = "OWNERSHIP_CONFLICT"


def _verified_marker(root, marker, files):
    if not isinstance(marker, dict):
        return False
    identifier = marker.get('transaction_id', '')
    if not isinstance(identifier, str) or len(identifier) != 32 or any(c not in '0123456789abcdef' for c in identifier):
        return False
    transaction = load(root / '.nexhome-installer/transactions' / identifier / 'record.json')
    if not isinstance(transaction, dict) or not isinstance(transaction.get('artifact'), dict):
        return False
    artifact = transaction['artifact']
    return (
        marker.get('owner') == Owner.NEIGHBOR_INSTALLER and marker.get('files') == files
        and marker.get('version') == artifact.get('version')
        and all(marker.get(k) == v for k, v in artifact_identity(artifact).items())
        and transaction.get('id') == identifier and transaction.get('phase') == 'COMMITTED'
        and artifact.get('files') == files and artifact.get('revision') == marker.get('revision')
        and artifact.get('origin') == marker.get('origin')
    )


def detect(root, trusted_trees=None):
    root = guarded_root(root)
    target = root / "custom_components/nexhome"
    files = inventory(target)
    exists = target.exists()
    fingerprint = digest(files)
    hacs = detect_hacs(root)
    hacs_present = hacs['present']
    claims = [row['origin'] for row in hacs['claims']]
    uncertain = hacs['uncertain']
    marker = load(root / ".nexhome-installer/owner.json")
    owner = None
    reason = "ABSENT"
    if claims:
        matched = len(claims) == 1 and (trusted_trees or {}).get(claims[0]) == fingerprint
        if marker or len(claims) > 1 or not exists or not hacs_present:
            owner = Owner.OWNERSHIP_CONFLICT
            reason = 'CONTRADICTORY_OWNER_EVIDENCE'
        elif claims[0] in (trusted_trees or {}) and not matched:
            owner = Owner.OWNERSHIP_CONFLICT
            reason = 'HACS_SOURCE_TREE_DISAGREEMENT'
        elif matched and not uncertain:
            owner = {OFFICIAL: Owner.OFFICIAL_HACS, COMMUNITY: Owner.COMMUNITY_HACS}.get(claims[0])
            reason = 'HACS_OWNER' if owner else 'UNKNOWN_HACS_SOURCE'
        else:
            reason = 'HACS_UNVERIFIED_TREE'
    elif marker and not uncertain:
        if exists and _verified_marker(root, marker, files):
            owner = Owner.NEIGHBOR_INSTALLER
            reason = "INSTALLER_MARKER_AND_HASHES"
        else:
            owner = Owner.OWNERSHIP_CONFLICT
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
        **(installed_identity(target, owner) if exists and owner in {Owner.NEIGHBOR_INSTALLER, Owner.COMMUNITY_HACS} else {}),
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


def identity_fingerprint(root, *, exclude_hacs=False, exclude_nexhome=False):
    """Do not save any registry contents or sensitive configuration values."""
    storage = root / ".storage"
    selected = {}
    excluded_domains = ({'hacs'} if exclude_hacs else set()) | ({'nexhome'} if exclude_nexhome else set())
    excluded_ids = set()
    if excluded_domains:
        entries = load(storage / 'core.config_entries', {'data': {'entries': []}})['data']['entries']
        excluded_ids = {row['entry_id'] for row in entries if row.get('domain') in excluded_domains}
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
        if excluded_domains:
            if name == 'core.config_entries':
                data = [row for row in data if row.get('domain') not in excluded_domains]
            elif name == 'core.entity_registry':
                data = [row for row in data if row.get('platform') not in excluded_domains and row.get('config_entry_id') not in excluded_ids]
            elif name == 'core.device_registry':
                def only_hacs(row):
                    ids = set(row.get('config_entries') or ([row['config_entry_id']] if row.get('config_entry_id') else []))
                    return bool(ids) and ids <= excluded_ids
                data = [row for row in data if not only_hacs(row)]
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
