# config_flow.py
from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class ICAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input["username"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("ica_list_id"): str,
                vol.Required("keep_entity_id"): str,
            }),
        )
