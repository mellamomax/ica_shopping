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

    async def save_synced_list(items: list[str]):
        await store.async_save({"items": items})

    async def load_synced_list() -> list[str]:
        data = await store.async_load()
        return data["items"] if data and "items" in data else []

    def handle_refresh(call):
        _LOGGER.debug("ICA refresh triggered")

        try:
            lists = api.fetch_lists()
            _LOGGER.debug("Fetched shopping lists: %s", lists)

            if not lists:
                _LOGGER.warning("No shopping lists found")
                return

            for lst in lists:
                for real_list in lst.get("items", []):
                    if "rows" not in real_list:
                        _LOGGER.warning("List saknar 'rows': %s", real_list)
                        continue

                    list_id = real_list.get("id")
                    safe_id = list_id.replace("-", "_").lower()
                    entity_id = f"sensor.ica_shopping_{safe_id}"

                    rows = real_list.get("rows", [])
                    items = [row["text"] for row in rows if isinstance(row, dict) and "text" in row]

                    hass.states.async_set(entity_id, len(items), {
                        "Namn": real_list.get("name", "ICA Lista"),
                        "Varor": ", ".join(items)
                    })

                    _LOGGER.info("Updated sensor: %s (%s)", real_list.get("name", "Unnamed"), entity_id)
        except Exception as e:
            _LOGGER.error("ICA refresh failed: %s", e)

    async def handle_google_keep_add_item(event):
        if event.origin != "local":
            return

        item = event.data.get("item")
        if not item:
            return
        _LOGGER.info("Google Keep: item added: %s", item)

        try:
            ica_lists = api.fetch_lists()
            list_id = ica_lists[0]["items"][0]["id"]
            api.add_item(list_id, item)
            _LOGGER.info("Item '%s' skickat till ICA", item)
        except Exception as e:
            _LOGGER.error("Misslyckades lägga till i ICA: %s", e)

        synced = await load_synced_list()
        if item not in synced:
            synced.append(item)
            await save_synced_list(synced)

    async def handle_google_keep_remove_item(event):
        if event.origin != "local":
            return

        item = event.data.get("item")
        if not item:
            return
        _LOGGER.info("Google Keep: item removed: %s", item)

        try:
            ica_lists = api.fetch_lists()
            real_list = ica_lists[0]["items"][0]
            for row in real_list.get("rows", []):
                if row["text"].strip().lower() == item.strip().lower():
                    api.remove_item(real_list["id"], row["id"])
                    _LOGGER.info("Removed '%s' from ICA", item)
                    break
        except Exception as e:
            _LOGGER.error("Misslyckades ta bort från ICA: %s", e)

        synced = await load_synced_list()
        if item in synced:
            synced.remove(item)
            await save_synced_list(synced)

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    hass.bus.async_listen("todo.add_item", handle_google_keep_add_item)
    hass.bus.async_listen("todo.remove_item", handle_google_keep_remove_item)

    return True
