"""DataUpdateCoordinator for AllEars."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_APP,
    ATTR_CONFIDENCE,
    ATTR_DEVICE_ID,
    ATTR_FLOW_NAME,
    ATTR_SOUND_CLASS,
    ATTR_TIMESTAMP,
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    DOMAIN,
    EVENT_SOUND_DETECTED,
    LOG_VALUE_MAX_LENGTH,
    WEBHOOK_TIMESTAMP_DRIFT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = f"{DOMAIN}_flows"
STORAGE_VERSION = 1

# Key in coordinator.data that goes up by one for every real sound event.
# Entities use it to tell a new detection apart from other refreshes
# (flow registration, clear history).
DATA_EVENT_SEQ = "event_seq"


class AllEarsDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holds the latest sound event and flow list for one AllEars phone."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        webhook_id: str | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self._reset_callback: CALLBACK_TYPE | None = None
        self.entry_id = entry_id
        self.webhook_id = webhook_id
        # Set by async_setup_entry once the device is in the device registry.
        self.device_id: str | None = None
        # Last time the phone reached HA (sound event or flow sync).
        self.last_seen: datetime | None = None
        self._event_seq = 0

        # Flow names sent by the app with action=register_flows, stored per
        # config entry so several phones keep separate lists.
        self._flow_registry: list[str] = []
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry_id}"
        )
        # Before 1.1 a single shared list was stored under this key.
        self._legacy_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY
        )

    # ── Flow Registry helpers ─────────────────────────────────────────────────

    @property
    def flow_list(self) -> list[str]:
        """Return the current list of registered flow names from the app."""
        return list(self._flow_registry)

    async def async_load_flows(self) -> None:
        """Load the saved flow list from storage on startup."""
        data = await self._store.async_load()
        if not data:
            data = await self._legacy_store.async_load()
        if data and isinstance(data, dict):
            saved_flows = data.get("flows", [])
            if isinstance(saved_flows, list):
                self._flow_registry = [str(f) for f in saved_flows]
                _LOGGER.debug("Loaded %d flows from storage", len(saved_flows))

    async def async_register_flows(self, flow_names: list[str]) -> None:
        """Store the flow catalogue sent by the Android app."""
        self.mark_seen()
        cleaned = list(dict.fromkeys(f.strip() for f in flow_names if f.strip()))
        if cleaned == self._flow_registry:
            _LOGGER.debug("Flow registry unchanged; skipping save")
            self.async_update_listeners()
            return

        self._flow_registry = cleaned
        await self._store.async_save({"flows": cleaned})
        _LOGGER.info("AllEars flow registry updated: %s", cleaned[:20])
        # Re-broadcast the current data (same event_seq) so the select entity
        # rebuilds its options without the sound_active sensor turning on.
        self.async_set_updated_data(dict(self.data or {}))

    @callback
    def mark_seen(self) -> None:
        """Record that the phone just contacted Home Assistant."""
        self.last_seen = datetime.now(UTC)

    @callback
    def async_clear(self) -> None:
        """Forget the last sound event (registered flows are kept)."""
        self.async_set_updated_data({})

    # ── Payload helpers ───────────────────────────────────────────────────────

    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Truncate all string values to LOG_VALUE_MAX_LENGTH for safe logging."""
        sanitized = {}
        for key, value in payload.items():
            if isinstance(value, str) and len(value) > LOG_VALUE_MAX_LENGTH:
                sanitized[key] = value[:LOG_VALUE_MAX_LENGTH]
            else:
                sanitized[key] = value
        return sanitized

    async def async_handle_sound_event(
        self, data: dict[str, Any], *, fire_event: bool = True
    ) -> dict[str, Any]:
        """Validate, store and broadcast a sound event.

        Fires `allears_sound_detected` carrying this phone's device_id, so
        device triggers only fire for their own phone. Returns the event data.
        """
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
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (float, int))
            or not (CONFIDENCE_MIN <= confidence <= CONFIDENCE_MAX)
        ):
            _LOGGER.warning("Invalid confidence: %s", self._sanitize_payload(data))
            raise HomeAssistantError(
                f"Confidence must be between {CONFIDENCE_MIN} and {CONFIDENCE_MAX}."
            )

        timestamp = data[ATTR_TIMESTAMP]
        if (
            isinstance(timestamp, bool)
            or not isinstance(timestamp, int)
            or timestamp <= 0
        ):
            _LOGGER.warning("Invalid timestamp: %s", self._sanitize_payload(data))
            raise HomeAssistantError("Timestamp must be a positive integer.")

        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        drift_ms = timestamp - now_ms
        if drift_ms > WEBHOOK_TIMESTAMP_DRIFT_SECONDS * 1000:
            _LOGGER.warning("Timestamp in future: %s", self._sanitize_payload(data))
            raise HomeAssistantError("Timestamp drift limit exceeded.")

        self.mark_seen()
        self._event_seq += 1
        state_dict: dict[str, Any] = {
            ATTR_FLOW_NAME: flow_name,
            ATTR_SOUND_CLASS: sound_class,
            ATTR_CONFIDENCE: float(confidence),
            ATTR_TIMESTAMP: timestamp,
            "last_updated": datetime.now(UTC).isoformat(),
            DATA_EVENT_SEQ: self._event_seq,
        }
        self.async_set_updated_data(state_dict)

        event_data: dict[str, Any] = {
            ATTR_APP: data[ATTR_APP],
            ATTR_FLOW_NAME: flow_name,
            ATTR_SOUND_CLASS: sound_class,
            ATTR_CONFIDENCE: float(confidence),
            ATTR_TIMESTAMP: timestamp,
        }
        if self.device_id is not None:
            event_data[ATTR_DEVICE_ID] = self.device_id
        if fire_event:
            self.hass.bus.async_fire(EVENT_SOUND_DETECTED, event_data)
        return event_data
