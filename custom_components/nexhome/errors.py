"""Safe error messages: never propagate raw HTTP bodies, URLs or credentials."""

from homeassistant.exceptions import HomeAssistantError


class GatewayError(HomeAssistantError):
    """Gateway operation failed, possibly after a command reached the device."""


class QueueFull(GatewayError):
    """Request was rejected before sending."""
