"""Ingress-only HTTP boundary; no browser access token, external port or telemetry."""

import hmac
import secrets
from pathlib import Path

from aiohttp import web

from neighbor_installer.files import InstallerError

WEB = Path(__file__).parent / 'web'


def ingress_identity(request):
    if request.remote != '172.30.32.2':
        raise web.HTTPForbidden()
    user = request.headers.get('X-Remote-User-Id', '')
    path = request.headers.get('X-Ingress-Path', '')
    if (not user or len(user) > 128 or not user.isalnum()
            or not path.startswith('/api/hassio_ingress/')):
        raise web.HTTPForbidden()
    # Supervisor 2026.10 enforces panel_admin before forwarding this request.
    return user


def create_app(controller, *, authenticate=ingress_identity):
    nonces = {}

    @web.middleware
    async def secure(request, handler):
        user = authenticate(request)
        request['verified_user'] = user
        if request.method != 'GET':
            supplied = request.headers.get('X-Nexhome-Confirm', '')
            expected = nonces.get(user, '')
            if (not expected or not supplied.isascii() or not hmac.compare_digest(supplied, expected)
                    or request.headers.get('Sec-Fetch-Site') == 'cross-site'
                    or request.content_type != 'application/json'):
                raise web.HTTPForbidden()
        response = await handler(request)
        response.headers.update({
            'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; "
                                       "img-src 'self' data:; object-src 'none'; base-uri 'self'; "
                                       "frame-ancestors 'self'; form-action 'self'",
        })
        return response

    app = web.Application(middlewares=[secure], client_max_size=8192)

    async def state(request):
        user = request['verified_user']
        if user not in nonces:
            if len(nonces) >= 64:
                raise web.HTTPServiceUnavailable()
            nonces[user] = secrets.token_urlsafe(32)
        return web.json_response(controller.view() | {'confirmation': nonces[user]})

    async def action(request):
        try:
            data = await request.json()
            if not isinstance(data, dict) or set(data) - {'action', 'plan', 'confirmed'}:
                raise InstallerError('UI_INPUT_INVALID')
            started = controller.start(data.get('action'), data)
            return web.json_response({'accepted': started}, status=202 if started else 409)
        except (ValueError, InstallerError):
            return web.json_response({'error': '这一步暂时不能执行，请重新检查。'}, status=400)

    async def diagnostics(_request):
        return web.json_response(controller.diagnostics(), headers={
            'Content-Disposition': 'attachment; filename="nexhome-diagnostics.json"'})

    async def asset(request):
        name = request.match_info.get('name', 'index.html')
        if name not in {'index.html', 'app.js', 'style.css'}:
            raise web.HTTPNotFound()
        return web.FileResponse(WEB / name)

    app.router.add_get('/', asset)
    app.router.add_get('/api/state', state)
    app.router.add_post('/api/action', action)
    app.router.add_get('/api/diagnostics', diagnostics)
    app.router.add_get('/{name}', asset)
    return app
