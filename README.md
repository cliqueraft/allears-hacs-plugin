# AllEars Sound Tracker
Subtitle: Home Assistant integration for the AllEars Android app

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/cliqueraft/allears-hacs-plugin)
[![Validate](https://github.com/cliqueraft/allears-hacs-plugin/actions/workflows/validate.yml/badge.svg)](https://github.com/cliqueraft/allears-hacs-plugin/actions/workflows/validate.yml)
[![Tests](https://github.com/cliqueraft/allears-hacs-plugin/actions/workflows/tests.yml/badge.svg)](https://github.com/cliqueraft/allears-hacs-plugin/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/cliqueraft/allears-hacs-plugin/blob/main/LICENSE)

## Overview
This integration receives classified sound events directly from the AllEars Android app via a local webhook. It creates sensors to track the latest detected sounds and flows within Home Assistant. You can use these entities to build powerful automations or trigger immediate alerts.

## Prerequisites
1. Home Assistant `2024.1.0` or later (CI tests 2024.1, 2024.6 and the current release)
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

**Step 2: Name the phone**
For example "Bedroom phone". Each phone running AllEars is added separately and gets its own device, webhook and entities.

**Step 3: Copy the webhook URL**
The next screen shows the URL for your home network and, if you have one set up, a remote URL. You can see it again later under the integration's **Configure** button.

**Step 4: Paste it into AllEars**
In AllEars, open a flow, add the action **Trigger Webhook** and paste the URL. Do this for every flow you want Home Assistant to hear about.

**Step 5: Sync your flows**
In AllEars → Settings, tap **Sync Flows with Home Assistant**. Your flows then show up in the automation editor and on the dashboard card.

**Step 6: Verify**
Developer Tools → Actions → `allears.test_webhook` → Perform action. The phone's *Last sound* entity should show "Test Sound".

## Dashboard card
The integration loads the card automatically; there is no resource to add.

1. Edit a dashboard → Add card → search **AllEars**
2. Pick the phone in the visual editor (optional: title, history window)

The card shows whether the phone is connected and when it was last seen, a live "sound detected" state, the last sound with its flow, confidence and time, your synced flows as filters, and the recent sounds from Home Assistant's history. Admins also get **Send test sound**, **Automate** (opens the device page, where new automations come pre-filled with the AllEars trigger) and **Clear**.

YAML:
```yaml
type: custom:all-ears-card
device_id: <your AllEars device id>   # optional, defaults to the first phone
title: Nursery                         # optional
show_history: true                     # optional
history_hours: 24                      # optional, 1-168
```

If you added `/all-ears-card/all-ears-card.js` as a dashboard resource for an older version, you can remove it.

## Webhook Specification
The integration robustly relies on **GET** requests with **URL Query Parameters** to guarantee compliance with all variants of the Android client.

Example incoming HTTP request:
```
GET /api/webhook/<id>?app=AllEars&flow_name=Security&sound_class=Glass+Breaking&confidence=0.87&timestamp=1711132800000
```
- Missing parameters fallback to built-in stable defaults.
- Enforced verification on timestamp drift and confidence value (`0.0`–`1.0`).

## Entities created
One set per phone. Entity ids start with the phone's name, e.g. `sensor.bedroom_phone_last_sound`.

| Entity | Type | Description |
|-----------|------|-------------|
| Last sound | Sensor | Sound name of the most recent detection. Kept across restarts. |
| Last flow | Sensor (enum) | The AllEars flow that matched it. Options are the synced flows. |
| Sound active | Binary sensor | On for 30 seconds after a detection, then off. Only real sounds turn it on. |
| Flow filter | Select | The synced flows. Picking one fires `allears_flow_selected`. |
| Last seen | Sensor (diagnostic) | When the phone last reached Home Assistant (sound or flow sync). |

Attributes of *Last sound*: `flow_name`, `confidence` (0-1), `timestamp` (ISO 8601, when the phone heard it), `last_updated`.

## Event
Every detection fires `allears_sound_detected` with `device_id`, `flow_name`, `sound_class`, `confidence`, `timestamp` and `app`.

## Services
| Service | Description | Fields |
|---------|-------------|--------|
| `allears.test_webhook` | Fires a "Test Sound" event from "Test Flow", exactly like the app. | `device_id` (optional, one or more phones) |
| `allears.clear_history` | Forgets the last sound and flow. Synced flows are kept. | `device_id` (optional) |

## Automation examples

Use the **device trigger**: it only fires for the phone you pick.

### Example 1: alert when the Security flow fires
1. Triggers → Add trigger → **Device** → pick your AllEars phone
2. Trigger: **AllEars heard a sound**
3. Flow: pick `Security` from the list (optional: Sound, for an exact sound name)

**YAML:**
```yaml
triggers:
  - trigger: device
    domain: allears
    device_id: <your-device-id>
    type: sound_detected
    flow_name: Security
actions:
  - action: notify.mobile_app_my_phone
    data:
      title: AllEars
      message: "{{ trigger.event.data.sound_class }} heard by the Security flow"
```

### Example 2: siren while a sound is active
```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.bedroom_phone_sound_active
    to: "on"
actions:
  - action: siren.turn_on
    target:
      entity_id: siren.alarm
```

## Troubleshooting
| Symptom | Cause | Fix |
|---------|-------|-----|
| Webhook URL unreachable from phone | HA not reachable from the phone's network | Put the phone on the same network as HA, or set up remote access (Settings → System → Network) and use the remote URL. |
| Card says "Waiting for the phone" | The phone has not called the webhook yet | In AllEars Settings, tap **Sync Flows with Home Assistant**. |
| No events arrive | | Watch the phone's *Last seen* sensor. If it never changes, the phone can't reach HA: check the URL in the flow's Trigger Webhook action. If it changes but no sounds arrive, check that the flow has the Trigger Webhook action. `allears.test_webhook` tests your automations without the phone. |
| *Sound active* turns off after 30 s | By design | Trigger on the change to "on", or use the device trigger. |
| Unexpected sounds | Detection threshold in AllEars is low | Raise the confidence threshold in AllEars. |
| A flow name is split in two | The app sends the flow list comma-separated | Avoid commas in flow names. |

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
