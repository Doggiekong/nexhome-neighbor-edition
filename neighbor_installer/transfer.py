"""Explicit, resumable owner handoff. HACS operations are supported UI steps.

Never restore HACS metadata, remove config entries, or claim atomic channel rollback.
A released HACS source cannot be recreated by a file rollback: recovery requires UI.
"""

import uuid

from .detection import Owner
from .files import InstallerError, copy_tree, digest, durable, inventory, load, lock
from .identity import transfer_identity
from .ownership import verify_post_migration_state

TERMINAL = {'COMMITTED', 'CANCELLED'}
TRANSITIONS = {
    None: {Owner.NEIGHBOR_INSTALLER, Owner.COMMUNITY_HACS},
    Owner.OFFICIAL_HACS: {Owner.NEIGHBOR_INSTALLER, Owner.COMMUNITY_HACS},
    Owner.NEIGHBOR_INSTALLER: {Owner.COMMUNITY_HACS},
    Owner.COMMUNITY_HACS: {Owner.COMMUNITY_HACS},
    Owner.MANUAL_UNKNOWN: {Owner.NEIGHBOR_INSTALLER, Owner.COMMUNITY_HACS},
}


class Transfer:
    def __init__(self, installer):
        self.installer = installer
        self.root = installer.root
        self.state = installer.state

    def _identity(self):
        return transfer_identity(self.root, self.installer._registry_view())

    def _save(self, record, phase):
        record['phase'] = phase
        record.setdefault('history', []).append(phase)
        durable(self.state / 'transfers' / record['id'] / 'record.json', record)
        durable(self.state / 'transfer-active.json', {'id': record['id'], 'phase': phase})

    def _load(self):
        active = load(self.state / 'transfer-active.json')
        identifier = active.get('id', '') if isinstance(active, dict) else ''
        if len(identifier) != 32 or any(c not in '0123456789abcdef' for c in identifier):
            raise InstallerError('TRANSFER_ID_INVALID')
        record = load(self.state / 'transfers' / identifier / 'record.json')
        if not record or record.get('id') != identifier:
            raise InstallerError('TRANSFER_RECORD_INVALID')
        return record

    def preview(self, destination):
        before = self.installer.inspect()
        if destination not in TRANSITIONS.get(before['owner'], set()):
            raise InstallerError('OWNER_TRANSITION_REFUSED')
        if before['hacs_schema_uncertain']:
            raise InstallerError('HACS_SCHEMA_UNCERTAIN')
        proposal = {'schema': 1, 'before': before, 'destination': destination,
                    'identity_sha256': self._identity(),
                    'hacs_ui_step_required': before['hacs_claim_count'] > 0 or destination == Owner.COMMUNITY_HACS,
                    'rollback': 'RECOVERY_REQUIRED_AFTER_EXTERNAL_SOURCE_CHANGE'}
        proposal['confirmation_sha256'] = digest(proposal)
        return proposal

    def begin(self, proposal, confirmation):
        with lock(self.root):
            self.installer._pending()
            if confirmation != proposal.get('confirmation_sha256'):
                raise InstallerError('EXPLICIT_TRANSFER_CONFIRMATION_REQUIRED')
            if self.preview(proposal['destination']) != proposal:
                raise InstallerError('TRANSFER_PREVIEW_STALE')
            record = {'id': uuid.uuid4().hex, 'proposal': proposal,
                      'before_files': inventory(self.installer.target),
                      'before_owner_marker': load(self.state / 'owner.json')}
            self._save(record, 'PREVIEW')
            backup = self.state / 'transfers' / record['id'] / 'backup'
            if self.installer.target.exists():
                copy_tree(self.installer.target, backup, private=True)
                if inventory(backup) != record['before_files']:
                    self._save(record, 'RECOVERY_REQUIRED')
                    raise InstallerError('TRANSFER_BACKUP_INVALID')
            self._save(record, 'BACKUP')
            return record

    def release_installer(self):
        """Explicit release of our own marker only, before supported HACS UI install."""
        with lock(self.root):
            record = self._load()
            if (record['phase'] != 'BACKUP'
                    or record['proposal']['before']['owner'] != Owner.NEIGHBOR_INSTALLER
                    or record['proposal']['destination'] != Owner.COMMUNITY_HACS):
                raise InstallerError('TRANSFER_PHASE_INVALID')
            if self.installer.inspect() != record['proposal']['before']:
                raise InstallerError('TRANSFER_PREVIEW_STALE')
            if self._identity() != record['proposal']['identity_sha256']:
                raise InstallerError('TRANSFER_IDENTITY_CHANGED')
            self._save(record, 'RELEASING_INSTALLER')
            (self.state / 'owner.json').unlink()
            self._save(record, 'SOURCE_RELEASED')
            return {'status': 'SOURCE_RELEASED', 'next': 'HACS_SUPPORTED_UI_INSTALL'}

    def verify_release(self):
        """Call after user removes source in HACS UI; never delete its metadata here."""
        with lock(self.root):
            record = self._load()
            if record['phase'] not in {'BACKUP', 'SOURCE_RELEASED'}:
                raise InstallerError('TRANSFER_PHASE_INVALID')
            detected = self.installer.inspect()
            if detected['hacs_claim_count'] or detected['hacs_schema_uncertain']:
                raise InstallerError('HACS_SOURCE_NOT_RELEASED')
            current = inventory(self.installer.target)
            if current not in ({}, record['before_files']):
                raise InstallerError('TRANSFER_UNEXPECTED_FILES')
            if self._identity() != record['proposal']['identity_sha256']:
                self._save(record, 'RECOVERY_REQUIRED')
                raise InstallerError('TRANSFER_IDENTITY_CHANGED')
            self._save(record, 'SOURCE_RELEASED')
            return record

    def deploy_installer(self, artifact, *, migration_preview=None):
        with lock(self.root):
            record = self._load()
            if record['proposal']['destination'] != Owner.NEIGHBOR_INSTALLER:
                raise InstallerError('HACS_DESTINATION_USE_SUPPORTED_UI')
            if record['phase'] != 'SOURCE_RELEASED':
                raise InstallerError('TRANSFER_PHASE_INVALID')
            detected = self.installer.inspect()
            if detected['hacs_claim_count'] or detected['hacs_schema_uncertain']:
                raise InstallerError('HACS_SOURCE_NOT_RELEASED')
            if inventory(self.installer.target) not in ({}, record['before_files']):
                raise InstallerError('TRANSFER_UNEXPECTED_FILES')
            if self._identity() != record['proposal']['identity_sha256']:
                raise InstallerError('TRANSFER_IDENTITY_CHANGED')
            record['artifact_manifest_sha256'] = artifact.manifest_sha256
            self._save(record, 'DEPLOY')
        # Engine takes the same lock and validates this exact handoff identifier.
        try:
            result = self.installer.apply(artifact, manual_fingerprint=detected['tree_sha256'],
                                          migration_preview=migration_preview, transfer_id=record['id'])
            if result['status'] not in {'COMMITTED', 'NO_OP'}:
                raise InstallerError('TRANSFER_DEPLOY_NOT_COMMITTED')
            return self.finish()
        except Exception:
            with lock(self.root):
                record = self._load()
                self._save(record, 'RECOVERY_REQUIRED')
            raise

    def finish(self):
        with lock(self.root):
            record = self._load()
            if record['phase'] == 'COMMITTED':
                verify_post_migration_state(self.installer.inspect(), record['proposal']['destination'])
                return {'status': 'NO_OP', 'transfer_id': record['id'],
                        'owner': record['proposal']['destination']}
            if record['phase'] not in {'BACKUP', 'SOURCE_RELEASED', 'DEPLOY', 'RECOVERY_REQUIRED'}:
                raise InstallerError('TRANSFER_PHASE_INVALID')
            self._save(record, 'HEALTH_CHECK')
            try:
                # HACS UI owns file deployment; we own only the explicit activation
                # checkpoint. Restart ensures no old Python module remains loaded.
                if record['proposal']['destination'] == Owner.COMMUNITY_HACS:
                    verify_post_migration_state(self.installer.inspect(), Owner.COMMUNITY_HACS)
                    before = self.installer.lifecycle.probe()
                    self._save(record, 'ACTIVATE')
                    self.installer.lifecycle.restart()
                    if not self.installer.lifecycle.wait(True, before.entry_states):
                        raise InstallerError('TRANSFER_HEALTH_FAILED')
                probe = self.installer.lifecycle.probe()
                if not probe.running or not probe.healthy:
                    raise InstallerError('TRANSFER_HEALTH_FAILED')
                verify_post_migration_state(self.installer.inspect(), record['proposal']['destination'])
                if self._identity() != record['proposal']['identity_sha256']:
                    raise InstallerError('TRANSFER_IDENTITY_REVIEW_REQUIRED')
                self._save(record, 'VERIFY_OWNER')
                self._save(record, 'COMMITTED')
                return {'status': 'COMMITTED', 'transfer_id': record['id'],
                        'owner': record['proposal']['destination']}
            except Exception:
                self._save(record, 'RECOVERY_REQUIRED')
                raise

    def resume(self):
        """Inspect only; no guessed source writes or automatic HACS rollback."""
        with lock(self.root):
            record = self._load()
            detected = self.installer.inspect()
            return {'phase': record['phase'], 'owner': detected['owner'],
                    'next': ('NO_ACTION' if record['phase'] in TERMINAL else
                             'VERIFY_RELEASE_OR_FINISH' if record['phase'] in {'BACKUP', 'SOURCE_RELEASED'}
                             else 'RECOVERY_REQUIRED'), 'transfer_id': record['id']}

    def cancel_before_release(self):
        with lock(self.root):
            record = self._load()
            if record['phase'] != 'BACKUP' or self.installer.inspect() != record['proposal']['before']:
                raise InstallerError('SOURCE_CHANGED_RECOVERY_REQUIRED')
            if inventory(self.installer.target) != record['before_files']:
                raise InstallerError('SOURCE_CHANGED_RECOVERY_REQUIRED')
            self._save(record, 'CANCELLED')
            return {'status': 'CANCELLED', 'no_files_written': True}
