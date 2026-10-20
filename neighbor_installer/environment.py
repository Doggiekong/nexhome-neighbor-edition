"""Local capability detection, never guess privileged access from a HA login."""

import os
import platform

from .files import guarded_root


def inspect_environment(root, *, supervisor_authorized=False):
    root = guarded_root(root)
    return {
        'os': platform.system(),
        'python': platform.python_version(),
        'config_readable': os.access(root, os.R_OK),
        'config_writable': os.access(root, os.W_OK),
        'ha_storage_present': (root / '.storage/core.config_entries').is_file(),
        'runtime_adapter': 'SUPERVISOR' if supervisor_authorized else 'EXPLICIT_ADAPTER_REQUIRED',
        'api_alone_can_deploy': False,
        'supported_engine_host': platform.system() == 'Linux',
    }
