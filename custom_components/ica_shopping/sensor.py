import logging

_LOGGER = logging.getLogger(__name__)


from datetime import timedelta
from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN, DATA_ICA

SCAN_INTERVAL = timedelta(minutes=60)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up ICA Shopping List sensors."""
    api = hass.data[DOMAIN][DATA_ICA]
    lists = await api.async_fetch_lists()  # ✅ Använd async-funktionen
    _LOGGER.debug("Fetched %d shopping lists: %s", len(lists), lists)
    entities = [ShoppingListSensor(api, lst) for lst in lists]
    async_add_entities(entities, True)

class ShoppingListSensor(SensorEntity):
    """Represents an ICA shopping list in Home Assistant."""

    def __init__(self, api, data):
        self._api = api
        self._list = data
        self._attr_name = data.get("name")
        self._attr_unique_id = data.get("id")
        self._attr_extra_state_attributes = {
            "items": [item["text"] for item in data.get("items", [])]
        }

    @property
    def state(self):
        """Return number of items in the list."""
        return len(self._list.get("items", []))

    @property
    def attribution(self):
        return "Data provided by ICA"

    async def async_update(self):
        """Update sensor data."""
        lists = await self._api.async_fetch_lists()
        _LOGGER.debug("Updating list %s", self._list.get("id"))
        for lst in lists:
            if lst.get("id") == self._list.get("id"):
                self._list = lst
                self._attr_extra_state_attributes["items"] = [
                    item["text"] for item in lst.get("items", [])
                ]
                _LOGGER.debug("Updated list %s with %d items", lst.get("name"), len(lst.get("items", [])))
                break
