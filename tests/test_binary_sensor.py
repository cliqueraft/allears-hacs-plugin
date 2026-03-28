"""Tests for the AllEars binary sensor."""

from __future__ import annotations

from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.allears.const import (
    BINARY_SENSOR_ACTIVE,
    BINARY_SENSOR_ACTIVE_WINDOW_SECONDS,
    DOMAIN,
)
from custom_components.allears.coordinator import AllEarsDataUpdateCoordinator

from .conftest import ENTRY_ID_FOR_TESTS


@pytest.mark.asyncio
async def test_sound_active_false_before_first_event(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Test the sound active binary sensor is off before any event."""
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{ENTRY_ID_FOR_TESTS}_{BINARY_SENSOR_ACTIVE}"
    )
    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF


@pytest.mark.asyncio
async def test_sound_active_true_immediately_after_event(
    hass: HomeAssistant, setup_integration: MockConfigEntry, valid_payload: dict[str, Any]
) -> None:
    """Test the sound active binary sensor turns on immediately after an event."""
    coordinator: AllEarsDataUpdateCoordinator = hass.data[DOMAIN][ENTRY_ID_FOR_TESTS]
    await coordinator.async_handle_sound_event(valid_payload)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{ENTRY_ID_FOR_TESTS}_{BINARY_SENSOR_ACTIVE}"
    )
    state = hass.states.get(entity_id)
    assert state.state == STATE_ON


@pytest.mark.asyncio
async def test_sound_active_resets_to_false_after_30s(
    hass: HomeAssistant, setup_integration: MockConfigEntry, valid_payload: dict[str, Any]
) -> None:
    """Test the sound active binary sensor resets to off after the active window."""
    coordinator: AllEarsDataUpdateCoordinator = hass.data[DOMAIN][ENTRY_ID_FOR_TESTS]
    await coordinator.async_handle_sound_event(valid_payload)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{ENTRY_ID_FOR_TESTS}_{BINARY_SENSOR_ACTIVE}"
    )
    state = hass.states.get(entity_id)
    assert state.state == STATE_ON

    future = dt_util.utcnow() + dt_util.dt.timedelta(
        seconds=BINARY_SENSOR_ACTIVE_WINDOW_SECONDS + 1
    )
    async_fire_time_changed(hass, future)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF


@pytest.mark.asyncio
async def test_sound_active_debounces_rapid_events(
    hass: HomeAssistant, setup_integration: MockConfigEntry, valid_payload: dict[str, Any], freezer: FrozenDateTimeFactory
) -> None:
    """Test the sound active binary sensor debounces rapid events."""
    coordinator: AllEarsDataUpdateCoordinator = hass.data[DOMAIN][ENTRY_ID_FOR_TESTS]
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{ENTRY_ID_FOR_TESTS}_{BINARY_SENSOR_ACTIVE}"
    )

    # Fire first event at t=0
    await coordinator.async_handle_sound_event(valid_payload)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON

    # Move forward 15s (before 30s timer expires)
    freezer.tick(dt_util.dt.timedelta(seconds=15))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Fire second event at t=15, should create new 30s timer ending at t=45
    await coordinator.async_handle_sound_event(valid_payload)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON

    # Move forward 25s to t=40. Second timer hasn't expired yet.
    freezer.tick(dt_util.dt.timedelta(seconds=25))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON

    # Move forward 10s to t=50. Second timer expires at t=45, should be off now.
    freezer.tick(dt_util.dt.timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF


@pytest.mark.asyncio
async def test_sound_active_cancel_callback_on_remove(
    hass: HomeAssistant, setup_integration: MockConfigEntry, valid_payload: dict[str, Any]
) -> None:
    """Test the sound active binary sensor cancels its reset callback on removal."""
    coordinator: AllEarsDataUpdateCoordinator = hass.data[DOMAIN][ENTRY_ID_FOR_TESTS]
    await coordinator.async_handle_sound_event(valid_payload)
    await hass.async_block_till_done()

    assert getattr(coordinator, "_reset_callback", False)

    await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()

    assert getattr(coordinator, "_reset_callback", None) is None


@pytest.mark.asyncio
async def test_sound_active_device_class_is_sound(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Test the sound active binary sensor has the SOUND device class."""
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{ENTRY_ID_FOR_TESTS}_{BINARY_SENSOR_ACTIVE}"
    )

    state = hass.states.get(entity_id)
    assert state.attributes.get("device_class") == BinarySensorDeviceClass.SOUND
