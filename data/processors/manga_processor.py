#!/usr/bin/env python3
"""Manga Processor for MAL manga data collection and processing.

This module handles manga-specific data collection from MAL and Jikan API,
integrating with the multi-media system architecture.
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


class MangaProcessor(BaseProcessor):
    """Processor for MAL manga data collection and processing.
    
    This processor handles:
    1. MAL OAuth authentication
    2. Fetching user's manga list
    3. Getting detailed manga information
    4. Collecting characters from manga
    5. Applying manga-specific filtering and processing
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the manga processor.
        
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
        self.processed_manga_ids: Set[int] = set()
        
        # Load existing MAL IDs from lookup files
        self.existing_manga_ids = self._load_existing_manga_ids()
        self.existing_character_ids = self._load_existing_character_ids()
        
        # HTTP session for API requests
        self.session: Optional[aiohttp.ClientSession] = None

    # ===== ABSTRACT METHOD IMPLEMENTATIONS =====
    
    def get_source_type(self) -> str:
        """Return the source type identifier for MAL manga."""
        return "mal_manga"
    
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
        """Standardize MAL manga series data to common format.
        
        Converts MAL manga format to standardized series format.
        """
        return {
            'source_type': 'mal_manga',
            'source_id': str(raw_series.get('mal_id') or raw_series.get('id')),
            'name': raw_series.get('title', 'Unknown'),
            'english_name': raw_series.get('title_english', ''),
            'creator': json.dumps({
                "author": raw_series.get('authors', ''),
                "serialization": raw_series.get('serializations', '')
            }),
            'media_type': 'manga',
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
        Uses directly passed series title when available, fallback to file lookup.
        """
        # Get series name from manga lookup
        series_mal_id = str(raw_character.get("series_mal_id", ""))
        
        # Use directly passed series title if available, otherwise resolve from files
        if "series_title" in raw_character and raw_character["series_title"]:
            series_name = raw_character["series_title"]
        else:
            # Fallback to file-based resolution for backwards compatibility
            series_name = self._resolve_series_name(series_mal_id)
        
        # Add (Manga) suffix to character name to differentiate from anime version
        character_name = raw_character.get('name', 'Unknown')
        if character_name != 'Unknown' and not character_name.endswith('(Manga)'):
            character_name = f"{character_name} (Manga)"
        
        return {
            'source_type': 'mal_manga',
            'source_id': str(raw_character.get('mal_id') or raw_character.get('id')),
            'name': character_name,
            'series': series_name,
            'series_source_id': series_mal_id,
            'genre': 'Manga',  # Formal name for manga genre
            'image_url': raw_character.get('image_url', ''),
            'about': raw_character.get('about', ''),
            'favorites': int(raw_character.get('favorites', 0))
        }

    def _resolve_series_name(self, series_mal_id: str) -> str:
        """Resolve series name from MAL ID using processed series data.
        
        Args:
            series_mal_id: MAL series ID as string
            
        Returns:
            Resolved series name or fallback with ID
        """
        if not series_mal_id:
            return "Unknown Series"
            
        # Try to load and search series_processed.csv for the series name
        try:
            import pandas as pd
            series_file = Path("data/intermediate/series_processed.csv")
            
            if series_file.exists():
                df = pd.read_csv(series_file)
                # Look for matching source_type AND source_id in the series data
                matching_series = df[
                    (df['source_type'] == 'mal_manga') & 
                    (df['source_id'].astype(str) == str(series_mal_id))
                ]
                
                if not matching_series.empty:
                    series_name = matching_series.iloc[0]['name']
                    logger.debug("Resolved series %s -> %s", series_mal_id, series_name)
                    return series_name
        
        except Exception as e:
            logger.debug("Could not resolve series name for %s: %s", series_mal_id, e)
        
        # Fallback to ID-based name if lookup fails
        return f"Unknown Series (MAL ID: {series_mal_id})"

    # ===== ID LOOKUP FILE MANAGEMENT =====
    
    def _load_existing_manga_ids(self) -> Set[int]:
        """Load existing manga IDs from lookup file to avoid re-scraping."""
        try:
            lookup_file = Path("data/registries/manga/existing_manga_ids.json")
            if lookup_file.exists():
                with open(lookup_file, 'r', encoding='utf-8') as f:
                    ids = json.load(f)
                logger.info("Loaded %d existing manga IDs from lookup file", len(ids))
                return set(ids)
            else:
                logger.info("No existing manga lookup file found - creating new one")
                # Create directory and empty file
                lookup_file.parent.mkdir(parents=True, exist_ok=True)
                with open(lookup_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                return set()
        except Exception as e:
            logger.error("Error loading manga lookup file: %s", e)
            return set()

    def _load_existing_character_ids(self) -> Set[int]:
        """Load existing character IDs from lookup file to avoid re-scraping."""
        try:
            lookup_file = Path("data/registries/manga/existing_character_ids.json")
            if lookup_file.exists():
                with open(lookup_file, 'r', encoding='utf-8') as f:
                    ids = json.load(f)
                logger.info("Loaded %d existing character IDs from manga lookup file", len(ids))
                return set(ids)
            else:
                logger.info("No existing manga character lookup file found - creating new one")
                # Create directory and empty file
                lookup_file.parent.mkdir(parents=True, exist_ok=True)
                with open(lookup_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                return set()
        except Exception as e:
            logger.error("Error loading manga character lookup file: %s", e)
            return set()
    
    def _is_series_already_mined(self, manga_id: int) -> bool:
        """Check if manga is already mined using lookup file."""
        return manga_id in self.existing_manga_ids
    
    def _is_character_already_mined(self, character_id: int) -> bool:
        """Check if character is already mined using lookup file."""
        return character_id in self.existing_character_ids
    
    def _update_lookup_files(self, processed_manga_ids: Set[int], processed_character_ids: Set[int]) -> None:
        """Update lookup files with newly processed IDs to prevent re-scraping."""
        try:
            # Update manga lookup file
            updated_manga_ids = self.existing_manga_ids.union(processed_manga_ids)
            manga_lookup_file = Path("data/registries/manga/existing_manga_ids.json")
            with open(manga_lookup_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(list(updated_manga_ids)), f, indent=2)
            logger.info("Updated manga lookup: added %d new manga IDs (total: %d)", 
                       len(processed_manga_ids), len(updated_manga_ids))
            
            # Update character lookup file  
            updated_character_ids = self.existing_character_ids.union(processed_character_ids)
            character_lookup_file = Path("data/registries/manga/existing_character_ids.json")
            with open(character_lookup_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(list(updated_character_ids)), f, indent=2)
            logger.info("Updated manga character lookup: added %d new character IDs (total: %d)", 
                       len(processed_character_ids), len(updated_character_ids))
                       
        except Exception as e:
            logger.error("Error updating manga lookup files: %s", e)

    # ===== MAL AUTHENTICATION =====
    
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
            
            # Setup OAuth flow
            redirect_uri = "http://localhost:8080/callback"
            auth_url, code_verifier = self.mal_service.generate_auth_url(redirect_uri)
            
            logger.info("Please visit this URL to authorize the application:")
            logger.info(auth_url)
            logger.info("After authorization, you will be redirected to a localhost URL.")
            logger.info("Copy the 'code' parameter from the URL and paste it below.")
            
            # Get authorization code from user
            auth_code = input("Enter the authorization code: ").strip()
            
            if not auth_code:
                logger.error("No authorization code provided")
                return False
            
            # Exchange code for access token
            if await self.mal_service.exchange_code_for_tokens(auth_code, redirect_uri, code_verifier):
                logger.info("✅ MAL authentication successful!")
                return True
            else:
                logger.error("❌ MAL authentication failed!")
                return False
                
        except Exception as e:
            logger.error("Error during MAL authentication: %s", e)
            return False

    async def _get_character_details(self, character_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed character information from Jikan API."""
        try:
            await asyncio.sleep(1.5)  # Rate limiting for Jikan API
            
            url = f"https://api.jikan.moe/v4/characters/{character_id}"

            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        character = data.get("data", {})
                        
                        return {
                            "mal_id": character.get("mal_id"),
                            "id": character.get("mal_id"),  # Add source_id field for standardization
                            "name": character.get("name", "Unknown"),
                            "name_kanji": character.get("name_kanji", ""),
                            "nicknames": character.get("nicknames", []),
                            "about": character.get("about", ""),
                            "image_url": character.get("images", {}).get("jpg", {}).get("image_url", ""),
                            "favorites": character.get("favorites", 0)
                        }
                    elif response.status == 404:
                        logger.warning("Character %d not found on Jikan API (404)", character_id)
                        return None
                    elif response.status == 429:
                        logger.warning("Rate limited for character %d, waiting longer...", character_id)
                        await asyncio.sleep(5)
                        return await self._get_character_details(character_id)  # Retry once
                    else:
                        logger.warning("Failed to get character details for %d: HTTP %d", character_id, response.status)
                        return None

        except asyncio.TimeoutError:
            logger.error("Timeout getting character details for %d", character_id)
            return None
        except Exception as e:
            logger.error("Error getting character details for %d: %s", character_id, e)
            return None

    # ===== MANGA DETAILS COLLECTION =====
    
    async def _get_manga_details(self, manga_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed manga information from Jikan API."""
        try:
            await asyncio.sleep(1.5)  # Rate limiting for Jikan API
            
            url = f"https://api.jikan.moe/v4/manga/{manga_id}"

            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(
                url, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                    if response.status == 200:
                        data = await response.json()
                        manga = data.get("data", {})

                        # Combine genres and themes for the genres field
                        genres_list = manga.get("genres", [])
                        themes_list = manga.get("themes", [])
                        all_genres = genres_list + themes_list
                        genres_and_themes = "|".join([g.get("name", "") for g in all_genres])

                        # Extract manga data in MAL format
                        return {
                            "mal_id": manga.get("mal_id"),
                            "id": manga.get("mal_id"),  # Add source_id field for standardization
                            "title": manga.get("title", "Unknown"),
                            "title_english": manga.get("title_english", ""),
                            "title_japanese": manga.get("title_japanese", ""),
                            "type": manga.get("type", ""),
                            "chapters": manga.get("chapters", 0),
                            "volumes": manga.get("volumes", 0),
                            "status": manga.get("status", ""),
                            "published_from": manga.get("published", {}).get("from", ""),
                            "published_to": manga.get("published", {}).get("to", ""),
                            "score": manga.get("score", 0.0),
                            "scored_by": manga.get("scored_by", 0),
                            "rank": manga.get("rank", 0),
                            "popularity": manga.get("popularity", 0),
                            "members": manga.get("members", 0),
                            "favorites": manga.get("favorites", 0),
                            "synopsis": manga.get("synopsis", ""),
                            "image_url": manga.get("images", {}).get("jpg", {}).get("large_image_url", ""),
                            "genres": genres_and_themes,
                            "authors": "|".join([a.get("name", "") for a in manga.get("authors", [])]),
                            "serializations": "|".join([s.get("name", "") for s in manga.get("serializations", [])])
                        }
                    elif response.status == 404:
                        logger.warning("Manga %d not found on Jikan API (404)", manga_id)
                        return None
                    elif response.status == 429:
                        logger.warning("Rate limited for manga %d, waiting longer...", manga_id)
                        await asyncio.sleep(5)
                        return await self._get_manga_details(manga_id)  # Retry once
                    else:
                        logger.warning("Failed to get manga details for %d: HTTP %d", manga_id, response.status)
                        return None

        except asyncio.TimeoutError:
            logger.error("Timeout getting manga details for %d", manga_id)
            return None
        except Exception as e:
            logger.error("Error getting manga details for %d: %s", manga_id, e)
            return None

    # ===== MANGA CHARACTER COLLECTION =====
    
    async def _get_manga_characters(self, manga_id: int, manga_title: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get characters from a manga using Jikan API.
        
        Args:
            manga_id: MAL manga ID
            manga_title: Manga title to include with character data
        """
        try:
            await asyncio.sleep(1.5)  # Rate limiting
            
            url = f"https://api.jikan.moe/v4/manga/{manga_id}/characters"

            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(
                url, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                    if response.status == 200:
                        data = await response.json()
                        characters = []
                        
                        total_chars = len(data.get("data", []))
                        logger.info("  Found %d characters in manga %d", total_chars, manga_id)

                        for char_data in data.get("data", []):
                            character = char_data.get("character", {})
                            character_id = character.get("mal_id")

                            if character_id and character_id not in self.processed_character_ids:
                                logger.debug("Processing character %d from manga %d: %s", 
                                           character_id, manga_id, character.get('name', 'Unknown'))

                                # Get detailed character information
                                character_details = await self._get_character_details(character_id)

                                if character_details:
                                    # Add series information for manga
                                    character_details["series_type"] = "manga"
                                    character_details["series_mal_id"] = manga_id
                                    # Pass the manga title directly to avoid file lookups
                                    if manga_title:
                                        character_details["series_title"] = manga_title
                                    characters.append(character_details)
                                
                                # Always add to processed IDs (whether successful or filtered)
                                # This prevents re-scraping both good and bad characters
                                self.processed_character_ids.add(character_id)
                            elif character_id in self.processed_character_ids:
                                logger.debug("  Skipped character %d - already processed", character_id)

                        return characters
                    elif response.status == 404:
                        logger.warning("Manga %d not found on Jikan API (404)", manga_id)
                        return []
                    elif response.status == 429:
                        logger.warning("Rate limited for manga %d, waiting longer...", manga_id)
                        await asyncio.sleep(5)
                        return await self._get_manga_characters(manga_id, manga_title)  # Retry once
                    else:
                        logger.warning("Failed to get characters for manga %d: HTTP %d", manga_id, response.status)
                        return []

        except asyncio.TimeoutError:
            logger.error("Timeout getting characters for manga %d", manga_id)
            return []
        except Exception as e:
            logger.error("Error getting characters for manga %d: %s", manga_id, e)
            return []

    # ===== MAIN DATA PULLING IMPLEMENTATION =====
    
    async def pull_raw_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Pull raw manga and character data from MAL.
        
        Skips series that are already in the ID registry to avoid 
        re-mining existing data.
        
        Returns:
            Tuple of (raw_series_list, raw_characters_list)
        """
        try:
            logger.info("📚 Starting MAL manga data pulling...")

            # Authenticate with MAL
            if not await self._authenticate_mal():
                logger.error("MAL authentication failed")
                return [], []

            # Get user's manga list (ONLY manga, not anime)
            logger.info("📖 Fetching user's manga list...")
            if not self.mal_service:
                logger.error("MAL service not initialized")
                return [], []
                
            manga_list = await self.mal_service.get_user_manga_list()
            logger.info("Found %d manga in user's MAL list", len(manga_list))

            # Collect all characters and manga data
            all_characters = []
            all_manga = []

            # Process ONLY manga - Skip existing manga like the anime processor
            for i, manga in enumerate(manga_list, 1):
                manga_id = manga["id"]
                title = manga["title"]

                # Skip if series already exists in lookup
                if self._is_series_already_mined(manga_id):
                    logger.info("Skipping manga %d/%d: %s - already mined", 
                               i, len(manga_list), title)
                    continue
                
                logger.info("Processing manga %d/%d: %s", i, len(manga_list), title)
                
                # Get manga details
                manga_details = await self._get_manga_details(manga_id)
                if manga_details:
                    all_manga.append(manga_details)
                    self.processed_manga_ids.add(manga_id)

                # Get characters from manga - pass the title for direct series name assignment
                characters = await self._get_manga_characters(manga_id, title)
                all_characters.extend(characters)

                logger.info("  Found %d new characters", len(characters))

            # Summary statistics
            total_manga_in_list = len(manga_list)
            manga_already_existed = len([m for m in manga_list if self._is_series_already_mined(m["id"])])
            manga_processed = total_manga_in_list - manga_already_existed

            logger.info("✅ Successfully pulled manga data from MAL!")
            logger.info("📊 Processing Summary:")
            logger.info("   - Total manga in MAL list: %d", total_manga_in_list)
            logger.info("   - Manga already mined (skipped): %d", manga_already_existed)
            logger.info("   - Manga processed: %d", manga_processed)
            logger.info("   - New manga pulled: %d", len(all_manga))
            logger.info("   - New characters pulled: %d", len(all_characters))
            
            if manga_processed > len(all_manga):
                logger.warning("⚠️  %d manga were processed but not added (likely due to API errors or rate limiting)", 
                             manga_processed - len(all_manga))
            
            # Update lookup files with all processed IDs (including filtered ones)
            # This prevents re-scraping both successful and filtered data
            logger.info("🔄 Updating lookup files...")
            self._update_lookup_files(self.processed_manga_ids, self.processed_character_ids)
            
            return all_manga, all_characters

        except Exception as e:
            logger.error("❌ Error during MAL manga data pulling: %s", e)
            return [], []

    # ===== UTILITY METHODS =====
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for this processor."""
        stats = super().get_processing_stats()
        stats.update({
            'mal_service_initialized': self.mal_service is not None,
            'existing_manga_loaded': len(self.existing_manga_ids),
            'existing_characters_loaded': len(self.existing_character_ids),
            'processed_character_ids': len(self.processed_character_ids),
            'processed_manga_ids': len(self.processed_manga_ids)
        })
        return stats

    async def __aenter__(self):
        """Async context manager entry."""
        # Create HTTP session for API requests
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Clean up HTTP session
        if self.session:
            await self.session.close()
            
        if self.mal_service:
            # Clean up MAL service if needed
            pass


# ===== TESTING =====

async def test_manga_processor():
    """Test the manga processor."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    
    print("Testing Manga Processor...")
    
    try:
        async with MangaProcessor() as processor:
            # Check configuration
            print(f"Configured: {processor.is_configured()}")
            print(f"Source type: {processor.get_source_type()}")
            
            # Check stats
            stats = processor.get_processing_stats()
            print(f"Stats: {stats}")
            
            # Note: Full testing requires MAL authentication
            # For now, just test initialization
            print("✅ Manga Processor initialization test completed!")
            
    except Exception as e:
        print(f"❌ Error testing manga processor: {e}")


if __name__ == "__main__":
    asyncio.run(test_manga_processor())