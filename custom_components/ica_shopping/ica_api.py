import requests
from datetime import datetime
from homeassistant.helpers import storage

from .const import (
    API_USER_INFO,
    API_LIST_ALL,
    API_ADD_ROW,
)

STORAGE_KEY = "ica_cookie_cache"
STORAGE_VERSION = 1


class ICAApi:
    def __init__(self, hass, username: str, password: str):
        self.hass = hass
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._token = None
        self._expires = None
        self._cookie_store = storage.Store(self.hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_initialize(self):
        """Ladda cookies från storage eller initiera ny inloggning."""
        data = await self._cookie_store.async_load()
        if data and data.get("cookies"):
            self.session.cookies.update(data["cookies"])
        else:
            await self._async_store_cookies()

    async def _async_store_cookies(self):
        """Här ska du logga in och spara cookies – placeholder."""
        # TODO: Implementera faktisk login med form-post eller Puppeteer
        cookies = self.session.cookies.get_dict()
        await self._cookie_store.async_save({"cookies": cookies})

    def _ensure_token(self):
        """Säkerställ giltigt access-token."""
        if self._token and datetime.utcnow() < self._expires:
            return

        resp = self.session.get(API_USER_INFO)
        resp.raise_for_status()
        data = resp.json()

        self._token = data["accessToken"]
        exp = data["tokenExpires"]
        self._expires = datetime.fromisoformat(exp.replace("Z", ""))

    def get_headers(self) -> dict:
        """Returnera headers med giltigt access-token."""
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def fetch_lists(self) -> list:
        """Synkront anrop för att hämta alla inköpslistor."""
        headers = self.get_headers()
        resp = self.session.get(API_LIST_ALL, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def async_fetch_lists(self) -> list:
        """Async wrapper för att hämta listor utan att blockera HA."""
        return await self.hass.async_add_executor_job(self.fetch_lists)

    def add_item(self, list_id: str, text: str) -> dict:
        """Lägg till en vara i en specifik lista."""
        headers = self.get_headers()
        url = API_ADD_ROW.format(list_id=list_id)
        payload = {
            "text": text,
            "strikedOver": False,
            "source": "HomeAssistant",
        }
        resp = self.session.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()
