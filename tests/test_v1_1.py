"""Tests for the 1.1 behaviour: per-phone routing, honest sound_active,
sensor attributes, last seen and trigger capabilities."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.allears.const import (
    ATTR_CONFIDENCE,
    ATTR_DEVICE_ID,
    ATTR_FLOW_NAME,
    BINARY_SENSOR_ACTIVE,
    CONF_DEVICE_NAME,
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_SOUND_DETECTED,
    SENSOR_LAST_SEEN,
    SENSOR_LAST_SOUND,
)

from .conftest import ENTRY_ID_FOR_TESTS, WEBHOOK_ID_FOR_TESTS


def _entity(hass: HomeAssistant, domain: str, key: str, entry_id: str = ENTRY_ID_FOR_TESTS) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{entry_id}_{key}")
    assert entity_id is not None
    return entity_id


@pytest.mark.asyncio
async def test_flow_sync_does_not_turn_sound_active_on(
    hass: HomeAssistant, hass_client_no_auth: Any, setup_integration: MockConfigEntry
) -> None:
    """Syncing flows from the app is not a sound and must not fire automations."""
    client = await hass_client_no_auth()
    resp = await client.get(
        f"/api/webhook/{WEBHOOK_ID_FOR_TESTS}",
        params={"action": "register_flows", "flows": "Nursery,Doorbell"},
    )
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()
    await client.close()

    assert hass.states.get(_entity(hass, "binary_sensor", BINARY_SENSOR_ACTIVE)).state == "off"
    # ...but it does count as the phone being seen.
    assert hass.states.get(_entity(hass, "sensor", SENSOR_LAST_SEEN)).state not in (
        "unknown",
        "unavailable",
    )


@pytest.mark.asyncio
async def test_clear_history_turns_sound_active_off(
    hass: HomeAssistant, setup_integration: MockConfigEntry, valid_payload: dict[str, Any]
) -> None:
    """Clearing must not count as a new sound."""
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    await coordinator.async_handle_sound_event(valid_payload)
    await hass.async_block_till_done()
    active = _entity(hass, "binary_sensor", BINARY_SENSOR_ACTIVE)
    assert hass.states.get(active).state == "on"

    await hass.services.async_call(DOMAIN, "clear_history", blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(active).state == "off"


@pytest.mark.asyncio
async def test_last_sound_sensor_exposes_attributes(
    hass: HomeAssistant, setup_integration: MockConfigEntry, valid_payload: dict[str, Any]
) -> None:
    """Flow, confidence and time are attributes of the last sound sensor."""
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    await coordinator.async_handle_sound_event(valid_payload)
    await hass.async_block_till_done()

    state = hass.states.get(_entity(hass, "sensor", SENSOR_LAST_SOUND))
    assert state.attributes[ATTR_FLOW_NAME] == valid_payload[ATTR_FLOW_NAME]
    assert state.attributes[ATTR_CONFIDENCE] == pytest.approx(0.87)
    assert state.attributes["timestamp"].startswith("2024-03-22")


@pytest.mark.asyncio
async def test_events_carry_device_id_and_route_per_phone(
    hass: HomeAssistant, hass_client_no_auth: Any, setup_integration: MockConfigEntry
) -> None:
    """Each phone's webhook updates its own device only."""
    second = MockConfigEntry(
        domain=DOMAIN,
        entry_id="second_entry",
        title="Kitchen tablet",
        data={CONF_WEBHOOK_ID: "second_hook", CONF_DEVICE_NAME: "Kitchen tablet"},
    )
    second.add_to_hass(hass)
    await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()

    events: list[Any] = []
    hass.bus.async_listen(EVENT_SOUND_DETECTED, events.append)

    client = await hass_client_no_auth()
    resp = await client.get(
        "/api/webhook/second_hook",
        params={"app": "AllEars", "flow": "Kitchen", "sound": "Dog", "score": "0.8"},
    )
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()
    await client.close()

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "second_entry")})
    assert device is not None
    assert len(events) == 1
    assert events[0].data[ATTR_DEVICE_ID] == device.id

    assert hass.states.get(_entity(hass, "sensor", SENSOR_LAST_SOUND, "second_entry")).state == "Dog"
    first_state = hass.states.get(_entity(hass, "sensor", SENSOR_LAST_SOUND)).state
    assert first_state == "unknown"

    await hass.config_entries.async_unload(second.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_trigger_capabilities_offer_registered_flows(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The automation editor gets a Flow dropdown from the registered flows."""
    from custom_components.allears.device_trigger import async_get_trigger_capabilities

    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    await coordinator.async_register_flows(["Nursery", "Doorbell"])
    caps = await async_get_trigger_capabilities(
        hass,
        {
            "platform": "device",
            "domain": DOMAIN,
            "device_id": coordinator.device_id,
            "type": "sound_detected",
        },
    )
    schema = caps["extra_fields"]
    assert schema({ATTR_FLOW_NAME: "Nursery"}) == {ATTR_FLOW_NAME: "Nursery"}
    with pytest.raises(Exception):
        schema({ATTR_FLOW_NAME: "Not a flow"})


@pytest.mark.asyncio
async def test_test_webhook_can_target_one_phone(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """test_webhook with a device_id only fires for that phone."""
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    events: list[Any] = []
    hass.bus.async_listen(EVENT_SOUND_DETECTED, events.append)

    await hass.services.async_call(
        DOMAIN, "test_webhook", {"device_id": "unknown"}, blocking=True
    )
    await hass.async_block_till_done()
    assert events == []

    await hass.services.async_call(
        DOMAIN, "test_webhook", {"device_id": coordinator.device_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert len(events) == 1
