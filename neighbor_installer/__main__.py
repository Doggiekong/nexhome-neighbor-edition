"""Local-only CLI. Credentials are read from the environment, never arguments."""

import argparse
import json
import os

from .artifact import Artifact
from .engine import Installer
from .environment import inspect_environment
from .files import InstallerError, load
from .hacs import COMMUNITY, OFFICIAL
from .lifecycle import SupervisorLifecycle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--trusted-trees', help='Locally reviewed origin-to-tree-SHA256 catalog; no network lookup')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('inspect')
    commands.add_parser('backup')
    commands.add_parser('recover')
    apply = commands.add_parser('apply')
    apply.add_argument('--artifact', required=True)
    apply.add_argument('--sha256', required=True)
    apply.add_argument('--confirm-manual-tree')
    rollback = commands.add_parser('rollback')
    rollback.add_argument('transaction_id')
    args = parser.parse_args()
    try:
        lifecycle = None if args.command in {'inspect', 'backup'} else SupervisorLifecycle(
            os.environ.get('SUPERVISOR_TOKEN'), ha_token=os.environ.get('HA_ACCESS_TOKEN'),
            ha_url=os.environ.get('HA_URL', 'http://homeassistant:80')
        )
        trusted = None
        if args.trusted_trees:
            from pathlib import Path
            trusted = load(Path(args.trusted_trees))
            if (not isinstance(trusted, dict) or any(
                key not in {OFFICIAL, COMMUNITY} or not isinstance(value, str) or len(value) != 64
                or any(c not in '0123456789abcdef' for c in value)
                for key, value in trusted.items()
            )):
                raise InstallerError('TRUSTED_TREE_CATALOG_INVALID')
        engine = Installer(args.config, lifecycle, trusted_trees=trusted)
        match args.command:
            case 'inspect':
                result = engine.inspect()
                result['environment'] = inspect_environment(
                    args.config, supervisor_authorized=bool(os.environ.get('SUPERVISOR_TOKEN'))
                )
            case 'backup':
                result = engine.backup_only()
            case 'recover':
                result = engine.recover()
            case 'rollback':
                result = engine.rollback(args.transaction_id)
            case 'apply':
                result = engine.apply(
                    Artifact.open(args.artifact, args.sha256), manual_fingerprint=args.confirm_manual_tree
                )
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get('status') not in {'ROLLED_BACK', 'RECOVERY_REQUIRED'} else 2
    except Exception as error:
        # Never serialize exception bodies originating in transports or configuration files.
        code = str(error) if isinstance(error, InstallerError) else 'UNEXPECTED_FAILURE_DETAILS_SUPPRESSED'
        print(json.dumps({'status': 'FAILED', 'error': code}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
