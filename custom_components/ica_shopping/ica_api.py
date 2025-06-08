import logging
import yaml
import aiohttp
import aiofiles
from .const import API_LIST_ALL, API_ADD_ROW, API_REMOVE_ROW

_LOGGER = logging.getLogger(__name__)

class ICAApi:
    def __init__(self, hass, username, password):
        self.hass = hass
        self.username = username
        self.password = password

    async def _get_token_from_secrets_async(self):
        path = self.hass.config.path("secrets.yaml")
        try:
            async with aiofiles.open(path, "r") as f:
                raw = await f.read()
                secrets = yaml.safe_load(raw)
            token = secrets.get("ica_token")
            if not token:
                _LOGGER.error("❗ Ingen ica_token hittades i secrets.yaml")
            return token
        except Exception as e:
            _LOGGER.error("❗ Kunde inte läsa secrets.yaml: %s", e)
            return None

    async def fetch_lists(self):
        token = await self._get_token_from_secrets_async()
        if not token:
            _LOGGER.error("❌ Avbryter fetch_lists - token saknas")
            return []

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_LIST_ALL, headers=headers) as resp:
                    _LOGGER.debug("📡 ICA API status: %s", resp.status)
                    if resp.status != 200:
                        _LOGGER.error("❗ ICA API error: %s", resp.status)
                        return []

                    result = await resp.json()
                    _LOGGER.debug("📦 ICA API raw response: %s", result)

                    # Returnera rätt beroende på format
                    if isinstance(result, dict) and "items" in result:
                        return result["items"]
                    elif isinstance(result, list):
                        return result
                    else:
                        _LOGGER.error("❗ Oväntat format på ICA-response: %s", type(result))
                        return []
        except Exception as e:
            _LOGGER.error("❗ Fel vid hämtning av ICA-listor: %s", e)
            return []

    async def add_item(self, list_id: str, item: str):
        token = await self._get_token_from_secrets_async()
        if not token:
            return False

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        data = {"text": item}
        url = API_ADD_ROW.format(list_id=list_id)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    _LOGGER.debug("➕ Lägg till '%s' till ICA (%s): %s", item, list_id, resp.status)
                    return resp.status == 200
        except Exception as e:
            _LOGGER.error("❗ Error adding item to ICA: %s", e)
            return False

    async def remove_item(self, list_id: str, row_id: str):
        token = await self._get_token_from_secrets_async()
        if not token:
            return False

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        url = API_REMOVE_ROW.format(list_id=list_id, row_id=row_id)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers) as resp:
                    _LOGGER.debug("🗑️ Ta bort rad '%s' från ICA (%s): %s", row_id, list_id, resp.status)
                    return resp.status == 200
        except Exception as e:
            _LOGGER.error("❗ Error removing item from ICA: %s", e)
            return False
            
    async def add_to_list(self, text: str):
        token = await self._get_token_from_secrets_async()
        if not token:
            _LOGGER.error("❌ Saknar token – kan inte lägga till i ICA")
            return False

        list_id = "55c428d8-8b05-48a7-b2a2-f84e0d91d155"  # Gärna lyft till konstant
        url = f"https://handla.api.ica.se/api/graphql/lists/{list_id}/items"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        payload = {
            "rows": [{"text": text}]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    _LOGGER.debug("➕ Försöker lägga till '%s' i ICA (%s)", text, resp.status)
                    if resp.status == 200:
                        _LOGGER.info("✅ Lade till '%s' i ICA-listan", text)
                        return True
                    else:
                        body = await resp.text()
                        _LOGGER.warning("❗ Kunde inte lägga till i ICA (%s): %s", resp.status, body)
                        return False
        except Exception as e:
            _LOGGER.error("❗ Fel vid add_to_list('%s'): %s", text, e)
            return False