import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, DATA_ICA

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=60)


async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.debug("📡 sensor.async_setup_entry startar...")

    api = hass.data[DOMAIN][DATA_ICA]
    list_id = entry.options.get("ica_list_id", entry.data["ica_list_id"])
    session_id = entry.options.get("session_id", entry.data["session_id"])
    
    list_name = await api.get_list_name(list_id)
    
    async_add_entities([
        ShoppingListSensor(hass, api, list_id, list_name),
        ICALastPurchaseSensor(hass, api, list_id, list_name)
    ], True)

class ShoppingListSensor(SensorEntity):
    def __init__(self, hass, api, list_id, list_name):
        self.hass = hass
        self._api = api
        self._list_id = list_id
        self._list_name = list_name

        self._attr_name = f"shoppinglist_{self._list_name.lower().replace(' ', '_')}"

        self._attr_native_unit_of_measurement = "items"
        self._attr_has_entity_name = False
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._list_id)},
            "name": f"ICA – {self._list_name}",
            "manufacturer": "ICA",
        }

    def _update_state(self, data):
        items = data.get("rows", [])
        _LOGGER.debug("📦 Items i lista %s: %s", self._list_id, items)
        self._attr_native_value = len(items)

        attributes = {
            "list_name": data.get("name", "")
        }
        for i, item in enumerate(items, start=1):
            attributes[f"vara_{i}"] = item.get("text", "")

        self._attr_extra_state_attributes = attributes


    async def async_update(self):
        _LOGGER.debug("🔄 async_update för lista %s", self._list_id)
        try:
            lists = await self._api.fetch_lists()
            for lst in lists:
                if lst.get("id") == self._list_id:
                    self._update_state(lst)
                    return
            _LOGGER.warning("⚠️ Kunde inte hitta lista med ID %s vid sensor update", self._list_id)
        except Exception as e:
            _LOGGER.error("💥 Fel i sensor async_update: %s", e)

    async def async_added_to_hass(self):
        async def handle_refresh(event):
            await self.async_update_ha_state(force_refresh=True)

        self._unsub_dispatcher = self.hass.bus.async_listen("ica_shopping_refresh", handle_refresh)

    async def async_will_remove_from_hass(self):
        if hasattr(self, "_unsub_dispatcher"):
            self._unsub_dispatcher()




from datetime import datetime
import aiohttp

class ICALastPurchaseSensor(SensorEntity):
    def __init__(self, hass, api, list_id, list_name):
        self.hass = hass
        self._api = api
        self._list_id = list_id
        self._list_name = list_name
        
        self._attr_unique_id = f"ica_last_purchase_{self._list_id}"
        self._attr_name = "Last Purchase"
        self._attr_native_value = None
        self._attr_has_entity_name = True
        self._attr_extra_state_attributes = {}
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._list_id)},
            "name": f"ICA – {self._list_name}",
            "manufacturer": "ICA",
        }

    async def async_added_to_hass(self):
        async def handle_refresh(event):
            await self.async_update_ha_state(force_refresh=True)

        self._unsub_dispatcher = self.hass.bus.async_listen("ica_shopping_refresh", handle_refresh)

    async def async_will_remove_from_hass(self):
        if hasattr(self, "_unsub_dispatcher"):
            self._unsub_dispatcher()

    async def async_update(self):
        try:
            token = await self._api._get_token_from_session_id()
            _LOGGER.debug("🧪 Token: %s", token)
            _LOGGER.debug("🧪 Session-ID: %s", self._api.session_id)
            
            if not token:
                return

            now = datetime.now()
            url = f"https://www.ica.se/api/cpa/purchases/historical/me/byyearmonth/{now.strftime('%Y-%m')}"

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Cookie": f"thSessionId={self._api.session_id}"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.warning("Kunde inte hämta köphistorik (%s)", resp.status)
                        return

                    data = await resp.json()
                    transactions = data.get("transactions", [])
                    if not transactions:
                        self._attr_native_value = "Inga köp"
                        self._attr_extra_state_attributes = {}
                        return

                    latest = transactions[0]
                    self._attr_native_value = latest["transactionDate"][:10]
                    self._attr_extra_state_attributes = {
                        "transaction_id": latest["transactionId"],
                        "belopp": latest["transactionValue"],
                        "rabatt": latest["totalDiscount"],
                        "butik": latest["storeMarketingName"],
                    }
        except Exception as e:
            _LOGGER.error("Fel i ICA Senaste Köp-sensor: %s", e)