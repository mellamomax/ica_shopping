import logging
import yaml
import aiohttp
import aiofiles
import time
from .const import API_LIST_ALL, API_ADD_ROW, API_REMOVE_ROW

_LOGGER = logging.getLogger(__name__)

class ICAApi:
    def __init__(self, hass, session_id):
        self.hass = hass
        self.session_id = session_id
        self._token = None
        self._token_timestamp = 0       
               
               

    
    async def _get_token_from_session_id(self, session_id: str):
        # Återanvänd token i upp till 10 minuter (600 sekunder)
        if self._token and (time.time() - self._token_timestamp) < 200:
            return self._token
        headers = {
            "Cookie": f"thSessionId={session_id}",
            "Accept": "application/json"
        }
        url = "https://www.ica.se/api/user/information"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error("❗ Misslyckades att hämta accessToken (%s)", resp.status)
                        return None
                    data = await resp.json()
                    token = data.get("accessToken")
                    _LOGGER.warning("🔑 Ny token hämtad: %s", token)
                    self._token = token
                    self._token_timestamp = time.time()
                    return token
        except Exception as e:
            _LOGGER.error("❗ Fel vid hämtning av accessToken: %s", e)
            return None



    async def fetch_lists(self):
        token = await self._get_token_from_session_id(self.session_id)
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
        token = await self._get_token_from_session_id(self.session_id)
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
        token = await self._get_token_from_session_id(self.session_id)
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
            
