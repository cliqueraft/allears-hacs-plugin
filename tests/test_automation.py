import homeassistant.components.automation as automation
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.allears.const import DOMAIN, SENSOR_LAST_FLOW
from custom_components.allears.coordinator import AllEarsDataUpdateCoordinator


@pytest.mark.asyncio
async def test_end_to_end_automation_trigger(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Test that a device state trigger on our sensor successfully runs an automation."""
    # 1. Setup an input boolean to act as our 'light bulb' that turns on when automation runs
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"test_success": {}}}
    )

    # 2. Setup the automation using the exact YAML output HA generates for a Device/State Trigger
    entity_registry = hass.data["entity_registry"]
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{setup_integration.entry_id}_{SENSOR_LAST_FLOW}"
    )
    assert entity_id is not None

    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "alias": "Test AllEars Automation",
                    "description": "Fires when AllEars app detects 'Speech test' flow",
                    "trigger": [
                        {
                            "platform": "state",
                            "entity_id": entity_id,
                            "to": "Speech test",
                        }
                    ],
                    "action": [
                        {
                            "service": "input_boolean.turn_on",
                            "target": {"entity_id": "input_boolean.test_success"},
                        }
                    ],
                }
            ]
        },
    )

    # Wait for HA to fully start up the automation component
    await hass.async_block_till_done()

    # Verify the input boolean starts out 'off'
    assert hass.states.get("input_boolean.test_success").state == "off"

    # 3. Simulate the Android App Webhook firing the "Speech test" flow
    coordinator: AllEarsDataUpdateCoordinator = hass.data[DOMAIN][
        setup_integration.entry_id
    ]
    payload = {
        "app": "AllEars",
        "flow_name": "Speech test",
        "sound_class": "speech",
        "confidence": 0.99,
        "timestamp": 1234567890000,
    }
    await coordinator.async_handle_sound_event(payload)

    # Let HA process the state change -> trigger matching -> automation execution
    await hass.async_block_till_done()

    # 4. Prove the automation successfully fired and flipped the switch!
    assert hass.states.get("input_boolean.test_success").state == "on"
    print("\n--- END TO END AUTOMATION PROOF ---")
    print(
        "SUCCESS: The automation successfully caught the 'Speech test' flow and executed its action!"
    )
