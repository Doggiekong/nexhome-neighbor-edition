"""Explicit runtime control boundary, independent of installer filesystem access."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .files import InstallerError


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise InstallerError('AUTHENTICATED_REDIRECT_REFUSED')


@dataclass
class Probe:
    ha_version: str
    running: bool
    healthy: bool
    integration_visible: bool
    entry_states: dict


class SupervisorLifecycle:
    """Run in an authorized companion outside Core, not inside restarting Core."""

    def __init__(self, token, *, ha_token=None, ha_url='http://homeassistant:80', timeout=150, interval=2):
        if not token:
            raise InstallerError("SUPERVISOR_AUTH_REQUIRED")
        self._token = token
        self._ha_token = ha_token
        self._ha_url = ha_url.rstrip('/')
        parsed = urllib.parse.urlsplit(self._ha_url)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or (
            parsed.path or parsed.query or parsed.fragment
        ):
            raise InstallerError('HA_ORIGIN_INVALID')
        self._opener = urllib.request.build_opener(NoRedirect())
        self.timeout = timeout
        self.interval = interval

    def request(self, method, path):
        core_api = path.startswith('/core/api/')
        if core_api and not self._ha_token:
            raise InstallerError('HA_AUTH_REQUIRED')
        url = self._ha_url + path.removeprefix('/core') if core_api else 'http://supervisor' + path
        request = urllib.request.Request(
            url,
            data=b"{}" if method == "POST" else None,
            method=method,
            headers={"Authorization": "Bearer " + (self._ha_token if core_api else self._token),
                     "Content-Type": "application/json"},
        )
        try:
            with self._opener.open(request, timeout=90) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise InstallerError(('HA' if core_api else 'SUPERVISOR') + '_HTTP_' + str(error.code)) from None
        except (OSError, ValueError):
            raise InstallerError(('HA' if core_api else 'SUPERVISOR') + '_REQUEST_FAILED') from None

    def probe(self):
        config = self.request("GET", "/core/api/config")
        supervisor = self.request("GET", "/supervisor/info")["data"]
        handlers = self.request("GET", "/core/api/config/config_entries/flow_handlers")
        entries = self.request("GET", "/core/api/config/config_entries/entry?domain=nexhome")
        visible = any(item == "nexhome" or isinstance(item, dict) and item.get("domain") == "nexhome" for item in handlers)
        return Probe(
            config["version"], config["state"] == "RUNNING", supervisor["healthy"], visible,
            {item["entry_id"]: item["state"] for item in entries},
        )

    def restart(self):
        self.request("POST", "/core/restart")

    def stop(self):
        self.request("POST", "/core/stop")

    def start(self):
        self.request("POST", "/core/start")

    def wait(self, present, baseline):
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                probe = self.probe()
                if (
                    probe.running and probe.healthy and probe.integration_visible == present
                    and probe.entry_states == baseline
                ):
                    return True
            except InstallerError:
                pass
            time.sleep(self.interval)
        return False
