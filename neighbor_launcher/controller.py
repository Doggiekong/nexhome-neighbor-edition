"""Thin UI orchestration. Ownership, deploy, migration and recovery stay in core."""

import json
import threading
import uuid
from pathlib import Path

from packaging.version import Version

from neighbor_installer.detection import Owner, identity_fingerprint
from neighbor_installer.files import InstallerError, durable, load
from neighbor_installer.identity import preview as migration_preview
from neighbor_installer.transfer import Transfer
from neighbor_installer.update import apply_update, preview_update

from .copy import OWNER_SCREEN, PHASE_LABELS, SCREENS


class Controller:
    def __init__(self, installer, artifact, data):
        self.engine = installer
        self.artifact = artifact.revalidate()
        self.data = Path(data)
        self.data.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.data / 'interface-state.json'
        self.guard = threading.Lock()
        self.worker = None
        self.plan = None
        self.state = load(self.path, {'screen': 'welcome', 'status': 'IDLE', 'steps': []})
        self.engine.observer = self._observe
        self._reconcile()

    def _save(self, screen=None, **values):
        if screen:
            self.state['screen'] = screen
        self.state.update(values)
        durable(self.path, self.state)

    def _observe(self, event):
        steps = list(self.state.get('steps', []))
        phase = event['phase']
        if phase in PHASE_LABELS and (not steps or steps[-1] != phase):
            steps.append(phase)
        self._save(steps=steps[-24:], last_event=event)

    def _reconcile(self):
        active = load(self.engine.state / 'active.json') or {}
        transfer = load(self.engine.state / 'transfer-active.json') or {}
        if self.state.get('screen') == 'confirm':
            # Preview confirmation is memory-only; reopening must obtain a fresh plan.
            self._save('welcome', status='IDLE')
        if self.state.get('screen') in {'not_found', 'hub_select', 'hub_confirm', 'connected'}:
            self._save('installed', status='DONE', connection_flow=None, connection_step=None)
        if self.state.get('status') == 'RUNNING':
            # The engine journal, never a browser flag, determines completion.
            event = self.state.get('last_event') or {}
            if active.get('id') == event.get('id') and active.get('phase') == 'COMMITTED':
                self._save('installed', status='DONE')
            elif active.get('phase') == 'ROLLED_BACK' and active.get('id') == event.get('id'):
                self._save('restored', status='DONE')
            else:
                self._save('interrupted', status='WAITING')
        if active.get('phase') == 'RECOVERY_REQUIRED' or transfer.get('phase') == 'RECOVERY_REQUIRED':
            self._save('recovery', status='WAITING')
        elif transfer.get('phase') in {'BACKUP', 'SOURCE_RELEASED'}:
            self._save('handoff', status='WAITING')
        elif active and active.get('phase') not in {'COMMITTED', 'ROLLED_BACK'}:
            self._save('interrupted', status='WAITING')

    def view(self):
        screen = self.state.get('screen', 'welcome')
        title, description, button = SCREENS.get(screen, SCREENS['failed'])
        detected = self.state.get('detected', {})
        # Explicit allowlist; no configuration data, raw exceptions, headers or logs.
        technical = {k: detected[k] for k in (
            'owner', 'reason', 'version', 'tree_sha256', 'hacs_present', 'entry_count'
        ) if k in detected}
        technical.update({'ha_version': self.state.get('ha_version'),
                          'candidate_version': self.artifact.metadata['version'],
                          'artifact_manifest_sha256': self.artifact.manifest_sha256,
                          'source': self.artifact.metadata['origin'],
                          'operation': self.state.get('last_event'),
                          'error_code': self.state.get('error_code')})
        return {'screen': screen, 'title': title, 'description': description, 'button': button,
                'busy': self.state.get('status') == 'RUNNING',
                'steps': [PHASE_LABELS[x] for x in self.state.get('steps', []) if x in PHASE_LABELS],
                'current_version': detected.get('version'), 'new_version': self.artifact.metadata['version'],
                'plan': self.plan['id'] if self.plan else None,
                'handoff_note': self.state.get('handoff_note'),
                'technical': technical,
                'can_connect': screen == 'latest'}

    def start(self, action, payload=None):
        if not self.guard.acquire(blocking=False):
            return False
        if not isinstance(action, str) or action not in {'check', 'prepare', 'confirm', 'cancel', 'handoff', 'recover'}:
            self.guard.release()
            raise InstallerError('UI_ACTION_REFUSED')
        permitted = {
            'prepare': {'fresh', 'official', 'update'}, 'confirm': {'confirm'},
            'cancel': {'confirm'}, 'handoff': {'handoff'}, 'recover': {'interrupted', 'recovery'},
        }
        if action in permitted and self.state['screen'] not in permitted[action]:
            self.guard.release()
            return False
        if action == 'confirm' and (not self.plan or (payload or {}).get('plan') != self.plan['id']):
            self.guard.release()
            return False
        self._save(status='RUNNING', error_code=None, last_event=None)

        def work():
            try:
                getattr(self, '_' + action)(payload or {})
            except InstallerError as error:
                self._save(self._failure_screen(), status='WAITING', error_code=str(error))
            except Exception:
                self._save(self._failure_screen(), status='WAITING', error_code='DETAILS_SUPPRESSED')
            finally:
                if self.state.get('status') == 'RUNNING':
                    self._save(status='WAITING')
                self.guard.release()
        self.worker = threading.Thread(target=work, name='nexhome-install', daemon=False)
        self.worker.start()
        return True

    def _failure_screen(self):
        active = load(self.engine.state / 'active.json') or {}
        transfer = load(self.engine.state / 'transfer-active.json') or {}
        if 'RECOVERY_REQUIRED' in {active.get('phase'), transfer.get('phase')}:
            return 'recovery'
        if transfer.get('phase') in {'BACKUP', 'SOURCE_RELEASED'}:
            return 'handoff'
        if active and active.get('phase') not in {'COMMITTED', 'ROLLED_BACK'}:
            return 'interrupted'
        return 'failed'

    def _check(self, _payload):
        if self.state['screen'] in {'interrupted', 'recovery', 'handoff'}:
            self._save(status='WAITING')
            return
        detected = self.engine.inspect()
        probe = self.engine.lifecycle.probe()
        self._save(detected=detected, ha_version=probe.ha_version)
        if not probe.running or not probe.healthy:
            screen = 'unhealthy'
        elif probe.ha_version not in self.artifact.metadata['tested_ha_versions']:
            screen = 'unsupported'
        elif any(value not in {'loaded', 'not_loaded'} for value in probe.entry_states.values()):
            screen = 'connection_wait'
        elif detected['owner'] == Owner.NEIGHBOR_INSTALLER:
            screen = 'update' if Version(detected['version']) < Version(self.artifact.metadata['version']) else 'latest'
        else:
            screen = OWNER_SCREEN.get(detected['owner'], 'unknown')
        self._save(screen, status='IDLE', steps=[])

    def _cancel(self, _payload):
        if self.state['screen'] != 'confirm':
            raise InstallerError('UI_CANCEL_NOT_AVAILABLE')
        self.plan = None
        self._save('welcome', status='IDLE')
        self._check({})

    def _prepare(self, _payload):
        detected = self.engine.inspect()
        if detected['owner'] not in {None, Owner.NEIGHBOR_INSTALLER, Owner.OFFICIAL_HACS}:
            raise InstallerError('UI_SOURCE_CANNOT_INSTALL')
        if detected['owner'] == Owner.NEIGHBOR_INSTALLER:
            plan = {'kind': 'update', 'core': preview_update(self.engine, self.artifact)}
        elif detected['owner'] == Owner.OFFICIAL_HACS:
            plan = {'kind': 'handoff', 'core': Transfer(self.engine).preview(Owner.NEIGHBOR_INSTALLER)}
        else:
            plan = {'kind': 'install', 'core': detected,
                    'identity': identity_fingerprint(self.engine.root)}
        self.plan = {'id': uuid.uuid4().hex, **plan}
        self._save('confirm', status='WAITING', detected=detected)

    def _confirm(self, payload):
        plan = self.plan
        if not plan or payload.get('plan') != plan['id'] or payload.get('confirmed') is not True:
            raise InstallerError('UI_CONFIRMATION_REQUIRED')
        self.plan = None  # single use; refresh/double-click cannot replay
        self._save('running', status='RUNNING', steps=[])
        if plan['kind'] == 'handoff':
            Transfer(self.engine).begin(plan['core'], plan['core']['confirmation_sha256'])
            self._save('handoff', status='WAITING')
            return
        if plan['kind'] == 'update':
            result = apply_update(self.engine, self.artifact, plan['core'], plan['core']['confirmation_sha256'])
        else:
            if (self.engine.inspect() != plan['core']
                    or identity_fingerprint(self.engine.root) != plan['identity']):
                raise InstallerError('UI_PREVIEW_STALE')
            result = self.engine.apply(self.artifact)
        self._result(result)

    def _result(self, result):
        if result['status'] in {'COMMITTED', 'NO_OP'}:
            detected = self.engine.inspect()
            self._save('latest' if detected['entry_count'] else 'installed', status='DONE', detected=detected)
        elif result['status'] == 'ROLLED_BACK':
            self._save('restored', status='DONE')
        else:
            self._save('recovery', status='WAITING')

    def _handoff(self, _payload):
        detected = self.engine.inspect()
        if detected['hacs_claim_count'] or detected['hacs_schema_uncertain']:
            self._save('handoff', status='WAITING', handoff_note='还没有确认完成，请先在 HACS 完成移除，再回来重新检查。')
            return
        transfer = Transfer(self.engine)
        transfer.verify_release()
        plan = migration_preview(self.engine.root, registry_view=self.engine._registry_view())
        self._save('running', status='RUNNING', handoff_note=None)
        self._result(transfer.deploy_installer(self.artifact, migration_preview=plan))

    def _recover(self, _payload):
        transfer = load(self.engine.state / 'transfer-active.json') or {}
        if transfer.get('phase') not in {None, 'COMMITTED', 'CANCELLED'}:
            self._save('recovery', status='WAITING', error_code='SOURCE_REVIEW_REQUIRED')
            return
        result = self.engine.recover()
        if result['status'] == 'NO_PENDING_TRANSACTION':
            self._save('welcome', status='IDLE')
            self._check({})
        else:
            self._result(result)

    def diagnostics(self):
        return {'product': 'NEXhome Neighbor Edition', 'screen': self.state['screen'],
                'technical': self.view()['technical']}

    def close(self):
        if self.worker and self.worker.is_alive():
            raise InstallerError('UI_OPERATION_STILL_RUNNING')
        self.plan = None


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
