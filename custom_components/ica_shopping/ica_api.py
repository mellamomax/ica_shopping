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
        headers = self.get_headers()
        resp = self.session.get(API_LIST_ALL, headers=headers)
        _LOGGER.debug("Shoppinglist response: %s", resp.text)
        resp.raise_for_status()
        data = resp.json()

        # Om ICA bara har en lista (vanligt), packa den i ett list-objekt
        return [{
            "id": "main",
            "items": data  # ← Hela listan är items
        }]

