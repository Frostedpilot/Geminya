"""AnimeThemes API service for fetching anime openings and endings."""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any
import aiohttp


class AnimeThemesService:
    """Service for fetching anime themes from AnimeThemes API."""
    
    def __init__(self):
        self.base_url = "https://api.animethemes.moe"
        self.rate_limit_delay = 2.5  # Increased to avoid rate limiting
        self.last_request_time = 0
    
    async def _rate_limit_check(self):
        """Ensure we don't exceed rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    async def get_themes_by_mal_id(self, mal_id: int) -> Optional[Dict[str, Any]]:
        """Fetch anime themes (OPs/EDs) by MAL ID.
        
        Returns:
            Dict with title, ops list, and eds list, or None if not found.
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            await self._rate_limit_check()
            
            try:
                # Use resource filter to look up by external MAL ID
                # IMPORTANT: Must include filter[has]=resources for site/external_id filters to work
                url = f"{self.base_url}/anime"
                params = {
                    "filter[has]": "resources",
                    "filter[site]": "MyAnimeList",
                    "filter[external_id]": mal_id,
                    "include": "animethemes.animethemeentries.videos,animethemes.song"
                }
                
                print(f"🔍 Querying AnimeThemes for MAL ID {mal_id}: {url}")
                print(f"   Params: {params}")
                
                connector = aiohttp.TCPConnector(force_close=True)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(
                        url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=15.0)
                    ) as response:
                        if response.status != 200:
                            print(f"❌ AnimeThemes returned status {response.status}")
                            return None
                        data = await response.json()
                        
                        # Debug: Log how many anime were returned
                        anime_count = len(data.get("anime", []))
                        print(f"   Response: {anime_count} anime returned")
                        if anime_count > 1:
                            print(f"   ⚠️  WARNING: Multiple anime returned! Expected 1.")
                            for idx, a in enumerate(data.get("anime", [])[:3]):
                                print(f"      [{idx}] {a.get('name', 'Unknown')}")
                
                # Check if anime exists in AnimeThemes
                if not data.get("anime"):
                    print(f"⚠️  MAL ID {mal_id}: Not found in AnimeThemes")
                    return None
                
                anime_entry = data["anime"][0]
                anime_name = anime_entry.get("name", "Unknown")
                print(f"✅ Found in AnimeThemes: {anime_name} (MAL ID: {mal_id})")
                
                result = {
                    "title": anime_name,
                    "ops": [],
                    "eds": []
                }
                
                for theme in anime_entry.get("animethemes", []):
                    theme_slug = theme.get("slug", "")  # e.g., "OP1", "ED2"
                    theme_type_field = theme.get("type", "")  # Could be "OP" or "ED"
                    
                    # Debug: print both fields to see which one is correct
                    # print(f"  Theme: slug={theme_slug}, type={theme_type_field}")
                    
                    # Get song info
                    song = theme.get("song") or {}
                    song_title = song.get("title", "Unknown")
                    # Get artist info - can be nested in artists array
                    artists = song.get("artists", [])
                    artist_name = artists[0].get("name", "Unknown") if artists else "Unknown"
                    
                    # Get the best video URL (prefer 1080p)
                    video_url = None
                    for entry in theme.get("animethemeentries", []):
                        for video in entry.get("videos", []):
                            if video.get("link"):
                                video_url = video["link"]
                                # Prefer 1080p
                                if video.get("resolution") == 1080:
                                    break
                        if video_url:
                            break
                    
                    if not video_url:
                        continue  # Skip themes without video
                    
                    theme_data = {
                        "slug": theme_slug,
                        "title": song_title,
                        "artist": artist_name,
                        "url": video_url
                    }
                    
                    # Check both slug and type field for classification
                    is_op = theme_slug.startswith("OP") or theme_type_field == "OP"
                    is_ed = theme_slug.startswith("ED") or theme_type_field == "ED"
                    
                    if is_op:
                        result["ops"].append(theme_data)
                    elif is_ed:
                        result["eds"].append(theme_data)
                
                return result
                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 2s, 4s
                    print(f"AnimeThemes request failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"AnimeThemes request failed after {max_retries} attempts: {e}")
                    return None
        
        return None
    
    async def get_random_op(self, mal_id: int) -> Optional[Dict[str, Any]]:
        """Get a random opening theme for an anime.
        
        Returns:
            Dict with slug, title, url, or None if no OPs found.
        """
        themes = await self.get_themes_by_mal_id(mal_id)
        if not themes or not themes.get("ops"):
            return None
        return random.choice(themes["ops"])
    
    async def get_random_ed(self, mal_id: int) -> Optional[Dict[str, Any]]:
        """Get a random ending theme for an anime.
        
        Returns:
            Dict with slug, title, url, or None if no EDs found.
        """
        themes = await self.get_themes_by_mal_id(mal_id)
        if not themes or not themes.get("eds"):
            return None
        return random.choice(themes["eds"])
    
    async def has_themes(self, mal_id: int, theme_type: str = "op") -> bool:
        """Check if anime has themes of the specified type.
        
        Args:
            mal_id: MAL ID of the anime
            theme_type: "op" or "ed"
        
        Returns:
            True if anime has at least one theme of the type.
        """
        themes = await self.get_themes_by_mal_id(mal_id)
        if not themes:
            return False
        if theme_type == "op":
            return len(themes.get("ops", [])) > 0
        else:
            return len(themes.get("eds", [])) > 0
