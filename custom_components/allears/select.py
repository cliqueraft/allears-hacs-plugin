"""Select platform for AllEars — Active Flow Filter entity."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_FLOW_NAME,
    DOMAIN,
    EVENT_FLOW_SELECTED,
    ICON_WAVES,
    SELECT_ALL_FLOWS,
    SELECT_FLOW_FILTER,
    SELECT_FLOW_FILTER_NAME,
)
from .coordinator import AllEarsDataUpdateCoordinator
from .sensor import _build_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AllEars select entities based on a config entry."""
    coordinator: AllEarsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AllEarsFlowFilterSelect(coordinator, entry)])


class AllEarsFlowFilterSelect(
    CoordinatorEntity[AllEarsDataUpdateCoordinator], SelectEntity
):
    """Select entity that exposes the registered flow list as a dropdown.

    Design intent
    ─────────────
    * Options are populated automatically when the Android app calls
      GET /api/webhook/<id>?action=register_flows&flows=Flow1,Flow2
    * Selecting an option fires the `allears_flow_selected` HA event so that
      users can trigger automations without writing any YAML.
    * Selecting "All Flows" clears the filter — the card shows all events.
    * The entity is always present (even on first boot) with a single placeholder
      option so it is immediately visible and usable in automations.
    """

    _attr_has_entity_name = True
    _attr_name = SELECT_FLOW_FILTER_NAME
    _attr_icon = ICON_WAVES
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: AllEarsDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)  # type: ignore[call-arg]
        self._attr_unique_id = f"{entry.entry_id}_{SELECT_FLOW_FILTER}"
        self._attr_device_info = _build_device_info(entry)
        self._current_option: str = SELECT_ALL_FLOWS

    # ── SelectEntity interface ────────────────────────────────────────────────

    @property
    def options(self) -> list[str]:
        """Return current flow options from the coordinator registry.

        Always starts with 'All Flows' sentinel so automations and the card
        have a stable 'no filter' option.  The rest are populated from the
        Android app's flow catalogue.
        """
        registered = self.coordinator.flow_list
        if registered:
            return [SELECT_ALL_FLOWS] + registered
        # No flows registered yet — return placeholder options so the entity
        # is not stuck in an error state while waiting for the app to connect.
        return [SELECT_ALL_FLOWS]

    @property
    def current_option(self) -> str:
        """Return the currently selected option."""
        # Guard: if the options list shrinks and the current selection is gone,
        # fall back to the sentinel option gracefully.
        if self._current_option not in self.options:
            self._current_option = SELECT_ALL_FLOWS
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        """Handle the user selecting a flow from the dropdown.

        Fires the `allears_flow_selected` event on the HA event bus so that
        automations can trigger on it without any sensor attribute gymnastics.

        Example automation:
            trigger:
              platform: event
              event_type: allears_flow_selected
              event_data:
                flow_name: "My Flow"
        """
        if option not in self.options:
            _LOGGER.warning(
                "Tried to select unknown flow option '%s'. Valid: %s",
                option,
                self.options,
            )
            return

        self._current_option = option
        self.async_write_ha_state()

        # Fire event so HA automations can react without needing state sensors.
        event_data: dict[str, Any] = {ATTR_FLOW_NAME: option}
        self.hass.bus.async_fire(EVENT_FLOW_SELECTED, event_data)
        _LOGGER.debug("Flow selected: %s — fired: %s", option, EVENT_FLOW_SELECTED)

    # ── CoordinatorEntity ─────────────────────────────────────────────────────

    def _handle_coordinator_update(self) -> None:
        """Refresh state when coordinator broadcasts — picks up new flow options."""
        self.async_write_ha_state()
