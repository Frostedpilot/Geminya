import discord
import aiohttp
import random
import asyncio
import time
import re
from discord.ext import commands
from discord import app_commands
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


@dataclass
class CharacterData:
    """Data structure for character information."""
    
    def __init__(self, character_data: Dict[str, Any], all_anime_appearances: List[Dict[str, Any]]):
        self.character_id = character_data.get('mal_id')
        self.character_name = self._extract_character_name(character_data)
        self.character_name_kanji = character_data.get('name_kanji', '')
        self.character_nicknames = character_data.get('nicknames', [])
        self.character_image = self._extract_character_image(character_data)
        
        # Store all anime appearances
        self.anime_appearances = all_anime_appearances
        
        # Extract primary anime (first one or most popular)
        self.primary_anime = self._get_primary_anime()
        
    def _extract_character_name(self, character_data: Dict) -> str:
        """Extract character name from Jikan character data."""
        return character_data.get('name', 'Unknown')
    
    def _extract_character_image(self, character_data: Dict) -> Optional[str]:
        """Extract character image URL from Jikan character data."""
        images = character_data.get('images', {})
        if images:
            jpg_images = images.get('jpg', {})
            if jpg_images:
                return jpg_images.get('image_url')
        return None
    
    def _get_primary_anime(self) -> Dict[str, Any]:
        """Get the primary anime (first in the list or most popular)."""
        if not self.anime_appearances:
            return {}
        
        # For now, just return the first anime
        # Could be enhanced to pick the most popular/highest scored one
        return self.anime_appearances[0].get('anime', {})
    
    def get_all_anime_titles(self) -> List[str]:
        """Get all anime titles from all appearances."""
        all_titles = []
        
        for appearance in self.anime_appearances:
            anime_data = appearance.get('anime', {})
            titles = self._extract_anime_titles(anime_data)
            all_titles.extend(titles)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_titles = []
        for title in all_titles:
            if title not in seen:
                seen.add(title)
                unique_titles.append(title)
        
        return unique_titles
    
    def get_all_anime_names_for_display(self) -> str:
        """Get formatted string of all anime names for display."""
        anime_names = []
        
        for appearance in self.anime_appearances:
            anime_data = appearance.get('anime', {})
            anime_title = self._extract_primary_anime_title(anime_data)
            if anime_title and anime_title != 'Unknown':
                anime_names.append(anime_title)
        
        if not anime_names:
            return 'Unknown'
        
        if len(anime_names) == 1:
            return anime_names[0]
        elif len(anime_names) <= 3:
            return ', '.join(anime_names)
        else:
            # Show first 3 and indicate there are more
            return f"{', '.join(anime_names[:3])} (+{len(anime_names) - 3} more)"
    
    def get_primary_anime_title(self) -> str:
        """Get the primary anime title for display."""
        return self._extract_primary_anime_title(self.primary_anime)
    
    def _extract_primary_anime_title(self, anime_data: Dict) -> str:
        """Extract the primary anime title."""
        title_data = anime_data.get('title', '')
        if isinstance(title_data, str) and title_data:
            return title_data
        
        titles = anime_data.get('titles', [])
        if titles:
            # Prefer English title, then Default, then any available
            for title_obj in titles:
                if title_obj.get('type') == 'English':
                    title = title_obj.get('title', '').strip()
                    if title:
                        return title
            for title_obj in titles:
                if title_obj.get('type') == 'Default':
                    title = title_obj.get('title', '').strip()
                    if title:
                        return title
            # If no English or Default, use the first available title
            for title_obj in titles:
                title = title_obj.get('title', '').strip()
                if title:
                    return title
        
        return 'Unknown'
    
    def _extract_anime_titles(self, anime_data: Dict) -> List[str]:
        """Extract all anime titles and synonyms from available data."""
        titles = []
        
        # Add main title (this is usually the primary title)
        main_title = anime_data.get('title', '').strip()
        if main_title:
            titles.append(main_title)
        
        # Check for titles array (newer Jikan API format) - this contains multiple title types
        title_objects = anime_data.get('titles', [])
        for title_obj in title_objects:
            title = title_obj.get('title', '').strip()
            if title and title not in titles:
                titles.append(title)
        
        # Check for legacy title fields (older API format)
        legacy_titles = [
            anime_data.get('title_english', ''),
            anime_data.get('title_japanese', ''),
            anime_data.get('title_romanji', ''),  # Sometimes present
        ]
        
        for legacy_title in legacy_titles:
            if legacy_title and legacy_title.strip() and legacy_title not in titles:
                titles.append(legacy_title.strip())
        
        # Add title_synonyms if available (these are alternative names/abbreviations)
        synonyms = anime_data.get('title_synonyms', [])
        if isinstance(synonyms, list):
            for synonym in synonyms:
                if synonym and synonym.strip() and synonym not in titles:
                    titles.append(synonym.strip())
        
        return [title for title in titles if title and title.strip()]
    
    def _is_latin_title(self, title: str) -> bool:
        """Check if title contains only Latin characters, numbers, and common punctuation."""
        try:
            # Allow ASCII letters, numbers, extended Latin characters, and common punctuation
            title.encode('ascii', errors='ignore').decode('ascii')
            # Also allow common extended characters used in anime titles
            forbidden_patterns = [
                r'[\u3040-\u309F]',  # Hiragana
                r'[\u30A0-\u30FF]',  # Katakana
                r'[\u4E00-\u9FAF]',  # CJK Unified Ideographs
            ]
            
            for pattern in forbidden_patterns:
                if re.search(pattern, title):
                    return False
            
            return True
        except:
            return False
    
    def get_all_character_names(self) -> List[str]:
        """Get all character names including nicknames."""
        names = [self.character_name]
        
        # Add kanji name if different and not empty
        if self.character_name_kanji and self.character_name_kanji != self.character_name:
            names.append(self.character_name_kanji)
        
        # Add nicknames
        if self.character_nicknames:
            names.extend(self.character_nicknames)
        
        return [name for name in names if name and name.strip()]


