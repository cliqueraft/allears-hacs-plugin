"""Tests for the AllEars coordinator."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from freezegun import freeze_time
from homeassistant.exceptions import HomeAssistantError

from custom_components.allears.const import (
    ATTR_CONFIDENCE,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
)
from custom_components.allears.coordinator import AllEarsDataUpdateCoordinator


@pytest.mark.asyncio
async def test_coordinator_updates_state_on_valid_event(
    coordinator: AllEarsDataUpdateCoordinator,
    valid_payload: dict[str, Any],
) -> None:
    """Test the coordinator correctly ingests a valid event payload."""
    await coordinator.async_handle_sound_event(valid_payload)
    assert coordinator.data[ATTR_SOUND_CLASS] == "Glass Breaking"
    assert coordinator.data[ATTR_FLOW_NAME] == "Front Door Security"
    assert coordinator.data[ATTR_CONFIDENCE] == 0.87
    assert "last_updated" in coordinator.data


@pytest.mark.asyncio
async def test_coordinator_rejects_payload_missing_sound_class(
    coordinator: AllEarsDataUpdateCoordinator,
    valid_payload: dict[str, Any],
) -> None:
    """Test the coordinator raises on missing sound class."""
    payload = dict(valid_payload)
    payload.pop(ATTR_SOUND_CLASS)
    with pytest.raises(HomeAssistantError):
        await coordinator.async_handle_sound_event(payload)


@pytest.mark.asyncio
async def test_coordinator_rejects_confidence_above_1(
    coordinator: AllEarsDataUpdateCoordinator,
    valid_payload: dict[str, Any],
) -> None:
    """Test the coordinator raises on confidence strictly greater than 1.0."""
    payload = dict(valid_payload)
    payload[ATTR_CONFIDENCE] = 1.001
    with pytest.raises(HomeAssistantError):
        await coordinator.async_handle_sound_event(payload)


@pytest.mark.asyncio
async def test_coordinator_rejects_confidence_below_0(
    coordinator: AllEarsDataUpdateCoordinator,
    valid_payload: dict[str, Any],
) -> None:
    """Test the coordinator raises on confidence strictly less than 0.0."""
    payload = dict(valid_payload)
    payload[ATTR_CONFIDENCE] = -0.001
    with pytest.raises(HomeAssistantError):
        await coordinator.async_handle_sound_event(payload)


@pytest.mark.asyncio
@freeze_time("2024-03-22 12:00:00")
async def test_coordinator_rejects_timestamp_drift(
    coordinator: AllEarsDataUpdateCoordinator,
    valid_payload: dict[str, Any],
) -> None:
    """Test the coordinator raises if the epoch timestamp is too far in the future."""
    import time

    payload = dict(valid_payload)
    payload[ATTR_TIMESTAMP] = int((time.time() + 61) * 1000)
    with pytest.raises(HomeAssistantError):
        await coordinator.async_handle_sound_event(payload)


@pytest.mark.asyncio
async def test_coordinator_logs_warning_on_invalid_payload(
    coordinator: AllEarsDataUpdateCoordinator,
    valid_payload: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the coordinator logs a WARNING prior to raising on validation failure."""
    payload = dict(valid_payload)
    payload.pop(ATTR_SOUND_CLASS)
    with caplog.at_level(logging.WARNING):
        with pytest.raises(HomeAssistantError):
            await coordinator.async_handle_sound_event(payload)
    assert "missing required keys" in caplog.text.lower()


@pytest.mark.asyncio
async def test_coordinator_sanitizes_long_values_before_logging(
    coordinator: AllEarsDataUpdateCoordinator,
    valid_payload: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the coordinator truncates long strings to prevent log spam."""
    payload = dict(valid_payload)
    payload[ATTR_SOUND_CLASS] = "A" * 500
    with caplog.at_level(logging.WARNING):
        # We also pop a field to force a validation error and print the payload
        payload.pop(ATTR_FLOW_NAME)
        with pytest.raises(HomeAssistantError):
            await coordinator.async_handle_sound_event(payload)
    # 200 is LOG_VALUE_MAX_LENGTH, with dict overhead it should still be < 300
    assert "A" * 250 not in caplog.text
