"""Sensor platform for AllEars."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ALLEARS_APP_IDENTIFIER,
    ATTR_CONFIDENCE,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
    CONF_DEVICE_NAME,
    DOMAIN,
    ICON_MICROPHONE,
    ICON_WAVES,
    SENSOR_LAST_FLOW,
    SENSOR_LAST_FLOW_NAME,
    SENSOR_LAST_SOUND,
    SENSOR_LAST_SOUND_NAME,
    VERSION,
)
from .coordinator import AllEarsDataUpdateCoordinator


def _epoch_ms_to_iso8601(epoch_ms: int) -> str:
    """Convert a Unix millisecond timestamp to an ISO8601 string.

    Args:
        epoch_ms: Unix timestamp in milliseconds.

    Returns:
        ISO8601 formatted string in UTC, e.g.
        '2024-03-22T12:00:00+00:00'.
    """
    return datetime.fromtimestamp(
        epoch_ms / 1000, tz=timezone.utc
    ).isoformat()


def _build_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Build device info for AllEars sensors."""
    name = entry.data.get(CONF_DEVICE_NAME, "AllEars Device")
    info: DeviceInfo = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": str(name),
        "manufacturer": ALLEARS_APP_IDENTIFIER,
        "model": "Sound Tracker",
        "sw_version": VERSION,
    }
    return info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AllEars sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AllEarsLastSoundSensor(coordinator, entry),
            AllEarsLastFlowSensor(coordinator, entry),
        ]
    )


class AllEarsLastSoundSensor(
    CoordinatorEntity[AllEarsDataUpdateCoordinator], SensorEntity
):
    """Representation of an AllEars last sound sensor."""

    _attr_has_entity_name = True
    _attr_name = SENSOR_LAST_SOUND_NAME
    _attr_icon = ICON_MICROPHONE

    def __init__(
        self, coordinator: AllEarsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)  # type: ignore[call-arg]
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_LAST_SOUND}"
        self._attr_device_info = _build_device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            val = self.coordinator.data.get(ATTR_SOUND_CLASS)
            return str(val) if val is not None else None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        conf = self.coordinator.data.get(ATTR_CONFIDENCE)
        raw_ts: int | None = self.coordinator.data.get(ATTR_TIMESTAMP)
        return {
            ATTR_FLOW_NAME: self.coordinator.data.get(ATTR_FLOW_NAME),
            ATTR_CONFIDENCE: float(f"{float(conf):.3f}") if conf is not None else None,
            ATTR_TIMESTAMP: _epoch_ms_to_iso8601(raw_ts) if raw_ts else None,
            "last_updated": self.coordinator.data.get("last_updated"),
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return self._attr_device_info


class AllEarsLastFlowSensor(
    CoordinatorEntity[AllEarsDataUpdateCoordinator], SensorEntity
):
    """Representation of an AllEars last flow sensor."""

    _attr_has_entity_name = True
    _attr_name = SENSOR_LAST_FLOW_NAME
    _attr_icon = ICON_WAVES

    def __init__(
        self, coordinator: AllEarsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)  # type: ignore[call-arg]
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_LAST_FLOW}"
        self._attr_device_info = _build_device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            val = self.coordinator.data.get(ATTR_FLOW_NAME)
            return str(val) if val is not None else None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        raw_ts: int | None = self.coordinator.data.get(ATTR_TIMESTAMP)
        return {
            ATTR_SOUND_CLASS: self.coordinator.data.get(ATTR_SOUND_CLASS),
            ATTR_TIMESTAMP: _epoch_ms_to_iso8601(raw_ts) if raw_ts else None,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return self._attr_device_info
