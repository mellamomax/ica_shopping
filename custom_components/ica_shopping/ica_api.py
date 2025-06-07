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
            return secrets.get("ica_token")
        except Exception as e:
            _LOGGER.error("Failed to read secrets.yaml: %s", e)
            return None

    async def fetch_lists(self):
        token = await self._get_token_from_secrets_async()
        if not token:
            return []

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_LIST_ALL, headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error("ICA API error: %s", resp.status)
                        return []

                    result = await resp.json()
                    _LOGGER.debug("📦 ICA API raw response: %s", result)

                    # Om svaret är en dict med 'items' – returnera listan direkt
                    if isinstance(result, dict) and "items" in result:
                        return result["items"]

                    # Om svaret redan är en lista – returnera som är
                    if isinstance(result, list):
                        return result

                    _LOGGER.error("❗ Oväntat format på ICA-response: %s", type(result))
                    return []

        except Exception as e:
            _LOGGER.error("Failed to fetch ICA list: %s", e)
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
                    if resp.status != 200:
                        _LOGGER.error("Failed to add item to ICA: %s", resp.status)
                        return False
                    return True
        except Exception as e:
            _LOGGER.error("Error adding item to ICA: %s", e)
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
                    if resp.status != 200:
                        _LOGGER.error("Failed to remove item from ICA: %s", resp.status)
                        return False
                    return True
        except Exception as e:
            _LOGGER.error("Error removing item from ICA: %s", e)
            return False
