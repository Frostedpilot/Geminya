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

    def apply_star_assignment_logic(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the new star assignment logic based on favorites and series popularity."""
        logger.info("⭐ Applying new star assignment logic...")
        
        df_result = df.copy()
        
        # Step 1: Characters with over 1000 favorites get 3★
        high_fav_mask = df_result['favorites'] > 1000
        df_result.loc[high_fav_mask, 'rarity'] = 3
        high_fav_count = high_fav_mask.sum()
        logger.info(f"  📊 Step 1: {high_fav_count} characters with >1000 favorites → 3★")
        
        # Step 2: Most favorite character in each series gets 3★
        # Group by series and find the character with highest favorites in each series
        series_max_idx = df_result.groupby('series')['favorites'].idxmax()
        df_result.loc[series_max_idx, 'rarity'] = 3
        
        # Count how many new 3★ characters this created (excluding those already 3★ from step 1)
        series_max_mask = df_result.index.isin(series_max_idx)
        new_series_max_mask = series_max_mask & ~high_fav_mask
        series_max_count = new_series_max_mask.sum()
        logger.info(f"  📊 Step 2: {series_max_count} series favorites (not already 3★) → 3★")
        
        # Step 3: For remaining characters, assign based on percentile
        # Find characters that are not yet 3★
        not_three_star_mask = df_result['rarity'] != 3
        remaining_chars = df_result[not_three_star_mask].copy()
        
        if len(remaining_chars) > 0:
            # Calculate 50th percentile of favorites for remaining characters
            percentile_50 = remaining_chars['favorites'].quantile(0.5)
            logger.info(f"  📊 Step 3: 50th percentile of remaining characters: {percentile_50:.0f} favorites")
            
            # Lower 50% become 1★, upper 50% become 2★
            lower_50_mask = (df_result['rarity'] != 3) & (df_result['favorites'] <= percentile_50)
            upper_50_mask = (df_result['rarity'] != 3) & (df_result['favorites'] > percentile_50)
            
            df_result.loc[lower_50_mask, 'rarity'] = 1
            df_result.loc[upper_50_mask, 'rarity'] = 2
            
            lower_count = lower_50_mask.sum()
            upper_count = upper_50_mask.sum()
            
            logger.info(f"  📊 Step 3a: {lower_count} characters (≤{percentile_50:.0f} fav) → 1★")
            logger.info(f"  📊 Step 3b: {upper_count} characters (>{percentile_50:.0f} fav) → 2★")
        
        # Final summary
        final_dist = df_result['rarity'].value_counts().sort_index()
        total_chars = len(df_result)
        logger.info("✅ Final star distribution:")
        for rarity, count in final_dist.items():
            percentage = (count / total_chars) * 100
            logger.info(f"  {rarity}★: {count} characters ({percentage:.1f}%)")
        
        return df_result

    def validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean the DataFrame for the new star system."""
        logger.info("🧹 Validating and cleaning data...")
        
        original_count = len(df)
        
        # Required columns for upload_to_mysql.py compatibility
        required_columns = ['mal_id', 'name', 'series', 'genre', 'rarity', 'image_url', 'favorites']
        
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
        df_clean = df_clean.dropna(subset=['mal_id', 'name', 'rarity'])
        
        # Ensure mal_id is integer
        df_clean['mal_id'] = pd.to_numeric(df_clean['mal_id'], errors='coerce')
        df_clean = df_clean.dropna(subset=['mal_id'])
        df_clean['mal_id'] = df_clean['mal_id'].astype(int)
        
        # Ensure rarity is integer and within valid range (1-3 for new system)
        df_clean['rarity'] = pd.to_numeric(df_clean['rarity'], errors='coerce')
        df_clean = df_clean.dropna(subset=['rarity'])
        df_clean['rarity'] = df_clean['rarity'].astype(int)
        
        # Apply star assignment logic based on favorites
        logger.info("🌟 Applying comprehensive star assignment logic...")
        df_clean['favorites'] = pd.to_numeric(df_clean['favorites'], errors='coerce').fillna(0).astype(int)
        
        # Apply the new star assignment logic
        df_clean = self.apply_star_assignment_logic(df_clean)
        
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
        
        # Remove duplicates based on mal_id
        duplicate_count = df_clean.duplicated(subset=['mal_id']).sum()
        if duplicate_count > 0:
            logger.warning(f"⚠️  Found {duplicate_count} duplicate mal_ids, keeping first occurrence")
            df_clean = df_clean.drop_duplicates(subset=['mal_id'], keep='first')
        
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
            
            # Ensure columns are in the expected order for upload_to_mysql.py
            column_order = ['mal_id', 'name', 'series', 'genre', 'rarity', 'image_url', 'favorites']
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
            
            if success:
                logger.info("🎉 Character final processing completed successfully!")
                logger.info(f"📤 Output ready for upload_to_mysql.py: {self.output_file}")
            
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
    print("  - mal_id, name, series, genre, rarity, image_url, favorites")
    print("="*70)
    
    if success:
        print("✅ SUCCESS: character_final.csv is ready!")
        print("🚀 Next step: Run upload_to_mysql.py to import to database")
    else:
        print("❌ FAILED: Check the logs above for errors")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
