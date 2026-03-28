"""Webhook handler for AllEars."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from aiohttp.web import Request, Response
from homeassistant.core import HomeAssistant

from .const import (
    ACTION_REGISTER_FLOWS,
    ALLEARS_APP_IDENTIFIER,
    ATTR_APP,
    ATTR_CONFIDENCE,
    ATTR_FLOW_NAME,
    ATTR_FLOWS,
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


def _find_coordinator(hass: HomeAssistant) -> AllEarsDataUpdateCoordinator | None:
    """Return the first AllEarsDataUpdateCoordinator found in hass.data."""
    for entry_coordinator in hass.data.get(DOMAIN, {}).values():
        if isinstance(entry_coordinator, AllEarsDataUpdateCoordinator):
            return entry_coordinator
    return None


async def _handle_register_flows(
    hass: HomeAssistant, query: Mapping[str, str]
) -> Response:
    """Handle action=register_flows — store the app's flow catalogue.

    Expected:
        GET /api/webhook/<id>?action=register_flows&flows=Flow1,Flow2,Flow3

    The flows param is a comma-separated list of flow names.  This is called by
    the Android app on startup so the HA card can show a live dropdown.
    """
    raw_flows: str = query.get(ATTR_FLOWS, "")
    flow_names: list[str] = [f.strip() for f in raw_flows.split(",") if f.strip()]

    if not flow_names:
        LOGGER.warning(
            "register_flows called but 'flows' param is empty or missing."
        )
        return Response(
            status=400,
            body=json.dumps({"error": "flows_param_required"}),
            content_type="application/json",
        )

    coordinator = _find_coordinator(hass)
    if coordinator is not None:
        await coordinator.async_register_flows(flow_names)
        LOGGER.info("Flow registry updated via webhook: %s", flow_names)
    else:
        LOGGER.warning("register_flows: no coordinator found — integration not ready?")

    return Response(
        status=200,
        body=json.dumps({"status": "ok", "registered": len(flow_names)}),
        content_type="application/json",
    )


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

        query = request.rel_url.query

        # Step 2 — Route registration action before normal sound processing
        action = query.get("action")
        if action == ACTION_REGISTER_FLOWS:
            return await _handle_register_flows(hass, query)

        # Step 3 — Extract parameters, supporting both legacy and new Android app keys
        flow_val = query.get(ATTR_FLOW_NAME) or query.get("flow")
        sound_val = query.get(ATTR_SOUND_CLASS) or query.get("sound")
        conf_val = query.get(ATTR_CONFIDENCE) or query.get("score")
        ts_val = query.get(ATTR_TIMESTAMP) or query.get("ts")

        missing_params: list[str] = []
        if flow_val is None:
            missing_params.append("flow")
        if sound_val is None:
            missing_params.append("sound")
        if missing_params:
            LOGGER.warning(
                "Webhook missing params %s — using defaults. "
                "Ensure AllEars app is sending query params.",
                missing_params,
            )

        # Graceful compatibility: fill defaults so the integration stays functional
        payload: dict[str, Any] = {
            ATTR_APP: query.get(ATTR_APP, ALLEARS_APP_IDENTIFIER),
            ATTR_FLOW_NAME: flow_val if flow_val is not None else "Manual Trigger",
            ATTR_SOUND_CLASS: sound_val if sound_val is not None else "Unknown Sound",
            ATTR_CONFIDENCE: conf_val if conf_val is not None else 1.0,
            ATTR_TIMESTAMP: ts_val
            if ts_val is not None
            else int(datetime.now(timezone.utc).timestamp() * 1000),
        }


        # Step 4 — App identity check (Warn but allow if missing)
        if query.get(ATTR_APP) is None:
            LOGGER.debug(
                "Webhook received without app identifier, defaulting to %s",
                ALLEARS_APP_IDENTIFIER,
            )
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

        # Step 5 — Type casting and validation
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

        # Step 6 — Timestamp drift check (Skip if initially missing)
        if query.get(ATTR_TIMESTAMP) is not None:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            drift_ms = timestamp - now_ms
            if drift_ms > WEBHOOK_TIMESTAMP_DRIFT_SECONDS * 1000:
                return Response(
                    status=422,
                    body=json.dumps({"error": "timestamp_drift"}),
                    content_type="application/json",
                )

        # Step 7 — Pass to coordinator and fire event
        coordinator = _find_coordinator(hass)
        if isinstance(coordinator, AllEarsDataUpdateCoordinator):
            await coordinator.async_handle_sound_event(payload)

        hass.bus.async_fire(EVENT_SOUND_DETECTED, payload)

        return Response(
            status=200,
            body=json.dumps({"status": "ok"}),
            content_type="application/json",
        )

    except Exception:
        LOGGER.exception("Unexpected webhook error")
        return Response(
            status=500,
            body=json.dumps({"error": "internal_error"}),
            content_type="application/json",
        )
