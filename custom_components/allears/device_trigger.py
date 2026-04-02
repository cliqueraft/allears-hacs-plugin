"""Provides device triggers for AllEars."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import ATTR_FLOW_NAME, DOMAIN, EVENT_SOUND_DETECTED

TRIGGER_TYPE_SOUND_DETECTED = "sound_detected"

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required("type"): TRIGGER_TYPE_SOUND_DETECTED,
        vol.Optional(ATTR_FLOW_NAME): cv.string,
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for AllEars devices."""
    triggers = [
        {
            # Required fields for HA device triggers
            "platform": "device",
            "domain": DOMAIN,
            "device_id": device_id,
            "type": TRIGGER_TYPE_SOUND_DETECTED,
        }
    ]
    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: CALLBACK_TYPE,
    trigger_info: dict[str, Any],
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    event_data: dict[str, Any] = {}

    # If the user specified a flow name in the visual editor UI,
    # we enforce that the event must exactly match the flow name.
    if ATTR_FLOW_NAME in config and config[ATTR_FLOW_NAME]:
        event_data[ATTR_FLOW_NAME] = config[ATTR_FLOW_NAME]

    # We map our custom device trigger straight into a native HA Event trigger
    event_config = {
        event_trigger.CONF_PLATFORM: "event",
        event_trigger.CONF_EVENT_TYPE: EVENT_SOUND_DETECTED,
        event_trigger.CONF_EVENT_DATA: event_data,
    }

    event_config_validated = event_trigger.TRIGGER_SCHEMA(event_config)

    return await event_trigger.async_attach_trigger(
        hass, event_config_validated, action, trigger_info, platform_type="device"
    )
