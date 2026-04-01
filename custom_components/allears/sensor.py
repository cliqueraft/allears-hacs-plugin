"""Sensor platform for AllEars."""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ALLEARS_APP_IDENTIFIER,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
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
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat()


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
    _attr_device_class = SensorDeviceClass.ENUM

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
    def options(self) -> list[str] | None:
        """Return a list of available flows to populate HA automation dropdowns.

        Using SensorDeviceClass.ENUM makes Home Assistant automatically build
        dropdown menus in the Automation UI for Device and State triggers.
        """
        flows = self.coordinator.flow_list.copy() if self.coordinator.flow_list else []
        current = self.native_value

        # In ENUM sensors, current state MUST exist in the options list.
        if current and current not in flows:
            flows.append(current)

        return flows if flows else None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return self._attr_device_info
