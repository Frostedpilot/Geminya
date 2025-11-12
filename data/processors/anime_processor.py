#!/usr/bin/env python3
"""Anime Processor for MAL anime data collection and processing.

This module extracts all anime-specific logic from pull_from_mal.py and character_edit.py
into a unified processor that integrates with the new multi-media system.
"""

import asyncio
import aiohttp
import json
import os
import sys
import logging
from typing import List, Dict, Optional, Tuple, Any, Set
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.processors.base_processor import BaseProcessor
from services.mal_api import MALAPIService
from config import Config

# Setup logging
logger = logging.getLogger(__name__)


class AnimeProcessor(BaseProcessor):
    """Processor for MAL anime data collection and processing.
    
    This processor handles:
    1. MAL OAuth authentication
    2. Fetching user's anime list
    3. Getting detailed anime information
    4. Collecting characters from anime
    5. Applying anime-specific filtering and processing
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the anime processor.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Initialize MAL service
        try:
            self.app_config = Config.create()
            self.mal_service = None
        except Exception as e:
            logger.error("Failed to initialize MAL config: %s", e)
            self.app_config = None
        
        # Track processed IDs to avoid duplicates within this session
        self.processed_character_ids: Set[int] = set()
        self.processed_anime_ids: Set[int] = set()
        
        # Load existing MAL IDs from lookup files
        self.existing_anime_ids = self._load_existing_anime_ids()
        self.existing_character_ids = self._load_existing_character_ids()

    # ===== ABSTRACT METHOD IMPLEMENTATIONS =====
    
    def get_source_type(self) -> str:
        """Return the source type identifier for MAL anime."""
        return "mal"
    
    def is_configured(self) -> bool:
        """Check if processor is properly configured for MAL."""
        if self.app_config is None:
            return False
        try:
            return (
                hasattr(self.app_config, 'mal_client_id') and
                hasattr(self.app_config, 'mal_client_secret') and
                bool(self.app_config.mal_client_id) and
                bool(self.app_config.mal_client_secret)
            )
        except Exception:
            return False

    def standardize_series_data(self, raw_series: Dict) -> Dict:
        """Standardize MAL anime series data to common format.
        
        Converts MAL anime format to standardized series format.
        """
        return {
            'source_type': 'mal',
            'source_id': str(raw_series.get('mal_id') or raw_series.get('id')),
            'name': raw_series.get('title', 'Unknown'),
            'english_name': raw_series.get('title_english', ''),
            'creator': json.dumps({"studio": raw_series.get('studios', '')}),
            'media_type': 'anime',
            'image_link': raw_series.get('image_url', ''),
            'genres': raw_series.get('genres', ''),
            'synopsis': raw_series.get('synopsis', ''),
            'favorites': int(raw_series.get('favorites', 0)),
            'members': int(raw_series.get('members', 0)),
            'score': float(raw_series.get('score', 0.0))
        }
    
    def standardize_character_data(self, raw_character: Dict) -> Dict:
        """Standardize MAL character data to common format.
        
        Converts MAL character format to standardized character format.
        Includes logic extracted from character_edit.py for series lookup.
        """
        # Get series name from anime lookup (extracted from character_edit.py)
        series_mal_id = str(raw_character.get("series_mal_id", ""))
        
        return {
            'source_type': 'mal',
            'source_id': str(raw_character.get('mal_id') or raw_character.get('id')),
            'name': raw_character.get('name', 'Unknown'),
            'series': f'Unknown Series (MAL ID: {series_mal_id})',  # Will be resolved later
            'series_source_id': series_mal_id,
            'genre': 'anime',  # All MAL data is anime for this processor
            'image_url': raw_character.get('image_url', ''),
            'about': raw_character.get('about', ''),
            'favorites': int(raw_character.get('favorites', 0))
        }

    # ===== HELPER METHODS =====
    
    def _load_existing_anime_ids(self) -> Set[int]:
        """Load existing anime IDs from lookup file."""
        lookup_file = Path("data/registries/anime/existing_anime_ids.json")
        try:
            with open(lookup_file, 'r', encoding='utf-8') as f:
                anime_ids = json.load(f)
                return set(anime_ids)
        except FileNotFoundError:
            logger.info("No existing anime lookup file found - will process all anime")
            return set()
        except Exception as e:
            logger.warning("Error loading existing anime IDs: %s", e)
            return set()
    
    def _load_existing_character_ids(self) -> Set[int]:
        """Load existing character IDs from lookup file."""
        lookup_file = Path("data/registries/anime/existing_character_ids.json")
        try:
            with open(lookup_file, 'r', encoding='utf-8') as f:
                character_ids = json.load(f)
                return set(character_ids)
        except FileNotFoundError:
            logger.info("No existing character lookup file found - will process all characters")
            return set()
        except Exception as e:
            logger.warning("Error loading existing character IDs: %s", e)
            return set()
    
    def _is_series_already_mined(self, anime_id: int) -> bool:
        """Check if anime is already mined using lookup file."""
        return anime_id in self.existing_anime_ids
    
    def _is_character_already_mined(self, character_id: int) -> bool:
        """Check if character is already mined using lookup file."""
        return character_id in self.existing_character_ids
    
    def _update_lookup_files(self, processed_anime_ids: Set[int], processed_character_ids: Set[int]) -> None:
        """Update lookup files with newly processed IDs to prevent re-scraping."""
        try:
            # Update anime lookup file
            updated_anime_ids = self.existing_anime_ids.union(processed_anime_ids)
            anime_lookup_file = Path("data/registries/anime/existing_anime_ids.json")
            with open(anime_lookup_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(list(updated_anime_ids)), f, indent=2)
            logger.info("Updated anime lookup: added %d new anime IDs (total: %d)", 
                       len(processed_anime_ids), len(updated_anime_ids))
            
            # Update character lookup file  
            updated_character_ids = self.existing_character_ids.union(processed_character_ids)
            character_lookup_file = Path("data/registries/anime/existing_character_ids.json")
            with open(character_lookup_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(list(updated_character_ids)), f, indent=2)
            logger.info("Updated character lookup: added %d new character IDs (total: %d)", 
                       len(processed_character_ids), len(updated_character_ids))
                       
        except Exception as e:
            logger.error("Error updating lookup files: %s", e)

    # ===== MAL AUTHENTICATION (extracted from pull_from_mal.py) =====
    
    async def _authenticate_mal(self) -> bool:
        """Complete MAL OAuth authentication."""
        try:
            if not self.mal_service:
                if not self.app_config:
                    logger.error("App config not available")
                    return False
                    
                self.mal_service = MALAPIService(
                    self.app_config.mal_client_id, 
                    self.app_config.mal_client_secret
                )
                await self.mal_service.__aenter__()
            
            # Setup OAuth flow (extracted from original implementation)
            redirect_uri = "http://localhost:8080/callback"
            auth_url, code_verifier = self.mal_service.generate_auth_url(redirect_uri)
            
            logger.info("Please visit this URL to authorize the application:")
            logger.info(auth_url)
            logger.info("After authorization, you will be redirected to a localhost URL.")
            logger.info("Copy the 'code' parameter from the URL and paste it below.")
            
            auth_code = input("Enter authorization code: ").strip()
            
            logger.info("Exchanging authorization code for tokens...")
            tokens = await self.mal_service.exchange_code_for_tokens(
                auth_code, redirect_uri, code_verifier
            )

            if tokens:
                logger.info("✅ MAL authentication successful!")
                return True
            else:
                logger.error("❌ MAL authentication failed!")
                return False

        except Exception as e:
            logger.error("❌ MAL authentication error: %s", e)
            return False

    # ===== CHARACTER DETAILS (extracted from pull_from_mal.py) =====
    
    async def _get_character_details(self, character_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed character information from Jikan API."""
        try:
            # Skip if character already exists in lookup
            if self._is_character_already_mined(character_id):
                logger.debug("Skipping character %d - already mined", character_id)
                return None
                
            await asyncio.sleep(1.5)  # Rate limiting

            url = f"https://api.jikan.moe/v4/characters/{character_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        character = data.get("data", {})

                        # Apply filters: remove characters with 0 favorites
                        favorites = character.get("favorites", 0)
                        if favorites == 0:
                            logger.debug("Skipping character %d - 0 favorites", character_id)
                            # Add to processed IDs even though filtered out (to prevent re-scraping)
                            self.processed_character_ids.add(character_id)
                            return None

                        # Extract character data in MAL format
                        return {
                            "mal_id": character.get("mal_id"),
                            "id": character.get("mal_id"),  # Add source_id field for standardization
                            "name": character.get("name", "Unknown"),
                            "name_kanji": character.get("name_kanji", ""),
                            "nicknames": "|".join(character.get("nicknames", [])),
                            "about": character.get("about", ""),
                            "image_url": character.get("images", {}).get("jpg", {}).get("image_url", ""),
                            "favorites": favorites
                        }
                    elif response.status == 404:
                        logger.warning("Character %d not found on Jikan API (404)", character_id)
                        # Add to processed IDs to prevent re-scraping non-existent characters
                        self.processed_character_ids.add(character_id)
                        return None
                    elif response.status == 429:
                        logger.warning("Rate limited for character %d, waiting longer...", character_id)
                        await asyncio.sleep(5)
                        return await self._get_character_details(character_id)  # Retry once
                    else:
                        logger.warning("Failed to get character details for %d: HTTP %d", character_id, response.status)
                        # Don't add to processed IDs for temporary failures (might work next time)
                        return None

        except asyncio.TimeoutError:
            logger.error("Timeout getting character details for %d", character_id)
            # Don't add to processed IDs for timeouts (might work next time)
            return None
        except Exception as e:
            logger.error("Error getting character details for %d: %s", character_id, e)
            # Don't add to processed IDs for generic errors (might work next time)
            return None

    # ===== ANIME DETAILS (extracted from pull_from_mal.py) =====
    
    async def _get_anime_details(self, anime_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed anime information from Jikan API."""
        try:
            # Note: We now process ALL anime (existing + new) for complete output
            # The user will handle filtering what's new vs existing manually
                
            await asyncio.sleep(1.5)  # Rate limiting

            url = f"https://api.jikan.moe/v4/anime/{anime_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        anime = data.get("data", {})

                        # Combine genres and themes for the genres field
                        genres_list = anime.get("genres", [])
                        themes_list = anime.get("themes", [])
                        all_genres = genres_list + themes_list
                        genres_and_themes = "|".join([g.get("name", "") for g in all_genres])

                        # Extract anime data in MAL format
                        return {
                            "mal_id": anime.get("mal_id"),
                            "id": anime.get("mal_id"),  # Add source_id field for standardization
                            "title": anime.get("title", "Unknown"),
                            "title_english": anime.get("title_english", ""),
                            "title_japanese": anime.get("title_japanese", ""),
                            "type": anime.get("type", ""),
                            "episodes": anime.get("episodes", 0),
                            "status": anime.get("status", ""),
                            "aired_from": anime.get("aired", {}).get("from", ""),
                            "aired_to": anime.get("aired", {}).get("to", ""),
                            "score": anime.get("score", 0.0),
                            "scored_by": anime.get("scored_by", 0),
                            "rank": anime.get("rank", 0),
                            "popularity": anime.get("popularity", 0),
                            "members": anime.get("members", 0),
                            "favorites": anime.get("favorites", 0),
                            "synopsis": anime.get("synopsis", ""),
                            "image_url": anime.get("images", {}).get("jpg", {}).get("large_image_url", ""),
                            "genres": genres_and_themes,
                            "studios": "|".join([s.get("name", "") for s in anime.get("studios", [])])
                        }
                    elif response.status == 404:
                        logger.warning("Anime %d not found on Jikan API (404)", anime_id)
                        return None
                    elif response.status == 429:
                        logger.warning("Rate limited for anime %d, waiting longer...", anime_id)
                        await asyncio.sleep(5)
                        return await self._get_anime_details(anime_id)  # Retry once
                    else:
                        logger.warning("Failed to get anime details for %d: HTTP %d", anime_id, response.status)
                        return None

        except asyncio.TimeoutError:
            logger.error("Timeout getting anime details for %d", anime_id)
            return None
        except Exception as e:
            logger.error("Error getting anime details for %d: %s", anime_id, e)
            return None

    # ===== ANIME CHARACTER COLLECTION (extracted from pull_from_mal.py) =====
    
    async def _get_anime_characters(self, anime_id: int) -> List[Dict[str, Any]]:
        """Get characters from an anime using Jikan API."""
        try:
            await asyncio.sleep(1.5)  # Rate limiting
            
            url = f"https://api.jikan.moe/v4/anime/{anime_id}/characters"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        characters = []
                        
                        total_chars = len(data.get("data", []))
                        logger.info("  Found %d characters in anime %d", total_chars, anime_id)

                        for char_data in data.get("data", []):
                            character = char_data.get("character", {})
                            character_id = character.get("mal_id")

                            if character_id and character_id not in self.processed_character_ids:
                                logger.debug("Processing character %d from anime %d: %s", 
                                           character_id, anime_id, character.get('name', 'Unknown'))

                                # Get detailed character information
                                character_details = await self._get_character_details(character_id)

                                if character_details:
                                    # Add series information for anime
                                    character_details["series_type"] = "anime"
                                    character_details["series_mal_id"] = anime_id
                                    characters.append(character_details)
                                
                                # Always add to processed IDs (whether successful or filtered)
                                # This prevents re-scraping both good and bad characters
                                self.processed_character_ids.add(character_id)
                            elif character_id in self.processed_character_ids:
                                logger.debug("  Skipped character %d - already processed", character_id)

                        return characters
                    elif response.status == 404:
                        logger.warning("Anime %d not found on Jikan API (404)", anime_id)
                        return []
                    elif response.status == 429:
                        logger.warning("Rate limited for anime %d, waiting longer...", anime_id)
                        await asyncio.sleep(5)
                        return await self._get_anime_characters(anime_id)  # Retry once
                    else:
                        logger.warning("Failed to get characters for anime %d: HTTP %d", anime_id, response.status)
                        return []

        except asyncio.TimeoutError:
            logger.error("Timeout getting characters for anime %d", anime_id)
            return []
        except Exception as e:
            logger.error("Error getting characters for anime %d: %s", anime_id, e)
            return []

    # ===== MAIN DATA PULLING IMPLEMENTATION =====
    
    async def pull_raw_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Pull raw anime and character data from MAL.
        
        Skips series that are already in the ID registry to avoid 
        re-mining existing data.
        
        Returns:
            Tuple of (raw_series_list, raw_characters_list)
        """
        try:
            logger.info("🎌 Starting MAL anime data pulling...")

            # Authenticate with MAL
            if not await self._authenticate_mal():
                logger.error("MAL authentication failed")
                return [], []

            # Get user's anime list (ONLY anime, not manga)
            logger.info("📺 Fetching user's anime list...")
            if not self.mal_service:
                logger.error("MAL service not initialized")
                return [], []
                
            anime_list = await self.mal_service.get_user_anime_list()
            logger.info("Found %d anime in user's MAL list", len(anime_list))

            # Collect all characters and anime data
            all_characters = []
            all_anime = []

            # Process ONLY anime (not manga) - Skip existing anime like the old script
            for i, anime in enumerate(anime_list, 1):
                anime_id = anime["id"]
                title = anime["title"]

                # Skip if series already exists in lookup
                if self._is_series_already_mined(anime_id):
                    logger.info("Skipping anime %d/%d: %s - already mined", 
                               i, len(anime_list), title)
                    continue
                
                logger.info("Processing anime %d/%d: %s", i, len(anime_list), title)
                
                # Get anime details
                anime_details = await self._get_anime_details(anime_id)
                if anime_details:
                    all_anime.append(anime_details)
                    self.processed_anime_ids.add(anime_id)

                # Get characters from anime
                characters = await self._get_anime_characters(anime_id)
                all_characters.extend(characters)

                logger.info("  Found %d new characters", len(characters))

            # Summary statistics
            total_anime_in_list = len(anime_list)
            anime_already_existed = len([a for a in anime_list if self._is_series_already_mined(a["id"])])
            anime_processed = total_anime_in_list - anime_already_existed

            logger.info("✅ Successfully pulled anime data from MAL!")
            logger.info("📊 Processing Summary:")
            logger.info("   - Total anime in MAL list: %d", total_anime_in_list)
            logger.info("   - Anime already mined (skipped): %d", anime_already_existed)
            logger.info("   - Anime processed: %d", anime_processed)
            logger.info("   - New anime pulled: %d", len(all_anime))
            logger.info("   - New characters pulled: %d", len(all_characters))
            
            if anime_processed > len(all_anime):
                logger.warning("⚠️  %d anime were processed but not added (likely due to API errors or rate limiting)", 
                             anime_processed - len(all_anime))
            
            # Update lookup files with all processed IDs (including filtered ones)
            # This prevents re-scraping both successful and filtered data
            logger.info("🔄 Updating lookup files...")
            self._update_lookup_files(self.processed_anime_ids, self.processed_character_ids)
            
            return all_anime, all_characters

        except Exception as e:
            logger.error("❌ Error during MAL anime data pulling: %s", e)
            return [], []

    # ===== UTILITY METHODS =====
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for this processor."""
        stats = super().get_processing_stats()
        stats.update({
            'mal_service_initialized': self.mal_service is not None,
            'existing_anime_loaded': len(self.existing_anime_ids),
            'existing_characters_loaded': len(self.existing_character_ids),
            'processed_character_ids': len(self.processed_character_ids),
            'processed_anime_ids': len(self.processed_anime_ids)
        })
        return stats

    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.mal_service:
            # Clean up MAL service if needed
            pass


# ===== TESTING =====

async def test_anime_processor():
    """Test the anime processor."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    
    print("Testing Anime Processor...")
    
    try:
        async with AnimeProcessor() as processor:
            # Check configuration
            print(f"Configured: {processor.is_configured()}")
            print(f"Source type: {processor.get_source_type()}")
            
            # Check stats
            stats = processor.get_processing_stats()
            print(f"Stats: {stats}")
            
            # Note: Full testing requires MAL authentication
            # For now, just test initialization
            print("✅ Anime Processor initialization test completed!")
            
    except Exception as e:
        print(f"❌ Error testing anime processor: {e}")


if __name__ == "__main__":
    asyncio.run(test_anime_processor())