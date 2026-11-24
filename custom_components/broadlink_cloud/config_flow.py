"""Configuration flow for BroadLink Cloud account authentication."""

from __future__ import annotations

import httpx
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import BroadlinkCloudAPI, BroadlinkLoginError, BroadlinkCloudError
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN


def _validate_credentials(email: str, password: str) -> str:
    """Validate login in a worker thread, never write credentials to logs."""

    client = BroadlinkCloudAPI()
    try:
        uid = client.login(email, password)
        client.get_families()
        return uid
    finally:
        client.close()


class BroadlinkCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create a configuration entry after a successful EU cloud login."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Prompt for the same credentials used in the official BroadLink app."""

        errors = {}
        if user_input is not None:
            try:
                uid = await self.hass.async_add_executor_job(
                    _validate_credentials,
                    user_input[CONF_EMAIL].strip(),
                    user_input[CONF_PASSWORD],
                )
            except BroadlinkLoginError:
                errors["base"] = "invalid_auth"
            except (httpx.HTTPError, BroadlinkCloudError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="BroadLink Cloud",
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL].strip(),
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
                    ),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
                    ),
                }
            ),
            errors=errors,
        )
