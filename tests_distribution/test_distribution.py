"""Distribution trust/detection contracts; no Hub or HA connections."""
import hashlib
import io
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from distribution import terminal as entry
from distribution.build import assemble

ROOT = Path(__file__).resolve().parents[1]


def target(*, image='ghcr.io/home-assistant/home-assistant:2026.10.2', mode='bridge', mount='bind', rw=True):
    return {'Id': 'a' * 64, 'Name': '/ha-test', 'Image': 'sha256:' + 'b' * 64,
            'Config': {'Image': image, 'Env': []}, 'State': {'Running': True},
            'HostConfig': {'NetworkMode': mode},
            'Mounts': [{'Destination': '/config', 'Type': mount, 'Source': '/test/config', 'RW': rw}],
            'NetworkSettings': {'Ports': {'80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '18123'}]}}}


def test_exact_existing_packet_and_app_source_match():
    assert hashlib.sha256((ROOT / 'nexhome_neighbor/payload.tar.gz').read_bytes()).hexdigest() == entry.PAYLOAD_SHA256
    for name in ['terminal.py', 'app_entry.py']:
        assert (ROOT / 'distribution' / name).read_bytes() == (ROOT / 'nexhome_neighbor' / name).read_bytes()


def test_only_one_discoverable_app_and_official_repository_shape():
    assert (ROOT / 'repository.yaml').is_file()
    configs = [p for p in ROOT.rglob('config.yaml')
               if not any(part.startswith('.') for part in p.relative_to(ROOT).parts)]
    assert configs == [ROOT / 'nexhome_neighbor/config.yaml']
    assert 'host_network' not in configs[0].read_text()


def test_distribution_pins_are_synchronized():
    data = json.loads((ROOT / 'distribution/lock.json').read_text())
    assert data['frontend_sha256'] == hashlib.sha256((ROOT / 'distribution/terminal.py').read_bytes()).hexdigest()
    assert data['bootstrap_sha256'] == hashlib.sha256((ROOT / 'distribution/start.sh').read_bytes()).hexdigest()
    assert data['frontend_sha256'] in (ROOT / 'distribution/start.sh').read_text()
    assert data['version'] == '0.1.0'
    assert data['public_release_created'] is False


def test_assembler_keeps_packet_immutable(tmp_path):
    shutil.copytree(ROOT / 'distribution', tmp_path / 'distribution')
    (tmp_path / 'nexhome_neighbor').mkdir()
    shutil.copyfile(ROOT / 'nexhome_neighbor/payload.tar.gz', tmp_path / 'nexhome_neighbor/payload.tar.gz')
    first = assemble(tmp_path)
    second = assemble(tmp_path)
    assert first == second
    assert first['artifact_archive_sha256'] == entry.PAYLOAD_SHA256


@pytest.mark.parametrize('url', [
    'http://github.com/a', 'https://evil.example/pkg',
    entry.DEFAULT_SOURCE + '?token=secret', 'https://name:secret@github.com/a',
    'https://github.com/Doggiekong/nexhome-neighbor-edition/archive/main.zip',
])
def test_untrusted_source_refused(url):
    with pytest.raises(entry.FriendlyError):
        entry.checked_source(url)


def test_fixed_release_source_only():
    assert entry.checked_source(entry.DEFAULT_SOURCE) == entry.DEFAULT_SOURCE


@pytest.mark.parametrize('url', ['http://127.0.0.1:9000', 'http://192.168.0.40:9000'])
def test_explicit_fixture_source(url):
    assert entry.checked_source(url, fixture=True) == url


@pytest.mark.parametrize('url', ['http://8.8.8.8/pkg', 'http://public.example/pkg'])
def test_fixture_cannot_be_public(url):
    with pytest.raises(entry.FriendlyError):
        entry.checked_source(url, fixture=True)


def test_tampered_archive_never_written(tmp_path):
    response = io.BytesIO(b'tampered')
    opener = Mock()
    opener.open.return_value = response
    destination = tmp_path / 'archive'
    with pytest.raises(entry.FriendlyError, match='校验'):
        entry.fetch_payload(entry.DEFAULT_SOURCE, destination, opener=opener)
    assert not destination.exists()


def test_frozen_archive_extracts_and_manifest_matches(tmp_path):
    entry.extract_payload(ROOT / 'nexhome_neighbor/payload.tar.gz', tmp_path / 'package')
    assert (tmp_path / 'package/neighbor_installer/engine.py').is_file()


@pytest.mark.parametrize('name,link', [('../escape', False), ('/absolute', False), ('safe', True)])
def test_archive_traversal_and_links_refused(tmp_path, name, link):
    p = tmp_path / 'unsafe.tgz'
    with tarfile.open(p, 'w:gz') as archive:
        item = tarfile.TarInfo(name)
        if link:
            item.type = tarfile.SYMTYPE
            item.linkname = '/etc/passwd'
        archive.addfile(item, io.BytesIO(b''))
    with pytest.raises(entry.FriendlyError):
        entry.extract_payload(p, tmp_path / 'out')
    assert not (tmp_path / 'escape').exists()


def test_single_detected_candidate_no_path_input():
    values = entry.candidates([target()], '192.168.0.20')
    assert len(values) == 1
    assert values[0]['config'] == '/test/config'
    assert values[0]['connect_url'] == 'http://127.0.0.1:18123'
    assert values[0]['browser_url'] == 'http://192.168.0.20:18123'
    assert values[0]['unsupported'] is None


def test_multiple_candidates_preserved_for_menu():
    a, b = target(), target()
    b['Name'] = '/other-ha'
    assert [x['name'] for x in entry.candidates([a, b], '192.168.0.20')] == ['ha-test', 'other-ha']


def test_dual_stack_same_published_port_is_one_endpoint():
    row = target()
    row['NetworkSettings']['Ports']['80/tcp'].append({'HostIp': '::', 'HostPort': '18123'})
    assert entry.candidates([row], '192.168.0.20')[0]['unsupported'] is None


@pytest.mark.parametrize('name', ['SUPERVISOR_TOKEN=never-print', 'HASSIO_TOKEN=never-print'])
def test_supervisor_managed_core_not_selected(name):
    row = target()
    row['Config']['Env'] = [name]
    assert entry.candidates([row], '192.168.0.20') == []


@pytest.mark.parametrize('image', ['nginx:latest', 'ghcr.io/home-assistant/observer:latest'])
def test_unrelated_services_never_selected(image):
    assert entry.candidates([target(image=image)], '192.168.0.20') == []


@pytest.mark.parametrize('mount,rw', [('volume', True), ('bind', False)])
def test_unsupported_mount_not_silently_rewritten(mount, rw):
    assert entry.candidates([target(mount=mount, rw=rw)], '192.168.0.20')[0]['unsupported']


def test_host_network_requires_config_inspection_not_scan():
    row = target(mode='host')
    row['NetworkSettings']['Ports'] = {}
    chosen = entry.candidates([row], '192.168.0.20')[0]
    assert chosen['unsupported'] is None and chosen['connect_url'] is None


@pytest.mark.parametrize('owner', ['MANUAL_UNKNOWN', 'OWNERSHIP_CONFLICT'])
def test_unknown_existing_install_gets_human_explanation(owner):
    with pytest.raises(entry.FriendlyError, match='不会覆盖'):
        entry.friendly_source({'owner': owner})


def test_official_existing_message_and_hacs_boundary():
    text = entry.friendly_source({'owner': None, 'installed': True, 'version': '1.1.16'})
    assert '备份' in text and '房间' in text and '自动化' in text
    with pytest.raises(entry.FriendlyError, match='HACS'):
        entry.friendly_source({'owner': 'OFFICIAL_HACS', 'hacs_claim_count': 1})


def test_no_docker_has_human_error(monkeypatch):
    monkeypatch.setattr(entry.subprocess, 'run', Mock(side_effect=FileNotFoundError))
    with pytest.raises(entry.FriendlyError, match='Docker'):
        entry.docker(['ps'])


def test_no_docker_permission_has_human_error(monkeypatch):
    monkeypatch.setattr(entry.subprocess, 'run', Mock(return_value=Mock(returncode=1)))
    with pytest.raises(entry.FriendlyError, match='权限'):
        entry.docker(['ps'])


def test_worker_secret_uses_stdin_not_argv_or_env(monkeypatch, tmp_path):
    monkeypatch.setattr(entry.os, 'stat', Mock(return_value=Mock(st_gid=989)))
    row = entry.candidates([target()], '192.168.0.20')[0]
    cmd = entry.worker_command(row, tmp_path, 'deploy')
    assert '--rm' in cmd and '--network' in cmd
    assert not any(x in cmd for x in ['-e', '--env', '--privileged'])
    assert row['image'] in cmd and row['name'] in cmd


def test_container_changed_after_menu_refuses_before_worker(monkeypatch, tmp_path):
    row = entry.candidates([target()], '192.168.0.20')[0]
    changed = target()
    changed['Id'] = 'c' * 64
    monkeypatch.setattr(entry, 'docker', lambda _: json.dumps([changed]))
    execute = Mock()
    monkeypatch.setattr(entry.subprocess, 'run', execute)
    with pytest.raises(entry.FriendlyError, match='发生变化'):
        entry.run_worker(row, tmp_path, 'deploy', token='not-logged')
    execute.assert_not_called()


def test_arrow_menu_actual_pty():
    import pty
    import select
    import signal
    import time
    pid, fd = pty.fork()
    if pid == 0:
        os.execv(sys.executable, [sys.executable, '-c',
                 "from distribution.terminal import choose;print('RESULT='+str(choose('Select',['one','two'])),flush=True)"])
    output = b''
    try:
        deadline = time.monotonic() + 4
        sent = False
        while time.monotonic() < deadline:
            if select.select([fd], [], [], 0.1)[0]:
                try:
                    output += os.read(fd, 4096)
                except OSError:
                    break
                if b'> one' in output and not sent:
                    os.write(fd, b'\x1b[B\n')
                    sent = True
                if b'RESULT=' in output:
                    break
        assert b'RESULT=1' in output
    finally:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        os.close(fd)


def test_specific_lan_binding_is_not_assumed_to_listen_on_loopback():
    row = target()
    row['NetworkSettings']['Ports']['80/tcp'][0]['HostIp'] = '192.168.0.20'
    selected = entry.candidates([row], '192.168.0.20')[0]
    assert selected['connect_url'] == 'http://192.168.0.20:18123'
    assert selected['unsupported'] is None
