"""Assemble distribution metadata/frontends without rebuilding the frozen SDK."""
import hashlib
import json
import re
import shutil
from pathlib import Path

from distribution.terminal import ARTIFACT_SHA256, DEFAULT_SOURCE, PAYLOAD_SHA256


def assemble(root):
    root = Path(root)
    app = root / 'nexhome_neighbor'
    payload = app / 'payload.tar.gz'
    if hashlib.sha256(payload.read_bytes()).hexdigest() != PAYLOAD_SHA256:
        raise ValueError('Frozen package changed; do not rebuild or substitute it')
    for name in ('terminal.py', 'app_entry.py'):
        shutil.copyfile(root / 'distribution' / name, app / name)
    runner = hashlib.sha256((root / 'distribution/terminal.py').read_bytes()).hexdigest()
    shell = root / 'distribution/start.sh'
    text = shell.read_text(encoding='utf-8')
    text = re.sub(r"echo '[a-f0-9]{64}  '", "echo '" + runner + "  '", text)
    shell.write_text(text, encoding='utf-8', newline='\n')
    lock = {'version': '0.1.1', 'artifact_archive_sha256': PAYLOAD_SHA256,
            'artifact_manifest_sha256': ARTIFACT_SHA256,
            'runtime_source_commit': 'dffa455d759a5c88d37cbcf4866d8fe131c17c6c',
            'frontend_sha256': runner,
            'bootstrap_sha256': hashlib.sha256(shell.read_bytes()).hexdigest(),
            'release_base': DEFAULT_SOURCE, 'public_release_created': True}
    (root / 'distribution/lock.json').write_text(json.dumps(lock, indent=2) + '\n', encoding='utf-8', newline='\n')
    return lock


if __name__ == '__main__':
    print(json.dumps(assemble(Path(__file__).resolve().parents[1])))
