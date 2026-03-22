"""DataUpdateCoordinator for AllEars."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_APP,
    ATTR_CONFIDENCE,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    DOMAIN,
    LOG_VALUE_MAX_LENGTH,
    WEBHOOK_TIMESTAMP_DRIFT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class AllEarsDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching AllEars data."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self._reset_callback: CALLBACK_TYPE | None = None
        self.entry_id = entry_id

    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Truncate all string values to LOG_VALUE_MAX_LENGTH for safe logging."""
        sanitized = {}
        for key, value in payload.items():
            if isinstance(value, str) and len(value) > LOG_VALUE_MAX_LENGTH:
                sanitized[key] = value[:LOG_VALUE_MAX_LENGTH]
            else:
                sanitized[key] = value
        return sanitized

    async def async_handle_sound_event(self, data: dict[str, Any]) -> None:
        """Validate, store, and broadcast a new sound event from webhook."""
        required_keys = {
            ATTR_APP,
            ATTR_FLOW_NAME,
            ATTR_SOUND_CLASS,
            ATTR_CONFIDENCE,
            ATTR_TIMESTAMP,
        }
        missing = required_keys - data.keys()
        if missing:
            _LOGGER.warning(
                "Missing required keys in payload: %s",
                self._sanitize_payload(data),
            )
            raise HomeAssistantError(f"Missing required keys: {missing}")

        flow_name = data[ATTR_FLOW_NAME]
        if not isinstance(flow_name, str) or not flow_name:
            _LOGGER.warning("Invalid flow name: %s", self._sanitize_payload(data))
            raise HomeAssistantError("Flow name must be a non-empty string.")

        sound_class = data[ATTR_SOUND_CLASS]
        if not isinstance(sound_class, str) or not sound_class:
            _LOGGER.warning("Invalid sound class: %s", self._sanitize_payload(data))
            raise HomeAssistantError("Sound class must be a non-empty string.")

        confidence = data[ATTR_CONFIDENCE]
        if not isinstance(confidence, (float, int)) or not (
            CONFIDENCE_MIN <= confidence <= CONFIDENCE_MAX
        ):
            _LOGGER.warning("Invalid confidence: %s", self._sanitize_payload(data))
            raise HomeAssistantError(
                f"Confidence must be between {CONFIDENCE_MIN} and {CONFIDENCE_MAX}."
            )

        timestamp = data[ATTR_TIMESTAMP]
        if not isinstance(timestamp, int) or timestamp <= 0:
            _LOGGER.warning("Invalid timestamp: %s", self._sanitize_payload(data))
            raise HomeAssistantError("Timestamp must be a positive integer.")

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        drift_ms = timestamp - now_ms
        if drift_ms > WEBHOOK_TIMESTAMP_DRIFT_SECONDS * 1000:
            _LOGGER.warning("Timestamp in future: %s", self._sanitize_payload(data))
            raise HomeAssistantError("Timestamp drift limit exceeded.")

        state_dict: dict[str, Any] = {
            ATTR_FLOW_NAME: flow_name,
            ATTR_SOUND_CLASS: sound_class,
            ATTR_CONFIDENCE: float(confidence),
            ATTR_TIMESTAMP: timestamp,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        self.async_set_updated_data(state_dict)

    def handle_webhook_payload(self, payload: dict[str, Any]) -> None:
        """Compat wrapper for webhook.py."""
        self.hass.async_create_task(self.async_handle_sound_event(payload))
