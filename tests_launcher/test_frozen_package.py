"""The entire Candidate package is pinned, not only integration files."""
import json
import subprocess

from neighbor_installer.files import inventory
from neighbor_launcher.package import package


def test_frozen_sdk_ignores_dirty_checkout_and_reproduces(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    def put(name, text):
        p = source / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    put('custom_components/nexhome/manifest.json', json.dumps({'domain':'nexhome','version':'0.1.0'}))
    put('custom_components/nexhome/product.json', json.dumps({'product_id':'nexhome-neighbor-edition','product_version':'0.1.0','upstream_base_version':'1.1.16','version_scheme':'neighbor-independent-v1'}))
    put('custom_components/nexhome/__init__.py', 'PINNED = True\n')
    for root in ('neighbor_installer', 'neighbor_launcher'):
        put(root+'/__init__.py', 'PINNED = True\n')
    for name in ('index.html','app.js','style.css'):
        put('neighbor_launcher/web/'+name, 'pinned')
    put('launcher_addon/config.yaml', 'version: 0.1.0\n')
    put('launcher_addon/Dockerfile', 'FROM scratch\n')
    put('NOTICE.md', 'Original attribution\n')
    def git(*args):
        return subprocess.check_output(['git','-C',str(source),*args],stderr=subprocess.DEVNULL).decode().strip()
    git('init')
    git('add','.')
    git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture')
    revision = git('rev-parse','HEAD')
    put('neighbor_launcher/__init__.py', 'DIRTY = True\n')
    put('NOTICE.md', 'dirty notice')
    first, second = tmp_path/'first', tmp_path/'second'
    assert package(source, revision, first) == package(source, revision, second)
    assert inventory(first) == inventory(second)
    assert (first/'neighbor_launcher/__init__.py').read_text() == 'PINNED = True\n'
    assert (first/'NOTICE.md').read_text() == 'Original attribution\n'
