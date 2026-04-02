"""The tests for AllEars device triggers."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.allears.const import ATTR_FLOW_NAME, DOMAIN, EVENT_SOUND_DETECTED


@pytest.mark.asyncio
async def test_get_triggers(hass: HomeAssistant) -> None:
    """Test we get the expected triggers from a device."""
    await async_setup_component(hass, "device_automation", {})

    # We can just call the module directly or use device_automation
    from custom_components.allears.device_trigger import async_get_triggers

    triggers = await async_get_triggers(hass, "test_device_id")

    assert len(triggers) == 1
    assert triggers[0]["platform"] == "device"
    assert triggers[0]["domain"] == DOMAIN
    assert triggers[0]["device_id"] == "test_device_id"
    assert triggers[0]["type"] == "sound_detected"


@pytest.mark.asyncio
async def test_attach_trigger(hass: HomeAssistant) -> None:
    """Test attaching a trigger."""
    import custom_components.allears.device_trigger as device_trigger

    config = {
        "platform": "device",
        "domain": DOMAIN,
        "device_id": "test_device_id",
        "type": "sound_detected",
        ATTR_FLOW_NAME: "Speech test",
    }

    calls = []

    from typing import Any
    async def _action(*args: Any, **kwargs: Any) -> None:
        calls.append(args)

    detach = await device_trigger.async_attach_trigger(
        hass,
        config,
        _action,
        {
            "trigger_data": {"test": "data"},
            "variables": {},
            "id": "0",
            "idx": "0",
            "alias": "test",
        },
    )

    # Fire the correct event
    hass.bus.async_fire(EVENT_SOUND_DETECTED, {ATTR_FLOW_NAME: "Speech test"})
    await hass.async_block_till_done()

    assert len(calls) == 1

    # Fire mismatch event
    hass.bus.async_fire(EVENT_SOUND_DETECTED, {ATTR_FLOW_NAME: "Barking"})
    await hass.async_block_till_done()

    assert len(calls) == 1  # Should not increase

    # Detach
    detach()

    # Fire again after detach
    hass.bus.async_fire(EVENT_SOUND_DETECTED, {ATTR_FLOW_NAME: "Speech test"})
    await hass.async_block_till_done()

    assert len(calls) == 1  # Should not increase
