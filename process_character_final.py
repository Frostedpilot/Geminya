#!/usr/bin/env python3
"""Process character_cleaned.xlsx and output data/character_final.csv for new star system."""

import pandas as pd
import os
import sys
import logging
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class CharacterFinalProcessor:
    def save_anime_final_csv(self, anime_map: dict) -> bool:
        """Save the anime/banner info to anime_final.csv."""
        try:
            import pandas as pd
            anime_list = []
            for key, info in anime_map.items():
                anime_list.append({
                    "mal_id": info["mal_id"],
                    "title": info["title"],
                    "title_english": info.get("title_english", None),
                    "image_url": info.get("image_url", None)
                })
            df_anime = pd.DataFrame(anime_list)
            output_path = os.path.join("data", "anime_final.csv")
            df_anime.to_csv(output_path, index=False, encoding='utf-8')
            logger.info(f"✅ Saved {len(df_anime)} anime banners to {output_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving anime_final.csv: {e}")
            return False
    def load_anime_mal(self) -> dict:
        """Load anime_mal.csv and return a mapping from series title to mal_id and banner info."""
        anime_map = {}
        try:
            df = pd.read_csv(os.path.join("data", "anime_mal.csv"))
            for _, row in df.iterrows():
                anime_map[str(row["title"]).strip().lower()] = {
                    "mal_id": int(row["mal_id"]),
                    "title": row["title"],
                    "title_english": row.get("title_english", None),
                    "image_url": row.get("image_url", None)
                }
        except Exception as e:
            logger.error(f"❌ Error loading anime_mal.csv: {e}")
        return anime_map
    """Process cleaned Excel file for the new star system."""

    def __init__(self):
        self.input_file = os.path.join("data", "characters_cleaned.xlsx")
        self.output_file = os.path.join("data", "character_final.csv")
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)

    def load_excel_data(self) -> Optional[pd.DataFrame]:
        """Load the cleaned Excel file."""
        try:
            logger.info(f"Loading Excel file: {self.input_file}")
            df = pd.read_excel(self.input_file)
            logger.info(f"✅ Loaded {len(df)} characters from Excel file")
            logger.info(f"📋 Columns: {list(df.columns)}")
            return df
        except FileNotFoundError:
            logger.error(f"❌ Excel file {self.input_file} not found!")
            return None
        except Exception as e:
            logger.error(f"❌ Error loading Excel file: {e}")
            return None

    def validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean the DataFrame for the new star system."""
        logger.info("🧹 Validating and cleaning data...")
        original_count = len(df)
        # Required columns for upload_to_mysql.py compatibility
        required_columns = ['waifu_id', 'name', 'series', 'genre', 'rarity', 'image_url', 'favorites']
        # If 'waifu_id' is not present but 'mal_id' is, rename it
        if 'waifu_id' not in df.columns and 'mal_id' in df.columns:
            df = df.rename(columns={"mal_id": "waifu_id"})
        # Check if all required columns exist
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"❌ Missing required columns: {missing_columns}")
            logger.info(f"Available columns: {list(df.columns)}")
            return pd.DataFrame()
        # Select only the required columns
        df_clean = df[required_columns].copy()
        # Add series_id (mal_id) by mapping series to anime_mal.csv
        anime_map = self.load_anime_mal()
        def get_series_id(series):
            key = str(series).strip().lower()
            return anime_map[key]["mal_id"] if key in anime_map else None
        df_clean["series_id"] = df_clean["series"].apply(get_series_id)
        # Clean and validate data
        # Remove rows with missing essential data
        df_clean = df_clean.dropna(subset=['waifu_id', 'name', 'rarity'])
        # Ensure waifu_id is integer
        df_clean['waifu_id'] = pd.to_numeric(df_clean['waifu_id'], errors='coerce')
        df_clean = df_clean.dropna(subset=['waifu_id'])
        df_clean['waifu_id'] = df_clean['waifu_id'].astype(int)
        
        # Ensure rarity is integer and within valid range (1-3 for new system)
        df_clean['rarity'] = pd.to_numeric(df_clean['rarity'], errors='coerce')
        df_clean = df_clean.dropna(subset=['rarity'])
        df_clean['rarity'] = df_clean['rarity'].astype(int)
        
        # Use the rarity values from the input file (no automatic assignment)
        logger.info("⭐ Using star ratings from input file (no automatic assignment)")
        df_clean['favorites'] = pd.to_numeric(df_clean['favorites'], errors='coerce').fillna(0).astype(int)
        
        # Log the star distribution from the input file
        star_dist = df_clean['rarity'].value_counts().sort_index()
        total_chars = len(df_clean)
        logger.info("📊 Star distribution from input file:")
        for rarity, count in star_dist.items():
            percentage = (count / total_chars) * 100
            logger.info(f"  {rarity}★: {count} characters ({percentage:.1f}%)")
        
        # Validate rarity range for new star system (1-3★ only)
        invalid_rarity = df_clean[(df_clean['rarity'] < 1) | (df_clean['rarity'] > 3)]
        if len(invalid_rarity) > 0:
            logger.warning(f"⚠️  Found {len(invalid_rarity)} characters with invalid rarity (outside 1-3 range)")
            logger.info("Removing characters with invalid rarity...")
            df_clean = df_clean[(df_clean['rarity'] >= 1) & (df_clean['rarity'] <= 3)]
        
        # Fill missing optional fields
        df_clean['series'] = df_clean['series'].fillna('Unknown Series')
        df_clean['genre'] = df_clean['genre'].fillna('Anime')
        df_clean['image_url'] = df_clean['image_url'].fillna('')
        
        # Remove duplicates based on waifu_id
        duplicate_count = df_clean.duplicated(subset=['waifu_id']).sum()
        if duplicate_count > 0:
            logger.warning(f"⚠️  Found {duplicate_count} duplicate waifu_ids, keeping first occurrence")
            df_clean = df_clean.drop_duplicates(subset=['waifu_id'], keep='first')
        
        cleaned_count = len(df_clean)
        removed_count = original_count - cleaned_count
        
        logger.info(f"✅ Data validation complete:")
        logger.info(f"  - Original: {original_count} characters")
        logger.info(f"  - Cleaned: {cleaned_count} characters")
        logger.info(f"  - Removed: {removed_count} characters")
        
        return df_clean

    def get_rarity_description(self, rarity: int) -> str:
        """Get description for rarity level."""
        descriptions = {
            1: "Common - Direct Gacha",
            2: "Uncommon - Direct Gacha",
            3: "Rare - Direct Gacha",
            4: "Epic - Upgrade Only",
            5: "Legendary - Upgrade Only"
        }
        return descriptions.get(rarity, "Unknown")

    def analyze_star_system_impact(self, df: pd.DataFrame):
        """Analyze the impact of the new star system on the character distribution."""
        logger.info("🔍 Analyzing new star system impact...")
        
        total_chars = len(df)
        gacha_chars = len(df[df['rarity'] <= 3])  # 1-3 stars available in gacha (all characters now)
        
        logger.info(f"📈 Star System Analysis:")
        logger.info(f"  Total Characters: {total_chars}")
        logger.info(f"  All characters available in gacha (1-3★): {gacha_chars} (100%)")
        logger.info(f"  Characters can be upgraded to 4-5★ using shards after summoning")
        
        # Show rarity distribution
        logger.info("🎯 Current Rarity Distribution:")
        for rarity in [1, 2, 3]:
            count = len(df[df['rarity'] == rarity])
            if count > 0:
                percentage = count / total_chars * 100
                logger.info(f"    {rarity}★: {count} characters ({percentage:.1f}%)")

    def save_final_csv(self, df: pd.DataFrame) -> bool:
        """Save the final processed data to CSV."""
        try:
            logger.info(f"💾 Saving final data to {self.output_file}")
            
            # Ensure columns are in the expected order for upload_to_postgres.py
            column_order = ['waifu_id', 'name', 'series', 'series_id', 'genre', 'rarity', 'image_url', 'favorites']
            df_final = df[column_order]
            
            # Save to CSV
            df_final.to_csv(self.output_file, index=False, encoding='utf-8')
            
            logger.info(f"✅ Successfully saved {len(df_final)} characters to {self.output_file}")
            logger.info(f"📁 File size: {os.path.getsize(self.output_file)} bytes")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving CSV file: {e}")
            return False

    def process(self) -> bool:
        """Main processing function."""
        try:
            logger.info("🚀 Starting character final processing for new star system...")
            # Load Excel data
            df = self.load_excel_data()
            if df is None:
                return False
            # Validate and clean data
            df_clean = self.validate_and_clean_data(df)
            if df_clean.empty:
                logger.error("❌ No valid data after cleaning!")
                return False
            # Analyze star system impact
            self.analyze_star_system_impact(df_clean)
            # Save final CSV
            success = self.save_final_csv(df_clean)
            # Save anime_final.csv
            anime_map = self.load_anime_mal()
            anime_success = self.save_anime_final_csv(anime_map)
            if success and anime_success:
                logger.info("🎉 Character and anime final processing completed successfully!")
                logger.info(f"📤 Output ready for upload_to_mysql.py: {self.output_file}")
            elif success:
                logger.warning("Character data saved, but anime_final.csv failed!")
            elif anime_success:
                logger.warning("Anime data saved, but character_final.csv failed!")
            return success and anime_success
        except Exception as e:
            logger.error(f"❌ Fatal error during processing: {e}")
            return False


def main():
    """Main function."""
    processor = CharacterFinalProcessor()
    success = processor.process()
    
    print("\n" + "="*70)
    print("🌟 CHARACTER FINAL PROCESSOR - NEW STAR SYSTEM")
    print("="*70)
    print("📥 Input:  character_cleaned.xlsx (your manually edited file)")
    print("📤 Output: data/character_final.csv (ready for upload_to_mysql.py)")
    print("📤 Output: data/anime_final.csv (banner/anime info for gacha system)")
    print("")
    print("🎯 New Star System Features:")
    print("  ⭐ 1-3★: Available through direct gacha")
    print("  ⭐ 4-5★: Obtainable only through shard upgrades")
    print("  🔄 Automatic validation and cleaning")
    print("  📊 Rarity distribution analysis")
    print("  ✅ Compatible with upload_to_mysql.py")
    print("")
    print("Required Excel columns:")
    print("  - waifu_id, name, series, series_id, genre, rarity, image_url, favorites")
    print("="*70)
    
    if success:
        print("✅ SUCCESS: character_final.csv and anime_final.csv are ready!")
        print("🚀 Next step: Run upload_to_mysql.py to import to database")
    else:
        print("❌ FAILED: Check the logs above for errors")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
