import logging
import yaml
import aiohttp
import aiofiles
from .const import API_LIST_ALL, API_ADD_ROW, API_REMOVE_ROW

_LOGGER = logging.getLogger(__name__)

class ICAApi:
    def __init__(self, hass, session_id):
        self.hass = hass
        self.session_id = session_id
        _LOGGER.warning("🧾 ICAApi init med session_id: %s", self.session_id)  # 👈 Lägg till denna rad

            
    async def _get_token_from_session_id(self):
        headers = {
            "Cookie": f"thSessionId={self.session_id}",
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
                    _LOGGER.warning("🔑 Token hämtad från session: %s", token)  # <- korrekt plats
                    return token
        except Exception as e:
            _LOGGER.error("❗ Fel vid hämtning av accessToken: %s", e)
            return None



    async def fetch_lists(self):
        token = await self._get_token_from_session_id()
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

    async def get_list_name(self, list_id: str) -> str:
        lists = await self.fetch_lists()
        for lst in lists:
            if lst.get("id") == list_id:
                return lst.get("name", f"Lista {list_id}")
        return f"Lista {list_id}"  # fallback

    async def get_list_by_id(self, list_id: str):
        lists = await self.fetch_lists()
        for lst in lists:
            if lst.get("id") == list_id:
                return lst
        return None


    async def add_item(self, list_id: str, item: str):
        token = await self._get_token_from_session_id()
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

    async def remove_item(self, row_id: str) -> bool:
        token = await self._get_token_from_session_id()
        if not token:
            _LOGGER.error("❌ Kan inte radera – token saknas")
            return False

        url = f"https://apimgw-pub.ica.se/sverige/digx/shopping-list/v1/api/row/{row_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "*/*"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers) as resp:
                    if resp.status in (200, 204):
                        _LOGGER.info("🗑️ Tog bort rad %s från ICA", row_id)
                        return True
                    else:
                        _LOGGER.warning("❗ Misslyckades ta bort rad %s – status %s", row_id, resp.status)
                        return False
        except Exception as e:
            _LOGGER.error("❗ Fel vid borttagning av ICA-rad: %s", e)
            return False

            
    async def add_to_list(self, list_id: str, text: str):
        token = await self._get_token_from_session_id()
        if not token:
            _LOGGER.error("❌ Saknar token – kan inte lägga till i ICA")
            return False

        url = f"https://apimgw-pub.ica.se/sverige/digx/shopping-list/v1/api/list/{list_id}/row"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        payload = {
          "text": text}


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