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

            target_ica_id = "f47d30ed-2555-4f81-88fd-c6d8019c5516"

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

            items = service_result.get("todo.google_keep_inkopslista", {}).get("items", [])
            if not isinstance(items, list):
                _LOGGER.warning("📭 Inga Keep-items hittades (tom eller fel typ)")
                keep_items = []
            else:
                keep_items = items
                keep_summaries = [item.get("summary", "").strip().lower() for item in items]
                _LOGGER.debug("🧾 Extraherade Keep-items: %s", keep_summaries)

            rows = real_list.get("rows", [])
            ica_items = [row["text"].strip() for row in rows if isinstance(row, dict) and isinstance(row.get("text"), str)]
            ica_lower = [item.lower() for item in ica_items]

            entity_id = f"sensor.ica_shopping_{target_ica_id.replace('-', '_')}"
            hass.states.async_set(entity_id, len(ica_items), {
                "Namn": real_list.get("name", "ICA Lista"),
                "Varor": ", ".join(ica_items)
            })

            _LOGGER.info("📡 Uppdaterade sensor: %s (%s)", real_list.get("name", "Unnamed"), entity_id)

            to_add = [item for item in ica_items if item.lower() not in keep_summaries]
            to_remove = [item for item in keep_items if item.get("summary", "").strip().lower() not in ica_lower]

            MAX_ITEMS_PER_REFRESH = 200
            if len(to_add) > MAX_ITEMS_PER_REFRESH:
                _LOGGER.warning("⚠️ För många varor att lägga till (%s). Begränsar till %s första.", len(to_add), MAX_ITEMS_PER_REFRESH)
                to_add = to_add[:MAX_ITEMS_PER_REFRESH]


            _LOGGER.debug("➕ Lägg till i Keep: %s", to_add)
            _LOGGER.debug("➖ Ta bort från Keep: %s", [item.get("summary") for item in to_remove])

            for item in to_add:
                await hass.services.async_call("todo", "add_item", {
                    "entity_id": "todo.google_keep_inkopslista",
                    "item": item
                })
                _LOGGER.info("✅ Lade till '%s' i Keep", item)

            for item in to_remove:
                summary = item.get("summary")
                if not summary:
                    _LOGGER.warning("⚠️ Saknar 'summary' för att ta bort item: %s", item)
                    continue
                await hass.services.async_call("todo", "remove_item", {
                    "entity_id": "todo.google_keep_inkopslista",
                    "item": summary
                })
                _LOGGER.info("🗑️ Tog bort '%s' från Keep", summary)

        except Exception as e:
            _LOGGER.error("💥 ICA refresh failed: %s", e)



    async def handle_keep_add_item(event):
        data = event.data
        service_data = data.get("service_data", {})
        entity_ids = service_data.get("entity_id", [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        if "todo.google_keep_inkopslista" not in entity_ids:
            return

        origin = data.get("origin", "UNKNOWN")

        # Hämta senaste Keep-listan
        service_result = await hass.services.async_call(
            "todo", "get_items",
            {"entity_id": "todo.google_keep_inkopslista"},
            blocking=True,
            return_response=True
        )

        items = service_result.get("todo.google_keep_inkopslista", {}).get("items", [])
        summaries = [item.get("summary", "").strip() for item in items if isinstance(item, dict)]

        MAX_ITEMS_FROM_KEEP = 100
        if len(summaries) > MAX_ITEMS_FROM_KEEP:
            _LOGGER.warning("⚠️ För många Keep-items (%s). Begränsar till %s första.", len(summaries), MAX_ITEMS_FROM_KEEP)
            summaries = summaries[:MAX_ITEMS_FROM_KEEP]

        # Hämta ICA-listan
        ica_list = await api.fetch_lists()
        rows = next((l.get("rows", []) for l in ica_list if l.get("id") == "f47d30ed-2555-4f81-88fd-c6d8019c5516"), [])
        ica_items = [row["text"].strip().lower() for row in rows if isinstance(row, dict) and isinstance(row.get("text"), str)]

        # Skydd: max 250 varor i ICA
        if len(rows) >= 250:
            _LOGGER.warning("🛑 ICA-listan har redan %s varor. Inga fler skickas.", len(rows))
            return

        # Beräkna tillgängligt utrymme
        available_space = 250 - len(rows)
        to_add = [s for s in summaries if s.lower() not in ica_items]
        to_add = to_add[:available_space]

        _LOGGER.debug("➕ ICA tillägg planeras (%s): %s", len(to_add), to_add)

        for summary in to_add:
            try:
                await api.add_to_list(summary)
                _LOGGER.info("📥 (origin=%s) Lade till '%s' i ICA", origin, summary)
            except Exception as e:
                _LOGGER.error("💥 Kunde inte lägga till '%s' i ICA: %s", summary, e)




    hass.bus.async_listen("call_service", handle_keep_add_item)


    hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    return True

