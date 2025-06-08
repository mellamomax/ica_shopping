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
    _LOGGER.debug("📦 Setting up ICA Shopping integration")
    conf = config.get(DOMAIN)
    if not conf:
        _LOGGER.warning("⚠️ ICA config saknas i configuration.yaml")
        return True

    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]

    api = ICAApi(hass, username, password)
    hass.data.setdefault(DOMAIN, {})[DATA_ICA] = api

    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def handle_refresh(call):
        _LOGGER.debug("🔁 ICA refresh triggered")

        try:
            _LOGGER.debug("⏳ Hämtar ICA-listor...")
            lists = await api.fetch_lists()
            _LOGGER.debug("✅ Fick tillbaka från fetch_lists(): %s", lists)

            if not lists:
                _LOGGER.warning("🚫 Inga shoppinglistor hittades")
                return

            target_ica_id = "55c428d8-8b05-48a7-b2a2-f84e0d91d155"

            real_list = None
            for l in lists:
                if l.get("id") == target_ica_id:
                    real_list = l
                    break

            if not real_list:
                _LOGGER.warning("❌ Hittade inte lista med ID %s", target_ica_id)
                return

            service_result = await hass.services.async_call(
                "todo", "get_items",
                {"entity_id": "todo.google_keep_inkopslista"},
                blocking=True,
                return_response=True
            )

            _LOGGER.debug("📥 DEBUG Keep get_items raw response: %s", service_result)

            # Plocka ut listan från response
            items = service_result.get("todo.google_keep_inkopslista", {}).get("items", [])
            if not isinstance(items, list):
                _LOGGER.warning("📭 Inga Keep-items hittades (tom eller fel typ)")
                keep_items = []
            else:
                keep_items = [item.get("summary", "").strip().lower() for item in items]
                _LOGGER.debug("🧾 Extraherade Keep-items: %s", keep_items)

            rows = real_list.get("rows", [])
            ica_items = [row["text"].strip() for row in rows if isinstance(row, dict) and "text" in row]
            ica_lower = [item.lower() for item in ica_items]

            entity_id = f"sensor.ica_shopping_{target_ica_id.replace('-', '_')}"
            hass.states.async_set(entity_id, len(ica_items), {
                "Namn": real_list.get("name", "ICA Lista"),
                "Varor": ", ".join(ica_items)
            })

            _LOGGER.info("📡 Uppdaterade sensor: %s (%s)", real_list.get("name", "Unnamed"), entity_id)

            to_add = [item for item in ica_items if item.lower() not in keep_items]
            to_remove = [item for item in keep_items if item not in ica_lower]

            _LOGGER.debug("➕ Lägg till i Keep: %s", to_add)
            _LOGGER.debug("➖ Ta bort från Keep: %s", to_remove)

            for item in to_add:
                await hass.services.async_call("todo", "add_item", {
                    "entity_id": "todo.google_keep_inkopslista",
                    "item": item
                })
                _LOGGER.info("✅ Lade till '%s' i Keep", item)

            for item in to_remove:
                await hass.services.async_call("todo", "remove_item", {
                    "entity_id": "todo.google_keep_inkopslista",
                    "item": item
                })
                _LOGGER.info("🗑️ Tog bort '%s' från Keep", item)

        except Exception as e:
            _LOGGER.error("💥 ICA refresh failed: %s", e)

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    return True

