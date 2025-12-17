"""Constants for the Laica Smart Scale integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "laica_smart_scale"

MANUFACTURER_ID = 0xA0AC

PLATFORMS: tuple[Platform, ...] = (Platform.SENSOR,)

# Since scales only advertise when used, keep entities available for a long time.
DEFAULT_AVAILABILITY_WINDOW = timedelta(hours=24)

DATA_LAST_SERVICE_INFO = "last_service_info"
DATA_LAST_SEEN = "last_seen"
DATA_LAST_PARSE_REPORT = "last_parse_report"
DATA_LAST_MEASUREMENTS = "last_measurements"
DATA_UNSUB_BLUETOOTH = "unsub_bluetooth"


def update_signal(entry_id: str) -> str:
    """Dispatcher signal for new advertisements for a config entry."""

    return f"{DOMAIN}_update_{entry_id}"

