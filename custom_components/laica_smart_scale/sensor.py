"""Sensors for Laica Smart Scale."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.util import dt as dt_util

from .const import (
    DATA_LAST_MEASUREMENTS,
    DATA_LAST_SEEN,
    DEFAULT_AVAILABILITY_WINDOW,
    DOMAIN,
    update_signal,
)


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    address = entry.data.get("address") or entry.unique_id
    return DeviceInfo(
        identifiers={(DOMAIN, address)},
        name=entry.title,
        manufacturer="Laica",
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities(
        [
            LaicaLastSeenSensor(hass, entry),
            LaicaWeightSensor(hass, entry),
            LaicaImpedanceSensor(hass, entry),
        ]
    )


class LaicaSensorBase(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, description: SensorEntityDescription) -> None:
        self.hass = hass
        self._entry_id = entry.entry_id
        self._address = entry.data.get("address") or entry.unique_id
        self.entity_description = description

        self._attr_unique_id = f"{self._address}_{description.key}"
        self._attr_device_info = _device_info(entry)

    @property
    def available(self) -> bool:
        entry_data: dict[str, Any] = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        last_seen: datetime | None = entry_data.get(DATA_LAST_SEEN)
        if last_seen is None:
            return False
        return dt_util.utcnow() - last_seen <= DEFAULT_AVAILABILITY_WINDOW

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, update_signal(self._entry_id), self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class LaicaLastSeenSensor(LaicaSensorBase):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            entry,
            SensorEntityDescription(
                key="last_seen",
                name="Last seen",
                device_class=SensorDeviceClass.TIMESTAMP,
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
        )

    @property
    def native_value(self) -> datetime | None:
        entry_data: dict[str, Any] = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        return entry_data.get(DATA_LAST_SEEN)


class LaicaWeightSensor(LaicaSensorBase):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            entry,
            SensorEntityDescription(
                key="weight",
                name="Weight",
                device_class=SensorDeviceClass.WEIGHT,
                native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                state_class=SensorStateClass.MEASUREMENT,
            ),
        )

    @property
    def native_value(self) -> float | None:
        entry_data: dict[str, Any] = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        measurements: dict[str, Any] = entry_data.get(DATA_LAST_MEASUREMENTS, {})
        return measurements.get("weight_kg")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        entry_data: dict[str, Any] = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        measurements: dict[str, Any] = entry_data.get(DATA_LAST_MEASUREMENTS, {})

        attrs = {
            "raw_weight_kg": measurements.get("weight_kg_raw"),
            "is_stable": measurements.get("weight_is_stable"),
            "raw_flags": measurements.get("weight_raw_flags"),
        }

        # Hide empty attrs to reduce UI noise.
        return {k: v for k, v in attrs.items() if v is not None} or None


class LaicaImpedanceSensor(LaicaSensorBase):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            entry,
            SensorEntityDescription(
                key="impedance",
                name="Impedance",
                native_unit_of_measurement="Ω",
                state_class=SensorStateClass.MEASUREMENT,
            ),
        )

    @property
    def native_value(self) -> int | None:
        entry_data: dict[str, Any] = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        measurements: dict[str, Any] = entry_data.get(DATA_LAST_MEASUREMENTS, {})
        return measurements.get("impedance_ohm")
