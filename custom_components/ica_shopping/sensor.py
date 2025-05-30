from datetime import timedelta
from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN, DATA_ICA

# Polla API:et var 10:e minut
SCAN_INTERVAL = timedelta(minutes=60)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up ICA Shopping List sensors via YAML."""
    api = hass.data[DOMAIN][DATA_ICA]
    lists = api.fetch_lists()
    entities = [ShoppingListSensor(api, lst) for lst in lists]
    async_add_entities(entities, True)

class ShoppingListSensor(SensorEntity):
    """Represents en ICA-inköpslista i Home Assistant."""

    def __init__(self, api, data):
        self._api = api
        self._list = data
        self._attr_name = data.get("name")
        self._attr_unique_id = data.get("id")
        self._attr_extra_state_attributes = {
            "items": data.get("items", [])
        }

    @property
    def state(self):
        """Antal varor i listan."""
        return len(self._list.get("items", []))

    @property
    def attribution(self):
        return "Data provided by ICA"

    def update(self):
        """Körs enligt SCAN_INTERVAL för att uppdatera listan."""
        lists = self._api.fetch_lists()
        for lst in lists:
            if lst.get("id") == self._list.get("id"):
                self._list = lst
                self._attr_extra_state_attributes["items"] = lst.get("items", [])
                break
