"""Webhook handler for AllEars."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from aiohttp.web import Request, Response
from homeassistant.core import HomeAssistant

from .const import (
    ALLEARS_APP_IDENTIFIER,
    ATTR_APP,
    ATTR_CONFIDENCE,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    DOMAIN,
    EVENT_SOUND_DETECTED,
    WEBHOOK_MAX_SIZE_BYTES,
    WEBHOOK_TIMESTAMP_DRIFT_SECONDS,
)
from .coordinator import AllEarsDataUpdateCoordinator

LOGGER: logging.Logger = logging.getLogger(__package__)


async def handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: Request
) -> Response:
    """Handle incoming webhook from AllEars app."""
    try:
        # Step 1 — Size guard BEFORE any parsing
        raw: bytes = await request.read()
        if len(raw) > WEBHOOK_MAX_SIZE_BYTES:
            return Response(
                status=413,
                body='{"error":"payload_too_large"}',
                content_type="application/json",
            )

        # Step 2 — Content-Type check
        if request.content_type != "application/json":
            return Response(
                status=415,
                body='{"error":"unsupported_media_type"}',
                content_type="application/json",
            )

        # Step 3 — JSON parse with explicit error handling
        try:
            payload: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            return Response(
                status=400,
                body='{"error":"invalid_json"}',
                content_type="application/json",
            )

        # Step 4 — Required field validation
        required_fields = {
            ATTR_APP,
            ATTR_FLOW_NAME,
            ATTR_SOUND_CLASS,
            ATTR_CONFIDENCE,
            ATTR_TIMESTAMP,
        }
        missing = required_fields - payload.keys()
        if missing:
            return Response(
                status=400,
                body=json.dumps({"error": "missing_fields", "fields": list(missing)}),
                content_type="application/json",
            )

        # Step 5 — App identity check
        if payload[ATTR_APP] != ALLEARS_APP_IDENTIFIER:
            app_val = str(payload[ATTR_APP])
            LOGGER.warning(
                "Rejected webhook from unknown app: %s",
                app_val[:50],
            )
            return Response(
                status=403,
                body='{"error":"forbidden"}',
                content_type="application/json",
            )

        # Step 6 — Type validation
        confidence = payload[ATTR_CONFIDENCE]
        if not isinstance(confidence, (float, int)) or not (
            CONFIDENCE_MIN <= confidence <= CONFIDENCE_MAX
        ):
            return Response(
                status=422,
                body=json.dumps(
                    {
                        "error": "validation_error",
                        "detail": "confidence must be float/int between 0.0 and 1.0",
                    }
                ),
                content_type="application/json",
            )

        timestamp = payload[ATTR_TIMESTAMP]
        if not isinstance(timestamp, int) or timestamp <= 0:
            return Response(
                status=422,
                body=json.dumps(
                    {"error": "validation_error", "detail": "timestamp must be int > 0"}
                ),
                content_type="application/json",
            )

        flow_name = payload[ATTR_FLOW_NAME]
        if not isinstance(flow_name, str) or not flow_name:
            return Response(
                status=422,
                body=json.dumps(
                    {
                        "error": "validation_error",
                        "detail": "flow_name must be non-empty string",
                    }
                ),
                content_type="application/json",
            )

        sound_class = payload[ATTR_SOUND_CLASS]
        if not isinstance(sound_class, str) or not sound_class:
            return Response(
                status=422,
                body=json.dumps(
                    {
                        "error": "validation_error",
                        "detail": "sound_class must be non-empty string",
                    }
                ),
                content_type="application/json",
            )

        # Step 7 — Timestamp drift check
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        drift_ms = timestamp - now_ms
        if drift_ms > WEBHOOK_TIMESTAMP_DRIFT_SECONDS * 1000:
            return Response(
                status=422,
                body='{"error":"timestamp_drift"}',
                content_type="application/json",
            )

        # Step 8 — Pass to coordinator and fire event
        coordinator: AllEarsDataUpdateCoordinator | None = None
        for entry_coordinator in hass.data.get(DOMAIN, {}).values():
            if isinstance(entry_coordinator, AllEarsDataUpdateCoordinator):
                coordinator = entry_coordinator
                break

        if isinstance(coordinator, AllEarsDataUpdateCoordinator):
            await coordinator.async_handle_sound_event(payload)

        hass.bus.async_fire(EVENT_SOUND_DETECTED, payload)

        return Response(
            status=200, body='{"status":"ok"}', content_type="application/json"
        )

    except Exception as err:
        LOGGER.error("Unexpected webhook error: %s", err)
        return Response(
            status=500,
            body='{"error":"internal_error"}',
            content_type="application/json",
        )
