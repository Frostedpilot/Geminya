"""AniList GraphQL API service for anime metadata.

Uses AniList to fetch rich metadata including tags, studios, etc.
Query by MAL ID using the idMal field.
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class AniListService:
    """Service for interacting with AniList GraphQL API."""
    
    API_URL = "https://graphql.anilist.co"
    
    # Query anime by MAL ID
    ANIME_BY_MAL_QUERY = """
    query ($malId: Int) {
        Media(idMal: $malId, type: ANIME) {
            id
            idMal
            title {
                romaji
                english
                native
            }
            format
            status
            startDate {
                year
                month
                day
            }
            episodes
            duration
            source
            averageScore
            meanScore
            genres
            tags {
                id
                name
                description
                category
                rank
                isMediaSpoiler
            }
            studios(isMain: true) {
                nodes {
                    id
                    name
                }
            }
            coverImage {
                large
                medium
            }
        }
    }
    """
    
    def __init__(self):
        self.rate_limit_delay = 1.5  # AniList rate limit (increased to avoid connection resets)
        self.last_request_time = 0
    
    async def _rate_limit_check(self):
        """Ensure we don't exceed rate limits."""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    async def get_anime_by_mal_id(self, mal_id: int, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Fetch anime metadata from AniList using MAL ID.
        
        Returns formatted data with:
        - title, title_english, title_japanese
        - year, score, episodes, format, source
        - genres, studios
        - primary_tags (first 5 by rank)
        - secondary_tags (next 5 by rank)
        
        Includes retry logic with exponential backoff for transient errors.
        """
        last_error = None
        
        for attempt in range(max_retries):
            await self._rate_limit_check()
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.API_URL,
                        json={
                            "query": self.ANIME_BY_MAL_QUERY,
                            "variables": {"malId": mal_id}
                        },
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as response:
                        if response.status != 200:
                            logger.warning(f"AniList API error: {response.status}")
                            return None
                        
                        data = await response.json()
                        
                        if "errors" in data:
                            logger.warning(f"AniList query errors: {data['errors']}")
                            return None
                        
                        media = data.get("data", {}).get("Media")
                        if not media:
                            logger.info(f"No AniList entry found for MAL ID {mal_id}")
                            return None
                        
                        return self._format_anime_data(media)
                        
            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"AniList request attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    await asyncio.sleep(2 ** attempt)
                continue
            except Exception as e:
                logger.error(f"AniList unexpected error: {e}")
                return None
        
        logger.error(f"AniList request failed after {max_retries} attempts: {last_error}")
        return None
    
    def _format_anime_data(self, media: Dict[str, Any]) -> Dict[str, Any]:
        """Format AniList response into game-friendly structure."""
        title = media.get("title", {})
        start_date = media.get("startDate", {})
        cover = media.get("coverImage", {})
        
        # Extract studios
        studios_data = media.get("studios", {}).get("nodes", [])
        studios = [s.get("name") for s in studios_data if s.get("name")]
        
        # Process tags - sorted by rank (higher rank = more relevant)
        tags_raw = media.get("tags", [])
        # Filter out spoiler tags and sort by rank descending
        tags_sorted = sorted(
            [t for t in tags_raw if not t.get("isMediaSpoiler")],
            key=lambda t: t.get("rank", 0),
            reverse=True
        )
        
        # First 5 = primary, next 5 = secondary
        primary_tags = [t.get("name") for t in tags_sorted[:5]]
        secondary_tags = [t.get("name") for t in tags_sorted[5:10]]
        
        # Format source to match Jikan format
        source_mapping = {
            "ORIGINAL": "Original",
            "MANGA": "Manga",
            "LIGHT_NOVEL": "Light novel",
            "VISUAL_NOVEL": "Visual novel",
            "VIDEO_GAME": "Game",
            "OTHER": "Other",
            "NOVEL": "Novel",
            "DOUJINSHI": "Doujinshi",
            "ANIME": "Anime",
            "WEB_NOVEL": "Web novel",
            "LIVE_ACTION": "Live action",
            "GAME": "Game",
            "COMIC": "Comic",
            "MULTIMEDIA_PROJECT": "Multimedia project",
            "PICTURE_BOOK": "Picture book"
        }
        
        # Format media type/format
        format_mapping = {
            "TV": "TV",
            "TV_SHORT": "TV Short",
            "MOVIE": "Movie",
            "SPECIAL": "Special",
            "OVA": "OVA",
            "ONA": "ONA",
            "MUSIC": "Music",
            "MANGA": "Manga",
            "NOVEL": "Novel",
            "ONE_SHOT": "One Shot"
        }
        
        raw_format = media.get("format", "")
        raw_source = media.get("source", "")
        
        return {
            "anilist_id": media.get("id"),
            "mal_id": media.get("idMal"),
            "title": title.get("romaji", "Unknown"),
            "title_english": title.get("english"),
            "title_japanese": title.get("native"),
            "year": start_date.get("year"),
            "score": (media.get("averageScore") or media.get("meanScore") or 0) / 10,  # AniList uses 0-100
            "episodes": media.get("episodes") or 0,
            "format": format_mapping.get(raw_format, raw_format or "Unknown"),
            "media_type": format_mapping.get(raw_format, raw_format or "Unknown"),  # Same as format
            "source": source_mapping.get(raw_source, raw_source or "Unknown"),
            "genres": media.get("genres", []),
            "studios": studios,
            "primary_tags": primary_tags,
            "secondary_tags": secondary_tags,
            "all_tags": [t.get("name") for t in tags_sorted],  # For reference
            "image": cover.get("large") or cover.get("medium")
        }
    
    async def search_anime(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search anime by name for autocomplete."""
        search_query = """
        query ($search: String, $perPage: Int) {
            Page(perPage: $perPage) {
                media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
                    id
                    idMal
                    title {
                        romaji
                        english
                    }
                    startDate {
                        year
                    }
                    averageScore
                }
            }
        }
        """
        
        await self._rate_limit_check()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    json={
                        "query": search_query,
                        "variables": {"search": query, "perPage": limit}
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    media_list = data.get("data", {}).get("Page", {}).get("media", [])
                    
                    results = []
                    for m in media_list:
                        title = m.get("title", {})
                        year = m.get("startDate", {}).get("year")
                        display_title = title.get("romaji") or title.get("english") or "Unknown"
                        
                        results.append({
                            "id": m.get("idMal") or m.get("id"),
                            "name": f"{display_title} ({year})" if year else display_title,
                            "value": display_title,
                            "score": (m.get("averageScore") or 0) / 10,
                            "year": year
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"AniList search failed: {e}")
            return []


# Global instance
anilist_service = AniListService()
