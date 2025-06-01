import requests
from datetime import datetime
from homeassistant.helpers import storage
import logging

from .const import API_USER_INFO, API_LIST_ALL, API_ADD_ROW

_LOGGER = logging.getLogger(__name__)

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
        """Ladda cookies från storage eller använd hårdkodade."""
        data = await self._cookie_store.async_load()
        if data and data.get("cookies"):
            self.session.cookies.update(data["cookies"])
            _LOGGER.debug("ICA cookies loaded from storage.")
        else:
            _LOGGER.warning("ICA cookies not found, using hardcoded fallback.")
            await self._async_store_cookies()

    async def _async_store_cookies(self):
        """Sätt hårdkodade ICA-webbcookies manuellt."""
        self.session.cookies.set("icase11", "CfDJ8N89z50GUBlCvsQoxy3YTEuO4o-8OxdcbPAW9ni1Pz5lF0gZCikYeAuKIvCmEeVjXf1njkppxp0NnUJ9hApxLVNGZVYQhcgdNLe_KUfLo9flEAPGoa_Qfulu-xCVXO5GpeDH9mEL6uOSZV38218zVII0Qt2yFEI7nJok3B0UqwaYaaQhiIriS3oI2JqZEpyRB7xAAvpTcgWiPP2kPHsI61mVYGk2c_ntLvtp0fJnZLS5EYhDHex1IsC1k2Zk7Ov9DA8yj6ohc1SwO6Zzbyvys5T8LXtdpsDKuuU4RLPS2xUIaXE-neD8KMNgjnCsi51QbvYhRXOgC0KrlRw1IpS84zhWcrypUi16e5B_OZW5kvnPMSoxDFO-yzdI43zpX9YPGkrwmdNeOYiPvBomWkbgc6fC5SlDL4xUODU-sQBBX5GEs0NwkPmjXyp-fLRMiQQmlm1DAc1oQ0r_KYmUhmnCb8kA7-K_RZyQZ6FhhUOytazQh-H1ay-UM8QGjZwlOw9P_w-TAT5FhpkBE4gIYzzWdbIY0Sdep1Xyr2-6TeQ-bgc1VriYjoxlM5iM4h_aR7qlTyUNSPYVxsSxg4D9taggrcedRUL1p-Cp779rLKb1Fk7we8GTbnb5y5bRc2I020rP9_64QYh7Y5KIetKIJSP6SVgGEp4bulVwo5mw2eWdLtICUVoDASIIlOBKZiz6Zoq9cJeTnXErEglDdjIEIw9d5r52xRTN0kVQfWKB3b3D9hG8i62mG16GHSCUQ9_DNcYvHq1r4f_Dz2CF-4MBemVTtQbqUYbkTx_qZmoLMDG0msr6Ab6saJvn4wHGK6m3csPWYBTNjz_-6zLLFu5UgffmwzrK-YLchMT8dupmkKsL9-l7T7nb88mAw6QeBHN_fgFFvAnNBltb-FQxtZqWagVGlKPMKMuaogJDs6XtW_ZL3TrWTySxNpabX2NNkNA5RCVC-HfGBFYLvSwxADE2-QeTEVnsLAjPzO2agTM-YUpXCtuTnutj9cL3JaK3OuBO6XZ13vEClcY06vKByHxFsV8-QRSRGON7RC4XFCBKju2OPOlCot8_iJ7i2LSCZPmdBnozLw", domain=".ica.se")
        self.session.cookies.set("TS0154f30f", "01f0ddaba314ed6025df396247bb0e708fab07687c203f42a8d10253cc44916d0783431e20442e1cac5d03938f00108459574980e1", domain=".ica.se")
        self.session.cookies.set("cookieConsent", "f9de53a2-e2c3-4c9a-84b7-13eaac1282e6", domain=".ica.se")
        self.session.cookies.set("cookieConsentToken", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmOWRlNTNhMi1lMmMzLTRjOWEtODRiNy0xM2VhYWMxMjgyZTYiLCJleHAiOjE3NDkxNjg0NjZ9.LYRZbl4_JjRFgc3ru7oQhn-uRaXUnSvBPLhEf-FJWCk", domain=".ica.se")

        await self._cookie_store.async_save({
            "cookies": self.session.cookies.get_dict()
        })
        _LOGGER.info("Hardcoded cookies saved to storage.")

    def _ensure_token(self):
        """Hämta nytt accessToken från ICA-webben."""
        if self._token and datetime.utcnow() < self._expires:
            return

        resp = self.session.get(API_USER_INFO)
        _LOGGER.debug("user/info response: %s", resp.text)
        resp.raise_for_status()
        data = resp.json()

        self._token = data["accessToken"]
        self._expires = datetime.fromisoformat(data["tokenExpires"].replace("Z", ""))
        _LOGGER.debug("New token valid until: %s", self._expires)

    def get_headers(self) -> dict:
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self._token}",
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
