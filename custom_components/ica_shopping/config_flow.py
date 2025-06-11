from homeassistant.core import callback
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import selector

import voluptuous as vol
from typing import Any
from .const import DOMAIN


class ICAConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ICAOptionsFlowHandler(config_entry)
    
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=user_input["ica_list_id"],
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("session_id"): str,
                vol.Required("ica_list_id"): str,
                vol.Optional("todo_entity_id"): selector({
                    "entity": {
                        "domain": "todo",
                        "multiple": False
                    }
                }),
            }),
        )

class ICAOptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("session_id", default=self.config_entry.data.get("session_id", "")): str,
                vol.Required("ica_list_id", default=self.config_entry.data.get("ica_list_id", "")): str,
                vol.Optional("todo_entity_id", default=self.config_entry.data.get("todo_entity_id", "")): selector({
                    "entity": {
                        "domain": "todo",
                        "multiple": False
                    }
                }),
            }),
        )


