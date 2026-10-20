"""Explicit migration preview, sanitized identity baselines and additive-only checks.

Never writes HA registry/configuration. Hashes configuration values in memory.
Code restoration does not promise registry rollback.
"""

from .files import InstallerError, digest, load

ENTITY_FIELDS = ('id', 'entity_id', 'unique_id', 'platform', 'name', 'original_name',
                 'hidden_by', 'disabled_by', 'area_id', 'device_id', 'icon', 'aliases', 'labels')
DEVICE_FIELDS = ('id', 'identifiers', 'config_entries', 'name_by_user', 'area_id', 'disabled_by')


def baseline(root, registry_view=None):
    storage = root / '.storage'
    entries = load(storage / 'core.config_entries', {'data': {'entries': []}})['data']['entries']
    selected = [e for e in entries if e['domain'] == 'nexhome']
    ids = {e['entry_id'] for e in selected}
    result = {'entries': {}, 'entities': {}, 'devices': {}, 'references': {}}
    for entry in selected:
        result['entries'][entry['entry_id']] = {
            **{k: entry.get(k) for k in ('entry_id', 'domain', 'unique_id', 'title', 'disabled_by', 'version', 'minor_version')},
            'options_sha256': digest(entry.get('options', {})),
            'data': {k: digest(v) for k, v in entry.get('data', {}).items()},
        }
    for collection, filename, fields in [
        ('entities', 'core.entity_registry', ENTITY_FIELDS),
        ('devices', 'core.device_registry', DEVICE_FIELDS),
    ]:
        rows = (registry_view[collection] if registry_view is not None else
                load(storage / filename, {'data': {collection: []}})['data'][collection])
        for row in rows:
            if collection == 'devices':
                # HA2026.10 v3 uses config_entry_id for a non-composite stored device.
                row = dict(row)
                row['config_entries'] = row.get('config_entries', [row['config_entry_id']] if row.get('config_entry_id') else [])
            relevant = row.get('config_entry_id') in ids if collection == 'entities' else bool(ids.intersection(row.get('config_entries', [])))
            if relevant:
                key = row['entity_id'] if collection == 'entities' else row['id']
                result[collection][key] = {k: row.get(k) for k in fields}
                if collection == 'entities':
                    if registry_view is not None and not isinstance(row.get('aliases'), list):
                        raise InstallerError('ENTITY_DETAILS_SCHEMA_UNSUPPORTED')
                    # HA's detailed API represents the computed-name sentinel as
                    # null, while storage keeps it outside the user alias list.
                    result[collection][key]['aliases'] = sorted(
                        a for a in (row.get('aliases') or []) if isinstance(a, str)
                    )
    if any(row['device_id'] and row['device_id'] not in result['devices'] for row in result['entities'].values()):
        raise InstallerError('DEVICE_SCHEMA_REQUIRES_SUPPORTED_REGISTRY_VIEW')
    # Hash user-owned references without trying to interpret or rewrite templates.
    paths = list(storage.glob('lovelace*')) + [storage / 'core.area_registry']
    paths += [root / n for n in ('configuration.yaml', 'automations.yaml', 'groups.yaml', 'scripts.yaml', 'scenes.yaml')]
    for path in paths:
        if path.is_symlink():
            raise InstallerError('IDENTITY_SYMLINK')
        if path.is_file():
            result['references'][str(path.relative_to(root))] = digest(path.read_bytes().hex())
    return result


def preview(root, semantics=None, registry_view=None):
    """Caller supplies only explicitly reviewed legacy→semantic approvals, not guesses."""
    captured = baseline(root, registry_view)
    approved = semantics or {}
    for legacy, record in approved.items():
        row = captured['entities'].get(legacy)
        if not row or row['hidden_by'] == 'user' or row['disabled_by'] or row['name'] or row['area_id']:
            raise InstallerError('SEMANTIC_APPROVAL_CONFLICTS_WITH_USER_INTENT')
        if record.get('legacy_unique_id') != row['unique_id'] or record.get('domain') not in {'light', 'fan'}:
            raise InstallerError('SEMANTIC_APPROVAL_INVALID')
    return {'schema': 1, 'baseline': captured, 'baseline_sha256': digest(captured),
            'semantics': approved, 'risk': 'ADDITIVE_FORWARD_ONLY_NO_REGISTRY_AUTORESTORE'}


