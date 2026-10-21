"""HTTP boundary, plain-language review guard and native Supervisor transport."""

import asyncio
import re
import socket
import tempfile
from contextlib import asynccontextmanager
from html.parser import HTMLParser
from pathlib import Path

import pytest
import pytest_socket
from aiohttp import ClientSession, UnixConnector, web

from neighbor_installer.lifecycle import SupervisorLifecycle
from neighbor_launcher.copy import HACS_STEPS, PHASE_LABELS, SCREENS
from neighbor_launcher.server import create_app
from tests_launcher.test_flows import lab as base_lab


@pytest.fixture
def lab(tmp_path):
    return base_lab.__wrapped__(tmp_path)


@asynccontextmanager
async def local_client(app):
    # Unix-only HTTP: the full suite retains its ban on LAN/TCP sockets.
    original_connect = socket.socket.connect
    pytest_socket.socket_allow_hosts(['127.0.0.1'], allow_unix_socket=True)
    with tempfile.TemporaryDirectory(prefix='nx-ui-') as directory:
        path = str(Path(directory) / 'http.sock')
        runner = web.AppRunner(app)
        await runner.setup()
        try:
            await web.UnixSite(runner, path).start()
            async with ClientSession(base_url='http://localhost', connector=UnixConnector(path=path)) as client:
                yield client
        finally:
            await runner.cleanup()
            socket.socket.connect = original_connect


async def test_direct_access_is_denied(lab):
    ui, *_ = lab
    async with local_client(create_app(ui)) as client:
        assert (await client.get('/')).status == 403
        assert (await client.get('/api/state', headers={'X-Remote-User-Id': 'admin'})).status == 403


async def test_authenticated_ui_csrf_and_diagnostics(lab):
    ui, *_ = lab
    app = create_app(ui, authenticate=lambda _request: 'fixture-admin')
    async with local_client(app) as client:
        state = await (await client.get('/api/state')).json()
        assert state['screen'] == 'welcome'
        assert (await client.post('/api/action', json={'action': 'check'})).status == 403
        headers = {'X-Nexhome-Confirm': state['confirmation']}
        assert (await client.post('/api/action', headers=headers, json={'action': 'check'})).status == 202
        await asyncio.to_thread(ui.worker.join, 5)
        assert (await (await client.get('/api/state')).json())['screen'] == 'fresh'
        assert (await client.post('/api/action', headers=headers, json={'action': 'confirm', 'plan': 'forged'})).status == 409
        exported = await (await client.get('/api/diagnostics')).text()
        assert state['confirmation'] not in exported
        assert (await client.get('/api/state')).headers['Cache-Control'] == 'no-store'
        assert (await client.get('/private-file')).status == 404
        assert (await client.post('/api/action', headers=headers | {'Sec-Fetch-Site': 'cross-site'},
                                  json={'action': 'check'})).status == 403


class OrdinaryText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.detail_depth = 0
        self.values = []

    def handle_starttag(self, tag, attrs):
        if tag == 'details':
            assert 'open' not in dict(attrs)
            self.detail_depth += 1

    def handle_endtag(self, tag):
        if tag == 'details':
            self.detail_depth -= 1

    def handle_data(self, text):
        if not self.detail_depth:
            self.values.append(text)


def test_jargon_guard_default_text():
    parser = OrdinaryText()
    parser.feed(Path('neighbor_launcher/web/index.html').read_text(encoding='utf-8'))
    values = parser.values + [item for row in SCREENS.values() for item in row]
    values += list(PHASE_LABELS.values()) + HACS_STEPS
    forbidden = r'\b(config entry|entity_id|unique_id|registry|manifest|hash|SHA|transaction|rollback|ownership|owner|MANUAL_UNKNOWN|OWNERSHIP_CONFLICT|custom_components|IOTID|SN|NSDP|endpoint|schema|artifact|repository|migration)\b'
    assert not any(re.search(forbidden, value, re.I) for value in values)


def test_native_proxy_does_not_need_user_token():
    runtime = SupervisorLifecycle('TEST_SUPERVISOR_ONLY', proxy_core=True)
    seen = []
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read(self):
            return b'{}'
    class Opener:
        def open(self, request, timeout):
            seen.append((request.full_url, request.get_header('Authorization'), timeout))
            return Response()
    runtime._opener = Opener()
    runtime.request('GET', '/core/api/config')
    runtime.request('POST', '/core/restart')
    assert seen[0] == ('http://supervisor/core/api/config', 'Bearer TEST_SUPERVISOR_ONLY', 90)
    assert seen[1][0] == 'http://supervisor/core/restart'
