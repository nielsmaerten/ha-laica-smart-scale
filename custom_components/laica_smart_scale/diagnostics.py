"""Diagnostics support for Laica Smart Scale."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from .const import (
    DATA_LAST_MEASUREMENTS,
    DATA_LAST_PARSE_REPORT,
    DATA_LAST_SEEN,
    DATA_LAST_SERVICE_INFO,
    DOMAIN,
)

TO_REDACT = {CONF_ADDRESS, "address", "unique_id"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})

    last_seen = entry_data.get(DATA_LAST_SEEN)

    diagnostics = {
        "config_entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "unique_id": entry.unique_id,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "last_seen": None if last_seen is None else last_seen.isoformat(),
        "last_service_info": entry_data.get(DATA_LAST_SERVICE_INFO),
        "last_parse_report": entry_data.get(DATA_LAST_PARSE_REPORT),
        "last_measurements": entry_data.get(DATA_LAST_MEASUREMENTS),
    }

    return async_redact_data(diagnostics, TO_REDACT)

