from homeassistant.components.sensor import SensorEntity
from homeassistant.const import ATTR_ATTRIBUTION
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .ica_api import ICAApi

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = ICAApi(
        hass,
        config_entry.data[CONF_USERNAME],
        config_entry.data[CONF_PASSWORD]
    )
    await api.async_initialize()
    lists = api.fetch_lists()
    entities = [ShoppingListSensor(api, lst) for lst in lists]
    async_add_entities(entities, True)

class ShoppingListSensor(SensorEntity):
    def __init__(self, api: ICAApi, data: dict):
        self._api = api
        self._list = data
        self._attr_name = data.get("name")
        self._attr_unique_id = data.get("id")
        self._attr_extra_state_attributes = {
            "items": data.get("items", [])
        }

    @property
    def state(self):
        return len(self._list.get("items", []))

    @property
    def attribution(self):
        return "Data provided by ICA"

    async def async_update(self):
        lists = self._api.fetch_lists()
        for lst in lists:
            if lst.get("id") == self._attr_unique_id:
                self._list = lst
                self._attr_extra_state_attributes["items"] = lst.get("items", [])
                break
