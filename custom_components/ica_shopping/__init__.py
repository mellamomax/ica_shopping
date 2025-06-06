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
    _LOGGER.debug("Setting up ICA Shopping...")
    conf = config.get(DOMAIN)
    if not conf:
        _LOGGER.warning("ICA config not found")
        return True

    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]

    api = ICAApi(hass, username, password)
    # await api.async_initialize()

    hass.data.setdefault(DOMAIN, {})[DATA_ICA] = api

    # Skapa dummy-sensor
    hass.states.async_set("sensor.ica_shopping_list", "No data", {
        "items": [],
        "updated_manually": True
    })


    def handle_refresh(call):
        """Manuell uppdatering av shoppinglista via tjänst."""
        _LOGGER.debug("ICA refresh triggered")
        try:
            api._token = None  # Tvinga ny token
            lists = api.fetch_lists()

            if not lists:
                _LOGGER.warning("No shopping lists found")
                return

            for lst in lists:
                list_id = lst.get("id")
                safe_id = list_id.replace("-", "_").lower()
                entity_id = f"sensor.ica_shopping_{safe_id}"
                items = [item["text"] for item in lst.get("items", [])]

                hass.states.async_set(entity_id, len(items), {
                    "items": items,
                    "items_string": ", ".join(items),
                    "list_name": lst.get("name"),
                    "updated_manually": True
                })

                _LOGGER.info("Updated sensor: %s (%s)", lst.get("name"), entity_id)

        except Exception as e:
            _LOGGER.error("ICA refresh failed: %s", e)

    def handle_add_item(call):
        """Lägg till vara i en lista via tjänst."""
        try:
            list_id = call.data["list_id"]
            text = call.data["text"]
            api.add_item(list_id, text)
            _LOGGER.info("Item '%s' added to list %s", text, list_id)
        except Exception as e:
            _LOGGER.error("Failed to add item: %s", e)

    hass.services.async_register(
        DOMAIN,
        "add_item",
        handle_add_item,
        schema=vol.Schema({
            vol.Required("list_id"): cv.string,
            vol.Required("text"): cv.string,
        }),
    )


    hass.services.async_register(DOMAIN, "refresh", handle_refresh)
    return True
