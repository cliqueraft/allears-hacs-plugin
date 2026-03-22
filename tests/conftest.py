"""Test configuration and fixtures for the AllEars integration."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, Final

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.allears.const import (
    ALLEARS_APP_IDENTIFIER,
    ATTR_APP,
    ATTR_CONFIDENCE,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
    CONF_DEVICE_NAME,
    CONF_WEBHOOK_ID,
    DOMAIN,
)
from custom_components.allears.coordinator import AllEarsDataUpdateCoordinator

pytest_plugins = ["pytest_homeassistant_custom_component"]


WEBHOOK_ID_FOR_TESTS: Final[str] = "test_webhook_id_abc123"
ENTRY_ID_FOR_TESTS: Final[str] = "test_entry_id_xyz789"
DEVICE_NAME_FOR_TESTS: Final[str] = "Test AllEars Device"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations for all tests in this suite."""


@pytest.fixture
def valid_payload() -> dict[str, Any]:
    """Return a payload matching the exact AllEars webhook contract."""
    return {
        ATTR_APP: ALLEARS_APP_IDENTIFIER,
        ATTR_FLOW_NAME: "Front Door Security",
        ATTR_SOUND_CLASS: "Glass Breaking",
        ATTR_CONFIDENCE: 0.87,
        ATTR_TIMESTAMP: 1711132800000,
    }


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a pre-built config entry with known test values."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=ENTRY_ID_FOR_TESTS,
        title=DEVICE_NAME_FOR_TESTS,
        data={
            CONF_WEBHOOK_ID: WEBHOOK_ID_FOR_TESTS,
            CONF_DEVICE_NAME: DEVICE_NAME_FOR_TESTS,
        },
    )


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> AsyncGenerator[MockConfigEntry, None]:
    """Set up the integration in a test HA instance and tear it down."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    yield mock_config_entry
    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
def coordinator(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> AllEarsDataUpdateCoordinator:
    """Return a coordinator with no data (pre-first-event state)."""
    return AllEarsDataUpdateCoordinator(hass, ENTRY_ID_FOR_TESTS)


@pytest.fixture
def coordinator_with_data(
    hass: HomeAssistant,
    coordinator: AllEarsDataUpdateCoordinator,
    valid_payload: dict[str, Any],
) -> AllEarsDataUpdateCoordinator:
    """Return a coordinator pre-loaded with one sound event."""
    coordinator.async_set_updated_data(
        {
            ATTR_FLOW_NAME: valid_payload[ATTR_FLOW_NAME],
            ATTR_SOUND_CLASS: valid_payload[ATTR_SOUND_CLASS],
            ATTR_CONFIDENCE: valid_payload[ATTR_CONFIDENCE],
            ATTR_TIMESTAMP: valid_payload[ATTR_TIMESTAMP],
            "last_updated": "2024-03-22T12:00:00+00:00",
        }
    )
    return coordinator
