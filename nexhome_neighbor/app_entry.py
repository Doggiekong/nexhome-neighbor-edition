"""Verify/extract the same immutable packet before starting its existing HAOS UI."""
import hashlib
import os
import runpy
import sys
import tarfile
from pathlib import Path

from terminal import PAYLOAD_SHA256, extract_payload

archive = Path('/opt/distribution/payload.tar.gz')
if hashlib.sha256(archive.read_bytes()).hexdigest() != PAYLOAD_SHA256:
    raise SystemExit('固定安装包校验不一致；未启动安装助手。')
target = Path('/opt/nexhome')
if target.exists():
    # A normal App restart may retain its writable container layer. Reuse only
    # the exact pinned extraction, never overwrite an unknown directory.
    with tarfile.open(archive, 'r:gz') as source:
        expected = {m.name: hashlib.sha256(source.extractfile(m).read()).hexdigest()
                    for m in source.getmembers() if m.isfile()}
    actual = {str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in target.rglob('*') if p.is_file() and not p.is_symlink()}
    if actual != expected or any(p.is_symlink() for p in target.rglob('*')):
        raise SystemExit('执行目录与固定安装包不一致，不覆盖未知内容。')
else:
    extract_payload(archive, target)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, str(target))
os.chdir(target)
runpy.run_module('neighbor_launcher', run_name='__main__')
