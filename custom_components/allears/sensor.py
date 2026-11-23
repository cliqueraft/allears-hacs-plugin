"""Sensor platform for AllEars."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ALLEARS_APP_IDENTIFIER,
    ATTR_CONFIDENCE,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
    CONF_DEVICE_NAME,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
    ICON_MICROPHONE,
    ICON_WAVES,
    SENSOR_LAST_FLOW,
    SENSOR_LAST_SEEN,
    SENSOR_LAST_SOUND,
    VERSION,
)
from .coordinator import AllEarsDataUpdateCoordinator


def _epoch_ms_to_iso8601(epoch_ms: int) -> str:
    """Convert a Unix millisecond timestamp to an ISO8601 UTC string."""
    return datetime.fromtimestamp(epoch_ms / 1000, tz=UTC).isoformat()


def _build_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Build device info for AllEars entities."""
    name = entry.data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)
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
            AllEarsLastSeenSensor(coordinator, entry),
        ]
    )


class _AllEarsRestoringSensor(
    CoordinatorEntity[AllEarsDataUpdateCoordinator], SensorEntity, RestoreEntity
):
    """Base: shows the coordinator's value, or the last value before restart."""

    _attr_has_entity_name = True
    _data_key: str = ""

    def __init__(
        self, coordinator: AllEarsDataUpdateCoordinator, entry: ConfigEntry, key: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)  # type: ignore[call-arg]
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = _build_device_info(entry)
        self._restored_value: str | None = None
        self._restored_attrs: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        """Restore the last known value so a restart doesn't blank the card."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._restored_value = last.state
            self._restored_attrs = dict(last.attributes)

    def _handle_coordinator_update(self) -> None:
        """New data (or a clear) replaces the restored value."""
        self._restored_value = None
        self._restored_attrs = {}
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data and data.get(self._data_key) is not None:
            return str(data[self._data_key])
        return self._restored_value

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return self._attr_device_info


class AllEarsLastSoundSensor(_AllEarsRestoringSensor):
    """The sound class of the most recent detection."""

    _attr_icon = ICON_MICROPHONE
    _data_key = ATTR_SOUND_CLASS

    def __init__(
        self, coordinator: AllEarsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_LAST_SOUND)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Flow, confidence and time of the last detection."""
        data = self.coordinator.data
        if not data or data.get(ATTR_SOUND_CLASS) is None:
            keep = (ATTR_FLOW_NAME, ATTR_CONFIDENCE, ATTR_TIMESTAMP, "last_updated")
            restored = {k: v for k, v in self._restored_attrs.items() if k in keep}
            return restored or None
        attrs: dict[str, Any] = {
            ATTR_FLOW_NAME: data.get(ATTR_FLOW_NAME),
            ATTR_CONFIDENCE: round(float(data.get(ATTR_CONFIDENCE, 0.0)), 3),
            "last_updated": data.get("last_updated"),
        }
        ts = data.get(ATTR_TIMESTAMP)
        if isinstance(ts, int) and ts > 0:
            attrs[ATTR_TIMESTAMP] = _epoch_ms_to_iso8601(ts)
        return attrs


class AllEarsLastFlowSensor(_AllEarsRestoringSensor):
    """The AllEars flow that matched the most recent detection."""

    _attr_icon = ICON_WAVES
    _attr_device_class = SensorDeviceClass.ENUM
    _data_key = ATTR_FLOW_NAME

    def __init__(
        self, coordinator: AllEarsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_LAST_FLOW)

    @property
    def options(self) -> list[str] | None:
        """Registered flows, so the automation editor offers a dropdown.

        An ENUM sensor's current state must be one of its options.
        """
        flows = self.coordinator.flow_list
        current = self.native_value
        if current and current not in flows:
            flows.append(current)
        return flows or None


class AllEarsLastSeenSensor(
    CoordinatorEntity[AllEarsDataUpdateCoordinator], SensorEntity, RestoreEntity
):
    """When the phone last reached Home Assistant (any webhook call)."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:cellphone-check"

    def __init__(
        self, coordinator: AllEarsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)  # type: ignore[call-arg]
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_LAST_SEEN}"
        self._attr_translation_key = SENSOR_LAST_SEEN
        self._attr_device_info = _build_device_info(entry)

    async def async_added_to_hass(self) -> None:
        """Restore the last-seen time after a restart."""
        await super().async_added_to_hass()
        if self.coordinator.last_seen is not None:
            return
        last = await self.async_get_last_state()
        if last is None or last.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        try:
            self.coordinator.last_seen = datetime.fromisoformat(last.state)
        except ValueError:
            pass

    @property
    def native_value(self) -> datetime | None:
        """Return the last-seen time."""
        return self.coordinator.last_seen
