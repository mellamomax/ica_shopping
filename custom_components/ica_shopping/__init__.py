import logging
import voluptuous as vol
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_call_later
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN, DATA_ICA
from .ica_api import ICAApi
from .config_flow import async_get_options_flow

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required("session_id"): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)

STORAGE_VERSION = 1
STORAGE_KEY = "ica_keep_synced_list"

# Constants
MAX_ICA_ITEMS = 250
MAX_KEEP_ITEMS = 100
DEBOUNCE_SECONDS = 1
TARGET_LIST_ID = "817e93f7-a47d-4ec4-8da2-ed94d8fb47a7"

async def async_setup(hass, config):
    _LOGGER.debug("📦 Setting up ICA Shopping integration")
    conf = config.get(DOMAIN)
    if not conf:
        _LOGGER.warning("⚠️ ICA config saknas i configuration.yaml")
        return True

    session_id = conf["session_id"]

    api = ICAApi(hass, session_id=session_id)

    hass.data.setdefault(DOMAIN, {})[DATA_ICA] = api

    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    # --- REFRESH SERVICE HANDLER ---
    async def handle_refresh(call):
        _LOGGER.debug("🔄 ICA refresh triggered via service")
        try:
            # Fetch lists
            lists = await api.fetch_lists()
            real_list = next((l for l in lists if l.get("id") == TARGET_LIST_ID), None)
            if not real_list:
                _LOGGER.warning("❌ Kunde inte hitta ICA-lista %s", TARGET_LIST_ID)
                return

            rows = real_list.get("rows", [])
            if len(rows) >= MAX_ICA_ITEMS:
                _LOGGER.error("🚫 ICA-listan är full (%s varor). Refresh stoppad.", len(rows))
                return

            # Create/update sensor
            ica_items = [row.get("text", "").strip() for row in rows if isinstance(row, dict)]
            entity_id = f"sensor.ica_shopping_{TARGET_LIST_ID.replace('-', '_')}"
            hass.states.async_set(
                entity_id,
                len(ica_items),
                {"Namn": real_list.get("name", "ICA Lista"), "Varor": ", ".join(ica_items)}
            )
            _LOGGER.info("📡 Sensor uppdaterad: %s med %s varor", entity_id, len(ica_items))

            # Sync ICA → Keep (original logic)
            service_result = await hass.services.async_call(
                "todo", "get_items",
                {"entity_id": "todo.google_keep_inkopslista_2_0"},
                blocking=True, return_response=True
            )
            keep_items = service_result.get("todo.google_keep_inkopslista_2_0", {}).get("items", [])
            keep_summaries = [i.get("summary", "").strip().lower() for i in keep_items if isinstance(i, dict)]

            to_add = [item for item in ica_items if item.lower() not in keep_summaries]
            to_remove = [i.get("summary") for i in keep_items if i.get("summary", "").strip().lower() not in [x.lower() for x in ica_items]]

            # Limit additions
            max_add = MAX_ICA_ITEMS - len(keep_items)
            to_add = to_add[:max_add]

            for item in to_add:
                await hass.services.async_call(
                    "todo", "add_item",
                    {"entity_id": "todo.google_keep_inkopslista_2_0", "item": item}
                )
                _LOGGER.info("✅ Lagt till '%s' i Keep", item)

            for summary in to_remove:
                if summary:
                    await hass.services.async_call(
                        "todo", "remove_item",
                        {"entity_id": "todo.google_keep_inkopslista_2_0", "item": summary}
                    )
                    _LOGGER.info("🗑️ Tagit bort '%s' från Keep", summary)

        except Exception as e:
            _LOGGER.error("💥 Fel vid refresh: %s", e)

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    # --- KEEP → ICA SYNC WITH CALL_SERVICE & DEBOUNCE ---
    debounce_unsub = None

    async def schedule_sync(_now=None):
        nonlocal debounce_unsub
        debounce_unsub = None
        _LOGGER.debug("🔁 Debounced Keep → ICA sync")
        try:
            # Get Keep items
            try:
                result = await hass.services.async_call(
                    "todo", "get_items",
                    {"entity_id": "todo.google_keep_inkopslista_2_0"},
                    blocking=True, return_response=True
                )
            except HomeAssistantError as err:
                _LOGGER.warning("⚠️ Keep-service missmatch: %s", err)
                return

            items = result.get("todo.google_keep_inkopslista_2_0", {}).get("items", [])
            summaries = [i.get("summary", "").strip() for i in items if isinstance(i, dict)]
            if len(summaries) > MAX_KEEP_ITEMS:
                summaries = summaries[:MAX_KEEP_ITEMS]

            # Fetch ICA rows
            lists = await api.fetch_lists()
            rows = next((l.get("rows", []) for l in lists if l.get("id") == TARGET_LIST_ID), [])
            if len(rows) >= MAX_ICA_ITEMS:
                _LOGGER.error("🚫 ICA-listan full (%s). Inga varor tillagda.", len(rows))
                return

            existing = [r.get("text", "").strip().lower() for r in rows if isinstance(r, dict)]
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
        if "todo.google_keep_inkopslista_2_0" not in entity_ids or "item" not in data:
            return

        if debounce_unsub:
            debounce_unsub()
        debounce_unsub = async_call_later(hass, DEBOUNCE_SECONDS, schedule_sync)

    hass.bus.async_listen("call_service", call_service_listener)

    return True
