"""Package an explicitly pinned private Git commit, without network or publication."""

import argparse
import hashlib
import io
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

from .artifact import Artifact
from .files import InstallerError, durable, inventory


def build(repo, revision, output, ha_versions):
    repo, output = Path(repo), Path(output)
    if output.exists():
        raise InstallerError('ARTIFACT_OUTPUT_ALREADY_EXISTS')
    resolved = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', '--verify', revision+'^{commit}'])
    commit = resolved.decode().strip()
    if commit != revision or len(commit) != 40:
        raise InstallerError('FULL_COMMIT_PIN_REQUIRED')
    data = subprocess.check_output(['git', '-C', str(repo), 'archive', commit, 'custom_components/nexhome'])
    output.mkdir(parents=True, mode=0o700)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                raise InstallerError('SOURCE_NON_REGULAR_FILE')
            path = PurePosixPath(member.name).relative_to('custom_components/nexhome')
            if '..' in path.parts or path.is_absolute():
                raise InstallerError('SOURCE_PATH_INVALID')
            target = output / 'nexhome' / str(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    import json
    manifest = json.loads((output / 'nexhome/manifest.json').read_text(encoding='utf-8'))
    durable(output / 'artifact.json', {
        'schema': 1, 'version': manifest['version'], 'revision': commit,
        'origin': 'https://github.com/Doggiekong/nexhome-neighbor-edition',
        'tested_ha_versions': ha_versions, 'files': inventory(output / 'nexhome'),
    })
    pin = hashlib.sha256((output / 'artifact.json').read_bytes()).hexdigest()
    Artifact.open(output, pin)
    return pin


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--ha-version', action='append', required=True)
    args = parser.parse_args()
    print(build(args.repo, args.commit, args.output, args.ha_version))
