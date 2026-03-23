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
    """Handle incoming GET webhook from AllEars app."""
    try:
        # Step 1 — Size guard via query string length
        query_string = request.rel_url.query_string
        if len(query_string) > WEBHOOK_MAX_SIZE_BYTES:
            return Response(
                status=413,
                body=json.dumps({"error": "query_string_too_large"}),
                content_type="application/json",
            )

        # Step 2 — Extract parameters from query
        query = request.rel_url.query

        # Graceful compatibility: Default values if parameters are missing
        # This is necessary because the Android app's triggerWebhook action
        # currently sends a bare GET request without query parameters.
        payload: dict[str, Any] = {
            ATTR_APP: query.get(ATTR_APP, ALLEARS_APP_IDENTIFIER),
            ATTR_FLOW_NAME: query.get(ATTR_FLOW_NAME, "Manual Trigger"),
            ATTR_SOUND_CLASS: query.get(ATTR_SOUND_CLASS, "Unknown Sound"),
            ATTR_CONFIDENCE: query.get(ATTR_CONFIDENCE, 1.0),
            ATTR_TIMESTAMP: query.get(
                ATTR_TIMESTAMP, int(datetime.now(timezone.utc).timestamp() * 1000)
            ),
        }

        # Step 3 — App identity check (Warn but allow if missing)
        if query.get(ATTR_APP) is None:
            LOGGER.debug("Webhook received without app identifier, defaulting to AllEars")
        elif payload[ATTR_APP] != ALLEARS_APP_IDENTIFIER:
            app_val = str(payload[ATTR_APP])
            LOGGER.warning(
                "Rejected webhook from unknown app: %s",
                app_val[:50],
            )
            return Response(
                status=403,
                body=json.dumps({"error": "forbidden"}),
                content_type="application/json",
            )

        # Step 4 — Type casting and validation
        try:
            confidence = float(payload[ATTR_CONFIDENCE])
            payload[ATTR_CONFIDENCE] = confidence
        except (ValueError, TypeError):
            return Response(
                status=422,
                body=json.dumps(
                    {
                        "error": "validation_error",
                        "detail": "confidence must be a float",
                    }
                ),
                content_type="application/json",
            )

        if not (CONFIDENCE_MIN <= confidence <= CONFIDENCE_MAX):
            return Response(
                status=422,
                body=json.dumps(
                    {
                        "error": "validation_error",
                        "detail": "confidence must be between 0.0 and 1.0",
                    }
                ),
                content_type="application/json",
            )

        try:
            timestamp = int(payload[ATTR_TIMESTAMP])
            payload[ATTR_TIMESTAMP] = timestamp
        except (ValueError, TypeError):
            return Response(
                status=422,
                body=json.dumps(
                    {
                        "error": "validation_error",
                        "detail": "timestamp must be an integer",
                    }
                ),
                content_type="application/json",
            )

        # Step 5 — Timestamp drift check (Skip if initially missing)
        if query.get(ATTR_TIMESTAMP) is not None:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            drift_ms = timestamp - now_ms
            if drift_ms > WEBHOOK_TIMESTAMP_DRIFT_SECONDS * 1000:
                return Response(
                    status=422,
                    body=json.dumps({"error": "timestamp_drift"}),
                    content_type="application/json",
                )

        # Step 6 — Pass to coordinator and fire event
        coordinator: AllEarsDataUpdateCoordinator | None = None
        for entry_coordinator in hass.data.get(DOMAIN, {}).values():
            if isinstance(entry_coordinator, AllEarsDataUpdateCoordinator):
                coordinator = entry_coordinator
                break

        if isinstance(coordinator, AllEarsDataUpdateCoordinator):
            await coordinator.async_handle_sound_event(payload)

        hass.bus.async_fire(EVENT_SOUND_DETECTED, payload)

        return Response(
            status=200,
            body=json.dumps({"status": "ok"}),
            content_type="application/json",
        )

    except Exception as err:
        LOGGER.error("Unexpected webhook error: %s", err)
        return Response(
            status=500,
            body=json.dumps({"error": "internal_error"}),
            content_type="application/json",
        )
