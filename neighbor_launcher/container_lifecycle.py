"""Explicit existing Docker HA lifecycle over the local Unix API only."""

import http.client
import json
import re
import socket
from pathlib import Path

from neighbor_installer.files import InstallerError
from neighbor_installer.lifecycle import SupervisorLifecycle


class LocalEngineConnection(http.client.HTTPConnection):
    def __init__(self):
        super().__init__("localhost", timeout=90)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect("/var/run/docker.sock")


class ContainerLifecycle(SupervisorLifecycle):
    def __init__(self, container, config, token, ha_url, *, request=None):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", container):
            raise InstallerError("CONTAINER_NAME_INVALID")
        self.container, self.config = container, Path(config).resolve()
        self.engine_request = request or self._request_engine
        super().__init__(token, ha_token=token, ha_url=ha_url, timeout=210)
        version = self.engine_request("GET", "/version")
        try:
            high = tuple(map(int, version["ApiVersion"].split(".")))
            low = tuple(map(int, version.get("MinAPIVersion", "1.41").split(".")))
            chosen = min(high, (1, 47))
            if len(chosen) != 2 or not (1, 41) <= chosen or chosen < low:
                raise ValueError
            self.api = "/v%d.%d" % chosen
        except KeyError, TypeError, ValueError, AttributeError:
            raise InstallerError("CONTAINER_ENGINE_API_UNSUPPORTED") from None
        self._inspect()

    @staticmethod
    def _request_engine(method, path):
        connection = LocalEngineConnection()
        try:
            connection.request(method, path, body=b"" if method == "POST" else None)
            response = connection.getresponse()
            if response.status not in ({200} if method == "GET" else {204, 304}):
                raise InstallerError("CONTAINER_ENGINE_HTTP_" + str(response.status))
            raw = response.read(1_048_577)
            if len(raw) > 1_048_576:
                raise InstallerError("CONTAINER_ENGINE_RESPONSE_TOO_LARGE")
            return json.loads(raw) if raw else None
        except OSError, ValueError, http.client.HTTPException:
            raise InstallerError("EXISTING_CONTAINER_OPERATION_FAILED") from None
        finally:
            connection.close()

    def _inspect(self):
        try:
            info = self.engine_request("GET", self.api + "/containers/" + self.container + "/json")
            # Official standalone images also have io.hass.type=core. Supervisor
            # authorization, not an image label, identifies managed Core.
            environment = info.get("Config", {}).get("Env", [])
            if not isinstance(environment, list) or any(
                isinstance(item, str) and item.startswith(("SUPERVISOR_TOKEN=", "HASSIO_TOKEN="))
                for item in environment
            ):
                raise InstallerError("SUPERVISOR_MANAGED_CONTAINER_REFUSED")
            mounts = [m for m in info["Mounts"] if m["Destination"] == "/config"]
            if (
                len(mounts) != 1
                or mounts[0]["Type"] != "bind"
                or not mounts[0].get("RW")
                or Path(mounts[0]["Source"]).resolve() != self.config
            ):
                raise InstallerError("CONTAINER_CONFIG_MOUNT_MISMATCH")
            return info
        except KeyError, TypeError, ValueError, AttributeError:
            raise InstallerError("CONTAINER_INSPECTION_INVALID") from None

    def request(self, method, path):
        if method == "GET" and path == "/supervisor/info":
            info = self._inspect()
            return {"data": {"healthy": info.get("State", {}).get("Running") is True}}
        if method != "GET" or not path.startswith("/core/api/"):
            raise InstallerError("CONTAINER_API_OPERATION_REFUSED")
        return super().request(method, path)

    def stop(self):
        self._inspect()
        self.engine_request("POST", self.api + "/containers/" + self.container + "/stop?t=30")

    def start(self):
        self._inspect()
        self.engine_request("POST", self.api + "/containers/" + self.container + "/start")

    def restart(self):
        self.stop()
        self.start()