class GuessCharacter:
    """Game state for Guess Character."""
    
    def __init__(self, target_character: CharacterData, difficulty: str = "normal"):
        self.target = target_character
        self.is_complete = False
        self.is_won = False
        self.difficulty = difficulty
        self.start_time = time.time()
        
        # Player gets only 1 guess
        self.max_guesses = 1
        self.guesses_made = 0
        self.character_guess = ""
        self.anime_guess = ""


class GuessCharacterCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.games: Dict[int, GuessCharacter] = {}  # channel_id -> game
        self.jikan_base_url = "https://api.jikan.moe/v4"
        self.rate_limit_delay = 1.0  # Jikan has rate limits, add delay between requests
        self.autocomplete_cache: Dict[str, Tuple[List[Dict[str, str]], float]] = {}  # Cache for autocomplete results
        self.autocomplete_cache_timeout = 300  # 5 minutes cache timeout
        self.last_autocomplete_time = 0
    
    async def _query_jikan(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make a REST API call to Jikan API with rate limiting."""
        try:
            # Add rate limiting delay to respect Jikan's limits
            await asyncio.sleep(self.rate_limit_delay)
            
            url = f"{self.jikan_base_url}{endpoint}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params or {},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:  # Rate limited
                        self.logger.warning("Jikan API rate limit hit, waiting longer")
                        await asyncio.sleep(3.0)
                        return None
                    else:
                        self.logger.warning(f"Jikan API returned status {response.status}")
                        return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error(f"Error querying Jikan API: {e}")
            return None

    async def _query_jikan_autocomplete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make a REST API call to Jikan API with lighter rate limiting for autocomplete."""
        try:
            current_time = time.time()
            
            # Light rate limiting for autocomplete - only allow one request per 0.1 seconds
            time_since_last = current_time - self.last_autocomplete_time
            if time_since_last < 0.1:
                await asyncio.sleep(0.1 - time_since_last)
            
            self.last_autocomplete_time = time.time()
            
            url = f"{self.jikan_base_url}{endpoint}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params or {},
                    timeout=aiohttp.ClientTimeout(total=2)  # Very short timeout for autocomplete
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 400:
                        # Log the specific error for 400 responses
                        response_text = await response.text()
                        query = params.get('q', 'None') if params else 'None'
                        self.logger.warning(f"Jikan API 400 error for query '{query}': {response_text}")
                        return None
                    elif response.status == 429:  # Rate limited
                        self.logger.warning("Jikan API rate limit hit during autocomplete")
                        return None
                    else:
                        self.logger.warning(f"Jikan API returned status {response.status} during autocomplete")
                        return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            query = params.get('q', 'None') if params else 'None'
            self.logger.error(f"Error querying Jikan API for autocomplete (query: '{query}'): {e}")
            return None
    
    async def _search_multiple_anime_cached(self, search_term: str, limit: int = 25) -> List[Dict[str, str]]:
        """Search for multiple anime with caching for autocomplete efficiency."""
        if not search_term or len(search_term.strip()) < 2:  # Reduced to 2 characters for better UX
            return []
        
        # Create cache key
        search_key = f"anime_{search_term.lower().strip()}"
        
        # Check cache first
        current_time = time.time()
        if search_key in self.autocomplete_cache:
            cached_data, timestamp = self.autocomplete_cache[search_key]
            if current_time - timestamp < self.autocomplete_cache_timeout:
                # Return cached results
                return cached_data[:limit]
        
        try:
            # Clean and validate search term
            clean_term = search_term.strip()
            if len(clean_term) < 2:  # Match the earlier check
                return []
            
            params = {
                'q': clean_term,
                'limit': min(limit, 25)  # Jikan has a limit of 25
            }
            
            # Use the autocomplete-specific query method
            data = await self._query_jikan_autocomplete('/anime', params)
            
            if not data:  # API returned None (could be 400, 429, or other error)
                return []
            
            choices = []
            added_values = set()  # Track added values to avoid duplicates
            if data.get('data'):
                for anime in data['data']:
                    # Extract all available titles including synonyms
                    anime_title = anime.get('title', 'Unknown')
                    anime_year = anime.get('year', 0)
                    
                    # Collect all title variations
                    all_titles = []
                    
                    # Main title
                    if anime_title and anime_title != 'Unknown':
                        all_titles.append(anime_title)
                    
                    # English title
                    if anime.get('title_english') and anime['title_english'] not in all_titles:
                        all_titles.append(anime['title_english'])
                    
                    # Japanese title
                    if anime.get('title_japanese') and anime['title_japanese'] not in all_titles:
                        all_titles.append(anime['title_japanese'])
                    
                    # Title synonyms
                    if anime.get('title_synonyms'):
                        for synonym in anime['title_synonyms']:
                            if synonym and synonym.strip() and synonym not in all_titles:
                                all_titles.append(synonym.strip())
                    
                    # Titles array (newer Jikan API format)
                    if anime.get('titles'):
                        for title_obj in anime['titles']:
                            title = title_obj.get('title', '').strip()
                            if title and title not in all_titles:
                                all_titles.append(title)
                    
                    # Add choices for each title variation
                    for title in all_titles:
                        if not title or title == 'Unknown':
                            continue
                        
                        # Avoid duplicate values
                        if title.lower() in added_values:
                            continue
                            
                        # Create display name with year for clarity
                        display_name = f"{title}"
                        if anime_year:
                            display_name += f" ({anime_year})"
                        
                        # Truncate display name if too long (Discord choice name limit is 100 chars)
                        if len(display_name) > 100:
                            display_name = display_name[:97] + "..."
                        
                        # Truncate value if too long (Discord choice value limit is also 100 chars)
                        choice_value = title
                        if len(choice_value) > 100:
                            choice_value = choice_value[:100]
                        
                        choices.append({
                            'name': display_name,
                            'value': choice_value
                        })
                        added_values.add(title.lower())  # Track this value as added
                        
                        if len(choices) >= 25:  # Discord limit
                            break
                    
                    if len(choices) >= 25:  # Discord limit
                        break
            
            # Cache the results
            self.autocomplete_cache[search_key] = (choices, current_time)
            
            # Clean old cache entries (keep cache size reasonable)
            if len(self.autocomplete_cache) > 100:
                # Remove oldest entries
                old_keys = sorted(self.autocomplete_cache.keys(), 
                                key=lambda k: self.autocomplete_cache[k][1])[:50]
                for key in old_keys:
                    del self.autocomplete_cache[key]
            
            return choices[:limit]
            
        except Exception as e:
            self.logger.error(f"Error in cached multiple anime search for '{search_term}': {e}")
            return []
    
    async def _search_multiple_characters_cached(self, search_term: str, limit: int = 25) -> List[Dict[str, str]]:
        """Search for multiple characters with caching and deduplication for autocomplete efficiency."""
        if not search_term or len(search_term.strip()) < 2:
            return []
        
        # Create cache key
        search_key = f"char_{search_term.lower().strip()}"
        
        # Check cache first
        current_time = time.time()
        if search_key in self.autocomplete_cache:
            cached_data, timestamp = self.autocomplete_cache[search_key]
            if current_time - timestamp < self.autocomplete_cache_timeout:
                # Return cached results
                return cached_data[:limit]
        
        try:
            # Clean and validate search term
            clean_term = search_term.strip()
            if len(clean_term) < 2:
                return []
            
            params = {
                'q': clean_term,
                'limit': min(limit, 25)  # Jikan has a limit of 25
            }
            
            # Use the autocomplete-specific query method
            data = await self._query_jikan_autocomplete('/characters', params)
            
            if not data:  # API returned None (could be 400, 429, or other error)
                return []
            
            choices = []
            seen_names = set()  # Track seen character names for deduplication
            
            if data.get('data'):
                for character in data['data']:
                    # Extract character name
                    char_name = character.get('name', 'Unknown')
                    
                    # Deduplicate by normalized character name (case-insensitive)
                    name_normalized = char_name.lower().strip()
                    if name_normalized in seen_names:
                        continue
                    seen_names.add(name_normalized)
                    
                    # Get anime information if available (first anime)
                    anime_info = ""
                    anime_list = character.get('anime', [])
                    if anime_list and len(anime_list) > 0:
                        first_anime = anime_list[0].get('anime', {})
                        anime_title = first_anime.get('title', '')
                        if anime_title:
                            anime_info = f" ({anime_title})"
                    
                    # Create display name
                    display_name = f"{char_name}{anime_info}"
                    
                    # Truncate display name if too long (Discord choice name limit is 100 chars)
                    if len(display_name) > 100:
                        display_name = display_name[:97] + "..."
                    
                    # Truncate value if too long (Discord choice value limit is also 100 chars)
                    choice_value = char_name
                    if len(choice_value) > 100:
                        choice_value = choice_value[:100]
                    
                    choices.append({
                        'name': display_name,
                        'value': choice_value
                    })
                    
                    if len(choices) >= 25:  # Discord limit
                        break
            
            # Cache the results
            self.autocomplete_cache[search_key] = (choices, current_time)
            
            # Clean old cache entries (keep cache size reasonable)
            if len(self.autocomplete_cache) > 100:
                # Remove oldest entries
                old_keys = sorted(self.autocomplete_cache.keys(), 
                                key=lambda k: self.autocomplete_cache[k][1])[:50]
                for key in old_keys:
                    del self.autocomplete_cache[key]
            
            return choices[:limit]
            
        except Exception as e:
            self.logger.error(f"Error in cached multiple character search for '{search_term}': {e}")
            return []
    
    async def anime_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete function for anime names."""
        # interaction parameter is required by Discord.py but not used
        del interaction  # Suppress unused argument warning
        
        # Return empty list for very short queries to avoid unnecessary API calls
        if not current or len(current.strip()) < 2:
            return []
        
        try:
            # Use asyncio.wait_for to ensure we don't exceed Discord's autocomplete timeout
            choices_data = await asyncio.wait_for(
                self._search_multiple_anime_cached(current, limit=20),
                timeout=2.0  # 2 second max timeout
            )
            return [
                app_commands.Choice(name=choice['name'], value=choice['value'])
                for choice in choices_data
            ]
        except asyncio.TimeoutError:
            self.logger.warning(f"Anime autocomplete timeout for query: '{current}'")
            return []
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error(f"Error in anime autocomplete: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in anime autocomplete: {e}")
            return []
    
    async def character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete function for character names."""
        # interaction parameter is required by Discord.py but not used
        del interaction  # Suppress unused argument warning
        
        # Return empty list for very short queries to avoid unnecessary API calls
        if not current or len(current.strip()) < 2:
            return []
        
        try:
            # Use asyncio.wait_for to ensure we don't exceed Discord's autocomplete timeout
            choices_data = await asyncio.wait_for(
                self._search_multiple_characters_cached(current, limit=20),
                timeout=2.0  # 2 second max timeout
            )
            return [
                app_commands.Choice(name=choice['name'], value=choice['value'])
                for choice in choices_data
            ]
        except asyncio.TimeoutError:
            self.logger.warning(f"Character autocomplete timeout for query: '{current}'")
            return []
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error(f"Error in character autocomplete: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in character autocomplete: {e}")
            return []
    

    

    
    def _get_character_selection_method(self, difficulty: str) -> str:
        """Get character selection method (always character_based now)."""
        return 'character_based'
    
    def _get_character_popularity_ranges(self, difficulty: str) -> Dict[str, int]:
        """Get character popularity ranges for this difficulty."""
        try:
            character_config = self.services.config.guess_character
            popularity_ranges = character_config.get('character_popularity', {})
            return popularity_ranges.get(difficulty, {})
        except (AttributeError, KeyError, TypeError):
            return {}
    
    def _get_character_roles_for_difficulty(self, difficulty: str) -> List[str]:
        """Get required character roles for this difficulty."""
        try:
            character_config = self.services.config.guess_character
            character_roles = character_config.get('character_roles', {})
            return character_roles.get(difficulty, ['Main', 'Supporting'])
        except (AttributeError, KeyError, TypeError):
            return ['Main', 'Supporting']

    def _is_troll_mode_enabled(self) -> bool:
        """Check if troll mode is enabled."""
        try:
            character_config = self.services.config.guess_character
            troll_config = character_config.get('troll_mode', {})
            return troll_config.get('enabled', False)
        except (AttributeError, KeyError, TypeError):
            return False
    
    def _get_troll_character_id(self) -> Optional[int]:
        """Get the character ID for troll mode."""
        try:
            character_config = self.services.config.guess_character
            troll_config = character_config.get('troll_mode', {})
            return troll_config.get('character_id')
        except (AttributeError, KeyError, TypeError):
            return None

    async def _fetch_troll_character(self) -> Optional[CharacterData]:
        """Fetch the specific troll character by ID."""
        character_id = self._get_troll_character_id()
        if not character_id:
            self.logger.error("Troll mode enabled but no character_id specified!")
            return None
        
        try:
            self.logger.info(f"🎭 TROLL MODE: Fetching character ID {character_id}")
            
            # Fetch character data from Jikan API
            character_data = await self._query_jikan(f'/characters/{character_id}')
            if not character_data or not character_data.get('data'):
                self.logger.error(f"Failed to fetch troll character {character_id}")
                return None
            
            char_info = character_data['data']
            
            # Check if character has image
            if not char_info.get('images', {}).get('jpg', {}).get('image_url'):
                self.logger.error(f"Troll character {character_id} has no image!")
                return None
            
            # Fetch character's anime appearances
            anime_data = await self._query_jikan(f'/characters/{character_id}/anime')
            anime_appearances = anime_data.get('data', []) if anime_data else []
            
            # Create CharacterData object
            troll_character = CharacterData(char_info, anime_appearances)
            
            self.logger.info(f"🎭 TROLL CHARACTER LOADED: {troll_character.character_name}")
            return troll_character
            
        except Exception as e:
            self.logger.error(f"Error fetching troll character {character_id}: {e}")
            return None

    async def _fetch_character_by_popularity(self, difficulty: str) -> Optional[CharacterData]:
        """Fetch a random character directly by popularity ranking."""
        popularity_ranges = self._get_character_popularity_ranges(difficulty)
        required_roles = self._get_character_roles_for_difficulty(difficulty)
        
        if not popularity_ranges:
            self.logger.warning(f"No character popularity ranges found for difficulty '{difficulty}'")
            return None
        
        # Create weighted list of popularity ranges
        weighted_ranges = []
        for range_str, weight in popularity_ranges.items():
            min_val, max_val = map(int, range_str.split('-'))
            weighted_ranges.extend([(min_val, max_val)] * weight)
        
        # Try multiple attempts to find a suitable character
        max_attempts = 20
        for attempt in range(max_attempts):
            try:
                # Randomly select a popularity range based on weights
                selected_range = random.choice(weighted_ranges)
                min_popularity, max_popularity = selected_range
                
                # Calculate correct page numbers based on character rankings
                # Each page contains 25 characters, so:
                # Page = (Rank - 1) ÷ 25 + 1
                # For a range, we need min_page to max_page
                # Examples:
                # - Rank 1-25 → Page 1
                # - Rank 1-1000 → Pages 1-40  
                # - Rank 1001-2500 → Pages 41-100
                # - Rank 10001-15000 → Pages 401-600
                min_page = max(1, (min_popularity - 1) // 25 + 1)
                max_page = (max_popularity - 1) // 25 + 1
                
                # Ensure we don't go beyond reasonable API limits (Jikan has thousands of pages)
                max_page = min(max_page, 1000)  # Limit to first 25,000 characters
                
                # Random page within the calculated range
                random_page = random.randint(min_page, max_page)
                
                self.logger.info(f"Attempt {attempt + 1}: Fetching characters from page {random_page} (popularity range: {min_popularity}-{max_popularity}, page range: {min_page}-{max_page})")
                
                # Fetch characters from Jikan API ordered by favorites (popularity)
                params = {
                    'page': random_page,
                    'limit': 25,  # Jikan default page size
                    'order_by': 'favorites',
                    'sort': 'desc'
                }
                
                data = await self._query_jikan('/characters', params)
                if not data or not data.get('data'):
                    continue
                
                # Filter characters that have images
                suitable_characters = []
                for char_data in data['data']:
                    # Check if character has image
                    if not char_data.get('images', {}).get('jpg', {}).get('image_url'):
                        continue
                    
                    # Accept this character as suitable - since we're fetching from pages ordered by popularity,
                    # characters on different pages will naturally fall into different popularity ranges
                    suitable_characters.append(char_data)
                
                if not suitable_characters:
                    continue
                
                # Randomly select one character from the suitable ones
                selected_character = random.choice(suitable_characters)
                character_id = selected_character.get('mal_id')
                
                if not character_id:
                    continue
                
                # Fetch full character details
                character_details = await self._query_jikan(f'/characters/{character_id}/full')
                if not character_details or not character_details.get('data'):
                    continue
                
                # Fetch character's anime appearances
                anime_appearances = await self._query_jikan(f'/characters/{character_id}/anime')
                if not anime_appearances or not anime_appearances.get('data'):
                    continue
                
                # Filter anime appearances by required roles (basic data only)
                filtered_appearances = []
                
                for appearance in anime_appearances['data']:
                    role = appearance.get('role', '')
                    if role in required_roles:
                        # Keep only basic anime data - no need for full details anymore
                        filtered_appearances.append(appearance)
                
                if not filtered_appearances:
                    self.logger.debug(f"Character {character_id} doesn't have required roles {required_roles}")
                    continue
                
                # Create CharacterData object
                character_data = CharacterData(character_details['data'], filtered_appearances)
                
                if character_data.character_image:
                    self.logger.info(f"Successfully found character: {character_data.character_name} (ID: {character_id}) with {len(filtered_appearances)} anime appearances")
                    return character_data
                
            except Exception as e:
                self.logger.warning(f"Error in attempt {attempt + 1} for character selection: {e}")
                continue
        
        self.logger.warning(f"Failed to find suitable character after {max_attempts} attempts for difficulty '{difficulty}'")
        return None


    

    
    async def _start_game(self, interaction: discord.Interaction, channel_id: int, difficulty: str) -> bool:
        """Start a new character guessing game with specified difficulty."""
        # Defer immediately to prevent timeout
        await interaction.response.defer(thinking=True)
        
        # Check if there's already a game in this channel
        if channel_id in self.games:
            existing_game = self.games[channel_id]
            if not existing_game.is_complete:
                await interaction.followup.send(
                    "❌ You already have an active character guessing game in this channel! "
                    "Complete it first or give up using `/guess_character action:Give Up`.",
                    ephemeral=True
                )
                return False

        # --- Daily Mission: Play a Game ---
        try:
            services = self.services
            db = services.database
            user = interaction.user
            from datetime import datetime, timezone
            import pytz
            tz = pytz.timezone('Asia/Bangkok')
            now_utc = datetime.now(timezone.utc)
            now_local = now_utc.astimezone(tz)
            today_date = now_local.date()
            mission = await db.get_or_create_mission({
                "name": "Play a Game!",
                "description": "Play any of the three games (anidle, guess anime, guess character) today.",
                "type": "play_game",
                "target_count": 1,
                "reward_type": "gems",
                "reward_amount": 200,
                "difficulty": "easy",
                "is_active": True
            })
            progress = await db.get_user_mission_progress(str(user.id), mission["id"], today_date)
            if not progress or (not progress["completed"] or not progress["claimed"]):
                await db.update_user_mission_progress(str(user.id), mission["id"], today_date)
                progress = await db.get_user_mission_progress(str(user.id), mission["id"], today_date)
                if progress and progress["completed"] and not progress["claimed"]:
                    claimed = await db.claim_user_mission_reward(str(user.id), mission["id"], today_date)
                    if claimed:
                        await interaction.followup.send(f"🎉 Daily Mission Complete! You earned 200 gems for playing a game today.", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Daily mission error: {e}")
        try:
            # Check if troll mode is enabled
            if self._is_troll_mode_enabled():
                self.logger.info(f"🎭 TROLL MODE ACTIVATED! Ignoring difficulty '{difficulty}' and using troll character")
                
                character_data = await asyncio.wait_for(
                    self._fetch_troll_character(),
                    timeout=30.0
                )
            else:
                self.logger.info(f"Using character-based selection for difficulty '{difficulty}'")
                
                # Use character-based selection
                character_data = await asyncio.wait_for(
                    self._fetch_character_by_popularity(difficulty),
                    timeout=30.0
                )
            
            if not character_data:
                await interaction.followup.send("❌ Sorry, I couldn't find a suitable character for this difficulty. Please try again!")
                return False
            
            if not character_data.character_image:
                await interaction.followup.send("❌ Sorry, this character doesn't have an image. Please try again!")
                return False
            
            # Create new game
            game = GuessCharacter(character_data, difficulty)
            self.games[channel_id] = game
            
            # Create game embed
            difficulty_text = difficulty.title()
            if self._is_troll_mode_enabled():
                difficulty_text += " 🎭"  # Add troll emoji hint
            
            embed = discord.Embed(
                title="🎭 Guess the Character!",
                description=f"**Difficulty:** {difficulty_text}\n\n"
                           f"**Rules:**\n"
                           f"• You have **1 guess** only!\n"
                           f"• Guess both the **character name** and **anime title**\n"
                           f"• If the character appears in multiple anime, any valid anime will be accepted! ✨\n"
                           f"• Use `/guess_character action:Make a Guess character: [name] anime: [title]`\n\n"
                           f"**Hint:** Here's the character's portrait!",
                color=0x9B59B6
            )
            
            if character_data.character_image:
                embed.set_image(url=character_data.character_image)
            
            embed.set_footer(text="Good luck! You only get one shot at this! 🎯")
            
            await interaction.followup.send(embed=embed)
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting new character game: {e}")
            await interaction.followup.send("❌ Sorry, there was an error starting the game. Please try again!")
            return False
    
    async def _make_guess(self, interaction: discord.Interaction, channel_id: int, character: str, anime: str):
        """Submit a guess for the character guessing game."""
        await interaction.response.defer()
        
        # Check if there's a game in this channel
        if channel_id not in self.games:
            await interaction.followup.send("❌ There's no character guessing game in progress in this channel!")
            return
        
        game = self.games[channel_id]
        
        # Check if game is already complete
        if game.is_complete:
            await interaction.followup.send("❌ This game is already finished!")
            return

        
        # Check if player has already used their guess
        if game.guesses_made >= game.max_guesses:
            await interaction.followup.send("❌ You've already used your guess!")
            return
        
        # Validate input
        if not character.strip() or not anime.strip():
            await interaction.followup.send("❌ Please provide both a character name and anime title!")
            return
        
        # Record the guess
        game.guesses_made += 1
        game.character_guess = character.strip()
        game.anime_guess = anime.strip()
        
        # Check if guesses are correct
        character_correct, matched_character_name = self._check_character_match(character, game.target)
        anime_correct, matched_anime_title = await self._check_anime_match_async(anime, game.target)
        
        # Complete the game
        game.is_complete = True
        game.is_won = character_correct and anime_correct
        
        # Create and send result embed
        result_embed = self._create_result_embed(game, character_correct, anime_correct, matched_anime_title, matched_character_name)
        await interaction.followup.send(embed=result_embed)
        
        # Remove the game
        del self.games[channel_id]
    
    async def _give_up(self, interaction: discord.Interaction, channel_id: int):
        """End the current character guessing game."""
        if channel_id not in self.games:
            await interaction.response.send_message("❌ There's no character guessing game in progress in this channel!")
            return
        
        game = self.games[channel_id]
        
        # Show the answer
        anime_count = len(game.target.anime_appearances)
        display_anime = game.target.get_primary_anime_title()
        
        description = f"**Character:** {game.target.character_name}\n"
        description += f"**Anime:** {display_anime}\n"
        
        if anime_count > 1:
            description += f"*(This character appears in {anime_count} anime)*"
        
        embed = discord.Embed(
            title="🏳️ Game Ended",
            description=description,
            color=0x95A5A6
        )
        
        if game.target.character_image:
            embed.set_thumbnail(url=game.target.character_image)
        
        await interaction.response.send_message(embed=embed)
        
        # Remove the game
        del self.games[channel_id]
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison by removing extra spaces, punctuation, and converting to lowercase."""
        # Remove common punctuation and normalize spaces
        text = re.sub(r'[^\w\s]', '', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _normalize_anime_title(self, title: str) -> str:
        """Normalize anime title for comparison, with special handling for years and brackets."""
        # Convert to lowercase first
        title = title.lower().strip()
        
        # Remove year patterns like (2023), (2020-2021), etc.
        title = re.sub(r'\s*\(\d{4}(?:-\d{4})?\)\s*', '', title)
        
        # Remove other common patterns
        title = re.sub(r'\s*\(tv\)\s*', '', title)
        title = re.sub(r'\s*\(ova\)\s*', '', title)
        title = re.sub(r'\s*\(movie\)\s*', '', title)
        title = re.sub(r'\s*\(special\)\s*', '', title)
        
        # Remove trailing periods and other punctuation that might cause issues
        title = re.sub(r'\.+$', '', title)  # Remove trailing periods
        
        # Remove remaining punctuation except for essential ones
        title = re.sub(r'[^\w\s\-\'\.]', '', title)
        
        # Remove any remaining trailing periods after punctuation removal
        title = re.sub(r'\.+$', '', title)
        
        # Normalize multiple spaces to single space
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def _normalize_character_name(self, name: str) -> str:
        """Normalize character name for comparison - simple case-insensitive matching."""
        # Convert to lowercase and strip whitespace
        name = name.lower().strip()
        
        # Remove punctuation and normalize spaces
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def _check_character_match(self, guess: str, target_character: CharacterData) -> Tuple[bool, Optional[str]]:
        """Check if the character guess matches any of the target character's names.
        
        Returns:
            Tuple of (is_match, matched_name) where matched_name is the specific name that matched
        """
        guess_normalized = self._normalize_character_name(guess)
        all_names = target_character.get_all_character_names()
        
        self.logger.info(f"Checking character guess '{guess}' (normalized: '{guess_normalized}') against {len(all_names)} names: {all_names[:3] if len(all_names) > 3 else all_names}")
        
        for name in all_names:
            name_normalized = self._normalize_character_name(name)
            if guess_normalized == name_normalized:
                self.logger.info(f"Character match found: '{guess}' (normalized: '{guess_normalized}') matches '{name}' (normalized: '{name_normalized}')")
                return True, name
        
        return False, None
    
    def _check_anime_match(self, guess: str, target_character: CharacterData) -> Tuple[bool, Optional[str]]:
        """Check if the anime guess matches any of the target anime using search API.
        
        Returns:
            Tuple of (is_match, matched_title) where matched_title is the specific title that matched
        """
        return asyncio.run(self._check_anime_match_async(guess, target_character))
    
    async def _check_anime_match_async(self, guess: str, target_character: CharacterData) -> Tuple[bool, Optional[str]]:
        """Async method to check anime match using Jikan search API."""
        try:
            # Get list of anime IDs that the character appears in
            character_anime_ids = set()
            character_anime_titles = {}  # ID -> title mapping for reference
            
            for appearance in target_character.anime_appearances:
                anime_data = appearance.get('anime', {})
                anime_id = anime_data.get('mal_id')
                anime_title = anime_data.get('title', 'Unknown')
                
                if anime_id:
                    character_anime_ids.add(anime_id)
                    character_anime_titles[anime_id] = anime_title
            
            if not character_anime_ids:
                self.logger.warning("No anime IDs found for character")
                return False, None
            
            self.logger.info(f"Checking anime guess '{guess}' against character's {len(character_anime_ids)} anime")
            
            # Search for the player's guess using Jikan API
            search_params = {
                'q': guess.strip(),
                'limit': 10  # Check first 10 results
            }
            
            search_results = await self._query_jikan('/anime', search_params)
            
            if not search_results or not search_results.get('data'):
                self.logger.info(f"No search results found for '{guess}'")
                return False, None
            
            # Check if the FIRST result matches any of the character's anime
            first_result = search_results['data'][0]
            first_result_id = first_result.get('mal_id')
            first_result_title = first_result.get('title', 'Unknown')
            
            self.logger.info(f"First search result: {first_result_title} (ID: {first_result_id})")
            
            if first_result_id in character_anime_ids:
                matched_title = character_anime_titles[first_result_id]
                self.logger.info(f"✅ MATCH! First search result matches character's anime: {matched_title}")
                return True, matched_title
            else:
                self.logger.info(f"❌ First search result does not match any of character's anime")
                # Log character's anime for debugging
                anime_list = [f"{title} (ID: {aid})" for aid, title in list(character_anime_titles.items())[:3]]
                self.logger.info(f"Character appears in: {anime_list}")
                return False, None
                
        except Exception as e:
            self.logger.error(f"Error during anime search matching: {e}")
            return False, None
    
    def _create_result_embed(self, game: GuessCharacter, character_correct: bool, anime_correct: bool, matched_anime_title: Optional[str] = None, matched_character_name: Optional[str] = None) -> discord.Embed:
        """Create the result embed showing the outcome."""
        character_data = game.target
        
        if character_correct and anime_correct:
            # Win
            title = "🎉 Congratulations! You Win! 🎉"
            description = f"**Perfect!** You got both the character and anime correct!\n\n"
            color = 0x2ECC71
        elif character_correct or anime_correct:
            # Partial
            title = "😔 So Close! Half Correct!"
            description = f"You got {'the character' if character_correct else 'the anime'} right, but missed {'the anime' if character_correct else 'the character'}.\n\n"
            color = 0xF39C12
        else:
            # Lose
            title = "💔 Better Luck Next Time!"
            description = f"Unfortunately, you didn't get either correct.\n\n"
            color = 0xE74C3C
        
        # Add user's guesses for reference
        description += f"**Your Guess:**\n"
        description += f"• Character: {game.character_guess} {'✅' if character_correct else '❌'}\n"
        description += f"• Anime: {game.anime_guess} {'✅' if anime_correct else '❌'}\n\n"
        
        # Add correct answers
        description += f"**Correct Answer:**\n"
        description += f"• Character: {character_data.character_name}\n"
        
        # Show one anime title - prefer the matched title if anime was correct, otherwise show primary anime
        anime_count = len(character_data.anime_appearances)
        if matched_anime_title and anime_correct:
            # Show the specific title that was matched
            display_anime = matched_anime_title
        else:
            # Show primary anime title
            display_anime = character_data.get_primary_anime_title()
        
        if anime_count > 1:
            description += f"• Anime: {display_anime}\n"
            description += f"  *(This character appears in {anime_count} anime - any would be correct!)*\n\n"
        else:
            description += f"• Anime: {display_anime}\n\n"
        
        # Add game info
        game_time = time.time() - game.start_time
        description += f"**Game Stats:**\n"
        description += f"• Difficulty: {game.difficulty.title()}\n"
        description += f"• Time: {game_time:.1f} seconds"
        
        embed = discord.Embed(title=title, description=description, color=color)
        
        if character_data.character_image:
            embed.set_thumbnail(url=character_data.character_image)
        
        return embed
    
    @app_commands.command(
        name="guess_character",
        description="Play Guess the Character! Identify a character from their portrait."
    )
    @app_commands.describe(
        action="Choose an action",
        character="Character name to guess (only for 'guess' action)",
        anime="Anime title to guess (only for 'guess' action)",
        difficulty="Choose difficulty level (only for 'start' action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Start New Game", value="start"),
        app_commands.Choice(name="Make a Guess", value="guess"),
        app_commands.Choice(name="Give Up", value="giveup")
    ])
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="Easy", value="easy"),
        app_commands.Choice(name="Normal", value="normal"),
        app_commands.Choice(name="Hard", value="hard"),
        app_commands.Choice(name="Expert", value="expert"),
        app_commands.Choice(name="Crazy", value="crazy"),
        app_commands.Choice(name="Insanity", value="insanity")
    ])
    @app_commands.autocomplete(character=character_autocomplete)
    @app_commands.autocomplete(anime=anime_autocomplete)
    async def guess_character(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        character: Optional[str] = None,
        anime: Optional[str] = None,
        difficulty: Optional[app_commands.Choice[str]] = None
    ):
        """Main guess character command."""
        if not interaction.channel:
            await interaction.response.send_message(
                "❌ This command can only be used in a channel!",
                ephemeral=True
            )
            return
            
        channel_id = interaction.channel.id
        
        if action.value == "start":
            difficulty_value = difficulty.value if difficulty else "normal"
            await self._start_game(interaction, channel_id, difficulty_value)
        elif action.value == "guess":
            await self._make_guess(interaction, channel_id, character or "", anime or "")
        elif action.value == "giveup":
            await self._give_up(interaction, channel_id)


async def setup(bot: commands.Bot):
    """Setup function for cog loading."""
    # Get services from bot instance
    services = getattr(bot, 'services', None)
    if services:
        await bot.add_cog(GuessCharacterCog(bot, services))
    else:
        # Fallback if services not available
        raise RuntimeError("Bot services not available")
