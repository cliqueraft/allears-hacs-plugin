"""Tests for the AllEars webhook."""

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
    """Test the webhook returns HTTP 200 OK for a valid payload."""
    client = await hass_client_no_auth()
    resp = await client.post(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        json=valid_payload,
    )
    assert resp.status == HTTPStatus.OK
    body = await resp.json()
    assert body == {"status": "ok"}


@pytest.mark.asyncio
async def test_webhook_fires_ha_event_on_valid_payload(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook fires an event to the HA bus on valid payload."""
    events = []
    hass.bus.async_listen(EVENT_SOUND_DETECTED, events.append)

    client = await hass_client_no_auth()
    await client.post(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        json=valid_payload,
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
    """Test the webhook passes valid payload data to the coordinator."""
    client = await hass_client_no_auth()
    await client.post(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        json=valid_payload,
    )
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][ENTRY_ID_FOR_TESTS]
    assert coordinator.data[ATTR_SOUND_CLASS] == "Glass Breaking"
    assert coordinator.data[ATTR_CONFIDENCE] == 0.87


@pytest.mark.asyncio
async def test_webhook_missing_required_field_returns_400(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook returns 400 Bad Request if standard fields are missing."""
    client = await hass_client_no_auth()
    for field in [
        ATTR_APP,
        ATTR_FLOW_NAME,
        ATTR_SOUND_CLASS,
        ATTR_CONFIDENCE,
        ATTR_TIMESTAMP,
    ]:
        payload = dict(valid_payload)
        payload.pop(field)
        resp = await client.post(
            f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
            json=payload,
        )
        assert resp.status == HTTPStatus.BAD_REQUEST
        body = await resp.json()
        assert "missing_fields" in body["error"]


@pytest.mark.asyncio
async def test_webhook_wrong_app_name_returns_403(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook returns 403 Forbidden if the app identifier does not match."""
    client = await hass_client_no_auth()
    payload = dict(valid_payload)
    payload[ATTR_APP] = "NotAllEars"
    resp = await client.post(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        json=payload,
    )
    assert resp.status == HTTPStatus.FORBIDDEN
    body = await resp.json()
    assert body == {"error": "forbidden"}


@pytest.mark.asyncio
async def test_webhook_invalid_json_returns_400(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
) -> None:
    """Test the webhook returns 400 Bad Request on completely invalid JSON bytes."""
    client = await hass_client_no_auth()
    resp = await client.post(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        data=b"this is not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status == HTTPStatus.BAD_REQUEST
    body = await resp.json()
    assert body == {"error": "invalid_json"}


@pytest.mark.asyncio
async def test_webhook_wrong_content_type_returns_415(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
    valid_payload: dict[str, Any],
) -> None:
    """Test the webhook returns 415 Unsupported Media Type if content type is wrong."""
    client = await hass_client_no_auth()
    resp = await client.post(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        data=json.dumps(valid_payload),
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status == HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    body = await resp.json()
    assert body == {"error": "unsupported_media_type"}


@pytest.mark.asyncio
async def test_webhook_payload_too_large_returns_413(
    hass: HomeAssistant,
    hass_client_no_auth: Any,
    setup_integration: MockConfigEntry,
) -> None:
    """Test the webhook returns 413 Payload Too Large on overly large requests."""
    client = await hass_client_no_auth()
    long_string = "A" * 65537
    resp = await client.post(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        data=long_string.encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    body = await resp.json()
    assert body == {"error": "payload_too_large"}


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
        payload = dict(valid_payload)
        payload[ATTR_CONFIDENCE] = bad_conf
        resp = await client.post(
            f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
            json=payload,
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
    payload = dict(valid_payload)
    payload[ATTR_TIMESTAMP] = frozen_now + 61000

    resp = await client.post(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        json=payload,
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
        resp = await client.post(
            f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
            json=valid_payload,
        )
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    body = await resp.json()
    assert body == {"error": "internal_error"}
    assert hass.is_running is True
