"""Binary sensor platform for AllEars."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BINARY_SENSOR_ACTIVE,
    BINARY_SENSOR_ACTIVE_NAME,
    BINARY_SENSOR_ACTIVE_WINDOW_SECONDS,
    DOMAIN,
    ICON_EAR,
)
from .coordinator import AllEarsDataUpdateCoordinator
from .sensor import _build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AllEars binary sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AllEarsSoundActiveSensor(coordinator, entry)])


class AllEarsSoundActiveSensor(
    CoordinatorEntity[AllEarsDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of an AllEars active binary sensor."""

    _attr_has_entity_name = True
    _attr_name = BINARY_SENSOR_ACTIVE_NAME
    _attr_device_class = BinarySensorDeviceClass.SOUND
    _attr_icon = ICON_EAR

    def __init__(
        self, coordinator: AllEarsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)  # type: ignore[call-arg]
        self._attr_unique_id = f"{entry.entry_id}_{BINARY_SENSOR_ACTIVE}"
        self._attr_device_info = _build_device_info(entry)
        self._is_active: bool = False

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        return self._is_active

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return self._attr_device_info

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._is_active = True

        if self.coordinator._reset_callback is not None:
            self.coordinator._reset_callback()
            self.coordinator._reset_callback = None

        self.coordinator._reset_callback = async_call_later(
            self.hass,
            BINARY_SENSOR_ACTIVE_WINDOW_SECONDS,
            self._async_reset,
        )

        self.async_write_ha_state()

    @callback
    def _async_reset(self, _now: datetime) -> None:
        """Auto-reset sound_active to False after window expires."""
        self._is_active = False
        self.coordinator._reset_callback = None
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when removed from hass."""
        if self.coordinator._reset_callback is not None:
            self.coordinator._reset_callback()
            self.coordinator._reset_callback = None
        await super().async_will_remove_from_hass()
