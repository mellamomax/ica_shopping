import logging
import voluptuous as vol
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN, DATA_ICA
from .ica_api import ICAApi

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Set up ICA Shopping integration."""
    conf = config.get(DOMAIN)
    if not conf:
        return True

    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]

    api = ICAApi(hass, username, password)
    await api.async_initialize()

    hass.data.setdefault(DOMAIN, {})[DATA_ICA] = api

    # Skapa dummy-sensor
    hass.states.async_set("sensor.ica_shopping_list", "No data", {
        "items": [],
        "updated_manually": True
    })

    def handle_refresh(call):
        """Manuell uppdatering av shoppinglista via tjänst."""
        try:
            api._token = None  # Tvinga ny token
            lists = api.fetch_lists()
            if lists:
                main_list = lists[0]
                items = [item["text"] for item in main_list.get("items", [])]
                hass.states.async_set("sensor.ica_shopping_list", len(items), {
                    "items": items,
                    "list_name": main_list.get("name"),
                    "updated_manually": True
                })
                _LOGGER.info("ICA list updated: %s", main_list.get("name"))
            else:
                hass.states.async_set("sensor.ica_shopping_list", 0, {
                    "items": [],
                    "list_name": "None",
                    "updated_manually": True
                })
        except Exception as e:
            _LOGGER.error("ICA refresh failed: %s", e)

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)
    return True
