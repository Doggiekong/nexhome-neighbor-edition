ARG BUILD_FROM=ghcr.io/home-assistant/qemux86-64-homeassistant:2026.10.2
FROM ${BUILD_FROM}
WORKDIR /opt/distribution
COPY payload.tar.gz terminal.py app_entry.py /opt/distribution/
ENV PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python", "/opt/distribution/app_entry.py"]
