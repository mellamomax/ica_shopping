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
    async_add_entities([
        ShoppingListSensor(hass, api, list_id),
        ICALastPurchaseSensor(hass, api, session_id)
    ], True)

class ShoppingListSensor(SensorEntity):
    def __init__(self, hass, api, list_id):
        self.hass = hass
        self._api = api
        self._list_id = list_id

        self._attr_unique_id = f"ica_shopping_{self._list_id}"
        self._attr_name = f"ICA Lista – {list_id}"
        self._attr_native_unit_of_measurement = "items"
        self._attr_has_entity_name = True
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._list_id)},
            "name": f"ICA Lista {self._list_id}",
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

from datetime import datetime
import aiohttp

class ICALastPurchaseSensor(SensorEntity):
    def __init__(self, hass, api, session_id):
        self.hass = hass
        self._api = api
        self._session_id = session_id
        self._attr_unique_id = f"ica_last_purchase"
        self._attr_name = "ICA Senaste Köp"
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "ica_last_purchase")},
            "name": "ICA Senaste Köp",
            "manufacturer": "ICA"
        }

    async def async_update(self):
        try:
            token = await self._api._get_token_from_session_id(self._session_id)
            if not token:
                return

            now = datetime.now()
            url = f"https://www.ica.se/api/cpa/purchases/historical/me/byyearmonth/{now.strftime('%Y-%m')}"

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Cookie": f"ASP.NET_SessionId={self._session_id}"
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
                        "stad": latest["storeCity"]
                    }
        except Exception as e:
            _LOGGER.error("Fel i ICA Senaste Köp-sensor: %s", e)