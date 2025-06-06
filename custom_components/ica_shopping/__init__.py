import logging
import voluptuous as vol
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN, DATA_ICA
from .ica_api import ICAApi

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Set up ICA Shopping integration."""
    _LOGGER.debug("Setting up ICA Shopping...")
    conf = config.get(DOMAIN)
    if not conf:
        _LOGGER.warning("ICA config not found")
        return True

    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]

    api = ICAApi(hass, username, password)
    hass.data.setdefault(DOMAIN, {})[DATA_ICA] = api

    def handle_refresh(call):
        """Manuell uppdatering av shoppinglista via tjänst."""
        _LOGGER.debug("ICA refresh triggered")

        try:
            lists = api.fetch_lists()
            _LOGGER.debug("Fetched shopping lists: %s", lists)

            if not lists:
                _LOGGER.warning("No shopping lists found")
                return

            for lst in lists:
                if "rows" not in lst:
                    _LOGGER.warning("List saknar 'rows': %s", lst)
                    continue

                list_id = lst.get("id")
                safe_id = list_id.replace("-", "_").lower()
                entity_id = f"sensor.ica_shopping_{safe_id}"

                rows = lst.get("rows", [])
                items = [row["text"] for row in rows if isinstance(row, dict) and "text" in row]

                hass.states.async_set(entity_id, len(items), {
                    "items": items,
                    "items_string": ", ".join(items),
                    "list_name": lst.get("name", "ICA Lista"),
                    "updated_manually": True
                })

                _LOGGER.info("Updated sensor: %s (%s)", lst.get("name", "Unnamed"), entity_id)

        except Exception as e:
            _LOGGER.error("ICA refresh failed: %s", e)

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)
    return True
