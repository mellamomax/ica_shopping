import requests
from datetime import datetime
from homeassistant.helpers import storage

from .const import (
    API_USER_INFO,
    API_LIST_ALL,
    API_ADD_ROW,
    COOKIE_CACHE_FILE,
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
        # Flytta Store-initialisering in hit
        self._cookie_store = storage.Store(self.hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_initialize(self):
        """Läs cookies från storage eller skapa nya."""
        data = await self._cookie_store.async_load()
        if data and data.get("cookies"):
            self.session.cookies.update(data["cookies"])
        else:
            await self._async_store_cookies()

    async def _async_store_cookies(self):
        """Placeholder för login (t.ex. Puppeteer) och spara cookies."""
        # TODO: Här fyller du på self.session.cookies genom inloggning
        cookies = self.session.cookies.get_dict()
        await self._cookie_store.async_save({"cookies": cookies})

    def _ensure_token(self):
        """Hämta nytt accessToken om det saknas eller har gått ut."""
        if self._token and datetime.utcnow() < self._expires:
            return

        resp = self.session.get(API_USER_INFO)
        data = resp.json()
        self._token = data["accessToken"]
        exp = data["tokenExpires"]
        # Konvertera ISO-tid och ta bort Z
        self._expires = datetime.fromisoformat(exp.replace("Z", ""))

    def get_headers(self) -> dict:
        """Returnera headers med giltig bearer-token."""
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def fetch_lists(self) -> list:
        """Hämta alla shoppinglistor."""
        headers = self.get_headers()
        resp = self.session.get(API_LIST_ALL, headers=headers)
        return resp.json()

    def add_item(self, list_id: str, text: str) -> dict:
        """Lägg till en rad i en specifik inköpslista."""
        headers = self.get_headers()
        url = API_ADD_ROW.format(list_id=list_id)
        payload = {
            "text": text,
            "strikedOver": False,
            "source": "HomeAssistant",
        }
        resp = self.session.post(url, headers=headers, json=payload)
        return resp.json()
