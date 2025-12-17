"""Laica Smart Scale integration (passive BLE advertisements)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
import logging

from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_register_callback,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import (
    DATA_LAST_MEASUREMENTS,
    DATA_LAST_PARSE_REPORT,
    DATA_LAST_SEEN,
    DATA_LAST_SERVICE_INFO,
    DATA_UNSUB_BLUETOOTH,
    DOMAIN,
    MANUFACTURER_ID,
    PLATFORMS,
    update_signal,
)
from .laica_parser import parse_laica_manufacturer_data

_LOGGER = logging.getLogger(__name__)

UnsubCallback = Callable[[], None]

_CONFIG_ENTRY_VERSION = 2


def _as_hex(data: bytes) -> str:
    return data.hex()


def _service_info_for_diagnostics(service_info: BluetoothServiceInfoBleak) -> dict:
    """Return a JSON-serializable snapshot of the last advertisement."""

    return {
        "address": service_info.address,
        "name": service_info.name,
        "rssi": service_info.rssi,
        "source": getattr(service_info, "source", None),
        "connectable": getattr(service_info, "connectable", None),
        "service_uuids": list(service_info.service_uuids or []),
        "service_data": {k: _as_hex(v) for k, v in (service_info.service_data or {}).items()},
        "manufacturer_data": {
            str(k): {"len": len(v), "hex": _as_hex(v)} for k, v in (service_info.manufacturer_data or {}).items()
        },
    }


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries."""

    if entry.version < 2:
        registry = er.async_get(hass)
        updated = 0
        for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                registry.async_update_entity(entity_entry.entity_id, disabled_by=None)
                updated += 1

        hass.config_entries.async_update_entry(entry, version=_CONFIG_ENTRY_VERSION)
        _LOGGER.debug("Migrated %s: enabled %s entities", entry.entry_id, updated)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry_data = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})

    address = entry.data.get("address") or entry.unique_id

    entry_data.setdefault(DATA_LAST_MEASUREMENTS, {})
    entry_data[DATA_LAST_SERVICE_INFO] = None
    entry_data[DATA_LAST_SEEN] = None
    entry_data[DATA_LAST_PARSE_REPORT] = None

    def _async_bluetooth_callback(service_info: BluetoothServiceInfoBleak, change: BluetoothChange) -> None:
        now = dt_util.utcnow()
        manufacturer_data = service_info.manufacturer_data or {}
        payload = manufacturer_data.get(MANUFACTURER_ID)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Laica advert: address=%s name=%s rssi=%s source=%s change=%s uuids=%s service_data=%s manuf_keys=%s",
                service_info.address,
                service_info.name,
                service_info.rssi,
                getattr(service_info, "source", None),
                getattr(change, "name", str(change)),
                list(service_info.service_uuids or []),
                {k: _as_hex(v) for k, v in (service_info.service_data or {}).items()},
                sorted(manufacturer_data.keys()),
            )

        if payload is None:
            # This should not happen once we match by manufacturer_id, but keep it visible.
            _LOGGER.debug("Laica advert missing manufacturer_id=0x%04x payload", MANUFACTURER_ID)
            return

        report = parse_laica_manufacturer_data(payload)
        entry_data[DATA_LAST_SERVICE_INFO] = _service_info_for_diagnostics(service_info)
        entry_data[DATA_LAST_SEEN] = now
        entry_data[DATA_LAST_PARSE_REPORT] = {
            "payload_len": report.payload_len,
            "payload_hex": report.payload_hex,
            "candidate_type_offsets": list(report.candidate_type_offsets),
            "attempts": list(report.attempts),
            "parsed": None if report.parsed is None else asdict(report.parsed),
        }

        # Store latest measurements (best-effort).
        measurements = entry_data[DATA_LAST_MEASUREMENTS]
        if report.parsed is not None:
            if report.parsed.weight_kg is not None:
                measurements["weight_kg_raw"] = report.parsed.weight_kg
                measurements["weight_is_stable"] = report.parsed.is_stable
                measurements["weight_raw_flags"] = (
                    None if report.parsed.raw_flags is None else f"0x{report.parsed.raw_flags:x}"
                )
                if report.parsed.is_stable:
                    measurements["weight_kg"] = report.parsed.weight_kg
            if report.parsed.impedance_ohm is not None:
                measurements["impedance_ohm"] = report.parsed.impedance_ohm
            measurements["last_packet_kind"] = report.parsed.kind
            measurements["last_packet_type_offset"] = report.parsed.type_byte_offset
            measurements["last_packet_ts"] = now.isoformat()

        # Rich per-packet logging for offline analysis.
        if _LOGGER.isEnabledFor(logging.DEBUG):
            type_at_10 = f"0x{payload[10]:02x}" if len(payload) > 10 else None
            _LOGGER.debug(
                "Laica mfg 0x%04x: len=%s hex=%s type10=%s type_offsets=%s parsed=%s",
                MANUFACTURER_ID,
                report.payload_len,
                report.payload_hex,
                type_at_10,
                list(report.candidate_type_offsets),
                None if report.parsed is None else report.parsed,
            )
            if report.parsed is None:
                _LOGGER.debug("Laica decode attempts: %s", list(report.attempts))

        async_dispatcher_send(hass, update_signal(entry.entry_id))

    matcher = BluetoothCallbackMatcher(address=address)
    entry_data[DATA_UNSUB_BLUETOOTH] = async_register_callback(
        hass,
        _async_bluetooth_callback,
        matcher,
        BluetoothScanningMode.ACTIVE,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})

    unsub: UnsubCallback | None = entry_data.get(DATA_UNSUB_BLUETOOTH)
    if unsub is not None:
        unsub()
        entry_data[DATA_UNSUB_BLUETOOTH] = None

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return unload_ok
