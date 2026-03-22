"""The AllEars Sound Tracker integration."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.components import webhook as ha_webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import CONF_DEVICE_NAME, CONF_WEBHOOK_ID, DOMAIN, SERVICE_CLEAR_HISTORY, PLATFORMS
from .coordinator import AllEarsDataUpdateCoordinator
from .services import async_register_services
from .webhook import handle_webhook

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the AllEars component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AllEars from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if CONF_WEBHOOK_ID not in entry.data or CONF_DEVICE_NAME not in entry.data:
        _LOGGER.error("Missing required config entry data")
        return False

    coordinator = AllEarsDataUpdateCoordinator(hass, entry.entry_id)

    ha_webhook.async_register(
        hass,
        DOMAIN,
        entry.title,
        entry.data[CONF_WEBHOOK_ID],
        handle_webhook,
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        ha_webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload entry."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register custom AllEars services if not already registered."""
    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_HISTORY):
        async_register_services(hass)
