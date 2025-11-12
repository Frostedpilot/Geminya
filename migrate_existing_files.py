#!/usr/bin/env python3
"""
Migration script to convert existing XLSX and CSV files from old anime-only schema 
to new multi-media schema with registry-compatible format.

This script converts:
1. anime_mal.xlsx → data/intermediate/series_processed.csv (new schema)
2. characters_cleaned.xlsx → data/intermediate/characters_processed.csv (new schema) 
3. characters_with_stats.csv → data/final/characters_with_stats.csv (new schema)
4. Creates ID registries with existing data mappings
"""

import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path


class SchemaConverter:
    """Converts old anime-only files to new multi-media schema format"""
    
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
    
    def backup_existing_files(self):
        """Create timestamped backups of existing files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(f"data/backups/migration_{timestamp}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        files_to_backup = [
            "data/anime_mal.xlsx",
            "data/characters_cleaned.xlsx", 
            "data/characters_with_stats.csv"
        ]
        
        for file_path in files_to_backup:
            if Path(file_path).exists():
                backup_path = backup_dir / Path(file_path).name
                if file_path.endswith('.xlsx'):
                    # Convert to CSV for backup
                    df = pd.read_excel(file_path)
                    df.to_csv(backup_path.with_suffix('.csv'), index=False)
                else:
                    df = pd.read_csv(file_path)
                    df.to_csv(backup_path, index=False)
                print(f"✅ Backed up {file_path} → {backup_path}")
    
    def convert_anime_series_file(self):
        """Convert anime_mal.xlsx to new series_processed.csv format"""
        print("🔄 Converting anime_mal.xlsx to new series format...")
        
        # Read the old anime file
        df = pd.read_excel("data/anime_mal.xlsx")
        
        # Transform to new schema format
        new_df = pd.DataFrame({
            'source_type': 'mal',
            'source_id': df['series_id'].astype(str),
            'unique_series_id': df['series_id'],  # Will be same for existing data
            'name': df['title'],
            'english_name': df['title_english'].fillna(''),
            'creator': df['studios'].apply(lambda x: json.dumps({"studio": x}) if pd.notna(x) else json.dumps({})),
            'media_type': 'anime',
            'image_link': df['image_url'].fillna(''),
            'genres': df['genres'].fillna(''),
            'synopsis': df['synopsis'].fillna(''),
            'favorites': df['favorites'].fillna(0),
            'members': df['members'].fillna(0),
            'score': df['score'].fillna(0.0)
        })
        
        # Save to intermediate directory
        output_path = "data/intermediate/series_processed.csv"
        new_df.to_csv(output_path, index=False)
        print(f"✅ Converted series data: {len(new_df)} series → {output_path}")
        return new_df
    
    def convert_characters_cleaned_file(self):
        """Convert characters_cleaned.xlsx to new characters_processed.csv format"""  
        print("🔄 Converting characters_cleaned.xlsx to new character format...")
        
        # Read the old characters file
        df = pd.read_excel("data/characters_cleaned.xlsx")
        
        # Need to map series names to series_ids from anime_mal.xlsx
        series_df = pd.read_excel("data/anime_mal.xlsx")
        series_mapping = dict(zip(series_df['title'], series_df['series_id']))
        
        # Transform to new schema format
        new_df = pd.DataFrame({
            'source_type': 'mal',
            'source_id': df['mal_id'].astype(str),
            'unique_waifu_id': df.index + 1,  # Temporary sequential IDs, will be fixed by registry
            'name': df['name'],
            'series': df['series'],
            'series_source_id': df['series'].map(series_mapping).fillna(0).astype(int).astype(str),
            'series_unique_id': df['series'].map(series_mapping).fillna(0).astype(int),
            'genre': df['genre'],  # This will become media_type in final processing
            'rarity': df['rarity'],
            'image_url': df['image_url'].fillna(''),
            'about': df['about'].fillna(''),
            'favorites': df['favorites'].fillna(0)
        })
        
        # Save to intermediate directory
        output_path = "data/intermediate/characters_processed.csv"
        new_df.to_csv(output_path, index=False)
        print(f"✅ Converted character data: {len(new_df)} characters → {output_path}")
        return new_df
    
    def convert_characters_with_stats_file(self):
        """Convert characters_with_stats.csv to new schema format"""
        print("🔄 Converting characters_with_stats.csv to new format...")
        
        # Read the existing stats file
        df = pd.read_csv("data/characters_with_stats.csv")
        
        # Need to map series names to series_ids
        series_df = pd.read_excel("data/anime_mal.xlsx")
        series_mapping = dict(zip(series_df['title'], series_df['series_id']))
        
        # Transform to new schema format
        new_df = pd.DataFrame({
            'source_type': 'mal',
            'source_id': df['mal_id'].astype(str),
            'unique_waifu_id': df.index + 1,  # Temporary sequential IDs
            'name': df['name'],
            'series': df['series'],
            'series_source_id': df['series'].map(series_mapping).fillna(0).astype(int).astype(str),
            'series_unique_id': df['series'].map(series_mapping).fillna(0).astype(int),
            'genre': df['genre'],  # This will become media_type
            'rarity': df['rarity'],
            'image_url': df['image_url'].fillna(''),
            'about': df['about'].fillna(''),
            'favorites': df['favorites'].fillna(0),
            'archetype': df['archetype'].fillna(''),
            'stats': df['stats'].fillna('{}'),
            'potency': df['potency'].fillna(0),
            'elemental_type': df['elemental_type'].fillna('[]'),
            'elemental_resistances': df['elemental_resistances'].fillna('{}')
        })
        
        # Save to final directory (this replaces the old stats file)
        output_path = "data/final/characters_with_stats.csv"
        new_df.to_csv(output_path, index=False)
        print(f"✅ Converted stats data: {len(new_df)} characters → {output_path}")
        return new_df
    
    def create_series_id_registry(self, series_df):
        """Create series_id_registry.csv from converted series data"""
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
        """Create character_id_registry.csv from converted character data"""
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
        """Validate that the conversion was successful"""
        print("🔍 Validating conversion...")
        
        validation_results = []
        
        # Check that files exist
        expected_files = [
            "data/intermediate/series_processed.csv",
            "data/intermediate/characters_processed.csv", 
            "data/final/characters_with_stats.csv",
            "data/registries/series_id_registry.csv",
            "data/registries/character_id_registry.csv"
        ]
        
        for file_path in expected_files:
            if Path(file_path).exists():
                df = pd.read_csv(file_path)
                validation_results.append(f"✅ {file_path}: {len(df)} rows")
            else:
                validation_results.append(f"❌ {file_path}: Missing!")
        
        # Check data integrity
        try:
            series_df = pd.read_csv("data/intermediate/series_processed.csv")
            chars_df = pd.read_csv("data/intermediate/characters_processed.csv")
            
            # Validate that all characters have valid series references
            series_ids = set(series_df['unique_series_id'])
            char_series_ids = set(chars_df['series_unique_id'])
            orphaned = char_series_ids - series_ids
            
            if orphaned:
                validation_results.append(f"⚠️  {len(orphaned)} characters reference missing series IDs: {orphaned}")
            else:
                validation_results.append("✅ All characters have valid series references")
                
        except Exception as e:
            validation_results.append(f"❌ Validation error: {e}")
        
        print("\n".join(validation_results))
        return validation_results
    
    def run_full_conversion(self):
        """Run the complete conversion process"""
        print("🚀 Starting schema conversion from old anime-only to new multi-media format...")
        print("=" * 80)
        
        try:
            # Step 1: Backup existing files
            self.backup_existing_files()
            
            # Step 2: Convert series data
            series_df = self.convert_anime_series_file()
            
            # Step 3: Convert character data
            characters_df = self.convert_characters_cleaned_file()
            
            # Step 4: Convert stats data
            stats_df = self.convert_characters_with_stats_file()
            
            # Step 5: Create ID registries
            self.create_series_id_registry(series_df)
            self.create_character_id_registry(characters_df)
            
            # Step 6: Validate conversion
            self.validate_conversion()
            
            print("=" * 80)
            print("✅ Schema conversion completed successfully!")
            print("\nNext steps:")
            print("1. Review converted files in data/intermediate/ and data/final/")
            print("2. Check ID registries in data/registries/")
            print("3. Test with collect_and_process_media.py")
            print("4. Run process_character_final.py with new inputs")
            
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            raise


if __name__ == "__main__":
    converter = SchemaConverter()
    converter.run_full_conversion()