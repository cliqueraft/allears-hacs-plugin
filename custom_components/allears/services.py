"""Services for the AllEars integration."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    ALLEARS_APP_IDENTIFIER,
    ATTR_APP,
    ATTR_CONFIDENCE,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
    DOMAIN,
    EVENT_SOUND_DETECTED,
    SERVICE_CLEAR_HISTORY,
    SERVICE_TEST_WEBHOOK,
)
from .coordinator import AllEarsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_clear_history(hass: HomeAssistant, call: ServiceCall) -> None:
    """Reset coordinator state for all AllEars entries."""
    for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
        if isinstance(coordinator, AllEarsDataUpdateCoordinator):
            coordinator.async_set_updated_data({})
            _LOGGER.info(
                "AllEars history cleared by user %s for entry %s",
                call.context.user_id,
                entry_id,
            )


async def async_test_webhook(hass: HomeAssistant, call: ServiceCall) -> None:
    """Fire a synthetic sound event to test automations."""
    test_payload: dict[str, Any] = {
        ATTR_APP: ALLEARS_APP_IDENTIFIER,
        ATTR_FLOW_NAME: "Test Flow",
        ATTR_SOUND_CLASS: "Test Sound",
        ATTR_CONFIDENCE: 1.0,
        ATTR_TIMESTAMP: int(time.time() * 1000),
    }

    for coordinator in hass.data.get(DOMAIN, {}).values():
        if isinstance(coordinator, AllEarsDataUpdateCoordinator):
            await coordinator.async_handle_sound_event(test_payload)

    hass.bus.async_fire(EVENT_SOUND_DETECTED, test_payload)

    _LOGGER.debug(
        "Test webhook event fired by user %s",
        call.context.user_id,
    )


def async_register_services(hass: HomeAssistant) -> None:
    """Register all AllEars services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_HISTORY,
        functools.partial(async_clear_history, hass),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_TEST_WEBHOOK,
        functools.partial(async_test_webhook, hass),
    )