def validate(root, plan, registry_view=None):
    before, after = plan['baseline'], baseline(root, registry_view)
    if digest(before) != plan['baseline_sha256']:
        raise InstallerError('MIGRATION_PREVIEW_TAMPERED')
    forward = False
    if before['references'] != after['references'] or set(before['entries']) != set(after['entries']):
        raise InstallerError('MIGRATION_IDENTITY_OR_REFERENCES_CHANGED')
    for identifier, original in before['entries'].items():
        current = after['entries'][identifier]
        for key in original:
            if key not in {'data', 'minor_version'} and original[key] != current[key]:
                raise InstallerError('MIGRATION_ENTRY_IDENTITY_CHANGED')
        for key, value in original['data'].items():
            if current['data'].get(key) != value:
                raise InstallerError('MIGRATION_STORED_DATA_CHANGED')
        added = set(current['data']) - set(original['data'])
        if added - {'identity_mode', 'sn_input'}:
            raise InstallerError('MIGRATION_UNEXPECTED_DATA_ADDITION')
        if 'identity_mode' in added and current['data']['identity_mode'] != digest('compat'):
            raise InstallerError('MIGRATION_MODE_CHANGED')
        if 'sn_input' in added and current['data']['sn_input'] != original['data'].get('sn'):
            raise InstallerError('MIGRATION_SERIAL_ALIAS_CHANGED')
        if current['minor_version'] != original['minor_version'] and not (
            original['version'] == 1 and original['minor_version'] in (None, 1) and current['minor_version'] == 2
        ):
            raise InstallerError('MIGRATION_SCHEMA_UNSUPPORTED')
        forward |= current != original
    if before['devices'] != after['devices']:
        raise InstallerError('MIGRATION_DEVICE_IDENTITY_CHANGED')
    allowed = plan['semantics']
    for identifier, original in before['entities'].items():
        current = after['entities'].get(identifier)
        if not current:
            raise InstallerError('MIGRATION_EXISTING_ENTITY_REMOVED')
        expected = dict(original)
        approval = allowed.get(identifier)
        if approval and original['hidden_by'] is None and current['hidden_by'] == 'integration':
            semantic_uid = approval['semantic_unique_id']
            marker = next((load(p, {'data': {}}).get('data', {}).get(original['unique_id'])
                           for p in (root / '.storage').glob('nexhome.semantic.*')
                           if load(p, {'data': {}}).get('data', {}).get(original['unique_id'])), None)
            if not marker or marker.get('owner') != 'nexhome' or marker.get('semantic_unique_id') != semantic_uid:
                raise InstallerError('MIGRATION_HIDDEN_WITHOUT_OWNERSHIP')
            expected['hidden_by'] = 'integration'
        if current != expected:
            raise InstallerError('MIGRATION_USER_METADATA_CHANGED')
        forward |= current != original
    for identifier, row in after['entities'].items():
        if identifier in before['entities']:
            continue
        matches = [v for v in allowed.values() if v['semantic_unique_id'] == row['unique_id']]
        if len(matches) != 1 or identifier.split('.')[0] != matches[0]['domain']:
            raise InstallerError('MIGRATION_UNAPPROVED_ENTITY_ADDITION')
        legacy = before['entities'][next(k for k, v in allowed.items() if v is matches[0])]
        if row['device_id'] != legacy['device_id'] or row['platform'] != 'nexhome':
            raise InstallerError('MIGRATION_SEMANTIC_DEVICE_CHANGED')
        forward = True
    return 'FORWARD_ONLY_BUT_COMPATIBLE' if forward else 'REVERSIBLE'
