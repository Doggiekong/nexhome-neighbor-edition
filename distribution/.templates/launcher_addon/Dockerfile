# Initial DEV/TEST amd64 build reuses the exact already-tested HA Python runtime.
# No Core services start: the entrypoint is only this install companion.
ARG BUILD_FROM=ghcr.io/home-assistant/qemux86-64-homeassistant:2026.10.2
FROM ${BUILD_FROM}
WORKDIR /opt/nexhome
COPY neighbor_installer /opt/nexhome/neighbor_installer
COPY neighbor_launcher /opt/nexhome/neighbor_launcher
COPY bundle /opt/nexhome/bundle
COPY trusted-trees.json /opt/nexhome/trusted-trees.json
ENV PYTHONPATH=/opt/nexhome PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python", "-m", "neighbor_launcher"]
