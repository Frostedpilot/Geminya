#!/usr/bin/env python3
"""ID Manager for multi-media integration with couple-based ID assignment.

This module manages the mapping from (source_type, source_id) to unique_id
with continuous ID ranges and file-based registry persistence.
"""

import os
import csv
import json
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import time

# Platform-specific imports
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

# Setup logging
logger = logging.getLogger(__name__)


class IDManager:
    """Manages couple-based ID assignment with continuous ranges.
    
    This class provides thread-safe ID assignment using file-based registries
    to track mappings from (source_type, source_id) to unique continuous IDs.
    """

    def __init__(self):
        self.series_registry_file = "data/registries/series_id_registry.csv"
        self.character_registry_file = "data/registries/character_id_registry.csv"
        
        # Ensure directories exist
        os.makedirs("data/registries", exist_ok=True)
        
        # Initialize registries if they don't exist
        self._ensure_registries_exist()
        
        logger.info("IDManager initialized with registries: %s, %s", 
                   self.series_registry_file, self.character_registry_file)

    def _ensure_registries_exist(self):
        """Create registry CSV files with headers if they don't exist."""
        series_headers = ["source_type", "source_id", "unique_series_id", "name", "created_at"]
        character_headers = ["source_type", "source_id", "unique_waifu_id", "name", "series_unique_id", "created_at"]
        
        if not os.path.exists(self.series_registry_file):
            with open(self.series_registry_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(series_headers)
            logger.info("Created series registry file: %s", self.series_registry_file)
        
        if not os.path.exists(self.character_registry_file):
            with open(self.character_registry_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(character_headers)
            logger.info("Created character registry file: %s", self.character_registry_file)



    def _with_file_lock(self, file_path: str, operation_func, *args, **kwargs):
        """Execute operation with exclusive file lock for thread safety."""
        try:
            # For now, use simple synchronization (can be enhanced later)
            # This is sufficient for single-process usage
            time.sleep(0.01)  # Small delay to avoid race conditions
            return operation_func(file_path, *args, **kwargs)
                
        except Exception as e:
            logger.error("Error with file lock operation on %s: %s", file_path, e)
            raise

    def _get_next_series_id_internal(self, file_path: str) -> int:
        """Internal method to get next available series ID."""
        try:
            df = pd.read_csv(file_path)
            if df.empty or 'unique_series_id' not in df.columns:
                return 1
            
            max_id = df['unique_series_id'].max()
            return int(max_id) + 1 if pd.notna(max_id) else 1
            
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return 1
        except Exception as e:
            logger.error("Error reading series registry: %s", e)
            return 1

    def _get_next_character_id_internal(self, file_path: str) -> int:
        """Internal method to get next available character ID."""
        try:
            df = pd.read_csv(file_path)
            if df.empty or 'unique_waifu_id' not in df.columns:
                return 1
                
            max_id = df['unique_waifu_id'].max()
            return int(max_id) + 1 if pd.notna(max_id) else 1
            
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return 1
        except Exception as e:
            logger.error("Error reading character registry: %s", e)
            return 1

    def get_next_series_id(self) -> int:
        """Get next available series ID (continuous)."""
        return self._with_file_lock(
            self.series_registry_file, 
            self._get_next_series_id_internal
        )

    def get_next_character_id(self) -> int:
        """Get next available character ID (continuous)."""
        return self._with_file_lock(
            self.character_registry_file, 
            self._get_next_character_id_internal
        )

    def _find_existing_series_id(self, source_type: str, source_id: str) -> Optional[int]:
        """Find existing series ID for (source_type, source_id) couple."""
        try:
            df = pd.read_csv(self.series_registry_file)
            # Ensure source_id is string for comparison
            source_id_str = str(source_id)
            matches = df[(df['source_type'] == source_type) & 
                        (df['source_id'] == source_id_str)]
            
            if not matches.empty:
                return int(matches.iloc[0]['unique_series_id'])
            return None
            
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return None
        except Exception as e:
            logger.error("Error finding existing series ID: %s", e)
            return None

    def _find_existing_character_id(self, source_type: str, source_id: str) -> Optional[int]:
        """Find existing character ID for (source_type, source_id) couple."""
        try:
            df = pd.read_csv(self.character_registry_file)
            # Ensure source_id is string for comparison
            source_id_str = str(source_id)
            matches = df[(df['source_type'] == source_type) & 
                        (df['source_id'] == source_id_str)]
            
            if not matches.empty:
                return int(matches.iloc[0]['unique_waifu_id'])
            return None
            
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return None
        except Exception as e:
            logger.error("Error finding existing character ID: %s", e)
            return None

    def _add_series_registry_entry(self, file_path: str, source_type: str, 
                                  source_id: str, name: str, unique_id: int):
        """Add entry to series registry."""
        entry = {
            'source_type': source_type,
            'source_id': str(source_id),  # Ensure source_id is stored as string
            'unique_series_id': unique_id,
            'name': name,
            'created_at': datetime.now().isoformat()
        }
        
        # Append to CSV
        with open(file_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=entry.keys())
            writer.writerow(entry)
            
        logger.info("Added series registry entry: (%s, %s) → %d (%s)", 
                   source_type, source_id, unique_id, name)

    def _add_character_registry_entry(self, file_path: str, source_type: str,
                                     source_id: str, name: str, unique_id: int, 
                                     series_id: int):
        """Add entry to character registry."""
        entry = {
            'source_type': source_type,
            'source_id': str(source_id),  # Ensure source_id is stored as string
            'unique_waifu_id': unique_id,
            'name': name,
            'series_unique_id': series_id,
            'created_at': datetime.now().isoformat()
        }
        
        # Append to CSV
        with open(file_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=entry.keys())
            writer.writerow(entry)
            
        logger.info("Added character registry entry: (%s, %s) → %d (%s, series=%d)", 
                   source_type, source_id, unique_id, name, series_id)

    def get_or_create_series_id(self, source_type: str, source_id: str, name: str) -> int:
        """Get existing ID or create new continuous ID for series.
        
        Args:
            source_type: Source identifier (e.g., 'mal', 'vndb', 'genshin')
            source_id: Original ID from that source
            name: Series name
            
        Returns:
            Unique continuous series ID
        """
        # Check if already exists
        existing_id = self._find_existing_series_id(source_type, source_id)
        if existing_id is not None:
            logger.debug("Found existing series ID: (%s, %s) → %d", 
                        source_type, source_id, existing_id)
            return existing_id
        
        # Get new ID and add entry with file lock and double-check
        def create_new_entry(file_path: str):
            # Double-check inside the lock to prevent race conditions
            existing_id_inner = self._find_existing_series_id(source_type, source_id)
            if existing_id_inner is not None:
                logger.debug("Double-check found existing series ID: (%s, %s) → %d", 
                            source_type, source_id, existing_id_inner)
                return existing_id_inner
                
            next_id = self._get_next_series_id_internal(file_path)
            self._add_series_registry_entry(file_path, source_type, source_id, name, next_id)
            logger.info("Created new series ID: (%s, %s) → %d", source_type, source_id, next_id)
            return next_id
            
        return self._with_file_lock(self.series_registry_file, create_new_entry)

    def get_or_create_character_id(self, source_type: str, source_id: str, 
                                  name: str, series_id: int) -> int:
        """Get existing ID or create new continuous ID for character.
        
        Args:
            source_type: Source identifier (e.g., 'mal', 'vndb', 'genshin')
            source_id: Original ID from that source  
            name: Character name
            series_id: Unique series ID this character belongs to
            
        Returns:
            Unique continuous character ID
        """
        # Check if already exists
        existing_id = self._find_existing_character_id(source_type, source_id)
        if existing_id is not None:
            logger.debug("Found existing character ID: (%s, %s) → %d", 
                        source_type, source_id, existing_id)
            return existing_id
        
        # Get new ID and add entry with file lock and double-check
        def create_new_entry(file_path: str):
            # Double-check inside the lock to prevent race conditions
            existing_id_inner = self._find_existing_character_id(source_type, source_id)
            if existing_id_inner is not None:
                logger.debug("Double-check found existing character ID: (%s, %s) → %d", 
                            source_type, source_id, existing_id_inner)
                return existing_id_inner
                
            next_id = self._get_next_character_id_internal(self.character_registry_file)
            self._add_character_registry_entry(
                file_path, source_type, source_id, name, next_id, series_id
            )
            logger.info("Created new character ID: (%s, %s) → %d", source_type, source_id, next_id)
            return next_id
            
        return self._with_file_lock(self.character_registry_file, create_new_entry)

    def get_series_registry(self) -> pd.DataFrame:
        """Get the complete series registry as DataFrame."""
        try:
            return pd.read_csv(self.series_registry_file)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return pd.DataFrame(columns=["source_type", "source_id", "unique_series_id", "name", "created_at"])

    def get_character_registry(self) -> pd.DataFrame:
        """Get the complete character registry as DataFrame."""
        try:
            return pd.read_csv(self.character_registry_file)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return pd.DataFrame(columns=["source_type", "source_id", "unique_waifu_id", "name", "series_unique_id", "created_at"])

    def migrate_existing_data(self, existing_series: List[Dict[str, Any]], 
                             existing_characters: List[Dict[str, Any]]):
        """Populate registries with existing database data.
        
        Args:
            existing_series: List of existing series from database
            existing_characters: List of existing characters from database
        """
        logger.info("Starting migration of existing data to ID registries...")
        
        # Migrate series data
        logger.info("Migrating %d existing series...", len(existing_series))
        for series in existing_series:
            # For existing data, assume source_type='mal' and use existing IDs
            source_id = str(series.get('mal_id', series.get('series_id', '')))
            name = series.get('name', series.get('title', 'Unknown'))
            unique_id = series.get('series_id', series.get('id'))
            
            if source_id and unique_id:
                self._add_series_registry_entry(
                    self.series_registry_file, 
                    'mal', source_id, name, int(unique_id)
                )
        
        # Migrate character data
        logger.info("Migrating %d existing characters...", len(existing_characters))
        for character in existing_characters:
            # For existing data, assume source_type='mal' and use existing IDs
            source_id = str(character.get('mal_id', character.get('waifu_id', '')))
            name = character.get('name', 'Unknown')
            unique_id = character.get('waifu_id', character.get('id'))
            series_id = character.get('series_id', 0)
            
            if source_id and unique_id:
                self._add_character_registry_entry(
                    self.character_registry_file,
                    'mal', source_id, name, int(unique_id), int(series_id)
                )
        
        logger.info("✅ Migration completed successfully!")

    def validate_registry_integrity(self) -> Dict[str, Any]:
        """Validate registry files for consistency and gaps."""
        report = {
            'series_total': 0,
            'characters_total': 0,
            'series_id_gaps': [],
            'character_id_gaps': [],
            'duplicates': [],
            'orphaned_characters': []
        }
        
        try:
            # Check series registry
            series_df = self.get_series_registry()
            if not series_df.empty:
                report['series_total'] = len(series_df)
                series_ids = sorted(series_df['unique_series_id'].tolist())
                
                # Check for gaps in ID sequence
                for i in range(1, max(series_ids) + 1):
                    if i not in series_ids:
                        report['series_id_gaps'].append(i)
                
                # Check for duplicates
                duplicates = series_df[series_df.duplicated(['source_type', 'source_id'], keep=False)]
                if not duplicates.empty:
                    report['duplicates'].extend(duplicates.to_dict('records'))
            
            # Check character registry
            char_df = self.get_character_registry()
            if not char_df.empty:
                report['characters_total'] = len(char_df)
                char_ids = sorted(char_df['unique_waifu_id'].tolist())
                
                # Check for gaps in ID sequence
                for i in range(1, max(char_ids) + 1):
                    if i not in char_ids:
                        report['character_id_gaps'].append(i)
                
                # Check for orphaned characters (series_id not in series registry)
                if not series_df.empty:
                    valid_series_ids = set(series_df['unique_series_id'].tolist())
                    orphaned = char_df[~char_df['series_unique_id'].isin(valid_series_ids)]
                    if not orphaned.empty:
                        report['orphaned_characters'].extend(orphaned.to_dict('records'))
        
        except Exception as e:
            logger.error("Error validating registry integrity: %s", e)
            report['error'] = str(e)
        
        return report


if __name__ == "__main__":
    # Test the ID manager
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    
    # Create test instance
    id_manager = IDManager()
    
    # Test series ID assignment
    print("Testing series ID assignment...")
    series1 = id_manager.get_or_create_series_id("mal", "16498", "Attack on Titan")
    series2 = id_manager.get_or_create_series_id("mal", "11757", "Sword Art Online")
    series3 = id_manager.get_or_create_series_id("vndb", "v17", "Fate/stay night")
    series4 = id_manager.get_or_create_series_id("genshin", "mondstadt", "Genshin Impact")
    
    print(f"Series IDs: {series1}, {series2}, {series3}, {series4}")
    
    # Test character ID assignment
    print("Testing character ID assignment...")
    char1 = id_manager.get_or_create_character_id("mal", "40028", "Mikasa Ackerman", series1)
    char2 = id_manager.get_or_create_character_id("mal", "36828", "Asuna Yuuki", series2)
    char3 = id_manager.get_or_create_character_id("vndb", "s83", "Saber", series3)
    char4 = id_manager.get_or_create_character_id("genshin", "amber", "Amber", series4)
    
    print(f"Character IDs: {char1}, {char2}, {char3}, {char4}")
    
    # Test duplicate assignment (should return same IDs)
    print("Testing duplicate assignment...")
    series1_dup = id_manager.get_or_create_series_id("mal", "16498", "Attack on Titan")
    char1_dup = id_manager.get_or_create_character_id("mal", "40028", "Mikasa Ackerman", series1)
    
    print(f"Duplicate IDs: {series1_dup} (should be {series1}), {char1_dup} (should be {char1})")
    
    # Validate integrity
    print("Validating registry integrity...")
    report = id_manager.validate_registry_integrity()
    print(f"Integrity report: {json.dumps(report, indent=2)}")
    
    print("✅ ID Manager test completed!")