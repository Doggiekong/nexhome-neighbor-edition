"""Owner policy independent of HACS storage details."""

from .detection import Owner
from .files import InstallerError


def verify_expected_owner(detected, expected):
    if detected['owner'] != expected:
        raise InstallerError('EXPECTED_OWNER_NOT_VERIFIED')
    return True


def refuse_conflicting_write(detected):
    if detected['owner'] == Owner.OWNERSHIP_CONFLICT:
        raise InstallerError('OWNERSHIP_CONFLICT_REFUSED')
    if detected['hacs_claim_count'] or detected['hacs_schema_uncertain']:
        raise InstallerError('HACS_IS_UPDATE_OWNER_OR_UNCERTAIN')


def verify_post_migration_state(detected, expected):
    verify_expected_owner(detected, expected)
    if expected == Owner.NEIGHBOR_INSTALLER:
        refuse_conflicting_write(detected)
    return True
