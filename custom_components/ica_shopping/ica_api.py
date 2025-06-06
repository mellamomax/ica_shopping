import requests
import yaml
import logging
from datetime import datetime
from homeassistant.exceptions import HomeAssistantError
from .const import API_LIST_ALL

_LOGGER = logging.getLogger(__name__)

class ICAApi:
    def __init__(self, hass, username: str, password: str):
        self.hass = hass
        self.session = requests.Session()

    def _get_token_from_secrets(self):
        """Hämtar bearer token från secrets.yaml."""
        try:
            path = self.hass.config.path("secrets.yaml")
            with open(path, "r") as f:
                secrets = yaml.safe_load(f)
            token = secrets.get("ica_access_token")
            if not token:
                raise HomeAssistantError("Access token saknas i secrets.yaml")
            return token
        except Exception as e:
            _LOGGER.error("Misslyckades läsa access token: %s", e)
            raise HomeAssistantError("Kunde inte läsa ICA access token")

    def get_headers(self) -> dict:
        token = self._get_token_from_secrets()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def fetch_lists(self) -> list:
        """Hämtar shoppinglistor från ICA."""
        headers = self.get_headers()
        try:
            resp = self.session.get(API_LIST_ALL, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            _LOGGER.error("Fel vid hämtning av listor: %s", e)
            return []
        except Exception:
            _LOGGER.error("Ogiltigt JSON-svar från ICA: %s", resp.text)
            return []
