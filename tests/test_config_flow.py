"""Tests for the AllEars config flow."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.allears.const import CONF_DEVICE_NAME, CONF_WEBHOOK_ID, DOMAIN

from .conftest import DEVICE_NAME_FOR_TESTS


@pytest.mark.asyncio
async def test_flow_user_step_shows_form(hass: HomeAssistant) -> None:
    """Test the user step shows the form correctly."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "data_schema" in result
    assert CONF_DEVICE_NAME in result["data_schema"].schema


@pytest.mark.asyncio
async def test_flow_user_step_advances_to_webhook_url_step(hass: HomeAssistant) -> None:
    """Test submitting the user step advances to the webhook URL step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_DEVICE_NAME: DEVICE_NAME_FOR_TESTS}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "webhook_url"
    assert "description_placeholders" in result
    assert "webhook_url" in result["description_placeholders"]
    webhook_url: str = result["description_placeholders"]["webhook_url"]
    assert "/api/webhook/" in webhook_url


@pytest.mark.asyncio
async def test_flow_webhook_url_step_creates_entry(hass: HomeAssistant) -> None:
    """Test completing the webhook URL step creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_DEVICE_NAME: DEVICE_NAME_FOR_TESTS}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == DEVICE_NAME_FOR_TESTS
    assert "data" in result
    assert CONF_WEBHOOK_ID in result["data"]
    assert result["data"][CONF_DEVICE_NAME] == DEVICE_NAME_FOR_TESTS
    webhook_id: str = result["data"][CONF_WEBHOOK_ID]
    assert isinstance(webhook_id, str)
    assert len(webhook_id) > 0


@pytest.mark.asyncio
async def test_flow_aborts_if_already_configured(hass: HomeAssistant) -> None:
    """Test the flow aborts if an AllEars entry is already configured."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_options_flow_allows_device_rename(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test the options flow correctly updates the device name."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    renamed_device: str = "Renamed Device"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_DEVICE_NAME: renamed_device}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_DEVICE_NAME] == renamed_device
    await hass.async_block_till_done()
