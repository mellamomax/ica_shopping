from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol
from typing import Any
from .const import DOMAIN

class ICAConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title=user_input["ica_list_id"], data=user_input)

        # Hämta bara todo-entity IDs
        entities = self.hass.states.async_entity_ids("todo")

        # Bygg friendly name + ID-par för dropdown
        choices = {}
        for entity_id in entities:
            state = self.hass.states.get(entity_id)
            if state:
                name = state.attributes.get("friendly_name", entity_id)
                display = f"{name} ({entity_id})"
                choices[display] = entity_id

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("personnummer"): str,
                vol.Required("pinkod"): str,
                vol.Required("ica_list_id"): str,
                vol.Optional("todo_entity_id", default=next(iter(choices.values()), "")): vol.In(choices),
            }),
        )
