import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, DATA_ICA
import asyncio  # lägg i toppen om inte redan finns

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=60)


async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.debug("📡 sensor.async_setup_entry startar...")

    api = hass.data[DOMAIN][DATA_ICA]
    list_id = entry.options.get("ica_list_id", entry.data["ica_list_id"])
    session_id = entry.options.get("session_id", entry.data["session_id"])
    
    try:
        list_name = await asyncio.wait_for(api.get_list_name(list_id), timeout=10)
    except Exception as e:
        _LOGGER.error("🚫 Misslyckades hämta listnamn: %s", e)
        list_name = "Okänd lista"
        
    _LOGGER.warning("✅ Lägger till sensorer (list_id: %s, name: %s)", list_id, list_name)

    async_add_entities([
        ShoppingListSensor(hass, api, list_id, list_name),
        ICALastPurchaseSensor(hass, api, list_id, list_name)
    ], False)

class ShoppingListSensor(SensorEntity):
    def __init__(self, hass, api, list_id, list_name):
        self.hass = hass
        self._api = api
        self._list_id = list_id
        self._list_name = list_name

        self._attr_unique_id = f"shoppinglist_{self._list_id}"  # 👈 Detta är nyckeln
        self._attr_name = "Shoppinglist"
        self._attr_native_unit_of_measurement = "items"
        self._attr_has_entity_name = True
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._list_id)},
            "name": f"ICA – {self._list_name}",
            "manufacturer": "ICA",
        }
        _LOGGER.debug("✅ Uppdatering klar för %s", self._attr_name)

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
            try:
                the_list = await asyncio.wait_for(self._api.get_list_by_id(self._list_id), timeout=10)
                _LOGGER.debug("📋 Innehåll från get_list_by_id: %s", the_list)
            except asyncio.TimeoutError:
                _LOGGER.error("⏱️ Timeout vid hämtning av ICA-lista %s.", self._list_id)
                return

            if the_list is None:
                _LOGGER.warning("❌ Kunde inte hitta lista med ID %s", self._list_id)
                return

            self._update_state(the_list)
            _LOGGER.debug("✅ Uppdatering klar för %s", self._attr_name)

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
        _LOGGER.warning("🚨 async_update körs för %s", self._attr_name)

        try:
            try:
                token = await asyncio.wait_for(self._api._get_token_from_session_id(), timeout=10)
            except asyncio.TimeoutError:
                _LOGGER.error("⏱️ Timeout vid hämtning av token.")
                return
            except Exception as e:
                _LOGGER.error("💥 Fel vid tokenhämtning: %s", e)
                return
            _LOGGER.debug("🧪 Token: %s", token)
            _LOGGER.debug("🧪 Session-ID: %s", self._api.session_id)
            
            if not token:
                return

            # 🛠️ Här börjar det nya try-blocket
            try:
                now = datetime.now()
                url = f"https://www.ica.se/api/cpa/purchases/historical/me/byyearmonth/{now.strftime('%Y-%m')}"

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Cookie": f"thSessionId={self._api.session_id}"
                }
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=10) as resp:
                        if resp.status == 403:
                            _LOGGER.warning("❌ Åtkomst nekad (403) vid hämtning av köphistorik – ignorerar.")
                            return
                        elif resp.status != 200:
                            _LOGGER.error("❌ Ovänntat fel (%s) vid hämtning av köphistorik", resp.status)
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

        except Exception as e:
            _LOGGER.error("🔥 Ovänterat fel i async_update: %s", e)