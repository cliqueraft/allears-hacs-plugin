"""Tests for the AllEars webhook (Graceful compatibility version)."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any
from unittest.mock import patch

import pytest
from freezegun import freeze_time
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.allears.const import (
    ATTR_APP,
    ATTR_CONFIDENCE,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
    DOMAIN,
    EVENT_SOUND_DETECTED,
)

from .conftest import ENTRY_ID_FOR_TESTS, WEBHOOK_ID_FOR_TESTS


@pytest.mark.asyncio
async def test_webhook_valid_payload_returns_200(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook returns HTTP 200 OK for a valid query."""
    client = await hass_client_no_auth()
    resp = await client.get(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        params=valid_payload,
    )
    assert resp.status == HTTPStatus.OK
    body = await resp.json()
    assert body == {"status": "ok"}


@pytest.mark.asyncio
async def test_webhook_bare_get_returns_200_and_defaults(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
) -> None:
    """Test the webhook handles a bare GET request (compatibility with current Android app)."""
    events = []
    hass.bus.async_listen(EVENT_SOUND_DETECTED, events.append)

    client = await hass_client_no_auth()
    resp = await client.get(f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}")
    assert resp.status == HTTPStatus.OK

    await hass.async_block_till_done()

    # Verify defaults are applied and event is fired
    assert len(events) == 1
    data = events[0].data
    assert data[ATTR_APP] == "AllEars"
    assert data[ATTR_FLOW_NAME] == "Manual Trigger"
    assert data[ATTR_SOUND_CLASS] == "Unknown Sound"
    assert data[ATTR_CONFIDENCE] == 1.0
    assert isinstance(data[ATTR_TIMESTAMP], int)


@pytest.mark.asyncio
async def test_webhook_fires_ha_event_on_valid_payload(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook fires an event to the HA bus on valid query."""
    events = []
    hass.bus.async_listen(EVENT_SOUND_DETECTED, events.append)

    client = await hass_client_no_auth()
    await client.get(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        params=valid_payload,
    )
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data[ATTR_SOUND_CLASS] == "Glass Breaking"


@pytest.mark.asyncio
async def test_webhook_updates_coordinator_on_valid_payload(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook passes valid query data to the coordinator."""
    client = await hass_client_no_auth()
    await client.get(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        params=valid_payload,
    )
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][ENTRY_ID_FOR_TESTS]
    assert coordinator.data[ATTR_SOUND_CLASS] == "Glass Breaking"
    assert coordinator.data[ATTR_CONFIDENCE] == 0.87


@pytest.mark.asyncio
async def test_webhook_wrong_app_name_returns_403(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook returns 403 Forbidden if the wrong app identifier is provided."""
    client = await hass_client_no_auth()
    params = dict(valid_payload)
    params[ATTR_APP] = "NotAllEars"
    resp = await client.get(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        params=params,
    )
    assert resp.status == HTTPStatus.FORBIDDEN
    body = await resp.json()
    assert body == {"error": "forbidden"}


@pytest.mark.asyncio
async def test_webhook_payload_too_large_returns_413(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
) -> None:
    """Test the webhook returns 413 Request Entity Too Large on overly large query strings."""
    client = await hass_client_no_auth()
    # Mocking the size limit to a small value to avoid hitting URL length limits in test environment
    with patch("custom_components.allears.webhook.WEBHOOK_MAX_SIZE_BYTES", 10):
        resp = await client.get(
            f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
            params={"large": "A" * 11},
        )
    assert resp.status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    body = await resp.json()
    assert body == {"error": "query_string_too_large"}


@pytest.mark.asyncio
async def test_webhook_confidence_out_of_range_rejected(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook returns 422 Unprocessable Entity if confidence is invalid."""
    client = await hass_client_no_auth()
    for bad_conf in [1.01, -0.01, "high"]:
        params = dict(valid_payload)
        params[ATTR_CONFIDENCE] = bad_conf
        resp = await client.get(
            f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
            params=params,
        )
        assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY
        body = await resp.json()
        assert body.get("error") == "validation_error"


@pytest.mark.asyncio
@freeze_time("2024-03-22 12:00:00")
async def test_webhook_future_timestamp_rejected(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook returns 422 if the timestamp is drifting into the future."""
    import time

    client = await hass_client_no_auth()
    frozen_now = int(time.time() * 1000)
    params = dict(valid_payload)
    params[ATTR_TIMESTAMP] = frozen_now + 61000

    resp = await client.get(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        params=params,
    )
    assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY
    body = await resp.json()
    assert body["error"] == "timestamp_drift"


@pytest.mark.asyncio
async def test_webhook_does_not_crash_on_any_exception(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook catches broad exceptions and returns 500 without crashing HA."""
    client = await hass_client_no_auth()
    with patch(
        "custom_components.allears.coordinator.AllEarsDataUpdateCoordinator.async_handle_sound_event",
        side_effect=RuntimeError("Test exception"),
    ):
        resp = await client.get(
            f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
            params=valid_payload,
        )
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    body = await resp.json()
    assert body == {"error": "internal_error"}
    assert hass.is_running is True
