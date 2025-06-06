import requests
import yaml
import logging
from homeassistant.exceptions import HomeAssistantError
from .const import API_LIST_ALL, API_ADD_ROW, API_REMOVE_ROW

_LOGGER = logging.getLogger(__name__)

class ICAApi:
    def __init__(self, hass, username: str, password: str):
        self.hass = hass
        self.session = requests.Session()

    def _get_token_from_secrets(self):
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
            "items": data
        }]

    def add_item(self, list_id: str, text: str) -> dict:
        headers = self.get_headers()
        url = API_ADD_ROW.format(list_id=list_id)
        payload = {
            "text": text,
            "strikedOver": False,
            "source": "HomeAssistant",
        }
        resp = self.session.post(url, headers=headers, json=payload)
        _LOGGER.debug("Add item response: %s", resp.text)
        resp.raise_for_status()
        return resp.json()

    def remove_item(self, list_id: str, row_id: str) -> None:
        headers = self.get_headers()
        url = API_REMOVE_ROW.format(list_id=list_id, row_id=row_id)
        resp = self.session.delete(url, headers=headers)
        _LOGGER.debug("Remove item response: %s", resp.text)
        resp.raise_for_status()
        return
