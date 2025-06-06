import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN, DATA_ICA

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=60)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up ICA Shopping List sensors."""
    api = hass.data[DOMAIN][DATA_ICA]

    lists = await hass.async_add_executor_job(api.fetch_lists)
    _LOGGER.debug("Fetched %d shopping lists: %s", len(lists), lists)
    entities = [ShoppingListSensor(hass, api, lst) for lst in lists]
    async_add_entities(entities, True)

class ShoppingListSensor(SensorEntity):
    """Represents an ICA shopping list in Home Assistant."""

    def __init__(self, hass, api, data):
        self.hass = hass
        self._api = api
        self._list = data
        self._attr_name = data.get("name")
        self._attr_unique_id = f"ica_shopping_{data.get('id')}"
        self._attr_extra_state_attributes = {
            "items": [item["text"] for item in data.get("items", [])],
            "list_name": self._attr_name
        }

    @property
    def state(self):
        return len(self._list.get("items", []))

    async def async_update(self):
        lists = await self.hass.async_add_executor_job(self._api.fetch_lists)
        for lst in lists:
            if lst.get("id") == self._list.get("id"):
                self._list = lst
                self._attr_extra_state_attributes["items"] = [
                    item["text"] for item in lst.get("items", [])
                ]
                break
