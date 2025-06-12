import logging
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_call_later
from .const import DOMAIN, DATA_ICA
from .ica_api import ICAApi

_LOGGER = logging.getLogger(__name__)


async def _trigger_sensor_update(hass, list_id):
    entity_id = f"sensor.ica_lista_{list_id}".replace("-", "_")
    await hass.helpers.entity_component.async_update_entity(entity_id)

STORAGE_VERSION = 1
STORAGE_KEY = "ica_keep_synced_list"
MAX_ICA_ITEMS = 250
MAX_KEEP_ITEMS = 100
DEBOUNCE_SECONDS = 1

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    _LOGGER.debug("\u2699\ufe0f ICA Shopping initieras via UI config entry")

    session_id = entry.options.get("session_id", entry.data["session_id"])
    list_id = entry.options.get("ica_list_id", entry.data["ica_list_id"])
    todo_entity = entry.options.get("todo_entity_id", entry.data.get("todo_entity_id"))
    api = ICAApi(hass, session_id=session_id)
    hass.data.setdefault(DOMAIN, {})[DATA_ICA] = api

    debounce_unsub = None

    async def schedule_sync(_now=None):
        nonlocal debounce_unsub
        debounce_unsub = None
        _LOGGER.debug("\ud83d\udd01 Debounced Keep → ICA sync")
        try:
            result = await hass.services.async_call(
                "todo", "get_items",
                {"entity_id": todo_entity},
                blocking=True, return_response=True
            )
            items = result.get(todo_entity, {}).get("items", [])
            summaries = [i.get("summary", "").strip() for i in items if isinstance(i, dict)]
            if len(summaries) > MAX_KEEP_ITEMS:
                summaries = summaries[:MAX_KEEP_ITEMS]

            lists = await api.fetch_lists()
            rows = next((l.get("rows", []) for l in lists if l.get("id") == list_id), [])
            if len(rows) >= MAX_ICA_ITEMS:
                _LOGGER.error("\ud83d\udeab ICA-listan full (%s). Inga varor tillagda.", len(rows))
                return

            existing = [r.get("text", "").strip().lower() for r in rows if isinstance(r, dict)]
            space = MAX_ICA_ITEMS - len(rows)
            to_add = [s for s in summaries if s.lower() not in existing][:space]

            any_added = False
            for text in to_add:
                success = await api.add_item(list_id, text)
                if success:
                    _LOGGER.info("\ud83d\udcc5 Lade till '%s' i ICA", text)
                    any_added = True

            if any_added:
                await _trigger_sensor_update(hass, list_id)

        except Exception as e:
            _LOGGER.error("\ud83d\udca5 Fel vid sync_keep_to_ica: %s", e)

    def call_service_listener(event):
        nonlocal debounce_unsub
        data = event.data.get("service_data", {})
        service = event.data.get("service")
        entity_ids = data.get("entity_id", [])
        item = data.get("item", "").strip().lower() if "item" in data else None

        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        if todo_entity not in entity_ids:
            return

        if service == "add_item":
            hass.data[DOMAIN].setdefault("recent_keep_adds", set()).add(item)
            _LOGGER.debug("\ud83d\udccc Noterat 'add_item' i Keep: %s", item)

        elif service == "remove_item":
            hass.data[DOMAIN].setdefault("recent_keep_removes", set()).add(item)
            _LOGGER.debug("\ud83d\udccc Noterat 'remove_item' i Keep: %s", item)

        if debounce_unsub:
            debounce_unsub()
        debounce_unsub = async_call_later(hass, DEBOUNCE_SECONDS, schedule_sync)

    hass.bus.async_listen("call_service", call_service_listener)

    async def handle_refresh(call):
        _LOGGER.debug("\ud83d\udd04 ICA refresh triggered via service")
        try:
            lists = await api.fetch_lists()
            the_list = next((l for l in lists if l.get("id") == list_id), None)
            if not the_list:
                _LOGGER.warning("\u274c Kunde inte hitta ICA-lista %s", list_id)
                return

            rows = the_list.get("rows", [])
            if len(rows) >= MAX_ICA_ITEMS:
                _LOGGER.error("\ud83d\udeab ICA-listan är full (%s varor). Refresh stoppad.", len(rows))
                return

            ica_items = [row.get("text", "").strip() for row in rows if isinstance(row, dict)]
            ica_items_lower = [x.lower() for x in ica_items]
            ica_rows_dict = {
                row.get("text", "").strip().lower(): row.get("id")
                for row in rows if isinstance(row, dict)
            }

            result = await hass.services.async_call(
                "todo", "get_items",
                {"entity_id": todo_entity},
                blocking=True, return_response=True
            )
            keep_items = result.get(todo_entity, {}).get("items", [])
            keep_summaries = [i.get("summary", "").strip() for i in keep_items if isinstance(i, dict)]
            keep_lower = [x.lower() for x in keep_summaries]

            recent_adds = hass.data[DOMAIN].get("recent_keep_adds", set())
            recent_removes = hass.data[DOMAIN].get("recent_keep_removes", set())

            to_add = [item for item in ica_items if item.lower() not in keep_lower and item.lower() not in recent_removes]
            max_add = MAX_ICA_ITEMS - len(keep_items)
            to_add = to_add[:max_add]

            for item in to_add:
                await hass.services.async_call("todo", "add_item", {"entity_id": todo_entity, "item": item})
                _LOGGER.info("\u2705 Lagt till '%s' i Keep", item)

            to_remove_from_keep = [i.get("summary") for i in keep_items if i.get("summary", "").strip().lower() not in ica_items_lower]
            for summary in to_remove_from_keep:
                if summary:
                    await hass.services.async_call("todo", "remove_item", {"entity_id": todo_entity, "item": summary})
                    _LOGGER.info("\ud83d\udd91\ufe0f Tagit bort '%s' från Keep", summary)

            to_remove_from_ica = [item for item in recent_removes if item in ica_rows_dict]
            for text in to_remove_from_ica:
                row_id = ica_rows_dict.get(text)
                if row_id:
                    await api.remove_item(list_id, row_id)
                    _LOGGER.info("\u274c Tog bort '%s' från ICA (baserat på Keep-radering)", text)

            await _trigger_sensor_update(hass, list_id)
            hass.data[DOMAIN]["recent_keep_adds"].clear()
            hass.data[DOMAIN]["recent_keep_removes"].clear()

        except Exception as e:
            _LOGGER.error("\ud83d\udca5 Fel vid refresh: %s", e)

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    entry.async_on_unload(entry.add_update_listener(_options_update_listener))
    return True

async def _options_update_listener(hass, entry):
    _LOGGER.debug("\u267b\ufe0f Optioner har ändrats, laddar om entry")
    await hass.config_entries.async_reload(entry.entry_id)
