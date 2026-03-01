"""Shikimori API service for fetching anime screenshots."""

import asyncio
import time
from typing import Dict, List, Optional, Any
import aiohttp


class ShikimoriService:
    """Service for interacting with Shikimori GraphQL API."""
    
    def __init__(self):
        self.base_url = "https://shikimori.one/api/graphql"
        self.request_timestamps: List[float] = []
        self.last_request_time = 0
    
    async def _rate_limit_check(self):
        """Ensure we don't exceed Shikimori rate limits (5 RPS, 90 RPM)."""
        current_time = time.time()
        
        # Clean old timestamps (older than 1 minute)
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if current_time - ts < 60
        ]
        
        # Check RPM limit (90 requests per minute)
        if len(self.request_timestamps) >= 90:
            sleep_time = 60 - (current_time - self.request_timestamps[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Check RPS limit (5 requests per second)
        if current_time - self.last_request_time < 0.2:
            await asyncio.sleep(0.2 - (current_time - self.last_request_time))
        
        self.last_request_time = time.time()
        self.request_timestamps.append(self.last_request_time)
    
    async def _query(
        self, 
        query: str, 
        variables: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute a GraphQL query against Shikimori API."""
        await self._rate_limit_check()
        
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Geminya Discord Activity"
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "errors" in data:
                            return None
                        return data.get("data")
                    else:
                        return None
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None
    
    async def get_anime_screenshots(self, shikimori_id: int, min_screenshots: int = 4) -> List[Dict[str, str]]:
        """Get screenshots for a specific anime by Shikimori ID.
        
        Args:
            shikimori_id: Shikimori anime ID
            min_screenshots: Minimum number of screenshots required
            
        Returns:
            List of screenshot dicts with 'original', 'medium', 'small' URLs
        """
        query = """
        query GetAnimeScreenshots($ids: String!) {
          animes(ids: $ids) {
            id
            screenshots {
              id
              originalUrl
              x332Url
              x166Url
            }
          }
        }
        """
        
        variables = {"ids": str(shikimori_id)}
        
        data = await self._query(query, variables)
        if not data or not data.get("animes"):
            return []
        
        animes = data.get("animes", [])
        if not animes:
            return []
        
        anime = animes[0]
        screenshots = anime.get("screenshots", [])
        
        if len(screenshots) < min_screenshots:
            return []
        
        return self._extract_screenshots(screenshots)
    
    async def get_random_anime_with_screenshots(
        self, 
        difficulty: str = "normal",
        min_screenshots: int = 4
    ) -> Optional[Dict[str, Any]]:
        """Fetch a random anime with sufficient screenshots for the game."""
        
        # Define difficulty score filters
        difficulty_scores = {
            "easy": 8,
            "normal": 6,
            "hard": 4,
            "expert": 3,
            "crazy": 2,
            "insanity": 1
        }
        min_score = difficulty_scores.get(difficulty, 6)
        
        query = """
        query GetAnimeWithScreenshots($limit: PositiveInt!, $score: Int) {
          animes(limit: $limit, score: $score, order: random) {
            id
            malId
            name
            english
            russian
            synonyms
            score
            episodes
            kind
            status
            airedOn { year }
            genres { name }
            studios { name }
            franchise
            poster { originalUrl mainUrl }
            screenshots {
              id
              originalUrl
              x332Url
              x166Url
            }
          }
        }
        """
        
        # Try multiple times to find anime with enough screenshots
        for _ in range(5):
            variables = {"limit": 20, "score": min_score}
            
            data = await self._query(query, variables)
            if not data or not data.get("animes"):
                continue
            
            # Filter anime with sufficient screenshots
            suitable_anime = []
            for anime in data["animes"]:
                screenshots = anime.get("screenshots", [])
                if len(screenshots) >= min_screenshots:
                    suitable_anime.append(anime)
            
            if suitable_anime:
                import random
                return random.choice(suitable_anime)
        
        return None
    
    async def search_anime(self, search_term: str, limit: int = 25) -> List[Dict[str, str]]:
        """Search for anime names for autocomplete."""
        if not search_term or len(search_term.strip()) < 2:
            return []
        
        query = """
        query SearchAnime($search: String!, $limit: PositiveInt!) {
          animes(search: $search, limit: $limit) {
            name
            english
            russian
            synonyms
            airedOn { year }
          }
        }
        """
        
        variables = {"search": search_term.strip(), "limit": limit}
        
        data = await self._query(query, variables)
        if not data or not data.get("animes"):
            return []
        
        results = []
        for anime in data["animes"]:
            name = anime.get("name", "")
            english = anime.get("english", "")
            year = anime.get("airedOn", {}).get("year", "")
            
            # Add primary name
            if name:
                display = f"{name}"
                if year:
                    display += f" ({year})"
                results.append({"name": display[:100], "value": name[:100]})
            
            # Add English name if different
            if english and english != name and len(results) < limit:
                display = f"{english}"
                if year:
                    display += f" ({year})"
                results.append({"name": display[:100], "value": english[:100]})
        
        return results[:limit]
    
    def format_anime_data(self, anime: Dict[str, Any]) -> Dict[str, Any]:
        """Format Shikimori anime data into a clean structure."""
        return {
            "id": anime.get("id"),
            "mal_id": anime.get("malId"),
            "name": anime.get("name", "Unknown"),
            "english": anime.get("english", ""),
            "russian": anime.get("russian", ""),
            "synonyms": anime.get("synonyms", []),
            "score": anime.get("score", 0) or 0,
            "episodes": anime.get("episodes", 0) or 0,
            "kind": anime.get("kind", "Unknown"),
            "status": anime.get("status", "Unknown"),
            "year": anime.get("airedOn", {}).get("year"),
            "genres": [g.get("name") for g in anime.get("genres", [])],
            "studios": [s.get("name") for s in anime.get("studios", [])],
            "franchise": anime.get("franchise", ""),
            "poster_url": self._extract_poster(anime.get("poster", {})),
            "screenshots": self._extract_screenshots(anime.get("screenshots", []))
        }
    
    def _extract_poster(self, poster: Dict) -> Optional[str]:
        """Extract poster URL."""
        if not poster:
            return None
        return poster.get("originalUrl") or poster.get("mainUrl")
    
    def _extract_screenshots(self, screenshots: List[Dict]) -> List[Dict[str, str]]:
        """Extract screenshot URLs."""
        result = []
        for ss in screenshots:
            result.append({
                "id": ss.get("id", ""),
                "original": ss.get("originalUrl", ""),
                "medium": ss.get("x332Url", ""),
                "small": ss.get("x166Url", "")
            })
        return result
    
    def get_all_titles(self, anime: Dict[str, Any]) -> List[str]:
        """Get all possible titles for matching."""
        titles = []
        
        if anime.get("name"):
            titles.append(anime["name"])
        if anime.get("english"):
            titles.append(anime["english"])
        if anime.get("russian"):
            titles.append(anime["russian"])
        
        for synonym in anime.get("synonyms", []):
            if synonym and synonym.strip():
                titles.append(synonym)
        
        return [t.strip() for t in titles if t and t.strip()]
