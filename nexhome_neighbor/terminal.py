"""Pinned distribution frontend. The existing Installer/Controller remain authoritative.

Host entry uses only Python's standard library; frozen SDK runs in the selected
existing HA image so a NAS Python version is never upgraded or silently assumed.
"""
import argparse
import getpass
import hashlib
import ipaddress
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

VERSION = '0.1.0'
DEFAULT_SOURCE = 'https://github.com/Doggiekong/nexhome-neighbor-edition/releases/download/v0.1.0'
PAYLOAD_NAME = 'nexhome-0.1.0.tar.gz'
PAYLOAD_SHA256 = '9c689161a068d840d1be66f88f1673fca2b5f4866a04b93237fe6b8b8679b093'
ARTIFACT_SHA256 = 'f6102c029ee3c27f65beafc68a5cbf22639df2a3a2dc713e0131f84144e390e1'
MAX_BYTES = 8 * 1024 * 1024


class FriendlyError(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.message, self.code = message, code


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        # GitHub release assets use a separately hosted HTTPS object, never HTTP.
        old, new = urllib.parse.urlsplit(request.full_url), urllib.parse.urlsplit(newurl)
        allowed = {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
        if old.scheme != 'https' or new.scheme != 'https' or old.hostname not in allowed or new.hostname not in allowed:
            raise FriendlyError('下载地址发生了未获信任的跳转，已停止。', 'SOURCE_REDIRECT_REFUSED')
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def checked_source(value, fixture=False):
    u = urllib.parse.urlsplit(value)
    if u.username or u.password or u.query or u.fragment or not u.hostname:
        raise FriendlyError('安装来源格式不正确，不能包含凭据。', 'SOURCE_INVALID')
    if fixture:
        try:
            addr = ipaddress.ip_address(u.hostname)
        except ValueError:
            raise FriendlyError('测试分发源必须是明确的本地地址。', 'FIXTURE_SOURCE_INVALID') from None
        if u.scheme not in {'http', 'https'} or not (addr.is_private or addr.is_loopback):
            raise FriendlyError('测试分发源只能用于本地隔离验证。', 'FIXTURE_SOURCE_INVALID')
    elif value.rstrip('/') != DEFAULT_SOURCE:
        raise FriendlyError('安装来源不是固定的官方项目分发入口。', 'SOURCE_NOT_PINNED')
    return value.rstrip('/')


def fetch_payload(source, target, *, opener=None):
    request = urllib.request.Request(source + '/' + PAYLOAD_NAME, headers={'User-Agent': 'Nexhome-Neighbor-Bootstrap/0.1.0'})
    try:
        with (opener or urllib.request.build_opener(NoRedirect())).open(request, timeout=30) as response:
            raw = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code in {401, 403, 404}:
            raise FriendlyError('当前固定安装包尚未开放或您没有访问权限；不会改装其他版本。', 'PINNED_PACKAGE_UNAVAILABLE') from None
        raise FriendlyError('暂时无法取得固定安装包，请稍后重试。', 'PACKAGE_DOWNLOAD_FAILED') from None
    except OSError:
        raise FriendlyError('下载连接失败，尚未修改 Home Assistant。', 'PACKAGE_DOWNLOAD_FAILED') from None
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != PAYLOAD_SHA256:
        raise FriendlyError('安装包校验不一致，已停止，不会继续安装。', 'PACKAGE_HASH_MISMATCH')
    target.write_bytes(raw)
    return target


def extract_payload(archive, root):
    root.mkdir(mode=0o700)
    seen = set()
    with tarfile.open(archive, 'r:gz') as src:
        members = src.getmembers()
        if len(members) > 1000 or sum(m.size for m in members) > 32 * MAX_BYTES:
            raise FriendlyError('安装包内容超出预期，已停止。', 'PACKAGE_LAYOUT_INVALID')
        for m in members:
            p = PurePosixPath(m.name)
            if not m.isfile() or p.is_absolute() or str(p) != m.name or '..' in p.parts or '\\' in m.name or m.name in seen:
                raise FriendlyError('安装包路径不安全，已停止。', 'PACKAGE_LAYOUT_INVALID')
            seen.add(m.name)
        for m in members:
            dst = root / m.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.extractfile(m).read())
    manifest = root / 'bundle/artifact.json'
    # The SDK's Artifact.open independently verifies the deployed file manifest.
    if not manifest.is_file() or hashlib.sha256(manifest.read_bytes()).hexdigest() != ARTIFACT_SHA256:
        raise FriendlyError('安装包的组件清单与固定版本不一致。', 'ARTIFACT_PIN_MISMATCH')


def candidates(rows, lan_ip):
    found = []
    for x in rows:
        cfg = x.get('Config', {})
        image = cfg.get('Image', '')
        image_name = image.split('@')[0].split(':')[0].rsplit('/', 1)[-1]
        if not image.startswith(('ghcr.io/home-assistant/', 'homeassistant/')) or not (
            image_name in {'home-assistant', 'homeassistant'} or image_name.endswith('-homeassistant')
        ):
            continue
        env = cfg.get('Env') or []
        if any(e.startswith(('SUPERVISOR_TOKEN=', 'HASSIO_TOKEN=')) for e in env):
            continue
        mounts = [m for m in x.get('Mounts', []) if m.get('Destination') == '/config']
        reason = None
        if len(mounts) != 1 or mounts[0].get('Type') != 'bind' or not mounts[0].get('RW'):
            reason = '这个配置卷不是当前已验证的可写主机目录，请让本机管理员确认。'
        config = mounts[0].get('Source') if len(mounts) == 1 else None
        if config and (not Path(config).is_absolute() or any(c in config for c in ',\n\r')):
            reason = '这个配置路径暂不能安全传给安装核心。'
        ports = x.get('NetworkSettings', {}).get('Ports', {}) or {}
        bindings = [(p, b) for p, values in ports.items() for b in (values or []) if p in {'80/tcp', '8123/tcp'}]
        port = None
        unique = {(p, b.get('HostPort')) for p, b in bindings}
        if len(unique) == 1:
            _, binding = next(((p, b) for p, b in bindings if b.get('HostIp') in {'0.0.0.0', '127.0.0.1', lan_ip}), bindings[0])
            port = binding.get('HostPort')
            ip = binding.get('HostIp')
            if ip not in {'0.0.0.0', '127.0.0.1', '::', lan_ip}:
                reason = '此容器的网页绑定暂不能可靠判断，请让本机管理员确认。'
        elif x.get('HostConfig', {}).get('NetworkMode') == 'host':
            # Selected container's inert config inspection supplies the port later.
            pass
        else:
            reason = '没有找到唯一的HA网页端口映射，请让本机管理员确认。'
        found.append({'name': x['Name'].lstrip('/'), 'id': x['Id'], 'image': x['Image'],
                      'config': config, 'running': bool(x.get('State', {}).get('Running')),
                      'connect_url': 'http://127.0.0.1:' + str(port) if port else None,
                      'browser_url': 'http://' + lan_ip + ':' + str(port) if port else None,
                      'unsupported': reason, 'network_mode': x.get('HostConfig', {}).get('NetworkMode')})
    return found


def docker(args):
    try:
        p = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        raise FriendlyError('没有找到 Docker；请在运行 Home Assistant 的主机终端打开安装入口。', 'DOCKER_NOT_FOUND') from None
    if p.returncode:
        raise FriendlyError('无法访问本机 Docker；可能未运行或当前账号没有权限。', 'DOCKER_ACCESS_DENIED')
    return p.stdout


def local_ip():
    # Routing query only: UDP connect sends no packet and never addresses a Hub.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('192.0.2.1', 9))
        ip = sock.getsockname()[0]
    finally:
        sock.close()
    if not ipaddress.ip_address(ip).is_private:
        raise FriendlyError('没有找到可供浏览器使用的家庭网络地址。', 'LAN_ADDRESS_UNCONFIRMED')
    return ip


def choose(title, options):
    import termios
    import tty
    with open('/dev/tty', 'r') as reader, open('/dev/tty', 'w') as stream:
        selected = 0
        previous = termios.tcgetattr(reader.fileno())
        try:
            tty.setcbreak(reader.fileno())
            while True:
                stream.write('\n' + title + '\n')
                for i, label in enumerate(options):
                    stream.write(('> ' if i == selected else '  ') + label + '\n')
                stream.flush()
                key = reader.read(1)
                if key == '\x1b':
                    tail = reader.read(2)
                    if tail == '[A':
                        selected = (selected - 1) % len(options)
                    elif tail == '[B':
                        selected = (selected + 1) % len(options)
                elif key in {'\r', '\n'}:
                    return selected
                elif key in {'', '\x03', '\x04'}:
                    raise KeyboardInterrupt
                stream.write('\x1b[' + str(len(options) + 2) + 'A\x1b[J')
        finally:
            termios.tcsetattr(reader.fileno(), termios.TCSADRAIN, previous)


def auth(origin):
    # No redirects when sending local HA credentials/tokens.
    class RejectRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args):
            return None
    opener = urllib.request.build_opener(RejectRedirect())
    def request(path, data, form=False):
        raw = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
        req = urllib.request.Request(origin + path, data=raw, headers={'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json'})
        with opener.open(req, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    with open('/dev/tty', 'r') as reader, open('/dev/tty', 'w') as terminal:
        terminal.write('\n请输入自己的HA用户名（仅用于当前本机登录）：')
        terminal.flush()
        username = reader.readline().strip()
        password = getpass.getpass('HA密码（隐藏输入、不保存）：', stream=terminal)
    try:
        first = request('/auth/login_flow', {'client_id': origin + '/', 'handler': ['homeassistant', None], 'redirect_uri': origin + '/?auth_callback=1'})
        result = request('/auth/login_flow/' + first['flow_id'], {'client_id': origin + '/', 'username': username, 'password': password})
        if result.get('type') != 'create_entry':
            raise FriendlyError('未完成本机HA登录；请先检查自己的账号或登录要求。', 'HA_LOGIN_NOT_COMPLETED')
        tokens = request('/auth/token', {'grant_type': 'authorization_code', 'code': result['result'], 'client_id': origin + '/'}, True)
        return tokens, lambda: request('/auth/token', {'action': 'revoke', 'token': tokens['refresh_token']}, True)
    except (OSError, KeyError, ValueError):
        raise FriendlyError('无法登录这台HA，未继续安装；密码和授权不会写入日志。', 'HA_LOGIN_FAILED') from None
    finally:
        password = None


def worker_command(candidate, directory, operation):
    uid, gid = os.getuid(), os.getgid()
    socket_gid = os.stat('/var/run/docker.sock').st_gid
    config = candidate['config']
    return ['docker', 'run', '--rm', '-i', '--network', 'host', '--user', str(uid) + ':' + str(gid),
            '--group-add', str(socket_gid), '--cpus', '0.5', '--memory', '512m', '--pids-limit', '128',
            '--mount', 'type=bind,src=' + config + ',dst=' + config,
            '--mount', 'type=bind,src=' + str(directory) + ',dst=/bootstrap,readonly',
            '--mount', 'type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock',
            '--entrypoint', 'python', candidate['image'], '/bootstrap/terminal.py',
            '--worker', operation, '--target', candidate['name'], '--config', config,
            '--origin', candidate['connect_url']]


def run_worker(candidate, directory, operation, token='', expected=None):
    current = json.loads(docker(['inspect', candidate['name']]))[0]
    if current.get('Id') != candidate['id'] or current.get('Image') != candidate['image']:
        raise FriendlyError('选择的HA容器在检查后发生变化，请重新检查，不会继续安装。', 'TARGET_CHANGED')
    p = subprocess.run(worker_command(candidate, directory, operation),
                       input=json.dumps({'token': token, 'expected': expected}), text=True, capture_output=True, timeout=360)
    try:
        result = json.loads(p.stdout)
    except ValueError:
        raise FriendlyError('这台HA的执行环境暂不兼容安装入口，尚不能继续。', 'WORKER_ENVIRONMENT_UNSUPPORTED') from None
    if result.get('error'):
        raise FriendlyError(result['message'], result['error'])
    return result


def worker(args):
    sys.path.insert(0, '/bootstrap/package')
    from neighbor_installer.artifact import Artifact
    from neighbor_installer.detection import identity_fingerprint
    from neighbor_installer.engine import Installer
    from neighbor_installer.files import digest, load
    from neighbor_launcher.bootstrap import deploy, verify_completion
    from neighbor_launcher.container_lifecycle import ContainerLifecycle
    from neighbor_launcher.controller import Controller
    package = Path('/bootstrap/package')
    artifact = Artifact.open(package / 'bundle', ARTIFACT_SHA256)
    message = json.load(sys.stdin)
    token = message.get('token', '')
    runtime = ContainerLifecycle(args.target, args.config, token, args.origin) if args.worker != 'inspect' else None
    engine = Installer(args.config, runtime, trusted_trees=load(package / 'trusted-trees.json', {}))
    def fingerprint():
        return digest({'source': engine.inspect(), 'identity': identity_fingerprint(Path(args.config))})
    if args.worker == 'inspect':
        return {'detected': engine.inspect()}
    if args.worker == 'deploy' and fingerprint() != message.get('expected'):
        return {'error': 'PREVIEW_CHANGED', 'message': '预览后的安装来源或用户配置发生变化，请重新检查。'}
    controller = Controller(engine, artifact, engine.state / 'beginner-ui')
    output = []
    if args.worker == 'verify':
        code = verify_completion(controller, output=output.append)
    else:
        code = deploy(controller, confirm=args.worker == 'deploy', output=output.append)
    view = controller.view()
    return {'code': code, 'screen': view['screen'], 'title': view['title'],
            'completion': view.get('completion', {}), 'native_url': view.get('native_url'),
            'details': controller.diagnostics(), 'messages': output, 'fingerprint': fingerprint()}


def friendly_source(detected):
    owner = detected.get('owner') or ''
    if owner in {'MANUAL_UNKNOWN', 'OWNERSHIP_CONFLICT'}:
        raise FriendlyError('发现以前安装过NexHome，但文件与安装来源对不上。为了保留您现在的配置，这次不会覆盖。', owner)
    if detected.get('hacs_claim_count') or detected.get('hacs_schema_uncertain'):
        raise FriendlyError('这份NexHome仍由HACS负责更新。请先由本机维护者通过HACS正常界面交接；不要删除HA里的设备条目。', 'HACS_HANDOFF_REQUIRED')
    if detected.get('installed'):
        return '✓ 已有NexHome ' + str(detected.get('version')) + '；升级将先备份并保留原设备、名称、房间和自动化引用。'
    return '✓ 当前尚未安装NexHome；将安装友邻加强版0.1.0。'


def host(args):
    print('\nNexHome 滨融府友邻加强版 0.1.0\n安装助手\n正在检查当前环境……', flush=True)
    if platform.system() != 'Linux':
        raise FriendlyError('请在运行Home Assistant的Linux/NAS主机Terminal中执行；这里不是已验证环境。', 'PLATFORM_UNSUPPORTED')
    source = checked_source(args.source, args.fixture)
    ip = local_ip()
    identifiers = docker(['ps', '-aq']).split()
    rows = json.loads(docker(['inspect', *identifiers])) if identifiers else []
    targets = candidates(rows, ip)
    if not targets:
        choose('没有自动找到Home Assistant；请在它所在主机确认安装方式后再试。', ['Docker/NAS容器：返回原管理工具检查', '我不知道：请本机维护者协助', '退出'])
        return 2
    chosen = targets[0] if len(targets) == 1 else targets[choose('请选择您正在使用的Home Assistant（↑ ↓ Enter）', [x['name'] for x in targets])]
    print('✓ 找到Home Assistant Container：' + chosen['name'], flush=True)
    if chosen['unsupported']:
        raise FriendlyError(chosen['unsupported'], 'TARGET_UNSUPPORTED')
    if not chosen['running']:
        raise FriendlyError('所选HA当前没有运行，请先在原管理工具启动它，再打开安装入口。', 'HA_STOPPED')
    config = Path(chosen['config'])
    if not config.is_dir() or not os.access(config, os.W_OK):
        raise FriendlyError('找到了HA，但当前账号没有修改配置目录的权限。', 'CONFIG_PERMISSION_DENIED')
    if chosen['network_mode'] == 'host':
        inspection = "import json,yaml;from pathlib import Path;s=Path('/config/configuration.yaml').read_text();assert len(s)<1048576;d=yaml.load(s,Loader=yaml.BaseLoader) or {};h=d.get('http',{});assert isinstance(h,dict);print(json.dumps({'port':int(h.get('server_port',8123)),'tls':bool(h.get('ssl_certificate'))}))"
        data = json.loads(docker(['exec', chosen['id'], 'python', '-c', inspection]))
        if not 1 <= data['port'] <= 65535 or data['tls']:
            raise FriendlyError('此HA使用需要额外确认的网页配置；不会降低TLS验证或猜地址。', 'HA_HTTP_SETTINGS_UNCONFIRMED')
        chosen['connect_url'] = 'http://127.0.0.1:' + str(data['port'])
        chosen['browser_url'] = 'http://' + ip + ':' + str(data['port'])
    print('✓ 自动找到配置目录和网页地址（无需手填）', flush=True)
    if choose('需要本机Docker和所选HA配置权限；不会操作其他容器。', ['继续检查固定安装包', '退出']) != 0:
        return 0
    with tempfile.TemporaryDirectory(prefix='nexhome-bootstrap-') as tmp:
        directory = Path(tmp)
        archive = fetch_payload(source, directory / PAYLOAD_NAME)
        extract_payload(archive, directory / 'package')
        shutil.copyfile(__file__, directory / 'terminal.py')
        print('✓ 固定0.1.0安装包及组件清单校验通过', flush=True)
        detected = run_worker(chosen, directory, 'inspect')['detected']
        print(friendly_source(detected), flush=True)
        print('请只在当前本机输入自己的HA账号；仅当前会话使用，结束后撤销授权。', flush=True)
        tokens, revoke = auth(chosen['connect_url'])
        try:
            preview = run_worker(chosen, directory, 'preview', tokens['access_token'])
            print('✓ Home Assistant ' + str(preview['details']['technical'].get('ha_version') or '版本已检查'), flush=True)
            print(preview['title'], flush=True)
            if preview['screen'] not in {'confirm', 'configured', 'ready', 'installed', 'latest'}:
                raise FriendlyError('检查发现当前来源或恢复状态需要处理，本次不会继续。', 'CORE_PREVIEW_REFUSED')
            if preview['screen'] == 'confirm':
                while True:
                    action = choose('将先备份、安装，并可能短暂重启这台HA。已有设备身份优先保留。', ['开始安装', '查看技术详情', '退出'])
                    if action == 2:
                        return 0
                    if action == 1:
                        print(json.dumps(preview['details'], ensure_ascii=False), flush=True)
                        continue
                    break
                result = run_worker(chosen, directory, 'deploy', tokens['access_token'], preview['fingerprint'])
                if result['code'] != 0:
                    raise FriendlyError('安装尚未完成，请保留当前状态和备份，不要删除重建。', 'CORE_DEPLOYMENT_NOT_COMPLETED')
            print('✓ 组件部署已确认；已有配置会沿用。', flush=True)
            print('请在浏览器打开：' + chosen['browser_url'] + '/config/integrations/integration/nexhome', flush=True)
            print('新安装连接入口：' + chosen['browser_url'] + '/_my_redirect/config_flow_start?domain=nexhome', flush=True)
            while True:
                action = choose('回到HA完成原生连接，看到设备，操作一盏灯并核对真实状态。', ['已找到设备并完成首次操作，检查READY', '查看技术详情', '稍后继续，安全退出'])
                if action == 2:
                    return 0
                result = run_worker(chosen, directory, 'verify', tokens['access_token'])
                if action == 1:
                    print(json.dumps(result['details'], ensure_ascii=False), flush=True)
                elif result['screen'] == 'ready':
                    print('✓ 安装与首次使用已完成：READY。终端可以关闭。', flush=True)
                    return 0
                else:
                    print('尚未取得完整的真实控制读回证据，不会提前标记完成。', flush=True)
        finally:
            try:
                revoke()
            except Exception:
                print('临时登录授权撤销未获确认，请在HA个人资料中撤销本次会话。', flush=True)
            tokens = None


def main():
    parser = argparse.ArgumentParser(description='NexHome友邻加强版安装助手')
    parser.add_argument('--source', default=DEFAULT_SOURCE)
    parser.add_argument('--fixture', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--worker', choices=['inspect', 'preview', 'deploy', 'verify'], help=argparse.SUPPRESS)
    parser.add_argument('--target', help=argparse.SUPPRESS)
    parser.add_argument('--config', help=argparse.SUPPRESS)
    parser.add_argument('--origin', help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.worker:
            try:
                print(json.dumps(worker(args), ensure_ascii=False))
            except Exception as error:
                code = str(error) if re_safe_code(str(error)) else type(error).__name__
                print(json.dumps({'error': code, 'message': '安装核心未确认安全条件；请保留现状，查看技术详情。'}))
            return 0
        return host(args)
    except FriendlyError as error:
        print('\n' + error.message, flush=True)
        try:
            if choose('本次已停止，不会强行覆盖。', ['退出', '查看技术详情']) == 1:
                print('技术代号：' + error.code, flush=True)
        except (OSError, KeyboardInterrupt):
            pass
        return 2
    except KeyboardInterrupt:
        print('\n已退出。若部署进行中被中断，请保留备份并先检查恢复状态。', flush=True)
        return 130
    except Exception:
        print('\n当前环境不能安全继续。未显示密码或异常堆栈，请保留现状让本机维护者检查。', flush=True)
        return 2


def re_safe_code(value):
    return bool(value) and len(value) < 100 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in value)


if __name__ == '__main__':
    raise SystemExit(main())
