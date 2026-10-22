"""Offline DEV/TEST application context; fixed Candidate, no release or publication."""

import argparse
import io
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

from neighbor_installer.build import build
from neighbor_installer.files import InstallerError, digest, durable, inventory
from neighbor_installer.hacs import COMMUNITY, OFFICIAL


def package(repo, revision, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    if output.exists() or output == repo or repo in output.parents:
        raise InstallerError('PACKAGE_OUTPUT_MUST_BE_NEW_OUTSIDE_REPOSITORY')
    output.mkdir(parents=True, mode=0o700)
    # All deployable code comes from the same immutable source revision.
    # A dirty checkout must never silently change the frozen launcher/installer.
    resolved = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', '--verify', revision+'^{commit}']).decode().strip()
    if resolved != revision or len(revision) != 40:
        raise InstallerError('FULL_COMMIT_PIN_REQUIRED')
    data = subprocess.check_output(['git', '-C', str(repo), 'archive', revision])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            selected = (
                path.as_posix() in {'launcher_addon/config.yaml', 'launcher_addon/Dockerfile', 'NOTICE.md'}
                or (len(path.parts) == 2 and path.parts[0] in {'neighbor_installer', 'neighbor_launcher'} and path.suffix == '.py')
                or path.as_posix() in {'neighbor_launcher/web/index.html', 'neighbor_launcher/web/app.js', 'neighbor_launcher/web/style.css'}
            )
            if not selected:
                continue
            if not member.isfile() or path.is_absolute() or '..' in path.parts:
                raise InstallerError('PACKAGE_SOURCE_NON_REGULAR_FILE')
            relative = path.name if path.parts[0] == 'launcher_addon' else path.as_posix()
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    pin = build(repo, revision, output / 'bundle', ['2026.10.2'])
    (output / 'bundle/artifact.sha256').write_text(pin + '\n', encoding='ascii')
    durable(output / 'trusted-trees.json', {
        # Independently reviewed official fixed-tag LF deployment, Stage C evidence.
        OFFICIAL: '4a0fc38f1b7280fc4ca9de4393e259b1fa193cd4e7f20dc27cf02c2b83331450',
        COMMUNITY: digest(inventory(output / 'bundle/nexhome')),
    })
    durable(output / 'package-evidence.json', {'kind': 'DEV_TEST_ONLY', 'candidate_revision': revision,
                                             'candidate_manifest_sha256': pin,
                                             'application_tree_sha256': digest(inventory(output))})
    return pin


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(package(args.repo, args.commit, args.output))
