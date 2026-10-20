"""Single-owner transaction engine: backup, atomic deploy, activate, health, rollback."""

import os
import uuid
from datetime import UTC, datetime

from packaging.version import Version

from .artifact import Artifact
from .detection import Owner, detect, identity_fingerprint
from .files import InstallerError, copy_tree, durable, guarded_root, inventory, load, lock, remove_owned

TERMINAL = {"COMMITTED", "ROLLED_BACK"}


class Installer:
    def __init__(self, root, lifecycle, *, trusted_trees=None):
        self.root = guarded_root(root)
        self.target = self.root / "custom_components/nexhome"
        self.state = self.root / ".nexhome-installer"
        self.lifecycle = lifecycle
        self.trusted_trees = trusted_trees

    def inspect(self):
        return detect(self.root, self.trusted_trees)

    def _record(self, tx, phase, error=None):
        tx["phase"] = phase
        tx.setdefault("history", []).append({"phase": phase, "at": datetime.now(UTC).isoformat()})
        if error:
            tx["error"] = error
        durable(self.state / "transactions" / tx["id"] / "record.json", tx)
        durable(self.state / "active.json", {"id": tx["id"], "phase": phase})

    def _pending(self):
        active = load(self.state / "active.json")
        if active and active.get("phase") not in TERMINAL:
            raise InstallerError("PENDING_TRANSACTION_USE_RECOVER")

    def _backup(self, tx):
        directory = self.state / "transactions" / tx["id"]
        if tx["before"]["exists"]:
            copy_tree(self.target, directory / "backup", private=True)
            if inventory(directory / "backup") != tx["before"]["files"]:
                raise InstallerError("BACKUP_HASH_MISMATCH")
        durable(directory / "backup-metadata.json", tx["before"])
        self._record(tx, "BACKUP")

    def _swap(self, files, source, tx):
        parent = self.target.parent
        parent.mkdir(exist_ok=True)
        staged = parent / (".nexhome-stage-" + tx["id"])
        retired = parent / (".nexhome-retired-" + tx["id"])
        if staged.exists() or retired.exists():
            raise InstallerError("STAGING_COLLISION")
        copy_tree(source, staged)
        if inventory(staged) != files:
            raise InstallerError("STAGING_HASH_MISMATCH")
        if self.target.exists():
            os.replace(self.target, retired)
        os.replace(staged, self.target)
        if retired.exists():
            remove_owned(retired, parent)

    def apply(self, artifact: Artifact, *, manual_fingerprint=None):
        with lock(self.root):
            self._pending()
            artifact.revalidate()
            detected = self.inspect()
            if detected["owner"] in (Owner.OFFICIAL_HACS, Owner.COMMUNITY_HACS):
                raise InstallerError("HACS_IS_UPDATE_OWNER")
            if detected["owner"] == Owner.MANUAL_UNKNOWN:
                if (
                    detected["hacs_claim_count"] or detected["hacs_schema_uncertain"]
                    or manual_fingerprint != detected["tree_sha256"]
                ):
                    raise InstallerError("UNKNOWN_OWNER_CONFIRM_FINGERPRINT_REQUIRED")
            files = inventory(self.target)
            if detected["owner"] == Owner.NEIGHBOR_INSTALLER and files == artifact.metadata["files"]:
                return {"status": "NO_OP", "version": artifact.metadata["version"], "owner": Owner.NEIGHBOR_INSTALLER}
            if detected["owner"] == Owner.NEIGHBOR_INSTALLER and detected["version"]:
                if Version(artifact.metadata['version']) == Version(detected['version']):
                    raise InstallerError('SAME_VERSION_DIFFERENT_FILES_REFUSED')
                if Version(artifact.metadata["version"]) < Version(detected["version"]):
                    raise InstallerError("DOWNGRADE_REFUSED")
            probe = self.lifecycle.probe()
            if not probe.running or not probe.healthy:
                raise InstallerError("HA_NOT_HEALTHY")
            if probe.ha_version not in artifact.metadata.get("tested_ha_versions", []):
                raise InstallerError("HA_VERSION_OUTSIDE_TESTED_MATRIX")
            if any(state not in {"loaded", "not_loaded"} for state in probe.entry_states.values()):
                raise InstallerError("EXISTING_ENTRY_REQUIRES_DIAGNOSIS_NO_AUTODISCOVERY")
            tx = {
                "id": uuid.uuid4().hex,
                "artifact": artifact.metadata,
                "artifact_manifest_sha256": artifact.manifest_sha256,
                "before": {
                    "exists": self.target.exists(), "files": files, "detection": detected,
                    "owner_marker": load(self.state / "owner.json"),
                    "identity_sha256": identity_fingerprint(self.root),
                    "entry_states": probe.entry_states, "ha_version": probe.ha_version,
                },
            }
            self._record(tx, "PRECHECK")
            try:
                self._backup(tx)
                artifact.revalidate()
                if inventory(self.target) != files or identity_fingerprint(self.root) != tx["before"]["identity_sha256"]:
                    raise InstallerError("CONCURRENT_CHANGE_BEFORE_DEPLOY")
                self._record(tx, "DEPLOY")
                self._swap(artifact.metadata["files"], artifact.directory / "nexhome", tx)
                self._record(tx, "ACTIVATE")
                self.lifecycle.restart()
                self._record(tx, "HEALTH_CHECK")
                if not self.lifecycle.wait(True, probe.entry_states):
                    raise InstallerError("NEW_VERSION_HEALTH_FAILED")
                if inventory(self.target) != artifact.metadata["files"]:
                    raise InstallerError("POST_DEPLOY_HASH_MISMATCH")
                if identity_fingerprint(self.root) != tx["before"]["identity_sha256"]:
                    raise InstallerError("IDENTITY_CHANGED_REVIEW_REQUIRED")
                durable(self.state / "owner.json", {
                    "schema": 1, "owner": Owner.NEIGHBOR_INSTALLER, "files": artifact.metadata["files"],
                    "version": artifact.metadata["version"], "revision": artifact.metadata["revision"],
                    "origin": artifact.metadata["origin"], "transaction_id": tx["id"],
                })
                self._record(tx, "COMMITTED")
                return {"status": "COMMITTED", "transaction_id": tx["id"], "version": artifact.metadata["version"]}
            except Exception:
                if tx['phase'] in {'PRECHECK', 'BACKUP'}:
                    if inventory(self.target) != files:
                        self._record(tx, 'RECOVERY_REQUIRED', 'CONCURRENT_CHANGE_BEFORE_DEPLOY')
                        raise InstallerError('RECOVERY_REQUIRED_BACKUP_PRESERVED') from None
                    self._record(tx, 'ROLLED_BACK', 'PRE_DEPLOY_FAILED')
                    return {'status': 'ROLLED_BACK', 'transaction_id': tx['id'], 'no_deploy_happened': True}
                self._record(tx, "FAIL", "INSTALL_OR_HEALTH_FAILED")
                return self._restore(tx)

    def _restore(self, tx):
        original = tx["before"]
        directory = self.state / "transactions" / tx["id"]
        try:
            current = inventory(self.target)
            if current not in (original["files"], tx["artifact"]["files"], {}):
                raise InstallerError("RECOVERY_CONCURRENT_FILES_REFUSED")
            if original["exists"] and inventory(directory / "backup") != original["files"]:
                raise InstallerError("RECOVERY_BACKUP_INVALID")
            parent = self.target.parent
            cleanup = []
            for prefix in (".nexhome-stage-", ".nexhome-retired-"):
                path = parent / (prefix + tx["id"])
                if path.exists():
                    allowed = original["files"] if "retired" in prefix else tx["artifact"]["files"]
                    actual = inventory(path)
                    if any(allowed.get(name) != value for name, value in actual.items()):
                        raise InstallerError("RECOVERY_STAGING_CHANGED")
                    cleanup.append(path)
            self._record(tx, "ROLLBACK")
            self.lifecycle.stop()  # Validate all local recovery inputs before stopping Core.
            for path in cleanup:
                remove_owned(path, parent)
            remove_owned(self.target, parent)
            if original["exists"]:
                copy_tree(directory / "backup", self.target)
            owner = self.state / "owner.json"
            if original["owner_marker"]:
                durable(owner, original["owner_marker"])
            elif owner.exists():
                owner.unlink()
            self._record(tx, "RESTORE")
            self.lifecycle.start()
            if not self.lifecycle.wait(original["exists"], original["entry_states"]):
                raise InstallerError("ROLLBACK_HEALTH_FAILED")
            if inventory(self.target) != original["files"]:
                raise InstallerError("RESTORE_HASH_MISMATCH")
            identity_unchanged = identity_fingerprint(self.root) == original["identity_sha256"]
            if not identity_unchanged:
                raise InstallerError('IDENTITY_REVIEW_REQUIRED_CODE_RESTORED')
            self._record(tx, "ROLLED_BACK")
            return {"status": "ROLLED_BACK", "transaction_id": tx["id"], "identity_unchanged": identity_unchanged}
        except Exception:
            self._record(tx, "RECOVERY_REQUIRED", "AUTOMATIC_RESTORE_NOT_CONFIRMED")
            raise InstallerError("RECOVERY_REQUIRED_BACKUP_PRESERVED") from None

    def recover(self):
        with lock(self.root):
            active = load(self.state / "active.json")
            if not active or active.get("phase") in TERMINAL:
                return {"status": "NO_PENDING_TRANSACTION"}
            identifier = active.get("id", "")
            if len(identifier) != 32 or any(c not in "0123456789abcdef" for c in identifier):
                raise InstallerError("TRANSACTION_ID_INVALID")
            tx = load(self.state / "transactions" / identifier / "record.json")
            if not tx or tx.get("id") != identifier:
                raise InstallerError("TRANSACTION_RECORD_INVALID")
            if tx["phase"] in {"PRECHECK", "BACKUP"}:
                # No deploy happened; current directory must still equal the captured original.
                if inventory(self.target) != tx["before"]["files"]:
                    raise InstallerError("PRECHECK_RECOVERY_CONCURRENT_CHANGE")
                self._record(tx, "ROLLED_BACK")
                return {"status": "ROLLED_BACK", "transaction_id": identifier, "no_deploy_happened": True}
            return self._restore(tx)

    def rollback(self, transaction_id):
        with lock(self.root):
            self._pending()
            if len(transaction_id) != 32 or any(c not in "0123456789abcdef" for c in transaction_id):
                raise InstallerError("TRANSACTION_ID_INVALID")
            tx = load(self.state / "transactions" / transaction_id / "record.json")
            if not tx or tx.get("phase") != "COMMITTED":
                raise InstallerError("NOT_A_COMMITTED_TRANSACTION")
            active = load(self.state / "active.json")
            if not active or active.get("id") != transaction_id:
                raise InstallerError("ONLY_LATEST_TRANSACTION_CAN_ROLL_BACK")
            return self._restore(tx)

    def backup_only(self):
        with lock(self.root):
            self._pending()
            before = self.inspect()
            identifier = uuid.uuid4().hex
            directory = self.state / "backups" / identifier
            directory.mkdir(parents=True, mode=0o700)
            if before["installed"]:
                copy_tree(self.target, directory / "nexhome", private=True)
            durable(directory / "metadata.json", before)
            return {"status": "BACKUP_ONLY", "backup_id": identifier, "tree_sha256": before["tree_sha256"]}
