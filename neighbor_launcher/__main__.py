"""Start only as an authorized HA application; no standalone public listener."""

import fcntl
import os
from pathlib import Path

from aiohttp import web

from neighbor_installer.artifact import Artifact
from neighbor_installer.engine import Installer
from neighbor_installer.files import InstallerError, load
from neighbor_installer.lifecycle import SupervisorLifecycle

from .controller import Controller
from .server import create_app


def main():
    token = os.environ.get('SUPERVISOR_TOKEN')
    if not token:
        raise InstallerError('NATIVE_HA_APPLICATION_REQUIRED')
    data = Path('/data')
    held = os.open(data / 'interface.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
    package = Path('/opt/nexhome/bundle')
    artifact = Artifact.open(package, (package / 'artifact.sha256').read_text().strip())
    runtime = SupervisorLifecycle(token, proxy_core=True, timeout=210)
    engine = Installer('/homeassistant', runtime,
                       trusted_trees=load(Path('/opt/nexhome/trusted-trees.json'), {}))
    controller = Controller(engine, artifact, data)
    web.run_app(create_app(controller), host='0.0.0.0', port=8099, access_log=None,
                print=None, shutdown_timeout=240)
    os.close(held)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never serialize an environment, request URL, token or traceback.
        raise SystemExit('安装入口暂时不能启动，请在 Home Assistant 中查看应用状态。') from None
