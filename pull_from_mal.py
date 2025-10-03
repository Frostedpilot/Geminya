#!/usr/bin/env python3
"""Script to pull character and anime data from MAL and export to CSV files."""

import asyncio
import aiohttp
import json
import sys
import os
import csv
import re
from typing import List, Dict, Any, Set, Optional
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.mal_api import MALAPIService
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class MALDataPuller:
    """Service to pull data from MAL and export to CSV files."""

    def __init__(self, config: Config):
        self.config = config
        self.mal_service = None
        
        # Track processed IDs to avoid duplicates
        self.processed_character_ids = set()
        self.processed_anime_ids = set()
        
        # Load existing data if CSV files exist
        self.existing_characters = self.load_existing_characters()
        self.existing_anime = self.load_existing_anime()

    def load_existing_characters(self) -> Set[int]:
        """Load existing character IDs from CSV to skip re-pulling."""
        existing_ids = set()
        csv_path = os.path.join('data', 'characters_mal.csv')
        try:
            with open(csv_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'mal_id' in row and row['mal_id']:
                        existing_ids.add(int(row['mal_id']))
            logger.info(f"Loaded {len(existing_ids)} existing character IDs from {csv_path}")
        except FileNotFoundError:
            logger.info(f"No existing {csv_path} found - will create new file")
        except Exception as e:
            logger.warning(f"Error loading existing characters: {e}")
        return existing_ids

    def load_existing_anime(self) -> Set[int]:
        """Load existing anime IDs from CSV to skip re-pulling."""
        existing_ids = set()
        csv_path = os.path.join('data', 'anime_mal.csv')
        try:
            with open(csv_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'mal_id' in row and row['mal_id']:
                        existing_ids.add(int(row['mal_id']))
            logger.info(f"Loaded {len(existing_ids)} existing anime IDs from {csv_path}")
        except FileNotFoundError:
            logger.info(f"No existing {csv_path} found - will create new file")
        except Exception as e:
            logger.warning(f"Error loading existing anime: {e}")
        return existing_ids

    async def __aenter__(self):
        """Async context manager entry."""
        self.mal_service = MALAPIService(
            self.config.mal_client_id, self.config.mal_client_secret
        )
        await self.mal_service.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.mal_service:
            await self.mal_service.__aexit__(exc_type, exc_val, exc_tb)

    def setup_oauth_flow(self, redirect_uri: str = "http://localhost:8080/callback"):
        """Setup OAuth flow for MAL authentication."""
        auth_url, code_verifier = self.mal_service.generate_auth_url(redirect_uri)

        print(f"🔐 MAL OAuth Setup Required")
        print(f"1. Open this URL in your browser:")
        print(f"   {auth_url}")
        print(f"2. Authorize the application")
        print(f"3. Copy the authorization code from the callback URL")
        print(f"4. Enter the code below:")

        auth_code = input("Enter authorization code: ").strip()
        return auth_code, code_verifier, redirect_uri

    async def authenticate_mal(self):
        """Complete MAL OAuth authentication."""
        try:
            auth_code, code_verifier, redirect_uri = self.setup_oauth_flow()

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
            logger.error(f"❌ MAL authentication error: {e}")
            return False

    async def get_character_details(self, character_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed character information from Jikan API."""
        try:
            # Skip if already exists
            if character_id in self.existing_characters:
                logger.debug(f"Skipping character {character_id} - already exists in CSV")
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
                            logger.debug(f"Skipping character {character_id} - 0 favorites")
                            return None

                        res = {
                            "mal_id": character.get("mal_id"),
                            "name": character.get("name", "Unknown"),
                            "name_kanji": character.get("name_kanji", ""),
                            "nicknames": "|".join(character.get("nicknames", [])),  # Join for CSV
                            "about": character.get("about", ""),
                            "image_url": character.get("images", {})
                            .get("jpg", {})
                            .get("image_url", ""),
                            "favorites": favorites,
                        }
                        
                        logger.info(f"Retrieved character {character_id}: {res['name']} ({favorites} favorites)")
                        return res
                    elif response.status == 404:
                        logger.warning(f"❌ Character {character_id} not found on Jikan API (404)")
                        return None
                    elif response.status == 429:
                        logger.warning(f"⏳ Rate limited for character {character_id}, waiting longer...")
                        await asyncio.sleep(5)
                        return await self.get_character_details(character_id)  # Retry once
                    else:
                        logger.warning(f"❌ Failed to get character details for {character_id}: HTTP {response.status}")
                        return None

        except asyncio.TimeoutError:
            logger.error(f"⏰ Timeout getting character details for {character_id}")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting character details for {character_id}: {e}")
            return None

    async def get_anime_details(self, anime_id: int) -> Optional[Dict[str, Any]]:
        """Get anime details and store in anime CSV."""
        try:
            # Skip if already exists
            if anime_id in self.existing_anime:
                logger.debug(f"Skipping anime {anime_id} - already exists in CSV")
                return None
                
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

                        res = {
                            "mal_id": anime.get("mal_id"),
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
                            "studios": "|".join([s.get("name", "") for s in anime.get("studios", [])]),
                        }
                        
                        logger.info(f"Retrieved anime {anime_id}: {res['title']}")
                        return res
                    elif response.status == 404:
                        logger.warning(f"❌ Anime {anime_id} not found on Jikan API (404) - may have been removed from MAL")
                        return None
                    elif response.status == 429:
                        logger.warning(f"⏳ Rate limited for anime {anime_id}, waiting longer...")
                        await asyncio.sleep(5)
                        return await self.get_anime_details(anime_id)  # Retry once
                    else:
                        logger.warning(f"❌ Failed to get anime details for {anime_id}: HTTP {response.status}")
                        return None

        except asyncio.TimeoutError:
            logger.error(f"⏰ Timeout getting anime details for {anime_id}")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting anime details for {anime_id}: {e}")
            return None

    async def get_anime_characters(self, anime_id: int) -> List[Dict[str, Any]]:
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
                        logger.info(f"  Found {total_chars} characters in anime {anime_id}")

                        for char_data in data.get("data", []):
                            character = char_data.get("character", {})
                            character_id = character.get("mal_id")

                            if character_id and character_id not in self.processed_character_ids:
                                logger.debug(f"Processing character {character_id} from anime {anime_id}: {character.get('name', 'Unknown')}")

                                # Get detailed character information
                                character_details = await self.get_character_details(character_id)

                                if character_details:
                                    # Add series information
                                    character_details["series_type"] = "anime"
                                    character_details["series_mal_id"] = anime_id
                                    characters.append(character_details)
                                    self.processed_character_ids.add(character_id)
                                else:
                                    logger.debug(f"  Skipped character {character_id} (likely 0 favorites or already exists)")
                            elif character_id in self.processed_character_ids:
                                logger.debug(f"  Skipped character {character_id} - already processed")

                        return characters
                    elif response.status == 404:
                        logger.warning(f"❌ Anime {anime_id} not found on Jikan API (404) - may have been removed from MAL")
                        return []
                    elif response.status == 429:
                        logger.warning(f"⏳ Rate limited for anime {anime_id}, waiting longer...")
                        await asyncio.sleep(5)
                        return await self.get_anime_characters(anime_id)  # Retry once
                    else:
                        logger.warning(f"❌ Failed to get characters for anime {anime_id}: HTTP {response.status}")
                        return []

        except asyncio.TimeoutError:
            logger.error(f"⏰ Timeout getting characters for anime {anime_id}")
            return []
        except Exception as e:
            logger.error(f"❌ Error getting characters for anime {anime_id}: {e}")
            return []

    async def get_manga_characters(self, manga_id: int) -> List[Dict[str, Any]]:
        """Get characters from a manga using Jikan API."""
        try:
            await asyncio.sleep(1.5)  # Rate limiting

            url = f"https://api.jikan.moe/v4/manga/{manga_id}/characters"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        characters = []

                        for char_data in data.get("data", []):
                            character = char_data.get("character", {})
                            character_id = character.get("mal_id")

                            if character_id and character_id not in self.processed_character_ids:
                                # Get detailed character information
                                character_details = await self.get_character_details(character_id)

                                if character_details:
                                    # Add series information
                                    character_details["series_type"] = "manga"
                                    character_details["series_mal_id"] = manga_id
                                    characters.append(character_details)
                                    self.processed_character_ids.add(character_id)

                        return characters
                    else:
                        logger.warning(f"Failed to get characters for manga {manga_id}: {response.status}")
                        return []

        except Exception as e:
            logger.error(f"Error getting characters for manga {manga_id}: {e}")
            return []

    def write_characters_csv(self, characters: List[Dict[str, Any]]):
        """Write characters to CSV file."""
        if not characters:
            logger.info("No new characters to write to CSV")
            return

        fieldnames = [
            "mal_id", "name", "name_kanji", "nicknames", "about", "image_url", 
            "favorites", "series_type", "series_mal_id"
        ]

        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        csv_path = os.path.join('data', 'characters_mal.csv')

        # Check if file exists to determine if we need headers
        file_exists = os.path.exists(csv_path)
        
        with open(csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header only if file is new
            if not file_exists:
                writer.writeheader()
            
            for character in characters:
                writer.writerow(character)
                
        logger.info(f"Wrote {len(characters)} characters to {csv_path}")

    def write_anime_csv(self, anime_list: List[Dict[str, Any]]):
        """Write anime to CSV file."""
        if not anime_list:
            logger.info("No new anime to write to CSV")
            return

        fieldnames = [
            "mal_id", "title", "title_english", "title_japanese", "type", "episodes",
            "status", "aired_from", "aired_to", "score", "scored_by", "rank",
            "popularity", "members", "favorites", "synopsis", "image_url", "genres", "studios"
        ]

        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        csv_path = os.path.join('data', 'anime_mal.csv')

        # Check if file exists to determine if we need headers
        file_exists = os.path.exists(csv_path)
        
        with open(csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header only if file is new
            if not file_exists:
                writer.writeheader()
            
            for anime in anime_list:
                writer.writerow(anime)
                
        logger.info(f"Wrote {len(anime_list)} anime to {csv_path}")

    async def pull_from_mal_user(self):
        """Main function to pull data from MAL user's lists and export to CSV."""
        try:
            logger.info("🎌 Starting MAL data pulling...")

            # Authenticate with MAL
            if not await self.authenticate_mal():
                return False

            # Get user's anime and manga lists
            logger.info("📺 Fetching user's anime list...")
            anime_list = await self.mal_service.get_user_anime_list()

            logger.info("📚 Fetching user's manga list...")
            manga_list = await self.mal_service.get_user_manga_list()

            logger.info(f"Found {len(anime_list)} anime and {len(manga_list)} manga in user's lists")

            # Collect all characters and anime data
            all_characters = []
            all_anime = []

            # Process anime
            for i, anime in enumerate(anime_list, 1):
                anime_id = anime["id"]
                title = anime["title"]

                # Skip if anime already exists in CSV
                if anime_id in self.existing_anime:
                    logger.info(f"Skipping anime {i}/{len(anime_list)}: {title} - already exists in data/anime_mal.csv")
                    continue

                logger.info(f"Processing anime {i}/{len(anime_list)}: {title}")
                
                # Get anime details
                anime_details = await self.get_anime_details(anime_id)
                if anime_details:
                    all_anime.append(anime_details)
                    self.processed_anime_ids.add(anime_id)

                # Get characters from anime
                characters = await self.get_anime_characters(anime_id)
                all_characters.extend(characters)

                logger.info(f"  Found {len(characters)} new characters")

            # Process manga (similar to anime but without anime details)
            for i, manga in enumerate(manga_list, 1):
                manga_id = manga["id"]
                title = manga["title"]

                logger.info(f"Processing manga {i}/{len(manga_list)}: {title}")
                characters = await self.get_manga_characters(manga_id)
                all_characters.extend(characters)

                logger.info(f"  Found {len(characters)} new characters")

            # Write data to CSV files
            logger.info(f"💾 Writing {len(all_characters)} characters to data/characters_mal.csv...")
            self.write_characters_csv(all_characters)

            logger.info(f"💾 Writing {len(all_anime)} anime to data/anime_mal.csv...")
            self.write_anime_csv(all_anime)

            # Summary statistics
            total_anime_in_list = len(anime_list)
            anime_already_existed = len([a for a in anime_list if a["id"] in self.existing_anime])
            anime_processed = total_anime_in_list - anime_already_existed

            logger.info(f"✅ Successfully exported data to CSV files!")
            logger.info(f"📊 Processing Summary:")
            logger.info(f"   - Total anime in MAL list: {total_anime_in_list}")
            logger.info(f"   - Anime already in CSV (skipped): {anime_already_existed}")
            logger.info(f"   - Anime processed: {anime_processed}")
            logger.info(f"   - New anime added to CSV: {len(all_anime)}")
            logger.info(f"   - New characters added to CSV: {len(all_characters)}")
            
            if anime_processed > len(all_anime):
                logger.warning(f"⚠️  {anime_processed - len(all_anime)} anime were processed but not added to CSV (likely due to API errors or rate limiting)")
            
            return True

        except Exception as e:
            logger.error(f"❌ Error during data pulling: {e}")
            return False


async def main():
    """Main function."""
    try:
        config = Config.create()

        async with MALDataPuller(config) as puller:
            success = await puller.pull_from_mal_user()

        return success

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
