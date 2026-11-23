"""The AllEars Sound Tracker integration."""

from __future__ import annotations

import logging
import pathlib

import homeassistant.helpers.config_validation as cv
from homeassistant.components import webhook as ha_webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (
    ALLEARS_APP_IDENTIFIER,
    CARD_FILENAME,
    CARD_URL_PATH,
    CONF_DEVICE_NAME,
    CONF_WEBHOOK_ID,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_HISTORY,
    VERSION,
)
from .coordinator import AllEarsDataUpdateCoordinator
from .services import async_register_services
from .webhook import handle_webhook

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

DATA_CARD_REGISTERED = f"{DOMAIN}_card_registered"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the Lovelace card and load it on every dashboard.

    `hass.http.register_static_path` was removed in HA 2025.7, which left the
    card unreachable on current installs. Use the async API, falling back for
    older cores. The card is also added as an extra frontend module, so users
    no longer have to add a dashboard resource by hand.
    """
    if hass.data.get(DATA_CARD_REGISTERED) or getattr(hass, "http", None) is None:
        return
    www_dir = str(pathlib.Path(__file__).parent / "www")
    try:
        try:
            from homeassistant.components.http import StaticPathConfig
        except ImportError:  # HA < 2024.7
            hass.http.register_static_path(CARD_URL_PATH, www_dir, False)
        else:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(CARD_URL_PATH, www_dir, False)]
            )
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Could not serve the AllEars card (non-fatal)", exc_info=True)
        return

    try:
        from homeassistant.components.frontend import add_extra_js_url

        # The version query makes browsers fetch the new card after an update.
        add_extra_js_url(hass, f"{CARD_URL_PATH}/{CARD_FILENAME}?v={VERSION}")
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Frontend not loaded; add the card as a dashboard resource")

    hass.data[DATA_CARD_REGISTERED] = True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the AllEars component."""
    hass.data.setdefault(DOMAIN, {})
    await _async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AllEars from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if CONF_WEBHOOK_ID not in entry.data or CONF_DEVICE_NAME not in entry.data:
        _LOGGER.error("Missing required config entry data")
        return False

    webhook_id: str = entry.data[CONF_WEBHOOK_ID]
    coordinator = AllEarsDataUpdateCoordinator(hass, entry.entry_id, webhook_id)
    await coordinator.async_load_flows()

    # Create the device first so its id can be attached to every event.
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=str(entry.data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)),
        manufacturer=ALLEARS_APP_IDENTIFIER,
        model="Sound Tracker",
        sw_version=VERSION,
    )
    coordinator.device_id = device.id

    hass.data[DOMAIN][entry.entry_id] = coordinator

    ha_webhook.async_register(
        hass,
        DOMAIN,
        entry.title,
        webhook_id,
        handle_webhook,
        allowed_methods=["GET"],
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_HISTORY):
        async_register_services(hass)

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
