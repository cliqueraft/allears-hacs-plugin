"""Services for the AllEars integration."""

from __future__ import annotations

import functools
import logging
import time

import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ALLEARS_APP_IDENTIFIER,
    ATTR_APP,
    ATTR_CONFIDENCE,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
    DOMAIN,
    SERVICE_CLEAR_HISTORY,
    SERVICE_TEST_WEBHOOK,
)
from .coordinator import AllEarsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string])}
)


def _target_coordinators(
    hass: HomeAssistant, call: ServiceCall
) -> list[AllEarsDataUpdateCoordinator]:
    """Coordinators for the devices in the call, or all of them if none given."""
    device_ids: list[str] | None = call.data.get(ATTR_DEVICE_ID)
    return [
        c
        for c in hass.data.get(DOMAIN, {}).values()
        if isinstance(c, AllEarsDataUpdateCoordinator)
        and (not device_ids or c.device_id in device_ids)
    ]


async def async_clear_history(hass: HomeAssistant, call: ServiceCall) -> None:
    """Forget the last sound event on the chosen (or all) AllEars devices."""
    for coordinator in _target_coordinators(hass, call):
        coordinator.async_clear()
        _LOGGER.info(
            "AllEars history cleared by user %s for entry %s",
            call.context.user_id,
            coordinator.entry_id,
        )


async def async_test_webhook(hass: HomeAssistant, call: ServiceCall) -> None:
    """Fire a synthetic sound event to test automations."""
    for coordinator in _target_coordinators(hass, call):
        await coordinator.async_handle_sound_event(
            {
                ATTR_APP: ALLEARS_APP_IDENTIFIER,
                ATTR_FLOW_NAME: "Test Flow",
                ATTR_SOUND_CLASS: "Test Sound",
                ATTR_CONFIDENCE: 1.0,
                ATTR_TIMESTAMP: int(time.time() * 1000),
            }
        )

    _LOGGER.debug("Test webhook event fired by user %s", call.context.user_id)


def async_register_services(hass: HomeAssistant) -> None:
    """Register all AllEars services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_HISTORY,
        functools.partial(async_clear_history, hass),
        schema=SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_TEST_WEBHOOK,
        functools.partial(async_test_webhook, hass),
        schema=SERVICE_SCHEMA,
    )
