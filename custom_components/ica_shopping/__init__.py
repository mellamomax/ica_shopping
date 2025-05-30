import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.discovery import async_load_platform

from .const import DOMAIN, DATA_ICA, COOKIE_CACHE_FILE
from .ica_api import ICAApi

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass, config):
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]

    api = ICAApi(hass, username, password)
    await api.async_initialize()

    # Spara API-instansen så sensorer och service kan använda den
    hass.data[DOMAIN] = {DATA_ICA: api}

    # Ladda sensor-plattformen
    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    # Registrera tjänst för att lägga till vara
    def handle_add_item(call):
        list_id = call.data["list_id"]
        text = call.data["text"]
        api.add_item(list_id, text)

    hass.services.async_register(
        DOMAIN,
        "add_item",
        handle_add_item,
        schema=vol.Schema(
            {vol.Required("list_id"): cv.string, vol.Required("text"): cv.string}
        ),
    )

    return True
