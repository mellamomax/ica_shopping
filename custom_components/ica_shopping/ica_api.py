import requests
import yaml
import logging
from datetime import datetime, timedelta
from .const import API_LIST_ALL, API_ADD_ROW

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
            return secrets.get("ica_access_token")
        except Exception as e:
            _LOGGER.error("Failed to read access token from secrets.yaml: %s", e)
            return None

    def get_headers(self) -> dict:
        token = self._get_token_from_secrets()
        if not token:
            raise Exception("No access token found in secrets.yaml")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def fetch_lists(self) -> list:
        headers = self.get_headers()
        resp = self.session.get(API_LIST_ALL, headers=headers)
        _LOGGER.debug("Shoppinglist response: %s", resp.text)
        resp.raise_for_status()
        return resp.json()

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
