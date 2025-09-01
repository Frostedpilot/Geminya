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
                    # Convert JSON fields back to Python objects
                    for col in ['base_stats', 'favorite_gifts', 'special_dialogue']:
                        if col in row and row[col]:
                            try:
                                row[col] = json.loads(row[col])
                            except Exception:
                                pass
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
                    # Convert favorites, members, score to correct types if present
                    if 'favorites' in s:
                        try:
                            s['favorites'] = int(float(s['favorites'])) if s['favorites'] != '' else None
                        except Exception:
                            s['favorites'] = None
                    if 'members' in s:
                        try:
                            s['members'] = int(float(s['members'])) if s['members'] != '' else None
                        except Exception:
                            s['members'] = None
                    if 'score' in s:
                        try:
                            s['score'] = float(s['score']) if s['score'] != '' else None
                        except Exception:
                            s['score'] = None
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
                    # Ensure numeric fields are correct type
                    for field in ["waifu_id", "series_id", "rarity", "favorites"]:
                        if field in character:
                            try:
                                character[field] = int(character[field])
                            except Exception:
                                character[field] = None
                    waifu_id = character["waifu_id"]
                    # Set canonical series name for denormalized field
                    character["series"] = series_id_to_name.get(character["series_id"], "Unknown Series")
                    # Check db_service is initialized
                    if not self.db_service:
                        logger.error("Database service is not initialized!")
                        failed_uploads += 1
                        continue
                    existing = await self.db_service.get_waifu_by_waifu_id(waifu_id)
                    if existing:
                        await self.db_service.update_waifu(waifu_id, character)
                        logger.info(f"  Updated existing character: {char_name} (WAIFU ID: {waifu_id})")
                    else:
                        await self.db_service.add_waifu(character)
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
