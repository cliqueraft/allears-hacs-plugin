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
    BINARY_SENSOR_ACTIVE_WINDOW_SECONDS,
    DOMAIN,
    ICON_EAR,
)
from .coordinator import DATA_EVENT_SEQ, AllEarsDataUpdateCoordinator
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
    _attr_translation_key = BINARY_SENSOR_ACTIVE
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
        self._last_seq: int | None = None

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
        """Turn on only for a new sound event.

        Flow registration and clear-history also refresh the coordinator;
        those must not switch the sensor on and fire automations.
        """
        data = self.coordinator.data or {}
        seq = data.get(DATA_EVENT_SEQ)
        if not data:
            # History cleared: switch off straight away.
            self._last_seq = None
            self._cancel_reset()
            if self._is_active:
                self._is_active = False
                self.async_write_ha_state()
            return
        if seq is not None and seq == self._last_seq:
            return
        self._last_seq = seq
        self._is_active = True

        self._cancel_reset()
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

    @callback
    def _cancel_reset(self) -> None:
        """Cancel a pending auto-reset, if any."""
        if self.coordinator._reset_callback is not None:
            self.coordinator._reset_callback()
            self.coordinator._reset_callback = None

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when removed from hass."""
        self._cancel_reset()
        await super().async_will_remove_from_hass()
