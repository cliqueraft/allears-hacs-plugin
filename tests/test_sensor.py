"""Tests for the AllEars sensors."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.allears.const import (
    ATTR_CONFIDENCE,
    ATTR_TIMESTAMP,
    DOMAIN,
    SENSOR_LAST_FLOW,
    SENSOR_LAST_SOUND,
)
from custom_components.allears.coordinator import AllEarsDataUpdateCoordinator

from .conftest import ENTRY_ID_FOR_TESTS


@pytest.mark.asyncio
async def test_last_sound_sensor_state_unknown_before_first_event(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Test the last sound sensor state is unknown before any event."""
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{ENTRY_ID_FOR_TESTS}_{SENSOR_LAST_SOUND}"
    )
    state = hass.states.get(entity_id)
    assert state.state == STATE_UNKNOWN


@pytest.mark.asyncio
async def test_last_sound_sensor_state_updates_after_event(
    hass: HomeAssistant, setup_integration: MockConfigEntry, valid_payload: dict[str, Any]
) -> None:
    """Test the last sound sensor state updates after an event."""
    coordinator: AllEarsDataUpdateCoordinator = hass.data[DOMAIN][ENTRY_ID_FOR_TESTS]
    await coordinator.async_handle_sound_event(valid_payload)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{ENTRY_ID_FOR_TESTS}_{SENSOR_LAST_SOUND}"
    )
    state = hass.states.get(entity_id)
    assert state.state == "Glass Breaking"


@pytest.mark.asyncio
async def test_last_flow_sensor_state_updates_after_event(
    hass: HomeAssistant, setup_integration: MockConfigEntry, valid_payload: dict[str, Any]
) -> None:
    """Test the last flow sensor state updates after an event."""
    coordinator: AllEarsDataUpdateCoordinator = hass.data[DOMAIN][ENTRY_ID_FOR_TESTS]
    await coordinator.async_handle_sound_event(valid_payload)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{ENTRY_ID_FOR_TESTS}_{SENSOR_LAST_FLOW}"
    )
    state = hass.states.get(entity_id)
    assert state.state == "Front Door Security"


@pytest.mark.asyncio
async def test_sensors_have_unique_ids_per_entry(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Test sensors have distinct unique IDs per config entry."""
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        entry_id="another_entry_id",
        title="Another Device",
        data={
            "webhook_id": "another_webhook",
            "device_name": "Another Device",
        },
    )
    entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(
        entity_registry, setup_integration.entry_id
    )
    entities2 = er.async_entries_for_config_entry(entity_registry, entry2.entry_id)

    unique_ids = set()
    for entity in entities + entities2:
        assert entity.unique_id not in unique_ids
        unique_ids.add(entity.unique_id)
