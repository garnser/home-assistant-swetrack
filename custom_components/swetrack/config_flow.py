from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import SweTrackApiClient, SweTrackApiError
from .const import CONF_BASE_URL, CONF_TOKEN, DEFAULT_BASE_URL, DOMAIN, CONF_SCAN_INTERVAL, CONF_FETCH_EXTENDED, DEFAULT_SCAN_INTERVAL, DEFAULT_FETCH_EXTENDED

class SweTrackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            base_url = user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL).strip()

            api = SweTrackApiClient(self.hass, token=token, base_url=base_url)
            try:
                # Validate token
                await api.async_get_devices()

                # Use account info as unique ID if available
                acct = await api.async_get_account_info()
                acct_data = acct.get("data") or {}
                # Best effort: choose something stable
                unique = str(acct_data.get("id") or acct_data.get("email") or base_url)

                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()

            except SweTrackApiError:
                errors["base"] = "auth"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="SweTrack",
                    data={
                        CONF_TOKEN: token,
                        CONF_BASE_URL: base_url,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN): str,
                vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_options(self, user_input=None) -> FlowResult:
        return await self.async_step_init(user_input)

class SweTrackOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=self.entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
                vol.Optional(CONF_FETCH_EXTENDED, default=self.entry.options.get(CONF_FETCH_EXTENDED, DEFAULT_FETCH_EXTENDED)): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

async def async_get_options_flow(config_entry):
    return SweTrackOptionsFlowHandler(config_entry)
