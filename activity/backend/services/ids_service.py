"""IDs.moe API service for anime ID conversions.

Uses the IDs.moe API to convert between different anime database IDs:
- MyAnimeList (MAL)
- Shikimori
- AniList
- AniDB

Requires API key from https://ids.moe (sign in to get your key)
"""

import logging
import aiohttp
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class IDsService:
    """Service for anime ID conversions using IDs.moe API."""
    
    BASE_URL = "https://api.ids.moe/ids"
    
    def __init__(self):
        self._api_key: Optional[str] = None
    
    def set_api_key(self, api_key: str):
        """Set the IDs.moe API key."""
        self._api_key = api_key
        logger.info("✅ IDs.moe API key configured")
    
    async def get_shikimori_id(self, mal_id: int) -> Optional[int]:
        """Convert MAL ID to Shikimori ID using IDs.moe API.
        
        Args:
            mal_id: MyAnimeList anime ID
            
        Returns:
            Shikimori ID or None if not found
        """
        logger.info(f"🔍 Looking up Shikimori ID for MAL ID {mal_id} (API key present: {bool(self._api_key)})")
        
        if not self._api_key:
            logger.error("❌ IDs.moe API key not configured - cannot fetch Shikimori ID")
            return None
        
        try:
            url = f"{self.BASE_URL}/{mal_id}?platform=mal"
            headers = {
                "Authorization": f"Bearer {self._api_key}"
            }
            
            logger.info(f"📡 Requesting: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_text = await response.text()
                    
                    if response.status == 404:
                        logger.warning(f"⚠️ No mapping found for MAL ID {mal_id} on IDs.moe")
                        logger.info(f"   Response: {response_text[:200]}")
                        return None
                    
                    if response.status == 401:
                        logger.error(f"❌ IDs.moe API authentication failed - check API key")
                        logger.error(f"   Response: {response_text[:200]}")
                        return None
                    
                    if response.status != 200:
                        logger.error(f"❌ IDs.moe API error for MAL ID {mal_id}: HTTP {response.status}")
                        logger.error(f"   Response: {response_text[:200]}")
                        return None
                    
                    data = await response.json()
                    logger.info(f"📊 IDs.moe raw response for MAL {mal_id}: {data}")
                    
                    # Extract Shikimori ID
                    shikimori_id = (data.get("shikimori") or 
                                   data.get("shikimori_id"))
                    
                    if not shikimori_id:
                        logger.warning(f"⚠️ IDs.moe response for MAL ID {mal_id} has no Shikimori ID")
                        return None
                    
                    return int(shikimori_id)
                    
        except aiohttp.ClientError as e:
            logger.error(f"❌ Network error fetching Shikimori ID for MAL ID {mal_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching Shikimori ID for MAL ID {mal_id}: {e}")
            return None


# Global instance
ids_service = IDsService()
