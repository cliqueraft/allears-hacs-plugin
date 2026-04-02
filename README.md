# AllEars Sound Tracker
Subtitle: Home Assistant integration for the AllEars Android app

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/cliqueraft/allears-hacs-plugin)
[![Validate](https://github.com/cliqueraft/allears-hacs-plugin/actions/workflows/validate.yml/badge.svg)](https://github.com/cliqueraft/allears-hacs-plugin/actions/workflows/validate.yml)
[![Tests](https://github.com/cliqueraft/allears-hacs-plugin/actions/workflows/tests.yml/badge.svg)](https://github.com/cliqueraft/allears-hacs-plugin/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/cliqueraft/allears-hacs-plugin/blob/main/LICENSE)

## Overview
This integration receives classified sound events directly from the AllEars Android app via a local webhook. It creates sensors to track the latest detected sounds and flows within Home Assistant. You can use these entities to build powerful automations or trigger immediate alerts.

## Prerequisites
1. Home Assistant `2024.1.0` or later
2. AllEars app installed on Android (https://play.google.com/store/apps/details?id=com.cliqueraft.allears&hl=en_IN)
3. HA reachable from the Android device (local network or Nabu Casa)

## Installation

### Method A — HACS (recommended):
1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three-dot menu → Custom repositories
4. Add: `https://github.com/cliqueraft/allears-hacs-plugin` — category: Integration
5. Search for "AllEars Sound Tracker" → Download
6. Restart Home Assistant

### Method B — Manual:
1. Download the latest release zip
2. Extract `custom_components/allears/` into your HA `config/custom_components/` directory
3. Restart Home Assistant

## Configuration
**Step 1: Add the integration**
Settings → Devices & Services → Add Integration → search "AllEars"

**Step 2: Name your device**
Enter a name (e.g. "Living Room AllEars")

**Step 3: Copy the webhook URL**
The next screen shows your unique webhook URL — copy it exactly.
It looks like: `http://<your-ha-ip>:8123/api/webhook/<id>`
This URL is permanent — it does not change after setup.

**Step 4: Paste into AllEars app**
Open AllEars → Settings → Home Assistant → Webhook URL
Paste the URL → Save

**Step 5: Verify**
In HA: Developer Tools → Services → `allears.test_webhook` → Call
The `sensor.last_detected_sound` entity should show "Test Sound"

## Lovelace Dashboard Card
AllEars includes a beautiful, native-feeling custom card for your dashboard.

**Step 1: Register the Resource**
1. Settings → Dashboards → Resources (top right 3-dot menu) → Add Resource
2. URL: `/all-ears-card/all-ears-card.js`
3. Resource Type: `JavaScript Module`

**Step 2: Add the Card**
1. Go to your Dashboard → Edit Dashboard → Add Card
2. Search for **AllEars Sound Tracker**
3. Configure your card using the built-in visual editor!

## Webhook Specification
The integration robustly relies on **GET** requests with **URL Query Parameters** to guarantee compliance with all variants of the Android client.

Example incoming HTTP request:
```
GET /api/webhook/<id>?app=AllEars&flow_name=Security&sound_class=Glass+Breaking&confidence=0.87&timestamp=1711132800000
```
- Missing parameters fallback to built-in stable defaults.
- Enforced verification on timestamp drift and confidence value (`0.0`–`1.0`).

## Entities created
| Entity ID | Type | Description | Resets |
|-----------|------|-------------|--------|
| `sensor.last_detected_sound` | Sensor | The YAMNet sound class name of the most recently detected sound | Persistent |
| `sensor.last_triggered_flow` | Sensor | The name of the AllEars flow that matched the detected sound | Persistent |
| `binary_sensor.sound_active` | Binary Sensor | On for 30 seconds after any sound detection, then auto-resets to off | Auto (30s) |

### Attributes
All `extra_state_attributes` exposed by `sensor.last_detected_sound`:
- `flow_name`: name of the matched flow
- `confidence`: detection confidence score (0.000–1.000)
- `timestamp`: ISO8601 UTC datetime of detection
- `last_updated`: ISO8601 UTC datetime coordinator last updated

## Services
| Service | Description | Fields |
|---------|-------------|--------|
| `allears.clear_history` | Resets all sound detection history across all AllEars devices. Useful for testing. | None |
| `allears.test_webhook` | Fires a synthetic sound event (sound_class="Test Sound", confidence=1.0). Use this to verify your HA automations are wired correctly. | None |

## Automation examples

You should exclusively use the native Home Assistant **Device Trigger** the integration automatically creates for you. It handles flow names and sound matches instantly and natively!

### Example 1 — Alert on glass breaking via "Security" flow:
Using the Home Assistant Visual Automation Editor:
1. Triggers → Add Trigger → **Device**
2. Select your `AllEars Device`
3. Trigger: **AllEars detects a sound**
4. Flow Name: `Security` 

**YAML Equivalent:**
```yaml
automation:
  alias: "Alert on glass breaking"
  trigger:
    - platform: device
      domain: allears
      device_id: <your-device-id>
      type: sound_detected
      flow_name: "Security"
  action:
    - service: notify.mobile_app
      data:
        title: "AllEars Alert"
        message: "Glass breaking detected by the Security flow!"
```

### Example 2 — Trigger a siren while sound_active is on:
```yaml
automation:
  alias: "Siren on sound active"
  trigger:
    - platform: state
      entity_id: binary_sensor.sound_active
      to: "on"
  action:
    - service: siren.turn_on
      target:
        entity_id: siren.alarm
```

## Troubleshooting
| Symptom | Cause | Fix |
|---------|-------|-----|
| Webhook URL unreachable from phone | HA not accessible from Android device's network | Ensure phone and HA are on the same LAN, or enable remote access via Nabu Casa (Settings → Home Assistant Cloud). |
| `binary_sensor.sound_active` resets too quickly | 30-second window is by design | This is intentional. Create automations that trigger on the state change to "on" rather than relying on it staying on. |
| `sensor.last_detected_sound` shows unexpected sounds | YAMNet confidence threshold in AllEars is set below 0.3 | Open AllEars → Settings → Detection Sensitivity and raise the confidence threshold. |
| Integration loads but never receives any events | | Run Developer Tools → Services → `allears.test_webhook`. If sensor updates: the integration is working — check the Android app's webhook URL setting and network connectivity. If sensor does not update: reload the integration via Settings → Devices & Services → AllEars → Reload. |

## Contributing
Requirements for all PRs:
- `ruff check` and `ruff format` must pass with zero warnings
- `mypy --strict` must pass with zero errors
- All new behaviour must have tests — coverage must stay above 90%
- Branch protection: validate and tests workflows must pass
- Explicit Pytest CI thread-safety bypasses exist in `conftest.py`.

Local dev setup:
```bash
git clone https://github.com/cliqueraft/allears-hacs-plugin
cd allears-hacs-plugin
pip install ruff mypy pytest pytest-asyncio \
  pytest-homeassistant-custom-component pytest-cov freezegun
pytest tests/ --cov=custom_components/allears
```

## License
MIT License. See LICENSE file.
