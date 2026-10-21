"""Separate Neighbor product lineage from upstream and early internal Candidates."""
from packaging.version import Version

from .files import InstallerError, load

PRODUCT_ID = 'nexhome-neighbor-edition'
SCHEME = 'neighbor-independent-v1'
LEGACY = {'1.1.17.dev1', '1.1.17.dev2', '1.1.17.dev3', '1.1.17.dev4'}
FIELDS = ('product_id', 'product_version', 'upstream_base_version', 'version_scheme')


def validate_identity(info, version):
    if (not isinstance(info, dict) or set(info) != set(FIELDS)
            or info.get('product_id') != PRODUCT_ID or info.get('version_scheme') != SCHEME
            or info.get('product_version') != version or info.get('upstream_base_version') != '1.1.16'):
        raise InstallerError('PRODUCT_IDENTITY_INVALID')
    return info


def artifact_identity(metadata):
    return {k: metadata[k] for k in FIELDS} if metadata.get('schema') == 2 else {}


def installed_identity(target, owner):
    raw = load(target / 'product.json')
    if raw is not None:
        manifest = load(target / 'manifest.json', {})
        return validate_identity(raw, manifest.get('version'))
    return {}


def relation(detected, metadata):
    """Only verified Installer ownership may cross the explicit historical lineage."""
    current, target = detected.get('version'), metadata['version']
    if metadata.get('schema') == 2:
        if detected.get('product_id') == PRODUCT_ID and detected.get('version_scheme') == SCHEME:
            pass
        elif (detected.get('owner') == 'NEIGHBOR_INSTALLER' and current in LEGACY
              and not detected.get('product_id')):
            return 'upgrade'
        else:
            raise InstallerError('VERSION_LINEAGE_UNVERIFIED')
    elif detected.get('product_id'):
        raise InstallerError('LEGACY_TARGET_REFUSED')
    a, b = Version(current), Version(target)
    return 'upgrade' if a < b else 'same' if a == b else 'downgrade'
