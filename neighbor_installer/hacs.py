"""Read-only HACS evidence adapter; never mutate HACS storage or call private APIs.

Storage shape pinned to upstream 2.0.5 utils/data.py. This is an internal,
version-sensitive evidence source, not a supported HACS management interface.
Unknown shapes fail closed. Supported UI is the only source-transfer writer.
"""

from .files import load

OFFICIAL = "nexhome-org/nexhome-homeassistant-component"
COMMUNITY = "Doggiekong/nexhome-neighbor-edition"


def detect_hacs(root):
    manifest = load(root / 'custom_components/hacs/manifest.json', {})
    present = (root / 'custom_components/hacs').exists()
    raw = load(root / '.storage/hacs.repositories')
    fallback = load(root / '.storage/hacs.data')
    uncertain = False
    # HACS 2.0.5 const.VERSION_STORAGE is the string '6', not HA's usual integer 1.
    supported_versions = (1, '6') if manifest.get('version') == '2.0.5' else (1,)
    if any(isinstance(item, dict) and item.get('version', 1) not in supported_versions for item in (raw, fallback)):
        uncertain = True
    rows = []
    if raw is not None and not (isinstance(raw, dict) and raw.get('data') == {}):
        data = raw.get('data') if isinstance(raw, dict) else None
        # Earlier installer fixtures used a nested repositories mapping.
        if isinstance(data, dict) and isinstance(data.get('repositories'), dict):
            data = data['repositories']
        if not isinstance(data, dict):
            uncertain = True
        else:
            rows = list(data.values())
    elif fallback is not None:
        data = fallback.get('data', {}).get('repositories') if isinstance(fallback, dict) else None
        if not isinstance(data, dict) or any(not isinstance(v, list) for v in data.values()):
            uncertain = True
        else:
            rows = [dict(row, category=category) if isinstance(row, dict) else row
                    for category, items in data.items() for row in items]
    claims = []
    for row in rows:
        if not isinstance(row, dict):
            uncertain = True
            continue
        if row.get('domain') != 'nexhome':
            # Known repo with missing domain must not silently disappear.
            if row.get('full_name') in (OFFICIAL, COMMUNITY) and row.get('installed') is True:
                uncertain = True
            continue
        if row.get('installed') is True:
            origin = row.get('full_name')
            if not isinstance(origin, str) or row.get('category', 'integration') != 'integration':
                uncertain = True
                continue
            claims.append({'origin': origin, 'version': row.get('version_installed')})
        elif row.get('installed') not in (None, False):
            uncertain = True
    if claims and manifest.get('version') != '2.0.5':
        uncertain = True
    return {'present': present, 'version': manifest.get('version'),
            'claims': claims, 'uncertain': uncertain, 'read_only_adapter': 'HACS-2.0.5'}


def detect_repository_origin(evidence):
    return evidence['claims'][0]['origin'] if len(evidence['claims']) == 1 else None


def detect_installed_version(evidence):
    return evidence['claims'][0]['version'] if len(evidence['claims']) == 1 else None
