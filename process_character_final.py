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
    """Process cleaned Excel file for the new star system."""

    def __init__(self):
        self.input_file = os.path.join("data", "characters_cleaned.xlsx")
        self.anime_input_file = os.path.join("data", "anime_mal.xlsx")
        self.character_output_file = os.path.join("data", "character_final.csv")
        self.anime_output_file = os.path.join("data", "anime_final.csv")
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
    def load_anime_excel(self) -> Optional[pd.DataFrame]:
        """Load the anime Excel file for series info."""
        try:
            logger.info(f"Loading Anime Excel file: {self.anime_input_file}")
            df = pd.read_excel(self.anime_input_file)
            logger.info(f"✅ Loaded {len(df)} anime/series from Excel file")
            logger.info(f"📋 Anime Columns: {list(df.columns)}")
            return df
        except FileNotFoundError:
            logger.error(f"❌ Anime Excel file {self.anime_input_file} not found!")
            return None
        except Exception as e:
            logger.error(f"❌ Error loading Anime Excel file: {e}")
            return None

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

    def save_final_csvs(self, df_char: pd.DataFrame, df_anime: pd.DataFrame) -> bool:
        """Save the final processed character and anime data to CSV."""
        try:
            logger.info(f"💾 Saving anime/series data to {self.anime_output_file}")
            anime_column_order = ['series_id', 'name', 'english_name', 'image_link']
            df_anime_final = df_anime[anime_column_order]
            df_anime_final.to_csv(self.anime_output_file, index=False, encoding='utf-8')
            logger.info(f"✅ Saved {len(df_anime_final)} series to {self.anime_output_file}")
            logger.info(f"📁 File size: {os.path.getsize(self.anime_output_file)} bytes")

            logger.info(f"💾 Saving character data to {self.character_output_file}")
            char_column_order = ['waifu_id', 'name', 'series', 'series_id', 'genre', 'rarity', 'image_url', 'favorites']
            df_char_final = df_char[char_column_order]
            df_char_final.to_csv(self.character_output_file, index=False, encoding='utf-8')
            logger.info(f"✅ Saved {len(df_char_final)} characters to {self.character_output_file}")
            logger.info(f"📁 File size: {os.path.getsize(self.character_output_file)} bytes")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving CSV files: {e}")
            return False

    def process(self) -> bool:
        """Main processing function for both characters and series."""
        try:
            logger.info("🚀 Starting character and series processing for new star system...")
            # Load character and anime data
            df_char = self.load_excel_data()
            df_anime = self.load_anime_excel()
            if df_char is None or df_anime is None:
                logger.error("❌ Missing input files!")
                return False
            # Clean character data
            df_char_clean = self.validate_and_clean_data(df_char)
            if df_char_clean.empty:
                logger.error("❌ No valid character data after cleaning!")
                return False
            # Clean and deduplicate anime/series data
            # Map anime_mal.xlsx columns to expected names
            df_anime['name'] = df_anime['title'].astype(str).str.strip()
            df_anime['english_name'] = df_anime['title_english'].astype(str).str.strip() if 'title_english' in df_anime.columns else ''
            df_anime['image_link'] = df_anime['image_url'].astype(str).str.strip() if 'image_url' in df_anime.columns else ''
            # Deduplicate by name
            df_anime = df_anime.drop_duplicates(subset=['name'])
            df_anime = df_anime.reset_index(drop=True)
            df_anime['series_id'] = df_anime.index + 1
            # Map series name to series_id for characters
            char_series_map = {n.strip().lower(): sid for n, sid in zip(df_anime['name'], df_anime['series_id'])}
            df_char_clean['series_id'] = df_char_clean['series'].astype(str).str.strip().str.lower().map(char_series_map)
            missing_series = df_char_clean[df_char_clean['series_id'].isnull()]['series'].unique()
            if len(missing_series) > 0:
                logger.warning(f"⚠️ Some characters have series not found in anime_mal.xlsx: {missing_series}")
                # Optionally, assign a default series_id or drop these rows
                df_char_clean = df_char_clean.dropna(subset=['series_id'])
            df_char_clean['series_id'] = df_char_clean['series_id'].astype(int)
            # Analyze star system impact
            self.analyze_star_system_impact(df_char_clean)
            # Save both CSVs
            success = self.save_final_csvs(df_char_clean, df_anime)
            if success:
                logger.info("🎉 Character and series processing completed successfully!")
                logger.info(f"📤 Outputs: {self.character_output_file}, {self.anime_output_file}")
            return success
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
    print("")
    print("🎯 New Star System Features:")
    print("  ⭐ 1-3★: Available through direct gacha")
    print("  ⭐ 4-5★: Obtainable only through shard upgrades")
    print("  🔄 Automatic validation and cleaning")
    print("  📊 Rarity distribution analysis")
    print("  ✅ Compatible with upload_to_mysql.py")
    print("")
    print("Required Excel columns:")
    print("  - waifu_id, name, series, genre, rarity, image_url, favorites")
    print("="*70)
    
    if success:
        print("✅ SUCCESS: character_final.csv is ready!")
        print("🚀 Next step: Run upload_to_mysql.py to import to database")
    else:
        print("❌ FAILED: Check the logs above for errors")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
