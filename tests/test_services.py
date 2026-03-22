"""Tests for the AllEars services."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.allears.const import (
    ALLEARS_APP_IDENTIFIER,
    ATTR_APP,
    ATTR_CONFIDENCE,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
    DOMAIN,
    EVENT_SOUND_DETECTED,
    SERVICE_CLEAR_HISTORY,
    SERVICE_TEST_WEBHOOK,
)


@pytest.mark.asyncio
async def test_clear_history_resets_coordinator_data(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the clear history service resets coordinator data."""
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    await coordinator.async_handle_sound_event(valid_payload)
    await hass.async_block_till_done()

    assert coordinator.data != {}

    await hass.services.async_call(DOMAIN, SERVICE_CLEAR_HISTORY, blocking=True)
    await hass.async_block_till_done()

    assert coordinator.data == {}


@pytest.mark.asyncio
async def test_clear_history_logs_calling_user(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the clear history service logs the calling user ID."""
    with caplog.at_level(logging.INFO):
        context = Context(user_id="test_user_123")
        await hass.services.async_call(
            DOMAIN, SERVICE_CLEAR_HISTORY, blocking=True, context=context
        )
        await hass.async_block_till_done()

    assert "test_user_123" in caplog.text


@pytest.mark.asyncio
async def test_test_webhook_fires_synthetic_event(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Test the test webhook service fires a synthetic event."""
    events = []
    hass.bus.async_listen(EVENT_SOUND_DETECTED, events.append)

    await hass.services.async_call(DOMAIN, SERVICE_TEST_WEBHOOK, blocking=True)
    await hass.async_block_till_done()

    assert len(events) == 1


@pytest.mark.asyncio
async def test_test_webhook_event_has_correct_test_payload(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Test the test webhook synthetic event has the correct payload."""
    events = []
    hass.bus.async_listen(EVENT_SOUND_DETECTED, events.append)

    await hass.services.async_call(DOMAIN, SERVICE_TEST_WEBHOOK, blocking=True)
    await hass.async_block_till_done()

    assert len(events) == 1
    event_data = events[0].data

    assert event_data[ATTR_SOUND_CLASS] == "Test Sound"
    assert event_data[ATTR_CONFIDENCE] == 1.0
    assert event_data[ATTR_APP] == ALLEARS_APP_IDENTIFIER
    assert isinstance(event_data[ATTR_TIMESTAMP], int)
    assert event_data[ATTR_TIMESTAMP] > 0
