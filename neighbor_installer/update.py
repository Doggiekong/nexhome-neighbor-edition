"""User-confirmed, pinned local artifact update; no timer or silent downloads."""

from .detection import Owner
from .files import InstallerError, digest
from .ownership import refuse_conflicting_write


def preview_update(installer, artifact):
    detected = installer.inspect()
    refuse_conflicting_write(detected)
    if detected['owner'] != Owner.NEIGHBOR_INSTALLER:
        raise InstallerError('INSTALLER_OWNER_REQUIRED')
    artifact = artifact.revalidate()
    proposal = {'owner': detected['owner'], 'from_version': detected['version'],
                'to_version': artifact.metadata['version'], 'source': artifact.metadata['origin'],
                'revision': artifact.metadata['revision'], 'before_tree': detected['tree_sha256'],
                'artifact_manifest_sha256': artifact.manifest_sha256}
    proposal['confirmation_sha256'] = digest(proposal)
    return proposal


def apply_update(installer, artifact, proposal, confirmation):
    if confirmation != proposal.get('confirmation_sha256'):
        raise InstallerError('EXPLICIT_UPDATE_CONFIRMATION_REQUIRED')
    if preview_update(installer, artifact) != proposal:
        raise InstallerError('UPDATE_PREVIEW_STALE')
    return installer.apply(artifact)
