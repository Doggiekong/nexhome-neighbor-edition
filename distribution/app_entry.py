"""Verify/extract the same immutable packet before starting its existing HAOS UI."""
import hashlib
import importlib
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
# Setting the environment after interpreter startup alone does not disable pyc.
sys.dont_write_bytecode = True
sys.path.insert(0, str(target))
os.chdir(target)
# Public presentation overlay: do not rewrite the immutable SDK/runtime packet.
server = importlib.import_module('neighbor_launcher.server')

public_web = Path('/opt/distribution/public-web')
public_web.mkdir(exist_ok=True)
if any(p.is_symlink() or p.name not in {'index.html', 'app.js', 'style.css'} for p in public_web.iterdir()):
    raise SystemExit('公开界面目录与预期不一致，未启动。')
for name in ('index.html', 'app.js', 'style.css'):
    content = (server.WEB / name).read_bytes()
    if name == 'index.html':
        old = '开发测试版本 · 尚未向真实住户发布'.encode()
        if content.count(old) != 1:
            raise SystemExit('固定界面文案与预期不一致，未启动。')
        content = content.replace(old, '正式发布版本 v0.1.0'.encode())
    (public_web / name).write_bytes(content)
server.WEB = public_web
runpy.run_module('neighbor_launcher', run_name='__main__')
