import logging
import voluptuous as vol
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_call_later
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

# Max items limits
MAX_ICA_ITEMS = 250
MAX_KEEP_ITEMS = 100
DEBOUNCE_SECONDS = 1

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

    # --- REFRESH SERVICE HANDLER ---
    async def handle_refresh(call):
        _LOGGER.debug("🔄 ICA refresh triggered via service")
        # original refresh logic goes here (fetch_lists, sync to Keep)
        # ...

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    # --- KEEP → ICA SYNC WITH CALL_SERVICE & DEBOUNCE ---
    debounce_unsub = None

    async def schedule_sync(_now=None):
        nonlocal debounce_unsub
        debounce_unsub = None
        _LOGGER.debug("🔁 Debounced Keep → ICA sync triggered")
        try:
            # Läs all data från Google Keep via service
            result = await hass.services.async_call(
                "todo", "get_items",
                {"entity_id": "todo.google_keep_inkopslista_2_0_2_0"},
                blocking=True, return_response=True
            )
            items = result.get("todo.google_keep_inkopslista_2_0", {}).get("items", [])
            summaries = [item.get("summary", "").strip() for item in items if isinstance(item, dict)]

            if len(summaries) > MAX_KEEP_ITEMS:
                _LOGGER.warning("⚠️ För många Keep-items (%s), begränsar till %s.", len(summaries), MAX_KEEP_ITEMS)
                summaries = summaries[:MAX_KEEP_ITEMS]

            lists = await api.fetch_lists()
            rows = next((l.get("rows", []) for l in lists if l.get("id") == "817e93f7-a47d-4ec4-8da2-ed94d8fb47a7"), [])
            existing = [row.get("text", "").strip().lower() for row in rows if isinstance(row, dict)]

            if len(rows) >= MAX_ICA_ITEMS:
                _LOGGER.warning("🛑 ICA-listan har redan %s varor, inga läggs till.", len(rows))
                return

            space = MAX_ICA_ITEMS - len(rows)
            to_add = [s for s in summaries if s.lower() not in existing][:space]
            for text in to_add:
                success = await api.add_to_list(text)
                if success:
                    _LOGGER.info("📥 Lade till '%s' i ICA", text)
        except Exception as e:
            _LOGGER.error("💥 Fel vid sync_keep_to_ica: %s", e)

    def call_service_listener(event):
        nonlocal debounce_unsub
        data = event.data.get("service_data", {})
        entity_ids = data.get("entity_id", [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        # Ignorera annat än vår lista
        if "todo.google_keep_inkopslista_2_0" not in entity_ids:
            return
        # Ignorera händelser utan item
        if "item" not in data:
            return

        # Debounce: avbryt tidigare planerad sync
        if debounce_unsub:
            debounce_unsub()
        # Schemalägg ny sync om DEBOUNCE_SECONDS
        debounce_unsub = async_call_later(hass, DEBOUNCE_SECONDS, schedule_sync)

    hass.bus.async_listen("call_service", call_service_listener)

    return True
