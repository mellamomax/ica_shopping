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

            if not lists:
                _LOGGER.warning("No shopping lists found")
                return

            # Hämta Google Keep-data
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

            for lst in lists:
                for real_list in lst.get("items", []):
                    if "rows" not in real_list:
                        _LOGGER.warning("List saknar 'rows': %s", real_list)
                        continue

                    list_id = real_list.get("id")
                    safe_id = list_id.replace("-", "_").lower()
                    entity_id = f"sensor.ica_shopping_{safe_id}"

                    rows = real_list.get("rows", [])
                    ica_items = [row["text"].strip() for row in rows if isinstance(row, dict) and "text" in row]

                    # Uppdatera sensor
                    hass.states.async_set(entity_id, len(ica_items), {
                        "Namn": real_list.get("name", "ICA Lista"),
                        "Varor": ", ".join(ica_items)
                    })

                    _LOGGER.info("Updated sensor: %s (%s)", real_list.get("name", "Unnamed"), entity_id)

                    # Synka till Keep
                    ica_lower = [item.lower() for item in ica_items]

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
