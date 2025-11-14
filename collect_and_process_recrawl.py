#!/usr/bin/env python3
"""Recrawl Media Collection and Processing Orchestrator.

This script handles processors that always re-crawl and override existing data.
Unlike the append-only script, this removes existing data for the source type
and replaces it with fresh data from the processor.

Usage for processors that need fresh data every run (e.g., games, wikis).
"""

import asyncio
import os
import sys
import logging
import pandas as pd
from typing import List, Dict, Optional, Any, Type
from pathlib import Path
import importlib
import traceback

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import processors that use recrawl behavior
from data.processors.base_processor import BaseProcessor
from data.processors.ss_processor import SSProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/media_recrawl.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class RecrawlMediaOrchestrator:
    """Orchestrator for recrawl-based media data collection and processing.
    
    This orchestrator handles processors that always fetch fresh data and
    replace existing data for their source type in the intermediate files.
    """

    def __init__(self):
        """Initialize the recrawl orchestrator."""
        self.series_file = Path("data/intermediate/series_recrawl.csv")
        self.characters_file = Path("data/intermediate/characters_recrawl.csv")
        
        # Ensure output directories exist
        self.series_file.parent.mkdir(parents=True, exist_ok=True)
        self.characters_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("RecrawlMediaOrchestrator initialized")

    def _remove_source_data_from_files(self, source_type: str) -> tuple[int, int]:
        """Remove existing data for a source type from intermediate files.
        
        Args:
            source_type: Source type to remove (e.g., 'ss')
            
        Returns:
            Tuple of (series_removed_count, characters_removed_count)
        """
        series_removed = 0
        characters_removed = 0
        
        # Remove from series file
        if self.series_file.exists():
            try:
                df_series = pd.read_csv(self.series_file)
                original_count = len(df_series)
                df_filtered = df_series[df_series['source_type'] != source_type]
                series_removed = original_count - len(df_filtered)
                df_filtered.to_csv(self.series_file, index=False)
                logger.info(f"Removed {series_removed} existing {source_type} series from file")
            except Exception as e:
                logger.error(f"Error removing {source_type} series data: {e}")
        
        # Remove from characters file  
        if self.characters_file.exists():
            try:
                df_characters = pd.read_csv(self.characters_file)
                original_count = len(df_characters)
                df_filtered = df_characters[df_characters['source_type'] != source_type]
                characters_removed = original_count - len(df_filtered)
                df_filtered.to_csv(self.characters_file, index=False)
                logger.info(f"Removed {characters_removed} existing {source_type} characters from file")
            except Exception as e:
                logger.error(f"Error removing {source_type} character data: {e}")
        
        return series_removed, characters_removed

    def _add_source_data_to_files(self, source_type: str, series_data: List[Dict], 
                                 character_data: List[Dict]) -> None:
        """Add new data for a source type to intermediate files.
        
        Args:
            source_type: Source type being added
            series_data: List of processed series data
            character_data: List of processed character data
        """
        # Add series data
        if series_data:
            try:
                df_new_series = pd.DataFrame(series_data)
                
                if self.series_file.exists():
                    df_existing = pd.read_csv(self.series_file)
                    df_combined = pd.concat([df_existing, df_new_series], ignore_index=True)
                else:
                    df_combined = df_new_series
                
                df_combined.to_csv(self.series_file, index=False)
                
                # Get total count for logging
                total_series = len(df_combined)
                logger.info(f"💾 Added {len(series_data)} {source_type} series to file (total: {total_series})")
            except Exception as e:
                logger.error(f"Error adding {source_type} series data: {e}")
        
        # Add character data
        if character_data:
            try:
                df_new_chars = pd.DataFrame(character_data)
                
                if self.characters_file.exists():
                    df_existing = pd.read_csv(self.characters_file)
                    df_combined = pd.concat([df_existing, df_new_chars], ignore_index=True)
                else:
                    df_combined = df_new_chars
                
                df_combined.to_csv(self.characters_file, index=False)
                
                # Get total count for logging
                total_chars = len(df_combined)
                logger.info(f"💾 Added {len(character_data)} {source_type} characters to file (total: {total_chars})")
            except Exception as e:
                logger.error(f"Error adding {source_type} character data: {e}")

    async def _run_processor(self, processor: BaseProcessor) -> Dict[str, Any]:
        """Run a single processor and update intermediate files.
        
        Args:
            processor: Processor instance to run
            
        Returns:
            Dictionary with processing results and statistics
        """
        source_type = processor.get_source_type()
        
        try:
            logger.info(f"🚀 Starting processor: {source_type}")
            
            # Step 1: Remove existing data for this source
            series_removed, chars_removed = self._remove_source_data_from_files(source_type)
            
            # Step 2: Pull raw data
            logger.info(f"📥 Pulling raw data from {source_type}...")
            async with processor:  # Use async context manager
                raw_series, raw_characters = await processor.pull_raw_data()
            
            logger.info(f"📊 Raw data collected: {len(raw_series)} series, {len(raw_characters)} characters")
            
            # Step 3: Process series
            logger.info(f"⚙️  Processing {len(raw_series)} series...")
            processed_series = processor.process_series(raw_series)
            logger.info(f"✅ Processed {len(processed_series)} series")
            
            # Step 4: Process characters  
            logger.info(f"⚙️  Processing {len(raw_characters)} characters...")
            processed_characters = processor.process_characters(raw_characters)
            logger.info(f"✅ Processed {len(processed_characters)} characters")
            
            # Step 5: Add new data to files
            logger.info(f"💾 Saving data to intermediate files...")
            self._add_source_data_to_files(source_type, processed_series, processed_characters)
            
            logger.info(f"🎉 Processor {source_type} completed successfully!")
            
            return {
                'source_type': source_type,
                'status': 'success',
                'raw_series': len(raw_series),
                'raw_characters': len(raw_characters),
                'processed_series': len(processed_series),
                'processed_characters': len(processed_characters),
                'series_removed': series_removed,
                'characters_removed': chars_removed,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"❌ Error in processor {source_type}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                'source_type': source_type,
                'status': 'failed',
                'raw_series': 0,
                'raw_characters': 0,
                'processed_series': 0,
                'processed_characters': 0,
                'series_removed': series_removed if 'series_removed' in locals() else 0,
                'characters_removed': chars_removed if 'chars_removed' in locals() else 0,
                'error': str(e)
            }

    async def run_all_processors(self) -> Dict[str, Any]:
        """Run all configured recrawl processors.
        
        Returns:
            Dictionary with overall processing results
        """
        logger.info("🎌 Starting Recrawl Media Collection & Processing...")
        
        # Initialize processors - add new recrawl processors here
        processors = [
            SSProcessor()
        ]
        
        logger.info(f"🔧 Initialized {len(processors)} recrawl processors")
        
        results = []
        total_series = 0
        total_characters = 0
        
        # Run each processor
        for processor in processors:
            result = await self._run_processor(processor)
            results.append(result)
            
            if result['status'] == 'success':
                total_series += result['processed_series']
                total_characters += result['processed_characters']
        
        # Calculate summary statistics
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']
        
        return {
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_processors': len(processors),
            'successful_processors': len(successful),
            'failed_processors': len(failed),
            'total_series': total_series,
            'total_characters': total_characters,
            'results': results,
            'series_file': str(self.series_file),
            'characters_file': str(self.characters_file)
        }

    def print_summary(self, summary: Dict[str, Any]) -> None:
        """Print a formatted summary of the processing results."""
        print("\n" + "=" * 80)
        print("RECRAWL MEDIA COLLECTION & PROCESSING SUMMARY")
        print("=" * 80)
        print(f"Timestamp: {summary['timestamp']}")
        print(f"Processors Run: {summary['total_processors']}")
        print(f"  ✅ Successful: {summary['successful_processors']}")
        print(f"  ❌ Failed: {summary['failed_processors']}")
        print()
        print(f"📊 TOTAL DATA REPLACED:")
        print(f"  Series: {summary['total_series']}")
        print(f"  Characters: {summary['total_characters']}")
        print()
        print(f"📋 BY SOURCE:")
        
        for result in summary['results']:
            status_icon = "✅" if result['status'] == 'success' else "❌"
            source = result['source_type'].upper()
            
            if result['status'] == 'success':
                print(f"  {status_icon} {source}:")
                print(f"    Raw: {result['raw_series']} series, {result['raw_characters']} characters")
                print(f"    Processed: {result['processed_series']} series, {result['processed_characters']} characters")
                print(f"    Replaced: {result['series_removed']} series, {result['characters_removed']} characters")
            else:
                print(f"  {status_icon} {source}: FAILED - {result['error']}")
        
        print()
        if summary['failed_processors'] == 0:
            print("🎉 NO ERRORS!")
        else:
            print("⚠️  SOME PROCESSORS FAILED - Check logs for details")
        
        print()
        print(f"📁 OUTPUT FILES:")
        print(f"  • {summary['series_file']} (RECRAWL processors only)")
        print(f"  • {summary['characters_file']} (RECRAWL processors only)")
        print(f"  • logs/media_recrawl.log")
        print()
        print(f"🔄 NEXT STEPS:")
        print(f"  1. Review recrawl files - fresh data from recrawl processors:")
        print(f"     • {summary['series_file']}")
        print(f"     • {summary['characters_file']}")
        print(f"  2. Copy to final/ and convert to Excel for editing:")
        print(f"     • {summary['series_file']} → data/final/series_recrawl.xlsx")
        print(f"     • {summary['characters_file']} → data/final/characters_recrawl.xlsx")
        print(f"  3. Manually edit recrawl data (filter, clean, assign ratings)")
        print(f"  4. Merge with append-only data if needed")
        print(f"  5. Run LLM processing for character stats (optional)")
        print(f"  6. Run process_character_final.py (processes your edited data)")
        print(f"  7. Run upload_to_postgres.py")
        print()
        print(f"📝 Note: Recrawl data is in separate files from append-only processors.")
        print("=" * 80)


async def main():
    """Main entry point for recrawl media collection."""
    try:
        orchestrator = RecrawlMediaOrchestrator()
        summary = await orchestrator.run_all_processors()
        orchestrator.print_summary(summary)
        
        if summary['failed_processors'] > 0:
            logger.error(f"🎉 Recrawl Media Collection completed with {summary['failed_processors']} failures")
            return 1
        else:
            logger.info("🎉 Recrawl Media Collection completed successfully!")
            return 0
            
    except Exception as e:
        logger.error(f"❌ Fatal error in recrawl media collection: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))