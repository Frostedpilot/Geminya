"""Jikan API service for fetching anime and character data from MyAnimeList."""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Tuple
import aiohttp


class JikanService:
    """Service for interacting with Jikan API (MyAnimeList)."""
    
    def __init__(self):
        self.base_url = "https://api.jikan.moe/v4"
        self.rate_limit_delay = 1.0  # Jikan has rate limits
        self.last_request_time = 0
        self.autocomplete_cache: Dict[str, Tuple[List[Dict], float]] = {}
        self.autocomplete_cache_timeout = 300  # 5 minutes
    
    def _is_hentai(self, anime: Dict[str, Any]) -> bool:
        """Check if anime has Hentai genre/tag."""
        genres = anime.get("genres", [])
        explicit_genres = anime.get("explicit_genres", [])
        demographics = anime.get("demographics", [])
        
        # Check all genre/demographic lists for hentai
        all_categories = genres + explicit_genres + demographics
        for category in all_categories:
            if category.get("name", "").lower() == "hentai":
                return True
        return False
    
    async def _rate_limit_check(self):
        """Ensure we don't exceed Jikan rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    async def _query(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0
    ) -> Optional[Dict[str, Any]]:
        """Make a REST API call to Jikan API with rate limiting."""
        await self._rate_limit_check()
        
        try:
            url = f"{self.base_url}{endpoint}"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params or {},
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        # Rate limited - wait longer
                        await asyncio.sleep(3.0)
                        return None
                    else:
                        return None
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None
    
    async def get_random_anime(self, difficulty: str = "normal", source: str = "anime_selection") -> Optional[Dict[str, Any]]:
        """Get a random anime based on difficulty using MAL popularity ranking.
        
        Args:
            difficulty: Difficulty level
            source: Config source ("anime_selection" or "theme_anime_selection")
        
        Uses weighted random selection based on config.yml rank_ranges.
        The Jikan API provides 25 items per page ordered by popularity.
        
        Ranking reference:
        - Rank 1-500: Very popular (Death Note, Attack on Titan, etc.)
        - Rank 500-2500: Popular to moderately popular
        - Rank 2500-5000: Less popular to obscure
        - Rank 5000-8000: Very obscure (~7500 members at rank 8000)
        """
        try:
            from .config_service import game_config
            
            min_rank, max_rank = game_config.select_rank_range(difficulty, source)
            
            # Calculate pages for the rank range
            # With limit=25, each page covers ~25 ranks: page 100 ≈ rank 2500
            # So: page = rank / 25
            start_page = max(1, min_rank // 25)
            end_page = max(start_page, max_rank // 25)
            
            # Try up to 5 times to find anime in the correct rank range
            for attempt in range(5):
                page = random.randint(start_page, end_page)
                params = {
                    "order_by": "popularity",
                    "sort": "asc",  # Ascending = rank 1 is first
                    "limit": 25,
                    "page": page
                }
                
                data = await self._query("/anime", params)
                if data and data.get("data"):
                    anime_list = data["data"]
                    # Filter by exact popularity rank and exclude hentai
                    filtered = [
                        a for a in anime_list 
                        if a.get("popularity") and min_rank <= a.get("popularity", 999999) <= max_rank
                        and not self._is_hentai(a)
                    ]
                    if filtered:
                        selected = random.choice(filtered)
                        popularity = selected.get('popularity', '?')
                        members = selected.get('members', 0)
                        print(f"✅ Selected '{selected.get('title')}' (rank #{popularity}, {members:,} members) [target: #{min_rank}-#{max_rank}]")
                        return selected
                    else:
                        # Log why filtering failed
                        if anime_list:
                            sample_rank = anime_list[0].get('popularity', '?')
                            print(f"⚠️  Attempt {attempt + 1}: Page {page} has rank #{sample_rank} (target: #{min_rank}-#{max_rank})")
            
            print(f"❌ Could not find anime in rank range #{min_rank}-#{max_rank} after 5 attempts")
            
        except Exception as e:
            print(f"❌ Config-based selection failed: {e}, falling back to score-based")
        
        # Fallback: score-based difficulty (old behavior)
        difficulty_ranges = {
            "easy": (8.0, 10.0),
            "normal": (6.0, 10.0),
            "hard": (5.0, 8.0),
            "expert": (4.0, 7.0),
            "crazy": (3.0, 6.0),
            "insanity": (1.0, 5.0)
        }
        
        min_score, max_score = difficulty_ranges.get(difficulty, (6.0, 10.0))
        
        params = {
            "min_score": min_score,
            "max_score": max_score,
            "order_by": "score",
            "limit": 25,
            "page": random.randint(1, 5)
        }
        
        data = await self._query("/anime", params)
        if data and data.get("data"):
            anime_list = data["data"]
            # Filter out hentai from fallback results
            filtered = [a for a in anime_list if not self._is_hentai(a)]
            if filtered:
                return random.choice(filtered)
        
        return None

    
    async def search_anime(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for an anime by name."""
        params = {"q": query, "limit": 1}
        data = await self._query("/anime", params)
        if data and data.get("data") and len(data["data"]) > 0:
            return data["data"][0]
        return None
    
    async def search_multiple_anime(self, query: str, limit: int = 25) -> List[Dict[str, str]]:
        """Search for multiple anime for autocomplete."""
        if not query or len(query.strip()) < 2:
            return []
        
        # Check cache
        cache_key = query.lower().strip()
        current_time = time.time()
        if cache_key in self.autocomplete_cache:
            cached_data, timestamp = self.autocomplete_cache[cache_key]
            if current_time - timestamp < self.autocomplete_cache_timeout:
                return cached_data[:limit]
        
        params = {"q": query.strip(), "limit": min(limit, 25)}
        data = await self._query("/anime", params, timeout=5.0)
        
        if not data or not data.get("data"):
            return []
        
        results = []
        for anime in data["data"]:
            title = anime.get("title", "Unknown")
            year = self._extract_year(anime)
            display_name = f"{title}"
            if year:
                display_name += f" ({year})"
            
            # Truncate for Discord limits
            if len(display_name) > 100:
                display_name = display_name[:97] + "..."
            if len(title) > 100:
                title = title[:100]
            
            results.append({
                "name": display_name,
                "value": title,
                "id": anime.get("mal_id"),
                "score": anime.get("score"),
                "year": year
            })
        
        # Cache results
        self.autocomplete_cache[cache_key] = (results, current_time)
        
        return results[:limit]
    
    async def get_character(self, character_id: int) -> Optional[Dict[str, Any]]:
        """Get character details by ID."""
        data = await self._query(f"/characters/{character_id}/full")
        if data and data.get("data"):
            return data["data"]
        return None
    
    async def get_random_character(self, difficulty: str = "normal") -> Optional[Dict[str, Any]]:
        """Get a random character based on difficulty with weighted selection.
        
        Uses config to select anime difficulty + character role (main/support).
        """
        from .config_service import game_config
        
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                # Get weighted anime difficulty and role from config
                anime_difficulty, target_role = game_config.select_character_params(difficulty)
                
                # Get anime using the selected difficulty
                anime = await self.get_random_anime(anime_difficulty)
                if not anime:
                    continue
                
                anime_id = anime.get("mal_id")
                if not anime_id:
                    continue
                
                # Get characters from this anime
                data = await self._query(f"/anime/{anime_id}/characters")
                if not data or not data.get("data"):
                    continue
                
                characters = data["data"]
                if not characters:
                    continue
                
                # Filter by target role
                role_chars = [c for c in characters if c.get("role") == target_role]
                
                # Fall back to other role if none found
                if not role_chars:
                    other_role = "Supporting" if target_role == "Main" else "Main"
                    role_chars = [c for c in characters if c.get("role") == other_role]
                
                # Fall back to any character if still none
                if not role_chars:
                    role_chars = characters
                
                if role_chars:
                    char_entry = random.choice(role_chars)
                    char_data = char_entry.get("character", {})
                    
                    # Ensure character has an image
                    images = char_data.get("images", {})
                    jpg = images.get("jpg", {})
                    if not jpg.get("image_url"):
                        continue  # Skip characters without images
                    
                    char_data["anime"] = anime  # Attach anime info
                    print(f"✅ Character: {char_data.get('name')} ({char_entry.get('role')}) from {anime.get('title')} [anime_diff: {anime_difficulty}]")
                    return char_data
                    
            except Exception as e:
                # Log and continue to next attempt
                continue
        
        return None
    
    async def search_character(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for a character by name."""
        params = {"q": query, "limit": 1}
        data = await self._query("/characters", params)
        if data and data.get("data") and len(data["data"]) > 0:
            return data["data"][0]
        return None
    
    async def search_multiple_characters(self, query: str, limit: int = 25) -> List[Dict[str, str]]:
        """Search for multiple characters for autocomplete with deduplication."""
        if not query or len(query.strip()) < 2:
            return []
        
        # Check cache
        cache_key = f"char_{query.lower().strip()}"
        current_time = time.time()
        if cache_key in self.autocomplete_cache:
            cached_data, timestamp = self.autocomplete_cache[cache_key]
            if current_time - timestamp < self.autocomplete_cache_timeout:
                return cached_data[:limit]
        
        params = {"q": query.strip(), "limit": min(limit, 25)}
        data = await self._query("/characters", params, timeout=5.0)
        
        if not data or not data.get("data"):
            return []
        
        results = []
        seen_names = set()  # Track seen character names for deduplication
        
        for char in data["data"]:
            name = char.get("name", "Unknown")
            
            # Deduplicate by normalized character name (case-insensitive)
            name_normalized = name.lower().strip()
            if name_normalized in seen_names:
                continue
            seen_names.add(name_normalized)
            
            display_name = name
            
            if len(display_name) > 100:
                display_name = display_name[:97] + "..."
            if len(name) > 100:
                name = name[:100]
            
            results.append({
                "name": display_name,
                "value": name,
                "id": char.get("mal_id")
            })
        
        # Cache results
        self.autocomplete_cache[cache_key] = (results, current_time)
        
        return results[:limit]
    
    def _extract_year(self, anime: Dict[str, Any]) -> Optional[int]:
        """Extract year from anime data."""
        aired = anime.get("aired", {})
        if isinstance(aired, dict):
            from_date = aired.get("from", "")
            if from_date:
                try:
                    return int(from_date[:4])
                except (ValueError, TypeError):
                    pass
        
        year = anime.get("year")
        return year if year else None
    
    def format_anime_data(self, anime: Dict[str, Any]) -> Dict[str, Any]:
        """Format raw Jikan anime data into a clean structure."""
        return {
            "id": anime.get("mal_id"),
            "title": anime.get("title", "Unknown"),
            "title_english": anime.get("title_english"),
            "title_japanese": anime.get("title_japanese"),
            "year": self._extract_year(anime),
            "score": anime.get("score", 0) or 0,
            "episodes": anime.get("episodes", 0) or 0,
            "genres": [g.get("name") for g in anime.get("genres", [])],
            "studios": [s.get("name") for s in anime.get("studios", [])],
            "source": anime.get("source", "Unknown"),
            "format": anime.get("type", "Unknown"),
            "season": anime.get("season", "").title() if anime.get("season") else "Unknown",
            "themes": [t.get("name") for t in anime.get("themes", [])],
            "image": self._extract_image(anime),
            "synopsis": anime.get("synopsis", "")
        }
    
    def _extract_image(self, anime: Dict[str, Any]) -> Optional[str]:
        """Extract image URL from anime data."""
        images = anime.get("images", {})
        jpg = images.get("jpg", {})
        return jpg.get("large_image_url") or jpg.get("image_url")
