"""Device triggers for AllEars.

One trigger, "AllEars heard a sound", with optional Flow and Sound filters.
In the automation editor the Flow field is a dropdown of the flows the
phone has registered, so users pick a flow instead of typing its name.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_DEVICE_ID,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    DOMAIN,
    EVENT_SOUND_DETECTED,
)
from .coordinator import AllEarsDataUpdateCoordinator

TRIGGER_TYPE_SOUND_DETECTED = "sound_detected"

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): TRIGGER_TYPE_SOUND_DETECTED,
        vol.Optional(ATTR_FLOW_NAME): cv.string,
        vol.Optional(ATTR_SOUND_CLASS): cv.string,
    }
)


def _coordinator_for_device(
    hass: HomeAssistant, device_id: str
) -> AllEarsDataUpdateCoordinator | None:
    """Return the coordinator behind an AllEars device, if it is loaded."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for entry_id in device.config_entries:
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
        if isinstance(coordinator, AllEarsDataUpdateCoordinator):
            return coordinator
    return None


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for AllEars devices."""
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: TRIGGER_TYPE_SOUND_DETECTED,
        }
    ]


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """Show Flow and Sound fields in the automation editor."""
    coordinator = _coordinator_for_device(hass, config[CONF_DEVICE_ID])
    flows = coordinator.flow_list if coordinator else []
    # Keep a previously saved flow selectable even if the app dropped it.
    current = config.get(ATTR_FLOW_NAME)
    if current and current not in flows:
        flows = [*flows, current]

    flow_field: Any = vol.In(flows) if flows else cv.string
    return {
        "extra_fields": vol.Schema(
            {
                vol.Optional(ATTR_FLOW_NAME): flow_field,
                vol.Optional(ATTR_SOUND_CLASS): cv.string,
            }
        )
    }


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: CALLBACK_TYPE,
    trigger_info: dict[str, Any],
) -> CALLBACK_TYPE:
    """Attach a trigger as an event trigger scoped to this device."""
    event_data: dict[str, Any] = {ATTR_DEVICE_ID: config[CONF_DEVICE_ID]}
    if config.get(ATTR_FLOW_NAME):
        event_data[ATTR_FLOW_NAME] = config[ATTR_FLOW_NAME]
    if config.get(ATTR_SOUND_CLASS):
        event_data[ATTR_SOUND_CLASS] = config[ATTR_SOUND_CLASS]

    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_SOUND_DETECTED,
            event_trigger.CONF_EVENT_DATA: event_data,
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
