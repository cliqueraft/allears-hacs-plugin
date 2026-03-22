"""Config flow for AllEars integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.network import get_url

from .const import CONF_DEVICE_NAME, CONF_WEBHOOK_ID, DEFAULT_DEVICE_NAME, DOMAIN


class AllEarsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AllEars."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._device_name: str | None = None
        self._webhook_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            self._device_name = user_input[CONF_DEVICE_NAME]
            self._webhook_id = webhook.async_generate_id()
            return await self.async_step_webhook_url()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME, default=DEFAULT_DEVICE_NAME): str,
                }
            ),
        )

    async def async_step_webhook_url(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the webhook URL to the user."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._device_name or DEFAULT_DEVICE_NAME,
                data={
                    CONF_WEBHOOK_ID: self._webhook_id,
                    CONF_DEVICE_NAME: self._device_name,
                },
            )

        ha_url = get_url(self.hass, prefer_external=False)
        webhook_url = f"{ha_url}/api/webhook/{self._webhook_id}"

        return self.async_show_form(
            step_id="webhook_url",
            description_placeholders={"webhook_url": webhook_url},
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> AllEarsOptionsFlow:
        """Return the options flow for this entry."""
        return AllEarsOptionsFlow(config_entry)


class AllEarsOptionsFlow(config_entries.OptionsFlow):
    """Handle AllEars options — allows renaming the device."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise the options flow with the existing entry."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Show the options form pre-populated with current device name."""
        if user_input is not None:
            # Merge update into entry data — webhook_id is immutable,
            # only device_name can change here.
            updated_data = {
                **self._config_entry.data,
                CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME],
            }
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data=updated_data,
                title=user_input[CONF_DEVICE_NAME],
            )
            return self.async_create_entry(title="", data={})

        current_name: str = self._config_entry.data.get(
            CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_NAME,
                        default=current_name,
                    ): str,
                }
            ),
            description_placeholders={
                "webhook_id": self._config_entry.data[CONF_WEBHOOK_ID],
            },
        )
