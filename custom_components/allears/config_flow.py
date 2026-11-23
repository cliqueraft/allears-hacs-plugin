"""Config flow for AllEars integration."""

from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import CONF_DEVICE_NAME, CONF_WEBHOOK_ID, DEFAULT_DEVICE_NAME, DOMAIN


def webhook_urls(hass: HomeAssistant, webhook_id: str) -> tuple[str, str]:
    """Return (home network URL, remote URL) text for the setup screens."""
    path = f"/api/webhook/{webhook_id}"
    try:
        local = get_url(hass, allow_external=False) + path
    except NoURLAvailableError:
        local = f"http://<your-ha-ip>:8123{path}"
    try:
        remote = get_url(hass, allow_internal=False, allow_cloud=False) + path
    except NoURLAvailableError:
        remote = "Not set up (Settings → System → Network → Home Assistant URL)"
    return local, remote


class AllEarsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AllEars. One entry per phone."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._device_name: str | None = None
        self._webhook_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for a name for this phone."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_DEVICE_NAME].strip()
            if not name:
                errors[CONF_DEVICE_NAME] = "name_required"
            elif any(e.title == name for e in self._async_current_entries()):
                errors[CONF_DEVICE_NAME] = "name_in_use"
            else:
                self._device_name = name
                # 16 hex characters (64 bits). The URL is copied, not typed:
                # the app has a paste field and a copy button.
                self._webhook_id = secrets.token_hex(8)
                await self.async_set_unique_id(self._webhook_id)
                return await self.async_step_webhook_url()

        default = (
            DEFAULT_DEVICE_NAME
            if not self._async_current_entries()
            else f"{DEFAULT_DEVICE_NAME} {len(self._async_current_entries()) + 1}"
        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_NAME, default=default): str}
            ),
            errors=errors,
        )

    async def async_step_webhook_url(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the webhook URL to paste into the app."""
        webhook_id = self._webhook_id or ""
        if user_input is not None:
            return self.async_create_entry(
                title=self._device_name or DEFAULT_DEVICE_NAME,
                data={
                    CONF_WEBHOOK_ID: webhook_id,
                    CONF_DEVICE_NAME: self._device_name,
                },
            )

        local, remote = webhook_urls(self.hass, webhook_id)
        return self.async_show_form(
            step_id="webhook_url",
            description_placeholders={
                "webhook_url": local,
                "remote_url": remote,
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> AllEarsOptionsFlow:
        """Return the options flow for this entry."""
        return AllEarsOptionsFlow(config_entry)


class AllEarsOptionsFlow(config_entries.OptionsFlow):
    """Rename the phone and see its webhook URL again."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise the options flow with the existing entry."""
        self._entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Show the options form pre-populated with current device name."""
        if user_input is not None:
            # webhook_id is immutable; only device_name can change here.
            updated_data = {
                **self._entry.data,
                CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME],
            }
            self.hass.config_entries.async_update_entry(
                self._entry,
                data=updated_data,
                title=user_input[CONF_DEVICE_NAME],
            )
            return self.async_create_entry(title="", data={})

        current_name: str = self._entry.data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)
        webhook_id: str = self._entry.data[CONF_WEBHOOK_ID]
        local, remote = webhook_urls(self.hass, webhook_id)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_NAME, default=current_name): str}
            ),
            description_placeholders={
                "webhook_id": webhook_id,
                "webhook_url": local,
                "remote_url": remote,
            },
        )
