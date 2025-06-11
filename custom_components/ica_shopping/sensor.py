import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, DATA_ICA

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=60)

async def async_setup_entry(hass, entry, async_add_entities):
    api = hass.data[DOMAIN][DATA_ICA]
    list_id = entry.options.get("ica_list_id", entry.data["ica_list_id"])

    lists = await api.fetch_lists()
    the_list = next((l for l in lists if l.get("id") == list_id), None)
    if the_list:
        async_add_entities([ShoppingListSensor(hass, api, the_list)], True)
    else:
        _LOGGER.warning("❌ Ingen lista med ID %s hittades vid sensor-setup", list_id)

class ShoppingListSensor(SensorEntity):
    def __init__(self, hass, api, data):
        self.hass = hass
        self._api = api
        self._list = data
        self._list_id = data.get("id")

        self._attr_unique_id = f"ica_shopping_{self._list_id}"
        self._attr_name = f"ICA Lista – {data.get('name')}"
        self._attr_native_unit_of_measurement = "items"
        self._attr_has_entity_name = True

        self._update_state(data)

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._list_id)},
            "name": f"ICA Lista – {data.get('name')}",
            "manufacturer": "ICA",
        }

    def _update_state(self, data):
        items = data.get("items", [])
        self._attr_native_value = len(items)
        self._attr_extra_state_attributes = {
            "items": [item["text"] for item in items],
            "list_name": data.get("name", "")
        }

    async def async_update(self):
        lists = await self._api.fetch_lists()
        for lst in lists:
            if lst.get("id") == self._list_id:
                self._list = lst
                self._update_state(lst)
                break
