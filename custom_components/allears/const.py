"""Constants for the AllEars Sound Tracker integration."""

from __future__ import annotations

import logging
from typing import Final

LOGGER: logging.Logger = logging.getLogger(__package__)

DOMAIN: Final[str] = "allears"
CONF_WEBHOOK_ID: Final[str] = "webhook_id"
CONF_DEVICE_NAME: Final[str] = "device_name"

ATTR_FLOW_NAME: Final[str] = "flow_name"
ATTR_SOUND_CLASS: Final[str] = "sound_class"
ATTR_CONFIDENCE: Final[str] = "confidence"
ATTR_TIMESTAMP: Final[str] = "timestamp"
ATTR_APP: Final[str] = "app"

EVENT_SOUND_DETECTED: Final[str] = "allears_sound_detected"

SENSOR_LAST_SOUND: Final[str] = "last_sound"
SENSOR_LAST_FLOW: Final[str] = "last_flow"

DATA_COORDINATOR: Final[str] = "coordinator"
DATA_SERVICES_SETUP: Final[str] = "services_setup"

VERSION: Final[str] = "1.0.0"

BINARY_SENSOR_ACTIVE: Final[str] = "sound_active"
BINARY_SENSOR_ACTIVE_WINDOW_SECONDS: Final[int] = 30

# "select" added here to enable the Active Flow Filter entity.
# Add future platforms (e.g. "number", "button") here as the product grows.
PLATFORMS: Final[list[str]] = ["sensor", "binary_sensor", "select"]

DEFAULT_DEVICE_NAME: Final[str] = "AllEars Device"

# Identity
ALLEARS_APP_IDENTIFIER: Final[str] = "AllEars"

# Sensor names
SENSOR_LAST_SOUND_NAME: Final[str] = "Last Detected Sound"
SENSOR_LAST_FLOW_NAME: Final[str] = "Last Triggered Flow"
BINARY_SENSOR_ACTIVE_NAME: Final[str] = "Sound Active"

# Icons
ICON_MICROPHONE: Final[str] = "mdi:microphone"
ICON_WAVES: Final[str] = "mdi:waves"
ICON_EAR: Final[str] = "mdi:ear-hearing"

# Webhook
WEBHOOK_MAX_SIZE_BYTES: Final[int] = 65536
WEBHOOK_TIMESTAMP_DRIFT_SECONDS: Final[int] = 60

# Validation
CONFIDENCE_MIN: Final[float] = 0.0
CONFIDENCE_MAX: Final[float] = 1.0

# Logging truncation
LOG_VALUE_MAX_LENGTH: Final[int] = 200

# Services
SERVICE_CLEAR_HISTORY: Final[str] = "clear_history"
SERVICE_TEST_WEBHOOK: Final[str] = "test_webhook"

# ── Flow Registry (auto-register from Android app) ───────────────────────────
# The app sends:  GET /api/webhook/<id>?action=register_flows&flows=Flow1,Flow2
# This lets HA know which flows exist for the card dropdown — without the user
# having to configure anything manually.
ACTION_REGISTER_FLOWS: Final[str] = "register_flows"
ATTR_FLOWS: Final[str] = "flows"

# ── Generic source-type (future-proof event routing) ─────────────────────────
# Currently always "sound"; later: "motion", "custom", etc.
ATTR_SOURCE_TYPE: Final[str] = "source_type"
SOURCE_TYPE_SOUND: Final[str] = "sound"

# ── Select entity — Active Flow Filter ───────────────────────────────────────
SELECT_FLOW_FILTER: Final[str] = "active_flow_filter"
SELECT_FLOW_FILTER_NAME: Final[str] = "Active Flow Filter"
SELECT_ALL_FLOWS: Final[str] = "All Flows"

# Fired on the HA event bus when the user picks a flow in the card dropdown.
# Automation trigger:  event_type: allears_flow_selected
EVENT_FLOW_SELECTED: Final[str] = "allears_flow_selected"
