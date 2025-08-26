#!/usr/bin/env python3
"""Script to upload character data from data/character_final.csv to PostgreSQL database."""

import asyncio
import csv
import json
import sys
import os
from typing import List, Dict, Any, Optional
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.database import DatabaseService
from services.waifu_service import WaifuService
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

class PostgresUploader:
    """Service to upload character data to PostgreSQL database."""

    def __init__(self, config: Config):
        self.config = config
        self.db_service = None
        self.waifu_service = None
        self.character_file = os.path.join("data", "character_final.csv")
        self.series_file = os.path.join("data", "anime_final.csv")

    async def __aenter__(self):
        """Async context manager entry."""
        self.db_service = DatabaseService(self.config)
        await self.db_service.initialize()

        self.waifu_service = WaifuService(self.db_service)
        await self.waifu_service.initialize()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.waifu_service:
            await self.waifu_service.close()
        if self.db_service:
            await self.db_service.close()

    def load_characters(self) -> List[Dict[str, Any]]:
        """Load characters from character_final.csv."""
        characters = []
        try:
            with open(self.character_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    characters.append(row)
            logger.info(f"Loaded {len(characters)} characters from {self.character_file}")
        except FileNotFoundError:
            logger.error(f"Input file {self.character_file} not found!")
            logger.error("Please run process_character_final.py first to generate data/character_final.csv")
            return []
        except Exception as e:
            logger.error(f"Error loading characters: {e}")
            return []
        return characters

    def load_series(self) -> List[Dict[str, Any]]:
        """Load series from anime_final.csv."""
        series = []
        try:
            with open(self.series_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    series.append(row)
            logger.info(f"Loaded {len(series)} series from {self.series_file}")
        except FileNotFoundError:
            logger.error(f"Input file {self.series_file} not found!")
            logger.error("Please run process_character_final.py first to generate data/anime_final.csv")
            return []
        except Exception as e:
            logger.error(f"Error loading series: {e}")
            return []
        return series

    def process_character_for_database(self, character: Dict[str, Any]) -> 'Optional[Dict[str, Any]]':
        """Process character data for database insertion."""
        waifu_id_raw = character.get("waifu_id", "")
        try:
            waifu_id = int(waifu_id_raw) if waifu_id_raw else None
        except (ValueError, TypeError):
            waifu_id = None
        if not waifu_id:
            logger.warning(f"Skipping character with missing or invalid waifu_id: {character.get('name', 'Unknown')}")
            return None
        try:
            rarity = int(character.get("rarity", 1))
        except (ValueError, TypeError):
            rarity = 1
        char_data = {
            "name": character.get("name", ""),
            "genre": character.get("genre", "Anime"),
            "element": self.determine_element(character),
            "rarity": rarity,
            "image_url": character.get("image_url", ""),
            "waifu_id": waifu_id,
            "base_stats": self.generate_base_stats(character),
            "birthday": None,  # Use None for SQL NULL in DATE column
            "favorite_gifts": self.generate_favorite_gifts(character),
            "special_dialogue": {},
        }
        return char_data

    def determine_element(self, character: Dict[str, Any]) -> str:
        """Determine character element based on traits and series."""
        about = character.get("about", "").lower()
        series = character.get("series", "").lower()
        name = character.get("name", "").lower()

        # Magic-related
        if any(word in about for word in ["magic", "witch", "spell", "mage", "wizard", "sorcerer"]):
            return "magic"
        
        # Fire-related
        if any(word in about for word in ["fire", "flame", "burn", "hot", "heat", "dragon"]):
            return "fire"
        
        # Water-related
        if any(word in about for word in ["water", "sea", "ocean", "river", "ice", "snow", "cold"]):
            return "water"
        
        # Earth-related
        if any(word in about for word in ["earth", "stone", "rock", "mountain", "forest", "nature"]):
            return "earth"
        
        # Air-related
        if any(word in about for word in ["wind", "air", "sky", "cloud", "flying", "bird"]):
            return "air"
        
        # Light-related
        if any(word in about for word in ["light", "holy", "divine", "angel", "pure", "bright"]):
            return "light"
        
        # Dark-related
        if any(word in about for word in ["dark", "shadow", "demon", "evil", "death", "vampire"]):
            return "dark"

        # Default to neutral
        return "neutral"

    def generate_base_stats(self, character: Dict[str, Any]) -> Dict[str, int]:
        """Generate base stats for character."""
        favorites = int(character.get("favorites", 0))
        
        # Base stats influenced by popularity
        base = 50
        popularity_bonus = min(favorites // 100, 30)  # Max 30 bonus points
        
        return {
            "attack": base + popularity_bonus + (hash(character.get("name", "")) % 21 - 10),
            "defense": base + popularity_bonus + (hash(character.get("name", "")[::-1]) % 21 - 10),
            "speed": base + popularity_bonus + (hash(character.get("about", "")[:10]) % 21 - 10),
            "hp": base + popularity_bonus + (hash(character.get("waifu_id", "0")) % 21 - 10)
        }

    def generate_favorite_gifts(self, character: Dict[str, Any]) -> List[str]:
        """Generate favorite gifts based on character traits."""
        about = character.get("about", "").lower()
        
        all_gifts = {
            "food": ["Chocolate", "Cake", "Ice Cream", "Cookies", "Candy"],
            "flower": ["Roses", "Sakura Petals", "Sunflower", "Lily", "Tulips"],
            "accessory": ["Hair Ribbon", "Necklace", "Earrings", "Bracelet", "Ring"],
            "book": ["Novel", "Manga", "Poetry Book", "Art Book", "Study Guide"],
            "toy": ["Plushie", "Figurine", "Music Box", "Puzzle", "Game"]
        }
        
        favorite_gifts = []
        
        # Analyze character description for preferences
        if any(word in about for word in ["food", "eat", "cook", "hungry", "sweet"]):
            favorite_gifts.extend(all_gifts["food"][:2])
        if any(word in about for word in ["flower", "garden", "nature", "beautiful"]):
            favorite_gifts.extend(all_gifts["flower"][:2])
        if any(word in about for word in ["book", "read", "study", "smart", "intelligent"]):
            favorite_gifts.extend(all_gifts["book"][:2])
        if any(word in about for word in ["cute", "pretty", "beautiful", "fashion"]):
            favorite_gifts.extend(all_gifts["accessory"][:2])

        # If no specific preferences found, add some defaults
        if not favorite_gifts:
            favorite_gifts = ["Chocolate", "Roses", "Hair Ribbon"]

        # Limit to 3-5 gifts
        return favorite_gifts[:5]

    async def upload_series_and_characters(self):
        """Upload series first, then characters to PostgreSQL database."""
        try:
            logger.info("💾 Starting series and character upload to PostgreSQL...")
            # Load series and character data
            series_list = self.load_series()
            characters = self.load_characters()
            if not series_list or not characters:
                return False
            # Check database connection
            logger.info("🔗 Testing database connection...")
            if not await self.db_service.test_connection():
                logger.error("❌ Database connection failed!")
                return False
            logger.info("✅ Database connection successful!")
            # Upload series
            successful_series = 0
            for s in series_list:
                try:
                    # Ensure series_id is an integer
                    s['series_id'] = int(s['series_id'])
                    # Check if series exists by series_id
                    existing = await self.db_service.get_series_by_id(s['series_id']) if hasattr(self.db_service, 'get_series_by_id') else None
                    if existing:
                        # Update the series in case of changes
                        await self.db_service.add_series(s)
                        logger.info(f"Updated existing series: {s.get('name', '')} (ID: {s.get('series_id', '')})")
                    else:
                        # Insert new series
                        await self.db_service.add_series(s)
                        successful_series += 1
                        logger.info(f"Inserted new series: {s.get('name', '')} (ID: {s.get('series_id', '')})")
                except Exception as e:
                    logger.error(f"❌ Failed to upload series {s.get('name', '')}: {e}")
            logger.info(f"✅ Uploaded {successful_series} new series entries.")
            # Build a name->series_id map from DB
            db_series = {s['name'].strip().lower(): s['series_id'] for s in (series_list)}
            # Upload characters
            successful_uploads = 0
            failed_uploads = 0
            # Build a series_id -> canonical name map from the loaded series_list
            series_id_to_name = {int(s['series_id']): s['name'] for s in series_list if s.get('series_id') and s.get('name')}
            for i, character in enumerate(characters, 1):
                char_name = character.get("name", "Unknown")
                try:
                    logger.info(f"Uploading character {i}/{len(characters)}: {char_name}")
                    char_data = self.process_character_for_database(character)
                    if not char_data:
                        failed_uploads += 1
                        continue
                    waifu_id = char_data["waifu_id"]
                    # Set series_id from CSV (already mapped in ETL)
                    char_data["series_id"] = int(character["series_id"])
                    # Set canonical series name for denormalized field
                    char_data["series"] = series_id_to_name.get(char_data["series_id"], "Unknown Series")
                    # Check db_service is initialized
                    if not self.db_service:
                        logger.error("Database service is not initialized!")
                        failed_uploads += 1
                        continue
                    existing = await self.db_service.get_waifu_by_waifu_id(waifu_id)
                    if existing:
                        logger.info(f"  Character {char_name} already exists in database (WAIFU ID: {waifu_id})")
                        continue
                    await self.db_service.add_waifu(char_data)
                    successful_uploads += 1
                    logger.info(f"  ✅ Successfully uploaded {char_name}")
                except Exception as e:
                    failed_uploads += 1
                    logger.error(f"  ❌ Failed to upload {char_name}: {e}")
            logger.info(f"📊 Upload Summary:")
            logger.info(f"  ✅ Successful: {successful_uploads}")
            logger.info(f"  ❌ Failed: {failed_uploads}")
            logger.info(f"  📝 Total processed: {len(characters)}")
            if successful_uploads > 0:
                logger.info("✅ Character upload completed successfully!")
                return True
            else:
                logger.warning("⚠️ No characters were uploaded!")
                return False
        except Exception as e:
            logger.error(f"❌ Error during series/character upload: {e}")
            return False


async def main():
    """Main function."""
    try:
        config = Config.create()

        async with PostgresUploader(config) as uploader:
            success = await uploader.upload_series_and_characters()

        return success

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
