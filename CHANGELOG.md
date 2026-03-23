# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-03-22

### Added
- Webhook receiver for AllEars Android app sound events
- `sensor.last_detected_sound` — exposes the classified sound label
  with confidence, flow name, and ISO8601 timestamp as attributes
- `sensor.last_triggered_flow` — exposes the AllEars flow name
  that matched the detected sound
- `binary_sensor.sound_active` — on for 30 seconds after any sound
  detection, then auto-resets to off; debounced on rapid events
- `allears.clear_history` service — resets all detection history
- `allears.test_webhook` service — fires synthetic event for
  automation testing without needing the Android device
- Config flow with two steps: device naming and webhook URL display,
  so users can copy the exact URL to paste into the AllEars app
- OptionsFlow allowing device rename post-setup without affecting
  the immutable webhook ID

### Security
- Payload size limited to 64KB before JSON parsing (DoS protection)
- App identity validation — rejects payloads where app != "AllEars"
- Confidence range validation — rejects values outside 0.0–1.0
- Timestamp drift validation — rejects events > 60 seconds in future
- Webhook_id immutable after creation — cannot be changed via
  OptionsFlow

[Unreleased]: https://github.com/cliqueraft/allears-hacs-plugin/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/cliqueraft/allears-hacs-plugin/releases/tag/v1.0.0
