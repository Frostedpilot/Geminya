#!/usr/bin/env python3
"""
CORRECT Migration script to convert files to new multi-media schema format.

This script properly converts:
1. anime_mal.xlsx → anime_mal.xlsx (updated schema, stays XLSX)
2. characters_cleaned.xlsx → characters_cleaned.xlsx (updated schema, stays XLSX) 
3. anime_mal.csv → data/intermediate/series_processed.csv (CSV to CSV)
4. character_sql.csv → data/intermediate/characters_processed.csv (CSV to CSV)
5. characters_with_stats.csv → data/final/characters_with_stats.csv (updated schema)
6. Creates ID registries
"""

import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path
import shutil


class CorrectSchemaConverter:
    """Properly converts files to new multi-media schema format"""
    
    def __init__(self):
        self.base_path = Path("data")
        self.ensure_directories()
        
    def ensure_directories(self):
        """Create necessary directories for new schema"""
        directories = [
            "data/registries",
            "data/intermediate", 
            "data/final",
            "data/backups"
        ]
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def backup_original_files(self):
        """Create timestamped backups of original files before conversion"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(f"data/backups/correct_migration_{timestamp}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        files_to_backup = [
            "data/anime_mal.xlsx",
            "data/characters_cleaned.xlsx", 
            "data/anime_mal.csv",
            "data/character_sql.csv",
            "data/characters_with_stats.csv"
        ]
        
        for file_path in files_to_backup:
            if Path(file_path).exists():
                backup_path = backup_dir / Path(file_path).name
                shutil.copy2(file_path, backup_path)
                print(f"✅ Backed up {file_path} → {backup_path}")
    
    def convert_anime_xlsx_file(self):
        """Convert anime_mal.xlsx to new schema → data/final/series_cleaned.xlsx"""
        print("🔄 Converting anime_mal.xlsx → data/final/series_cleaned.xlsx with new schema...")
        
        # Read the original XLSX file
        df = pd.read_excel("data/anime_mal.xlsx")
        
        # Add new schema fields while keeping existing ones
        df['source_type'] = 'mal'
        df['source_id'] = df['series_id'].astype(str)
        df['unique_series_id'] = df['series_id']  # Same for existing data
        
        # Convert studios to creator JSON format if exists
        if 'studios' in df.columns:
            df['creator'] = df['studios'].apply(lambda x: json.dumps({"studio": x}) if pd.notna(x) else json.dumps({}))
        else:
            df['creator'] = json.dumps({})
            
        # Add media_type
        df['media_type'] = 'anime'
        
        # Rename columns to match new schema
        column_mapping = {
            'title': 'name',
            'title_english': 'english_name', 
            'image_url': 'image_link'
        }
        df = df.rename(columns=column_mapping)
        
        # Save to final directory as series_cleaned.xlsx
        output_path = "data/final/series_cleaned.xlsx"
        df.to_excel(output_path, index=False)
        print(f"✅ Created series_cleaned.xlsx with new schema: {len(df)} series → {output_path}")
        return df
    
    def convert_characters_xlsx_file(self):
        """Convert characters_cleaned.xlsx → data/final/characters_cleaned.xlsx with new schema"""
        print("🔄 Converting characters_cleaned.xlsx → data/final/characters_cleaned.xlsx with new schema...")
        
        # Read the original XLSX file
        df = pd.read_excel("data/characters_cleaned.xlsx")
        
        # Need series mapping from anime_mal.csv for series_id lookup
        series_df = pd.read_csv("data/anime_mal.csv")
        series_mapping = dict(zip(series_df['title'], series_df['mal_id']))
        
        # Add new schema fields
        df['source_type'] = 'mal'
        df['source_id'] = df['mal_id'].astype(str)
        df['unique_waifu_id'] = range(1, len(df) + 1)  # Sequential for existing data
        
        # Map series to IDs
        df['series_source_id'] = df['series'].map(series_mapping).fillna(0).astype(int).astype(str) 
        df['series_unique_id'] = df['series'].map(series_mapping).fillna(0).astype(int)
        
        # Save to final directory with new schema
        output_path = "data/final/characters_cleaned.xlsx"
        df.to_excel(output_path, index=False)
        print(f"✅ Updated characters_cleaned.xlsx with new schema: {len(df)} characters → {output_path}")
        return df
    
    def convert_csv_anime_to_series_processed(self):
        """Convert anime_mal.csv → data/intermediate/series_processed.csv"""
        print("🔄 Converting anime_mal.csv → series_processed.csv...")
        
        # Read the CSV file
        df = pd.read_csv("data/anime_mal.csv")
        
        # Transform to new schema format
        new_df = pd.DataFrame({
            'source_type': 'mal',
            'source_id': df['mal_id'].astype(str),
            'unique_series_id': df['mal_id'],
            'name': df['title'],
            'english_name': df['title_english'].fillna('') if 'title_english' in df.columns else '',
            'creator': df['studios'].apply(lambda x: json.dumps({"studio": x}) if pd.notna(x) and x else json.dumps({})) if 'studios' in df.columns else json.dumps({}),
            'media_type': 'anime',
            'image_link': df['image_url'].fillna('') if 'image_url' in df.columns else '',
            'genres': df['genres'].fillna('') if 'genres' in df.columns else '',
            'synopsis': df['synopsis'].fillna('') if 'synopsis' in df.columns else '',
            'favorites': df['favorites'].fillna(0) if 'favorites' in df.columns else 0,
            'members': df['members'].fillna(0) if 'members' in df.columns else 0,
            'score': df['score'].fillna(0.0) if 'score' in df.columns else 0.0
        })
        
        # Save to intermediate directory
        output_path = "data/intermediate/series_processed.csv"
        new_df.to_csv(output_path, index=False)
        print(f"✅ Created series_processed.csv: {len(new_df)} series → {output_path}")
        return new_df
    
    def convert_csv_character_sql_to_characters_processed(self):
        """Convert character_sql.csv → data/intermediate/characters_processed.csv"""
        print("🔄 Converting character_sql.csv → characters_processed.csv...")
        
        # Read the CSV file
        df = pd.read_csv("data/character_sql.csv")
        
        # Need series mapping for series_id lookup
        series_df = pd.read_csv("data/anime_mal.csv")
        series_mapping = dict(zip(series_df['title'], series_df['mal_id']))
        
        # Transform to new schema format
        source_id_col = 'mal_id' if 'mal_id' in df.columns else ('waifu_id' if 'waifu_id' in df.columns else None)
        waifu_id_col = 'waifu_id' if 'waifu_id' in df.columns else None
        
        new_df = pd.DataFrame({
            'source_type': 'mal',
            'source_id': df[source_id_col].astype(str) if source_id_col else pd.Series(range(1, len(df)+1)).astype(str),
            'unique_waifu_id': df[waifu_id_col] if waifu_id_col else pd.Series(range(1, len(df)+1)),
            'name': df['name'],
            'series': df['series'],
            'series_source_id': df['series'].map(series_mapping).fillna(0).astype(int).astype(str),
            'series_unique_id': df['series'].map(series_mapping).fillna(0).astype(int),
            'genre': df['genre'] if 'genre' in df.columns else 'anime',
            'rarity': df['rarity'],
            'image_url': df['image_url'].fillna('') if 'image_url' in df.columns else '',
            'about': df['about'].fillna('') if 'about' in df.columns else '',
            'favorites': df['favorites'].fillna(0) if 'favorites' in df.columns else 0
        })
        
        # Save to intermediate directory
        output_path = "data/intermediate/characters_processed.csv"
        new_df.to_csv(output_path, index=False)
        print(f"✅ Created characters_processed.csv: {len(new_df)} characters → {output_path}")
        return new_df
    
    def update_characters_with_stats_csv(self):
        """Update characters_with_stats.csv with new schema fields"""
        print("🔄 Updating characters_with_stats.csv with new schema...")
        
        # Read the existing stats file
        df = pd.read_csv("data/characters_with_stats.csv")
        
        # Need series mapping for series_id lookup
        series_df = pd.read_csv("data/anime_mal.csv")
        series_mapping = dict(zip(series_df['title'], series_df['mal_id']))
        
        # Add new schema fields to existing data
        df['source_type'] = 'mal'
        df['source_id'] = df['mal_id'].astype(str)
        df['unique_waifu_id'] = range(1, len(df) + 1)  # Sequential for existing data
        df['series_source_id'] = df['series'].map(series_mapping).fillna(0).astype(int).astype(str)
        df['series_unique_id'] = df['series'].map(series_mapping).fillna(0).astype(int)
        
        # Reorder columns to put new schema fields first
        new_columns = ['source_type', 'source_id', 'unique_waifu_id', 'series_source_id', 'series_unique_id'] + \
                     [col for col in df.columns if col not in ['source_type', 'source_id', 'unique_waifu_id', 'series_source_id', 'series_unique_id']]
        df = df[new_columns]
        
        # Save updated file
        output_path = "data/final/characters_with_stats.csv"
        df.to_csv(output_path, index=False)
        print(f"✅ Updated characters_with_stats.csv: {len(df)} characters → {output_path}")
        return df
    
    def create_series_id_registry(self, series_df):
        """Create series_id_registry.csv from series data"""
        print("🔄 Creating series ID registry...")
        
        registry_df = pd.DataFrame({
            'source_type': series_df['source_type'],
            'source_id': series_df['source_id'], 
            'unique_series_id': series_df['unique_series_id'],
            'name': series_df['name'],
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        output_path = "data/registries/series_id_registry.csv"
        registry_df.to_csv(output_path, index=False)
        print(f"✅ Created series registry: {len(registry_df)} entries → {output_path}")
        return registry_df
    
    def create_character_id_registry(self, characters_df):
        """Create character_id_registry.csv from character data"""
        print("🔄 Creating character ID registry...")
        
        registry_df = pd.DataFrame({
            'source_type': characters_df['source_type'],
            'source_id': characters_df['source_id'],
            'unique_waifu_id': characters_df['unique_waifu_id'], 
            'name': characters_df['name'],
            'series_unique_id': characters_df['series_unique_id'],
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        output_path = "data/registries/character_id_registry.csv"
        registry_df.to_csv(output_path, index=False)
        print(f"✅ Created character registry: {len(registry_df)} entries → {output_path}")
        return registry_df
    
    def validate_conversion(self):
        """Validate the conversion was successful"""
        print("🔍 Validating conversion...")
        
        results = []
        
        # Check XLSX files have new columns in correct locations
        try:
            series_xlsx = pd.read_excel("data/final/series_cleaned.xlsx")
            required_cols = ['source_type', 'source_id', 'unique_series_id', 'creator', 'media_type']
            missing = [col for col in required_cols if col not in series_xlsx.columns]
            if missing:
                results.append(f"❌ data/final/series_cleaned.xlsx missing: {missing}")
            else:
                results.append(f"✅ data/final/series_cleaned.xlsx has correct schema ({len(series_xlsx)} rows)")
        except Exception as e:
            results.append(f"❌ data/final/series_cleaned.xlsx error: {e}")
            
        try:
            chars_xlsx = pd.read_excel("data/final/characters_cleaned.xlsx")
            required_cols = ['source_type', 'source_id', 'unique_waifu_id', 'series_source_id', 'series_unique_id']
            missing = [col for col in required_cols if col not in chars_xlsx.columns]
            if missing:
                results.append(f"❌ data/final/characters_cleaned.xlsx missing: {missing}")
            else:
                results.append(f"✅ data/final/characters_cleaned.xlsx has correct schema ({len(chars_xlsx)} rows)")
        except Exception as e:
            results.append(f"❌ data/final/characters_cleaned.xlsx error: {e}")
        
        # Check CSV files
        csv_files = [
            "data/intermediate/series_processed.csv",
            "data/intermediate/characters_processed.csv",
            "data/final/characters_with_stats.csv",
            "data/registries/series_id_registry.csv",
            "data/registries/character_id_registry.csv"
        ]
        
        for file_path in csv_files:
            if Path(file_path).exists():
                df = pd.read_csv(file_path)
                results.append(f"✅ {file_path}: {len(df)} rows")
            else:
                results.append(f"❌ {file_path}: Missing!")
        
        print("\n".join(results))
        return results
    
    def run_correct_conversion(self):
        """Run the correct conversion process"""
        print("🚀 Starting CORRECT schema conversion...")
        print("XLSX files → XLSX files (updated schema)")
        print("CSV files → processed CSV files")
        print("=" * 80)
        
        try:
            # Step 1: Backup original files
            self.backup_original_files()
            
            # Step 2: Convert XLSX files (keeping as XLSX)
            self.convert_anime_xlsx_file()
            self.convert_characters_xlsx_file()
            
            # Step 3: Convert CSV files to processed CSV
            series_df = self.convert_csv_anime_to_series_processed()
            characters_df = self.convert_csv_character_sql_to_characters_processed() 
            
            # Step 4: Update stats CSV
            self.update_characters_with_stats_csv()
            
            # Step 5: Create ID registries
            self.create_series_id_registry(series_df)
            self.create_character_id_registry(characters_df)
            
            # Step 6: Validate conversion
            self.validate_conversion()
            
            print("=" * 80)
            print("✅ CORRECT schema conversion completed successfully!")
            print("\nConverted files:")
            print("- data/final/series_cleaned.xlsx (from anime_mal.xlsx with new schema)")
            print("- data/final/characters_cleaned.xlsx (updated with new schema)") 
            print("- data/intermediate/series_processed.csv (from anime_mal.csv)")
            print("- data/intermediate/characters_processed.csv (from character_sql.csv)")
            print("- data/final/characters_with_stats.csv (updated schema)")
            print("- ID registries created")
            
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            raise


if __name__ == "__main__":
    converter = CorrectSchemaConverter()
    converter.run_correct_conversion()