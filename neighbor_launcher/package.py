"""Offline DEV/TEST application context; fixed Candidate, no release or publication."""

import argparse
import shutil
from pathlib import Path

from neighbor_installer.build import build
from neighbor_installer.files import InstallerError, digest, durable, inventory
from neighbor_installer.hacs import COMMUNITY, OFFICIAL


def package(repo, revision, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    if output.exists() or output == repo or repo in output.parents:
        raise InstallerError('PACKAGE_OUTPUT_MUST_BE_NEW_OUTSIDE_REPOSITORY')
    output.mkdir(parents=True, mode=0o700)
    for name in ('config.yaml', 'Dockerfile'):
        shutil.copyfile(repo / 'launcher_addon' / name, output / name)
    for module in ('neighbor_installer', 'neighbor_launcher'):
        destination = output / module
        destination.mkdir()
        for source in (repo / module).glob('*.py'):
            shutil.copyfile(source, destination / source.name)
    web = output / 'neighbor_launcher/web'
    web.mkdir()
    for name in ('index.html', 'app.js', 'style.css'):
        shutil.copyfile(repo / 'neighbor_launcher/web' / name, web / name)
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
