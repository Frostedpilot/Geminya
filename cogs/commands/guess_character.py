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
        """Extract all anime titles and synonyms."""
        titles = []
        
        # Add main title
        main_title = self._extract_primary_anime_title(anime_data)
        if main_title and main_title != 'Unknown':
            titles.append(main_title)
        
        # Add title_synonyms if available
        if 'title_synonyms' in anime_data and anime_data['title_synonyms']:
            titles.extend(anime_data['title_synonyms'])
        
        # Add titles from titles array
        title_objects = anime_data.get('titles', [])
        for title_obj in title_objects:
            title = title_obj.get('title', '').strip()
            if title and title not in titles:
                titles.append(title)
        
        # Add title_english and title_japanese if available
        if anime_data.get('title_english') and anime_data['title_english'] not in titles:
            titles.append(anime_data['title_english'])
        if anime_data.get('title_japanese') and anime_data['title_japanese'] not in titles:
            titles.append(anime_data['title_japanese'])
        
        # Return all titles, but prioritize Latin titles for better user experience
        # Keep both Latin and non-Latin titles to be more inclusive
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
        """Search for multiple characters with caching for autocomplete efficiency."""
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
            if data.get('data'):
                for character in data['data']:
                    # Extract character name
                    char_name = character.get('name', 'Unknown')
                    
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
    
    def _get_character_selection_config(self, difficulty: str) -> List[Dict[str, Any]]:
        """Get anime difficulty and character role combinations for the chosen difficulty."""
        config_map = {
            'easy': [
                {'anime_difficulty': 'easy', 'character_roles': ['Main']},
                {'anime_difficulty': 'normal', 'character_roles': ['Main']}
            ],
            'normal': [
                {'anime_difficulty': 'easy', 'character_roles': ['Supporting']},
                {'anime_difficulty': 'normal', 'character_roles': ['Supporting']}
            ],
            'hard': [
                {'anime_difficulty': 'hard', 'character_roles': ['Main']},
                {'anime_difficulty': 'expert', 'character_roles': ['Main']}
            ],
            'expert': [
                {'anime_difficulty': 'hard', 'character_roles': ['Supporting']},
                {'anime_difficulty': 'expert', 'character_roles': ['Supporting']}
            ],
            'crazy': [
                {'anime_difficulty': 'crazy', 'character_roles': ['Main']}
            ],
            'insanity': [
                {'anime_difficulty': 'crazy', 'character_roles': ['Supporting']}
            ]
        }
        
        return config_map.get(difficulty, config_map['normal'])  # Default to normal if not found
    
    def _get_selection_config(self, difficulty: str) -> Tuple[str, Dict[str, int]]:
        """Get selection method and ranges based on difficulty level from config."""
        try:
            # Get config settings - now access anidle directly as a dict
            anime_config = self.services.config.anidle
            
            # Get selection method for this difficulty
            selection_methods = anime_config.get('selection_method', {})
            selection_method = selection_methods.get(difficulty, 'score')  # Default to score
            
            # Get selection ranges for this method and difficulty
            selection_ranges = anime_config.get('selection_ranges', {})
            method_ranges = selection_ranges.get(selection_method, {})
            difficulty_ranges = method_ranges.get(difficulty, {})
            
            if difficulty_ranges:
                self.logger.info(f"Using {selection_method} selection for {difficulty} difficulty: {len(difficulty_ranges)} ranges")
                return selection_method, difficulty_ranges
            
            # Fallback to hard-coded defaults if config not found
            self.logger.warning(f"Selection config not found for {difficulty}, using fallback defaults")
            fallback_weights = {
                '8.0-10': 15, '6.0-7.9': 15, '5.0-5.9': 2, '4.0-4.9': 1, '0-3.9': 1
            }
            return 'score', fallback_weights
            
        except (AttributeError, KeyError, TypeError) as e:
            self.logger.error(f"Error reading selection config: {e}")
            # Hard fallback to default score-based selection
            fallback_weights = {
                '8.0-10': 15, '6.0-7.9': 15, '5.0-5.9': 2, '4.0-4.9': 1, '0-3.9': 1
            }
            self.logger.info(f"Using hard fallback score weights: {len(fallback_weights)} ranges")
            return 'score', fallback_weights

    async def _select_random_anime_by_difficulty(self, difficulty: str) -> Optional[Dict[str, Any]]:
        """Select a random anime based on difficulty using anidle's popularity ranges."""
        try:
            # Get config settings - now access anidle directly as a dict
            anime_config = self.services.config.anidle
            
            # Get selection method and ranges for this difficulty
            selection_method, selection_ranges = self._get_selection_config(difficulty)
            sort_method = anime_config.get('sort_method', 'popularity')
            
            # Create weighted list of ranges
            weighted_ranges = []
            for range_str, weight in selection_ranges.items():
                min_val, max_val = map(float, range_str.split('-'))
                weighted_ranges.extend([(min_val, max_val)] * weight)
            
            # Randomly select a range based on weights
            selected_range = random.choice(weighted_ranges)
            min_val, max_val = selected_range
            
            # Build API parameters based on selection method
            if selection_method == 'score':
                self.logger.info(f"Using score selection: {min_val}-{max_val}")
                # For score-based selection, we need to use sort by score
                api_params = {
                    'min_score': min_val,
                    'max_score': max_val,
                    'order_by': 'score'
                }
            elif selection_method == 'popularity':
                self.logger.info(f"Using popularity selection: rank {int(min_val)}-{int(max_val)}")
                # For popularity-based selection, we need to calculate page range
                # Jikan shows 25 anime per page, so rank 1-25 = page 1, rank 26-50 = page 2, etc.
                start_page = max(1, int(min_val) // 25)
                end_page = max(start_page, int(max_val) // 25)
                
                # Select a random page within the calculated range
                random_page = random.randint(start_page, end_page)
                api_params = {
                    'page': random_page,
                    'order_by': 'popularity'
                }
            else:
                # Fallback to popularity-based selection
                self.logger.warning(f"Unknown selection method '{selection_method}', falling back to popularity")
                api_params = {
                    'page': random.randint(1, 10),
                    'order_by': 'popularity'
                }
            
            # Query anime using Jikan API
            data = await self._query_jikan('/anime', api_params)
            if data and data.get('data'):
                anime_list = data['data']
                if anime_list:
                    # Filter results based on selection method if needed
                    if selection_method == 'popularity':
                        filtered_anime = []
                        for anime in anime_list:
                            popularity = anime.get('popularity')
                            if popularity and min_val <= popularity <= max_val:
                                filtered_anime.append(anime)
                        
                        if filtered_anime:
                            anime_list = filtered_anime
                    
                    # Randomly select one anime from the filtered list
                    selected_anime = random.choice(anime_list)
                    
                    # Log selection details
                    anime_title = selected_anime.get('title', 'Unknown')
                    anime_popularity = selected_anime.get('popularity', 'N/A')
                    
                    self.logger.info(f"Selected anime for character game: {anime_title} (Popularity: {anime_popularity})")
                    return selected_anime
            
            # Fallback if no results found
            self.logger.warning("No anime found with specified criteria, trying fallback")
            fallback_params = {
                'page': random.randint(1, 10),
                'limit': 25,
                'order_by': 'popularity'
            }
            
            data = await self._query_jikan('/anime', fallback_params)
            if data and data.get('data') and data['data']:
                selected_anime = random.choice(data['data'])
                anime_title = selected_anime.get('title', 'Unknown')
                self.logger.info(f"Fallback selected anime for character game: {anime_title}")
                return selected_anime
            
            self.logger.error("Could not retrieve any anime from API")
            return None
            
        except Exception as e:
            self.logger.error(f"Error in anime selection for character game: {e}")
            return None
    
    async def _get_random_character_from_anime(self, anime_id: int, anime_data: Dict[str, Any], required_roles: Optional[List[str]] = None) -> Optional[CharacterData]:
        """Get a random character from the specified anime and fetch all their anime appearances."""
        try:
            # Get characters for this anime
            data = await self._query_jikan(f'/anime/{anime_id}/characters')
            
            if not data or not data.get('data'):
                self.logger.warning(f"No characters found for anime {anime_id}")
                return None
            
            characters = data['data']
            
            # Filter by required roles if specified
            if required_roles:
                filtered_characters = [char for char in characters if char.get('role') in required_roles]
                if filtered_characters:
                    characters = filtered_characters
                else:
                    # If no characters match required roles, log and fall back to all main/supporting
                    self.logger.warning(f"No characters with roles {required_roles} found, falling back to all main/supporting")
                    characters = [char for char in characters if char.get('role') in ['Main', 'Supporting']]
            else:
                # Default behavior: filter for main and supporting characters only
                characters = [char for char in characters if char.get('role') in ['Main', 'Supporting']]
            
            if not characters:
                # If no suitable characters, use all characters as last resort
                characters = data['data']
            
            if not characters:
                self.logger.warning(f"No suitable characters found for anime {anime_id}")
                return None
            
            # Select random character
            selected_character = random.choice(characters)
            character_data = selected_character.get('character', {})
            character_id = character_data.get('mal_id')
            
            if not character_id:
                self.logger.warning("Selected character has no ID")
                return None
            
            # Fetch full character details to get nicknames and other information
            full_character_data = await self._query_jikan(f'/characters/{character_id}')
            
            if full_character_data and full_character_data.get('data'):
                # Use the full character data which includes nicknames
                character_data = full_character_data['data']
            else:
                self.logger.warning(f"Could not fetch full character details for {character_id}, using basic data")
                # Keep the basic character_data from the anime endpoint
            
            # Now fetch all anime appearances for this character
            character_full_data = await self._query_jikan(f'/characters/{character_id}/anime')
            
            if not character_full_data or not character_full_data.get('data'):
                self.logger.warning(f"Could not fetch anime appearances for character {character_id}")
                # Fall back to just the original anime
                anime_appearances = [{'anime': anime_data, 'role': selected_character.get('role', '')}]
                self.logger.info(f"Using fallback anime data: {anime_data.get('title', 'No title')}")
            else:
                anime_appearances = character_full_data['data']
                
                self.logger.info(f"Found {len(anime_appearances)} anime appearances for character")
                
                # Log first anime appearance for debugging
                if anime_appearances:
                    first_anime = anime_appearances[0].get('anime', {})
                    self.logger.info(f"First anime appearance: {first_anime.get('title', 'No title')}")
            
            # Ensure we have at least one anime appearance
            if not anime_appearances:
                self.logger.warning("No anime appearances found after filtering, using original anime as fallback")
                anime_appearances = [{'anime': anime_data, 'role': selected_character.get('role', '')}]
            
            # Log selection
            char_name = character_data.get('name', 'Unknown')
            char_role = selected_character.get('role', 'Unknown')
            anime_count = len(anime_appearances)
            required_roles_str = f" (required: {required_roles})" if required_roles else ""
            self.logger.info(f"Selected character: {char_name} (Role: {char_role}, appears in {anime_count} anime{required_roles_str})")
            
            return CharacterData(character_data, anime_appearances)
            
        except Exception as e:
            self.logger.error(f"Error getting character from anime {anime_id}: {e}")
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
        try:
            # Get character selection configuration for this difficulty
            selection_configs = self._get_character_selection_config(difficulty)
            
            # Try each configuration until we find a character
            character_data = None
            selected_config = None
            
            # Shuffle the configurations to add variety
            random.shuffle(selection_configs)
            
            # Limit attempts to prevent infinite loops
            max_attempts = 10
            attempt_count = 0
            
            for config in selection_configs:
                if attempt_count >= max_attempts:
                    self.logger.warning(f"Max attempts ({max_attempts}) reached for difficulty '{difficulty}'")
                    break
                
                anime_difficulty = config['anime_difficulty']
                required_roles = config['character_roles']
                attempt_count += 1
                
                self.logger.info(f"Attempt {attempt_count}: {difficulty} difficulty with anime difficulty '{anime_difficulty}' and roles {required_roles}")
                
                try:
                    # Select random anime based on the anime difficulty with timeout
                    anime_data = await asyncio.wait_for(
                        self._select_random_anime_by_difficulty(anime_difficulty),
                        timeout=10.0
                    )
                    if not anime_data:
                        self.logger.warning(f"Could not find anime for difficulty '{anime_difficulty}', trying next config")
                        continue
                    
                    anime_id = anime_data.get('mal_id')
                    if not anime_id:
                        self.logger.warning(f"Anime data missing ID, trying next config")
                        continue
                    
                    # Get random character from the anime with required roles and timeout
                    character_data = await asyncio.wait_for(
                        self._get_random_character_from_anime(anime_id, anime_data, required_roles),
                        timeout=15.0
                    )
                    if character_data and character_data.character_image:
                        selected_config = config
                        self.logger.info(f"Successfully found character with config: anime_difficulty='{anime_difficulty}', roles={required_roles}")
                        break
                    else:
                        self.logger.warning(f"Could not find suitable character for anime {anime_id} with roles {required_roles}, trying next config")
                        
                except asyncio.TimeoutError:
                    self.logger.error(f"Timeout during character selection for difficulty '{anime_difficulty}', trying next config")
                    continue
                except Exception as e:
                    self.logger.error(f"Error during character selection: {e}, trying next config")
                    continue
            
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
            embed = discord.Embed(
                title="🎭 Guess the Character!",
                description=f"**Difficulty:** {difficulty.title()}\n\n"
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
        character_correct = self._check_character_match(character, game.target)
        anime_correct = self._check_anime_match(anime, game.target)
        
        # Complete the game
        game.is_complete = True
        game.is_won = character_correct and anime_correct
        
        # Create and send result embed
        result_embed = self._create_result_embed(game, character_correct, anime_correct)
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
        embed = discord.Embed(
            title="🏳️ Game Ended",
            description=f"**Character:** {game.target.character_name}\n"
                       f"**Anime:** {game.target.get_all_anime_names_for_display()}\n",
            color=0x95A5A6
        )
        
        if game.target.character_image:
            embed.set_thumbnail(url=game.target.character_image)
        
        await interaction.response.send_message(embed=embed)
        
        # Remove the game
        del self.games[channel_id]
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison by removing extra spaces, punctuation, and converting to lowercase."""
        import re
        # Remove common punctuation and normalize spaces
        text = re.sub(r'[^\w\s]', '', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _check_character_match(self, guess: str, target_character: CharacterData) -> bool:
        """Check if the character guess matches any of the target character's names."""
        guess_normalized = self._normalize_text(guess)
        all_names = target_character.get_all_character_names()
        
        for name in all_names:
            name_normalized = self._normalize_text(name)
            if guess_normalized == name_normalized:
                return True
        
        return False
    
    def _check_anime_match(self, guess: str, target_character: CharacterData) -> bool:
        """Check if the anime guess matches any of the target anime's titles."""
        guess_normalized = self._normalize_text(guess)
        all_titles = target_character.get_all_anime_titles()
        
        # Log available titles for debugging (only first few to avoid spam)
        if len(all_titles) > 5:
            sample_titles = all_titles[:5] + [f"... and {len(all_titles) - 5} more"]
        else:
            sample_titles = all_titles
        
        self.logger.info(f"Checking anime guess '{guess}' against {len(all_titles)} titles: {sample_titles}")
        
        for title in all_titles:
            title_normalized = self._normalize_text(title)
            if guess_normalized == title_normalized:
                self.logger.info(f"Anime match found: '{guess}' matches '{title}'")
                return True
        
        return False
    
    def _create_result_embed(self, game: GuessCharacter, character_correct: bool, anime_correct: bool) -> discord.Embed:
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
        
        # Show all anime appearances
        anime_count = len(character_data.anime_appearances)
        if anime_count > 1:
            description += f"• Anime: {character_data.get_all_anime_names_for_display()}\n"
            description += f"  *(This character appears in {anime_count} anime - any would be correct!)*\n\n"
        else:
            description += f"• Anime: {character_data.get_all_anime_names_for_display()}\n\n"
        
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
