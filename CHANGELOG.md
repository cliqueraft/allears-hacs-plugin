# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-11-24

The April "v1.1.0" GitHub release shipped the 1.0.0 code, so these changes are released as 1.2.0.

### Fixed
- Dashboard card was unreachable on Home Assistant 2025.7 and later:
  `register_static_path` was removed from core. The card is now served with
  `async_register_static_paths` (with a fallback for older cores).
- The card looked for entity ids the integration never created
  (`sensor.allears_last_detected_sound` and friends), so it showed blanks.
  It now finds the AllEars entities through the device registry.
- `sound_active` turned on (and fired automations) when the app synced its
  flows or when history was cleared. It now turns on only for a real sound.
- Device triggers fired for every AllEars phone. Events now carry the
  `device_id` and each trigger only listens to its own phone.
- Webhooks always went to the first configured entry. Each webhook now
  updates its own phone.
- The Flow field was missing from the device trigger in the automation
  editor. It is now a dropdown of the flows the phone has synced.
- The last sound sensor had none of the documented attributes.
- Card rendered flow and sound names as raw HTML.
- Setup screens pointed to an app setting that does not exist.
- Config flow crashed when Home Assistant had no URL configured.

### Added
- Several phones: one config entry, device and webhook per phone.
- Card loads automatically; no dashboard resource needed. New visual editor
  (pick the phone, title, history window).
- Card shows connection status, live listening state, last sound with flow,
  confidence and time, the synced flows as filters, and recent sounds from
  the recorder, so history survives a page reload.
- `Last seen` diagnostic sensor: when the phone last reached Home Assistant.
- Sound sensors keep their last value across restarts.
- Optional `device_id` on `allears.test_webhook` and `allears.clear_history`.
- Device trigger can also filter on the sound name.
- Webhook URL (home and remote) shown again under the integration's Configure.

### Changed
- New webhook ids are 16 hex characters (was 8). Existing ids keep working.
- Entity names come from translations ("Last sound", "Last flow",
  "Sound active", "Flow filter", "Last seen"). Existing entity ids are kept.
- Invalid sound events return HTTP 422 instead of 500.

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

[Unreleased]: https://github.com/cliqueraft/allears-home-assistant/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/cliqueraft/allears-home-assistant/releases/tag/v1.0.0
