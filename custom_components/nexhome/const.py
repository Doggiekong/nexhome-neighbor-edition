"""Wire constants and conservative candidate defaults."""

DOMAIN = "nexhome"
PRODUCT_VERSION = "0.1.0"
UPSTREAM_BASE_VERSION = "1.1.16"
PRODUCT_ID = "nexhome-neighbor-edition"
VERSION = PRODUCT_VERSION
UPSTREAM_VERSION = UPSTREAM_BASE_VERSION
IP_CONFIG = "ip_address"
SN_CONFIG = "sn_input"
PLATFORMS = ["light", "fan", "climate", "cover", "sensor", "switch"]
POLL_SECONDS = 3
FRESH_SECONDS = 15
PENDING_SECONDS = 5
CHUNK_SIZE = 64
QUEUE_LIMIT = 32
CONTROL_BURST = 3
