import logging
import voluptuous as vol
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from .const import DOMAIN, DATA_ICA
from .ica_api import ICAApi

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)

STORAGE_VERSION = 1
STORAGE_KEY = "ica_keep_synced_list"

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
    hass.data.setdefault(DOMAIN, {})[DATA_ICA] = api

    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def handle_refresh(call):
        _LOGGER.debug("ICA refresh triggered")

        try:
            # Hämta ICA-data
            lists = await api.fetch_lists()
            _LOGGER.debug("Fetched shopping lists: %s", lists)
            _LOGGER.debug("🔍 Resultat från fetch_lists(): %s", lists)

            if not lists:
                _LOGGER.warning("No shopping lists found")
                return

            # Hårdkoda ICA-list-ID
            target_ica_id = "55c428d8-8b05-48a7-b2a2-f84e0d91d155"

            real_list = None
            for lst in lists:
                for l in lst.get("items", []):
                    if l.get("id") == target_ica_id:
                        real_list = l
                        break

            if not real_list:
                _LOGGER.warning("Hittade ingen lista med ID %s", target_ica_id)
                return

            # Hämta Keep-data
            keep_response = await hass.services.async_call(
                "todo", "get_items",
                {"entity_id": "todo.google_keep_inkopslista"},
                blocking=True, return_response=True
            )

            if not keep_response or not isinstance(keep_response, list):
                _LOGGER.warning("No Keep items returned")
                keep_items = []
            else:
                keep_items = [item.get("summary", "").strip().lower() for item in keep_response]

            _LOGGER.debug("Current Google Keep items: %s", keep_items)

            # Hantera ICA-items
            rows = real_list.get("rows", [])
            ica_items = [row["text"].strip() for row in rows if isinstance(row, dict) and "text" in row]
            ica_lower = [item.lower() for item in ica_items]

            # Uppdatera sensor
            entity_id = "sensor.ica_shopping_55c428d8_8b05_48a7_b2a2_f84e0d91d155"
            hass.states.async_set(entity_id, len(ica_items), {
                "Namn": real_list.get("name", "ICA Lista"),
                "Varor": ", ".join(ica_items)
            })

            _LOGGER.info("Updated sensor: %s (%s)", real_list.get("name", "Unnamed"), entity_id)

            # Synka till Keep
            to_add = [item for item in ica_items if item.lower() not in keep_items]
            to_remove = [item for item in keep_items if item not in ica_lower]

            _LOGGER.debug("Items to add to Keep: %s", to_add)
            _LOGGER.debug("Items to remove from Keep: %s", to_remove)

            for item in to_add:
                await hass.services.async_call(
                    "todo", "add_item",
                    {
                        "entity_id": "todo.google_keep_inkopslista",
                        "item": item
                    }
                )
                _LOGGER.info("Added '%s' to Google Keep", item)

            for item in to_remove:
                await hass.services.async_call(
                    "todo", "remove_item",
                    {
                        "entity_id": "todo.google_keep_inkopslista",
                        "item": item
                    }
                )
                _LOGGER.info("Removed '%s' from Google Keep", item)

        except Exception as e:
            _LOGGER.error("ICA refresh failed: %s", e)

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    return True
