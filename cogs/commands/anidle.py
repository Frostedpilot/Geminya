import discord
import aiohttp
import random
import asyncio
import time
import re
from discord.ext import commands
from discord import app_commands
from typing import Dict, List, Optional, Any, Tuple

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class AnimeData:
    """Data structure for anime information."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('mal_id')
        self.title = self._extract_title(data)
        self.synonyms = self._extract_synonyms(data)
        self.year = self._extract_year(data)
        self.score = data.get('score', 0) or 0  # Keep native MAL 1-10 scale
        self.episodes = data.get('episodes', 0) or 0
        self.genres = self._extract_genres(data.get('genres', []))
        self.studios = self._extract_studios(data.get('studios', []))
        self.source = self._extract_source(data.get('source', 'Unknown'))
        self.format = self._extract_format(data.get('type', 'Unknown'))
        self.season = self._extract_season(data)
        self.themes = self._extract_themes(data.get('themes', []))
        self.cover_image = self._extract_cover_image(data.get('images', {}))
    
    def _extract_title(self, data: Dict) -> str:
        """Extract the best available title from Jikan data."""
        # Jikan provides title as a string or nested object
        title_data = data.get('title', '')
        if isinstance(title_data, str):
            return title_data or 'Unknown'
        
        # Handle titles object if it exists
        titles = data.get('titles', [])
        if titles:
            # Prefer English title, then Default, then any available
            for title_obj in titles:
                if title_obj.get('type') == 'English':
                    return title_obj.get('title', 'Unknown')
            for title_obj in titles:
                if title_obj.get('type') == 'Default':
                    return title_obj.get('title', 'Unknown')
            return titles[0].get('title', 'Unknown')
        
        return str(title_data) if title_data else 'Unknown'
    
    def _extract_synonyms(self, data: Dict) -> List[str]:
        """Extract synonyms and alternative titles from Jikan data."""
        synonyms = []
        
        # Add title_synonyms if available
        if 'title_synonyms' in data and data['title_synonyms']:
            synonyms.extend(data['title_synonyms'])
        
        # Add titles from titles array
        titles = data.get('titles', [])
        for title_obj in titles:
            title = title_obj.get('title', '').strip()
            if title and title not in synonyms:
                synonyms.append(title)
        
        # Add title_english and title_japanese if available
        if data.get('title_english') and data['title_english'] not in synonyms:
            synonyms.append(data['title_english'])
        if data.get('title_japanese') and data['title_japanese'] not in synonyms:
            synonyms.append(data['title_japanese'])
        
        return synonyms
    
    def _extract_year(self, data: Dict) -> int:
        """Extract year from Jikan aired data."""
        aired = data.get('aired', {})
        if isinstance(aired, dict):
            from_date = aired.get('from', '')
            if from_date:
                try:
                    # Parse date string like "2013-04-07T00:00:00+00:00"
                    return int(from_date[:4])
                except (ValueError, TypeError):
                    pass
        
        # Fallback to year field if available
        year = data.get('year', 0)
        return year if year else 0
    
    def _extract_genres(self, genres_data: List) -> List[str]:
        """Extract genre names from Jikan data."""
        if not genres_data:
            return ['Unknown']
        return [genre.get('name', 'Unknown') for genre in genres_data if genre.get('name')]
    
    def _extract_studios(self, studios_data: List) -> List[str]:
        """Extract studio names from Jikan data."""
        if not studios_data:
            return ['Unknown']
        return [studio.get('name', 'Unknown') for studio in studios_data if studio.get('name')]
    
    def _extract_source(self, source: str) -> str:
        """Extract source from Jikan data without extensive mapping."""
        return source if source else 'Unknown'
    
    def _extract_format(self, format_type: str) -> str:
        """Extract format from Jikan data without mapping."""
        return format_type if format_type else 'Unknown'
    
    def _extract_season(self, data: Dict) -> str:
        """Extract season from Jikan data."""
        # Jikan provides season separately from year
        season = data.get('season', '').title() if data.get('season') else ''
        
        if season:
            return season
        else:
            return 'Unknown'
    
    def _extract_themes(self, themes_data: List) -> List[str]:
        """Extract theme names from Jikan data."""
        if not themes_data:
            return ['Unknown']
        themes = [theme.get('name', 'Unknown') for theme in themes_data if theme.get('name')]
        return themes if themes else ['Unknown']
    
    def _extract_cover_image(self, images_data: Dict) -> Optional[str]:
        """Extract cover image URL from Jikan data."""
        if not images_data:
            return None
        
        # Jikan images structure: {"jpg": {"image_url": "...", "large_image_url": "..."}}
        jpg_images = images_data.get('jpg', {})
        if jpg_images:
            return (jpg_images.get('large_image_url') or 
                   jpg_images.get('image_url'))
        
        webp_images = images_data.get('webp', {})
        if webp_images:
            return (webp_images.get('large_image_url') or 
                   webp_images.get('image_url'))
        
        return None
    
    def get_all_titles(self) -> List[str]:
        """Get all possible titles including synonyms for matching, filtered for English/Latin characters only."""
        titles = [self.title]
        if self.synonyms:
            titles.extend(self.synonyms)
        
        # Filter titles to only include those with English/Latin characters and numbers
        filtered_titles = []
        for title in titles:
            if title and title.strip():
                # Check if title contains only Latin alphabet, numbers, spaces, and common punctuation
                if self._is_latin_title(title.strip()):
                    filtered_titles.append(title.strip())
        
        return filtered_titles
    
    def _is_latin_title(self, title: str) -> bool:
        """Check if title contains only Latin characters, numbers, and common punctuation."""
        import re
        # Check if title contains only allowed characters (Latin alphabet, numbers, punctuation)
        # We exclude non-Latin scripts like Japanese, Chinese, Korean, Arabic, etc.
        try:
            # Allow ASCII letters, numbers, extended Latin characters, and common punctuation
            title.encode('ascii', errors='ignore').decode('ascii')
            # Also allow common extended characters used in anime titles
            forbidden_patterns = [
                r'[\u3040-\u309F]',  # Hiragana
                r'[\u30A0-\u30FF]',  # Katakana  
                r'[\u4E00-\u9FAF]',  # CJK Unified Ideographs
                r'[\u0400-\u04FF]',  # Cyrillic
                r'[\u0590-\u05FF]',  # Hebrew
                r'[\u0600-\u06FF]',  # Arabic
            ]
            
            for pattern in forbidden_patterns:
                if re.search(pattern, title):
                    return False
            
            return True
        except UnicodeError:
            return False


class Anidle:
    """Game state for Anidle."""
    
    def __init__(self, target_anime: AnimeData, difficulty: str = "normal"):
        self.target = target_anime
        self.guesses: List[AnimeData] = []
        self.max_guesses = 21
        self.is_complete = False
        self.is_won = False
        self.hint_penalty = 0  # Track additional guess penalty from hints
        self.difficulty = difficulty  # Track game difficulty
    
    def add_guess(self, guess: AnimeData) -> bool:
        """Add a guess and check if game is complete."""
        self.guesses.append(guess)
        
        if guess.id == self.target.id:
            self.is_complete = True
            self.is_won = True
            return True
        
        # Check if total guesses (including hint penalty) exceed max
        total_guesses = len(self.guesses) + self.hint_penalty
        if total_guesses >= self.max_guesses:
            self.is_complete = True
            self.is_won = False
        
        return False
    
    def get_comparison(self, guess: AnimeData) -> Dict[str, str]:
        """Compare guess with target and return result indicators."""
        comparison = {}
        
        # Title comparison - check main title and synonyms
        guess_titles = [title.lower().strip() for title in guess.get_all_titles()]
        target_titles = [title.lower().strip() for title in self.target.get_all_titles()]
        
        title_match = any(guess_title in target_titles for guess_title in guess_titles)
        comparison['title'] = f"{guess.title} {'✅' if title_match else '❌'}"
        
        # Year comparison
        if guess.year == self.target.year:
            comparison['year'] = f"{guess.year} ✅"
        elif guess.year < self.target.year:
            comparison['year'] = f"{guess.year} ⬆️"
        else:
            comparison['year'] = f"{guess.year} ⬇️"
        
        # Score comparison
        if guess.score == self.target.score:
            comparison['score'] = f"{guess.score}/10 ✅"
        elif guess.score < self.target.score:
            comparison['score'] = f"{guess.score}/10 ⬆️"
        else:
            comparison['score'] = f"{guess.score}/10 ⬇️"
        
        # Episodes comparison
        if guess.episodes == self.target.episodes:
            comparison['episodes'] = f"{guess.episodes} ✅"
        elif guess.episodes < self.target.episodes:
            comparison['episodes'] = f"{guess.episodes} ⬆️"
        else:
            comparison['episodes'] = f"{guess.episodes} ⬇️"
        
        # Genres comparison - show individual matches
        guess_genres = set(guess.genres)
        target_genres = set(self.target.genres)
        if guess_genres == target_genres:
            comparison['genres'] = f"{', '.join(sorted(guess.genres))} ✅"
        else:
            # Show individual genre matches
            genre_matches = []
            for genre in guess.genres:
                if genre in target_genres:
                    genre_matches.append(f"{genre} ✅")
                else:
                    genre_matches.append(f"{genre} ❌")
            comparison['genres'] = ', '.join(genre_matches) if genre_matches else '❌'
        
        # Studio comparison - show individual matches
        guess_studios = set(guess.studios)
        target_studios = set(self.target.studios)
        if guess_studios == target_studios:
            comparison['studio'] = f"{', '.join(sorted(guess.studios))} ✅"
        else:
            # Show individual studio matches
            studio_matches = []
            for studio in guess.studios:
                if studio in target_studios:
                    studio_matches.append(f"{studio} ✅")
                else:
                    studio_matches.append(f"{studio} ❌")
            comparison['studio'] = ', '.join(studio_matches) if studio_matches else '❌'
        
        # Source comparison
        comparison['source'] = f"{guess.source} {'✅' if guess.source == self.target.source else '❌'}"
        
        # Format comparison
        comparison['format'] = f"{guess.format} {'✅' if guess.format == self.target.format else '❌'}"
        
        # Season comparison
        comparison['season'] = f"{guess.season} {'✅' if guess.season == self.target.season else '❌'}"
        
        # Themes comparison - show individual matches
        guess_themes = set(guess.themes)
        target_themes = set(self.target.themes)
        if guess_themes == target_themes:
            comparison['themes'] = f"{', '.join(sorted(guess.themes))} ✅"
        else:
            # Show individual theme matches
            theme_matches = []
            for theme in guess.themes:
                if theme in target_themes:
                    theme_matches.append(f"{theme} ✅")
                else:
                    theme_matches.append(f"{theme} ❌")
            comparison['themes'] = ', '.join(theme_matches) if theme_matches else '❌'
        
        return comparison


class AnidleCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.games: Dict[int, Anidle] = {}  # channel_id -> game
        self.jikan_base_url = "https://api.jikan.moe/v4"
        self.page_cache: Dict[str, int] = {}  # Cache for max page results
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
    
    async def _get_max_page_from_jikan(self, sort_method: str) -> int:
        """Get the maximum page number from Jikan API pagination info."""
        # Create cache key
        cache_key = f"general-{sort_method}"
        
        # Check if result is already cached
        if cache_key in self.page_cache:
            cached_result = self.page_cache[cache_key]
            self.logger.info(f"Using cached max page: {cached_result} for sort method {sort_method}")
            return cached_result
        
        try:
            # Query first page to get pagination info
            params = {
                'page': 1,
                'limit': 25,  # Jikan default limit
                'order_by': sort_method,
                'sort': 'desc'
            }
            
            data = await self._query_jikan('/anime', params)
            
            if data and data.get('pagination'):
                # Use last_visible_page from Jikan's pagination response
                max_page = data['pagination'].get('last_visible_page', 1)
                
                # Cache the result
                self.page_cache[cache_key] = max_page
                self.logger.info(f"Jikan API returned max page: {max_page} for sort method {sort_method}")
                return max_page
            else:
                self.logger.warning(f"No pagination data found for sort method {sort_method}")
                return 1
            
        except Exception as e:
            self.logger.error(f"Error getting max page from Jikan API: {e}")
            return 1  # Fallback to page 1

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

    async def _get_random_anime(self, difficulty: str = "normal") -> Optional[AnimeData]:
        """Get a random anime for the game using weighted selection based on selection ranges and difficulty."""
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
            
            # Add common parameters
            api_params.update({
                'limit': 25
            })
            
            # Query anime using Jikan API
            data = await self._query_jikan('/anime', api_params)
            if data and data.get('data'):
                anime_list = data['data']
                if anime_list:
                    # Filter results based on selection method if needed
                    if selection_method == 'popularity':
                        # For popularity selection, filter by actual rank within range
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
                    anime_score = selected_anime.get('score', 'N/A')
                    anime_popularity = selected_anime.get('popularity', 'N/A')
                    
                    self.logger.info(f"Selected anime: {anime_title} (Score: {anime_score}, Popularity: {anime_popularity})")
                    return AnimeData(selected_anime)
            
            # Fallback if no results found
            self.logger.warning(f"No anime found with {selection_method} selection, trying fallback")
            fallback_params = {
                'page': random.randint(1, 10),
                'limit': 25,
                'order_by': sort_method
            }
            
            data = await self._query_jikan('/anime', fallback_params)
            if data and data.get('data') and data['data']:
                selected_anime = random.choice(data['data'])
                anime_title = selected_anime.get('title', 'Unknown')
                self.logger.info(f"Fallback selected anime: {anime_title}")
                return AnimeData(selected_anime)
            
            self.logger.error("Could not retrieve any anime from API")
            return None
            
        except Exception as e:
            self.logger.error(f"Error in anime selection: {e}")
            return None

    async def _search_anime(self, search_term: str) -> Optional[AnimeData]:
        """Search for an anime by name using Jikan API."""
        try:
            params = {
                'q': search_term,
                'limit': 1
            }
            
            data = await self._query_jikan('/anime', params)
            
            if data and data.get('data') and data['data']:
                return AnimeData(data['data'][0])
            
            return None
        except Exception as e:
            self.logger.error(f"Error searching anime: {e}")
            return None
    
    async def _search_multiple_anime_cached(self, search_term: str, limit: int = 25) -> List[Dict[str, str]]:
        """Search for multiple anime with caching for autocomplete efficiency."""
        if not search_term or len(search_term.strip()) < 2:  # Reduced to 2 characters for better UX
            return []
        
        # Create cache key
        search_key = search_term.lower().strip()
        
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
            if data.get('data'):
                for anime in data['data']:
                    anime_data = AnimeData(anime)
                    
                    # Get all possible titles for this anime (already filtered for Latin characters)
                    all_titles = anime_data.get_all_titles()
                    
                    # Filter titles that contain the search term (case-insensitive)
                    search_lower = clean_term.lower()
                    matching_titles = [
                        title for title in all_titles 
                        if search_lower in title.lower()
                    ]
                    
                    # If no direct matches in filtered titles, include the main title anyway
                    # since Jikan's search already filtered relevant results
                    if not matching_titles and anime_data.title:
                        matching_titles = [anime_data.title]
                    
                    # Add each matching title as a choice
                    for title in matching_titles[:3]:  # Limit to 3 titles per anime to avoid clutter
                        if len(choices) < 25:  # Discord limit
                            # Create display name with year for clarity
                            display_name = f"{title}"
                            if anime_data.year:
                                display_name += f" ({anime_data.year})"
                            
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
            self.logger.warning(f"Autocomplete timeout for query: '{current}'")
            return []
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error(f"Error in anime autocomplete: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in autocomplete: {e}")
            return []
    
    def _create_guess_embed(self, game: Anidle, guess: AnimeData, comparison: Dict[str, str]) -> discord.Embed:
        """Create an embed showing the guess results."""
        total_guesses = len(game.guesses) + game.hint_penalty
        
        # Get difficulty emoji
        difficulty_emojis = {
            "easy": "🟢",
            "normal": "🟡", 
            "hard": "🟠",
            "expert": "🔴",
            "crazy": "🟣",
            "insanity": "⚫"
        }
        difficulty_emoji = difficulty_emojis.get(game.difficulty, "🟡")
        
        embed = discord.Embed(
            title=f"Anidle {difficulty_emoji} - Guess {total_guesses}/{game.max_guesses}",
            color=0x02A9FF
        )
        
        # Add guess information
        embed.add_field(
            name="🎯 Your Guess",
            value=f"**{guess.title}**",
            inline=False
        )
        
        # Create comparison table
        comparison_text = (
            f"**Title:** {comparison['title']}\n"
            f"**Year:** {comparison['year']}\n"
            f"**Score:** {comparison['score']}\n"
            f"**Episodes:** {comparison['episodes']}\n"
            f"**Source:** {comparison['source']}\n"
            f"**Format:** {comparison['format']}\n"
            f"**Season:** {comparison['season']}"
        )
        
        embed.add_field(
            name="📊 Comparison",
            value=comparison_text,
            inline=False
        )
        
        # Add genres comparison separately to handle longer text
        embed.add_field(
            name="🎭 Genres",
            value=comparison['genres'],
            inline=False
        )
        
        # Add studio comparison separately to handle longer text
        embed.add_field(
            name="🏢 Studio",
            value=comparison['studio'],
            inline=False
        )
        
        # Add themes comparison separately to handle longer text
        embed.add_field(
            name="🎨 Themes",
            value=comparison['themes'],
            inline=False
        )
        
        # # Add legend
        # legend = (
        #     "**Legend:**\n"
        #     "✅ = Correct/Match\n"
        #     "⬆️ = Target is higher\n"
        #     "⬇️ = Target is lower\n"
        #     "❌ = Incorrect/No match"
        # )
        # embed.add_field(name="ℹ️ Legend", value=legend, inline=False)
        
        return embed
    
    def _create_game_over_embed(self, game: Anidle) -> discord.Embed:
        """Create an embed for game completion."""
        total_guesses = len(game.guesses) + game.hint_penalty
        
        # Get difficulty descriptions
        difficulty_descriptions = {
            "easy": "🟢 Easy",
            "normal": "🟡 Normal", 
            "hard": "🟠 Hard",
            "expert": "🔴 Expert",
            "crazy": "🟣 Crazy",
            "insanity": "⚫ Insanity"
        }
        difficulty_text = difficulty_descriptions.get(game.difficulty, "🟡 Normal")
        
        if game.is_won:
            embed = discord.Embed(
                title="🎉 Congratulations!",
                description=f"You guessed it in {total_guesses} tries!\n**Difficulty:** {difficulty_text}",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(
                title="💀 Game Over!",
                description=f"Better luck next time!\n**Difficulty:** {difficulty_text}",
                color=0xFF0000
            )
        
        # Show the target anime
        target_info = (
            f"**Title:** {game.target.title}\n"
            f"**Year:** {game.target.year}\n"
            f"**Score:** {game.target.score}/10\n"
            f"**Episodes:** {game.target.episodes}\n"
            f"**Genres:** {', '.join(game.target.genres)}\n"
            f"**Studio:** {', '.join(game.target.studios)}\n"
            f"**Source:** {game.target.source}\n"
            f"**Format:** {game.target.format}\n"
            f"**Season:** {game.target.season}\n"
            f"**Themes:** {', '.join(game.target.themes)}"
        )
        
        embed.add_field(
            name="🎯 The Answer",
            value=target_info,
            inline=False
        )
        
        return embed
    
    @app_commands.command(
        name="anidle",
        description="Play Anidle! Guess the anime based on its properties."
    )
    @app_commands.describe(
        action="Choose an action",
        guess="Anime name to guess (only for 'guess' action)",
        difficulty="Choose difficulty level (only for 'start' action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Start New Game", value="start"),
        app_commands.Choice(name="Make a Guess", value="guess"),
        app_commands.Choice(name="Get Hint", value="hint"),
        app_commands.Choice(name="Game Status", value="status"),
        app_commands.Choice(name="Give Up", value="giveup")
    ])
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="Easy - Popular & Well-known Anime", value="easy"),
        app_commands.Choice(name="Normal - Mixed Selection", value="normal"),
        app_commands.Choice(name="Hard - Obscure & Lesser-known", value="hard"),
        app_commands.Choice(name="Expert - Ultra Obscure & Hidden Gems", value="expert"),
        app_commands.Choice(name="Crazy - Extremely Obscure & Challenging", value="crazy"),
        app_commands.Choice(name="Insanity - The Most Impossible Challenge", value="insanity")
    ])
    @app_commands.autocomplete(guess=anime_autocomplete)
    async def anidle(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        guess: Optional[str] = None,
        difficulty: Optional[app_commands.Choice[str]] = None
    ):
        """Main anidle command."""
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
            await self._make_guess(interaction, channel_id, guess or "")
        elif action.value == "hint":
            await self._give_hint(interaction, channel_id)
        elif action.value == "status":
            await self._show_status(interaction, channel_id)
        elif action.value == "giveup":
            await self._give_up(interaction, channel_id)
    
    async def _start_game(self, interaction: discord.Interaction, channel_id: int, difficulty: str = "normal"):
        """Start a new anidle game with specified difficulty."""
        # Defer immediately to prevent timeout
        await interaction.response.defer(thinking=True)
        
        # Check if there's already an active game in this channel
        if channel_id in self.games:
            existing_game = self.games[channel_id]
            if not existing_game.is_complete:
                await interaction.followup.send(
                    "❌ You already have an active game in this channel! "
                    "Complete it first or wait for it to timeout. Use `/anidle` to continue your current game.",
                    ephemeral=True
                )
                return
            else:
                # Clean up completed game before starting new one
                del self.games[channel_id]

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
            target_anime = await self._get_random_anime(difficulty)
            if not target_anime:
                await interaction.followup.send(
                    "❌ Failed to fetch anime data. Please try again later!",
                    ephemeral=True
                )
                return
            
            self.games[channel_id] = Anidle(target_anime, difficulty)
            
            # Get difficulty description
            difficulty_descriptions = {
                "easy": "🟢 **Easy** - Popular & Well-known Anime",
                "normal": "🟡 **Normal** - Mixed Selection", 
                "hard": "🟠 **Hard** - Obscure & Lesser-known",
                "expert": "🔴 **Expert** - Ultra Obscure & Hidden Gems",
                "crazy": "🟣 **Crazy** - Extremely Obscure & Challenging",
                "insanity": "⚫ **Insanity** - The Most Impossible Challenge"
            }
            
            embed = discord.Embed(
                title="🎮 Anidle Started!",
                description=(
                    f"Guess the anime! You have 21 tries.\n"
                    f"**Difficulty:** {difficulty_descriptions.get(difficulty, '🟡 **Normal**')}\n\n"
                    f"Use `/anidle guess <anime_name>` to make a guess.\n\n"
                    f"**Properties to match:**\n"
                    f"• Title, Year, Score, Episodes\n"
                    f"• Genres, Studio, Source, Format\n"
                    f"• Season, Themes"
                ),
                color=0x02A9FF
            )
            
            embed.add_field(
                name="ℹ️ How to Play",
                value=(
                    "**Arrows indicate:**\n"
                    "⬆️ Target value is higher\n"
                    "⬇️ Target value is lower\n"
                    "✅ Exact match\n"
                    "❌ No match"
                ),
                inline=False
            )
            
            # Add difficulty explanation
            difficulty_explanations = {
                "easy": "Focuses on mainstream, popular anime that most people have heard of.",
                "normal": "Balanced mix of popular and lesser-known anime.",
                "hard": "Emphasizes obscure, underrated, or niche anime series.",
                "expert": "Ultra challenging with the most obscure and unknown anime.",
                "crazy": "Extremely challenging with very obscure and forgotten anime.",
                "insanity": "The ultimate challenge - only the most impossible and unknown anime."
            }
            
            embed.add_field(
                name="🎯 Difficulty Info",
                value=f"{difficulty_explanations.get(difficulty, 'Balanced mix of popular and lesser-known anime.')}\n*Weights are configurable in config.yml*",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            self.logger.info(f"Started anidle game in channel {channel_id} with target: {target_anime.title} (Difficulty: {difficulty})")
            
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            self.logger.error(f"Error starting anidle game: {e}")
            await interaction.followup.send(
                "❌ An error occurred while starting the game. Please try again!",
                ephemeral=True
            )
    
    async def _make_guess(self, interaction: discord.Interaction, channel_id: int, guess: str):
        """Make a guess in the anidle game."""
        # Check if there's an active game
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel! Use `/anidle start` to begin a new game.",
                ephemeral=True
            )
            return
        
        game = self.games[channel_id]
        
        # Check if game is already completed
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed! Start a new game with `/anidle start`.",
                ephemeral=True
            )
            return

        
        # Validate guess input
        if not guess or not guess.strip():
            await interaction.response.send_message(
                "❌ Please provide an anime name to guess! Use the autocomplete feature to help find the correct title.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(thinking=True)
        
        try:
            anime_data = await self._search_anime(guess.strip())
            if not anime_data:
                await interaction.followup.send(
                    f"❌ Couldn't find anime: '{guess}'. Please check the spelling and try again, or use the autocomplete feature for suggestions!",
                    ephemeral=True
                )
                return
            
            # Check if this anime has already been guessed
            for previous_guess in game.guesses:
                if previous_guess.id == anime_data.id:
                    await interaction.followup.send(
                        f"❌ You've already guessed '{anime_data.title}'! Try a different anime.",
                        ephemeral=True
                    )
                    return
            
            game.add_guess(anime_data)
            comparison = game.get_comparison(anime_data)
            
            # Send guess result
            guess_embed = self._create_guess_embed(game, anime_data, comparison)
            await interaction.followup.send(embed=guess_embed)
            
            # Check if game is complete
            if game.is_complete:
                game_over_embed = self._create_game_over_embed(game)
                await interaction.followup.send(embed=game_over_embed)
                
                # Clean up the game
                del self.games[channel_id]
                
                self.logger.info(f"Anidle game completed in channel {channel_id}. Won: {game.is_won}")
            
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            self.logger.error(f"Error making guess in anidle: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing your guess. Please try again!",
                ephemeral=True
            )
    
    async def _give_hint(self, interaction: discord.Interaction, channel_id: int):
        """Display the anime poster image and add 10 guess penalty."""
        # Check if there's an active game
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel! Use `/anidle start` to begin a new game.",
                ephemeral=False
            )
            return
        
        game = self.games[channel_id]
        
        # Check if game is already completed
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed! Start a new game with `/anidle start`.",
                ephemeral=False
            )
            return
        
        # Check if adding 10 to total guesses would exceed max_guesses (21)
        total_guesses = len(game.guesses) + game.hint_penalty
        if total_guesses + 10 > game.max_guesses:
            await interaction.response.send_message(
                f"❌ Cannot use hint! Adding 10 guesses would exceed the maximum limit of {game.max_guesses} guesses. Current total: {total_guesses}/{game.max_guesses}",
                ephemeral=False
            )
            return
        
        # Check if there are any guesses made yet (optional: you might want hints only after some attempts)
        if len(game.guesses) == 0:
            await interaction.response.send_message(
                "💡 **Hint available!** But consider making at least one guess first to get a feel for the game. Using a hint adds +10 to your guess count!",
                ephemeral=False
            )
            return
        
        # Add 10 guess penalty
        game.hint_penalty += 10
        total_guesses = len(game.guesses) + game.hint_penalty
        
        embed = discord.Embed(
            title="🖼️ Poster Hint!",
            description=f"Here's the poster for the anime you're looking for!\n**Penalty**: +10 guesses (Total: {total_guesses}/{game.max_guesses})",
            color=0xFFD700
        )
        
        # Add poster image if available
        if game.target.cover_image:
            embed.set_image(url=game.target.cover_image)
        else:
            embed.add_field(
                name="⚠️ No Image Available",
                value="Poster image is not available for this anime.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    async def _give_up(self, interaction: discord.Interaction, channel_id: int):
        """Give up the current game."""
        # Check if there's an active game
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel! Use `/anidle start` to begin a new game.",
                ephemeral=True
            )
            return
        
        game = self.games[channel_id]
        
        # Check if game is already completed
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed! The results were already shown.",
                ephemeral=True
            )
            return
        
        # Check if any guesses have been made
        if len(game.guesses) == 0:
            await interaction.response.send_message(
                "❓ Are you sure you want to give up without making any guesses? Try at least one guess first!",
                ephemeral=True
            )
            return
        
        # End the game
        game.is_complete = True
        game.is_won = False
        
        game_over_embed = self._create_game_over_embed(game)
        await interaction.response.send_message(embed=game_over_embed)
        
        # Clean up
        del self.games[channel_id]
        
        self.logger.info(f"User gave up anidle game in channel {channel_id} after {len(game.guesses)} guesses")
    
    async def _show_status(self, interaction: discord.Interaction, channel_id: int):
        """Show the current game status."""
        # Check if there's an active game
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel! Use `/anidle start` to begin a new game.",
                ephemeral=True
            )
            return
        
        game = self.games[channel_id]
        
        # Check if game is already completed
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed! The results were already shown. Use `/anidle start` to begin a new game.",
                ephemeral=True
            )
            return
        
        total_guesses = len(game.guesses) + game.hint_penalty
        remaining_guesses = game.max_guesses - total_guesses
        
        # Get difficulty description
        difficulty_descriptions = {
            "easy": "🟢 Easy - Popular & Well-known",
            "normal": "🟡 Normal - Mixed Selection", 
            "hard": "🟠 Hard - Obscure & Lesser-known",
            "expert": "🔴 Expert - Ultra Obscure & Hidden Gems",
            "crazy": "🟣 Crazy - Extremely Obscure & Challenging",
            "insanity": "⚫ Insanity - The Most Impossible Challenge"
        }
        
        embed = discord.Embed(
            title="📊 Game Status",
            color=0x02A9FF
        )
        
        embed.add_field(
            name="🎯 Progress",
            value=(
                f"**Difficulty:** {difficulty_descriptions.get(game.difficulty, '🟡 Normal')}\n"
                f"**Guesses Made:** {len(game.guesses)}\n"
                f"**Hint Penalty:** +{game.hint_penalty}\n"
                f"**Total Used:** {total_guesses}/{game.max_guesses}\n"
                f"**Remaining:** {remaining_guesses}"
            ),
            inline=False
        )
        
        if len(game.guesses) > 0:
            recent_guesses = game.guesses[-3:]  # Show last 3 guesses
            guess_list = []
            for i, guess in enumerate(recent_guesses):
                guess_number = len(game.guesses) - len(recent_guesses) + i + 1
                guess_list.append(f"{guess_number}. {guess.title}")
            
            embed.add_field(
                name="🕰️ Recent Guesses",
                value="\n".join(guess_list),
                inline=False
            )
        
        embed.add_field(
            name="ℹ️ Available Actions",
            value=(
                "• `/anidle guess <anime>` - Make a guess\n"
                "• `/anidle hint` - Get poster hint (+10 penalty)\n"
                "• `/anidle giveup` - End the game"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function for cog loading."""
    # Get services from bot instance
    services = getattr(bot, 'services', None)
    if services:
        await bot.add_cog(AnidleCog(bot, services))
    else:
        # Fallback if services not available
        raise RuntimeError("Bot services not available")
