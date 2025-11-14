#!/usr/bin/env python3
"""Multi-Media Collection and Processing Orchestrator.

This is the main script that replaces the old multi-step workflow:
OLD: pull_from_mal.py → character_edit.py → manual editing → process_character_final.py
NEW: collect_and_process_media.py → manual editing → process_character_final.py

This orchestrator manages all media processors (anime, visual novel, games, etc.)
and coordinates the unified data collection workflow.
"""

import asyncio
import os
import sys
import logging
from typing import List, Dict, Optional, Any, Type
from pathlib import Path
import importlib
import traceback

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import processors
from data.processors.base_processor import BaseProcessor
from data.processors.anime_processor import AnimeProcessor
from data.processors.manga_processor import MangaProcessor
from data.processors.vndb_processor import VNDBProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/media_collection.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class MediaCollectionOrchestrator:
    """Main orchestrator for multi-media data collection and processing.
    
    This class manages all processors and coordinates the unified workflow:
    1. Discover and initialize available processors
    2. Run each configured processor to pull raw data
    3. Process and standardize all data with unified ID assignment
    4. Output standardized intermediate files for manual editing
    5. Provide statistics and reporting
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the orchestrator.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.processors: Dict[str, BaseProcessor] = {}
        self.results: Dict[str, Dict] = {}
        
        # Create output directories
        os.makedirs('data/intermediate', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        logger.info("MediaCollectionOrchestrator initialized")

    def _discover_processors(self) -> List[Type[BaseProcessor]]:
        """Discover all available processor classes.
        
        Returns:
            List of processor classes found in data/processors/
        """
        processor_classes = []
        
        # Manually registered processors (for now)
        available_processors = [
            # AnimeProcessor,
            # MangaProcessor,
            # VNDBProcessor,
            # GameProcessor,         # Future
        ]
        
        for processor_class in available_processors:
            try:
                # Test if processor can be imported and initialized
                test_processor = processor_class()
                processor_classes.append(processor_class)
                logger.debug("Discovered processor: %s", processor_class.__name__)
            except Exception as e:
                logger.warning("Failed to load processor %s: %s", processor_class.__name__, e)
                
        logger.info("Discovered %d processor classes", len(processor_classes))
        return processor_classes

    def _initialize_processors(self) -> Dict[str, BaseProcessor]:
        """Initialize all available and configured processors.
        
        Returns:
            Dictionary of source_type -> processor instance
        """
        processors = {}
        processor_classes = self._discover_processors()
        
        for processor_class in processor_classes:
            try:
                # Create processor instance based on processor type
                if processor_class.__name__ == 'VNDBProcessor':
                    # VNDB processor uses config file initialization
                    processor = VNDBProcessor.from_config_file()
                else:
                    # Other processors use app config
                    processor = processor_class(self.config.get(processor_class.__name__.lower(), {}))
                
                source_type = processor.get_source_type()
                
                # Check if processor is configured
                if processor.is_configured():
                    processors[source_type] = processor
                    logger.info("✅ Initialized processor: %s (%s)", processor_class.__name__, source_type)
                else:
                    logger.warning("⚠️  Processor %s not configured - skipping", processor_class.__name__)
                    
            except Exception as e:
                logger.error("❌ Failed to initialize processor %s: %s", processor_class.__name__, e)
                logger.debug("Processor initialization error:", exc_info=True)
                
        logger.info("Initialized %d processors: %s", len(processors), list(processors.keys()))
        return processors

    async def _run_processor(self, source_type: str, processor: BaseProcessor) -> Dict[str, Any]:
        """Run a single processor to collect and process data.
        
        Args:
            source_type: The source type identifier
            processor: The processor instance to run
            
        Returns:
            Dictionary with processing results and statistics
        """
        result = {
            'source_type': source_type,
            'success': False,
            'raw_series': [],
            'raw_characters': [],
            'processed_series': [],
            'processed_characters': [],
            'stats': {},
            'errors': []
        }
        
        # Initialize processor (create sessions, etc.)
        try:
            await processor.__aenter__()
        except Exception as init_error:
            logger.error("Failed to initialize processor %s: %s", source_type, init_error)
            result['errors'].append(f"Initialization failed: {init_error}")
            return result
        
        try:
            logger.info("🚀 Starting processor: %s", source_type)
            
            # Step 1: Pull raw data
            logger.info("📥 Pulling raw data from %s...", source_type)
            raw_series, raw_characters = await processor.pull_raw_data()
            
            result['raw_series'] = raw_series
            result['raw_characters'] = raw_characters
            
            logger.info("📊 Raw data collected: %d series, %d characters", 
                       len(raw_series), len(raw_characters))
            
            # Step 2: Process series data
            if raw_series:
                logger.info("⚙️  Processing %d series...", len(raw_series))
                processed_series = processor.process_series(raw_series)
                result['processed_series'] = processed_series
                logger.info("✅ Processed %d series", len(processed_series))
            
            # Step 3: Process character data  
            if raw_characters:
                logger.info("⚙️  Processing %d characters...", len(raw_characters))
                processed_characters = processor.process_characters(raw_characters)
                result['processed_characters'] = processed_characters
                logger.info("✅ Processed %d characters", len(processed_characters))
            
            # Step 4: Get processing statistics
            result['stats'] = processor.get_processing_stats()
            result['success'] = True
            
            logger.info("🎉 Processor %s completed successfully!", source_type)
            
        except Exception as e:
            error_msg = f"Error in processor {source_type}: {e}"
            result['errors'].append(error_msg)
            logger.error("❌ %s", error_msg)
            logger.debug("Processor error details:", exc_info=True)
        
        finally:
            # Ensure proper cleanup of processor resources (close sessions, etc.)
            try:
                await processor.__aexit__(None, None, None)
            except Exception as cleanup_error:
                logger.warning("Error during processor cleanup: %s", cleanup_error)
            
        return result

    def _combine_all_data(self) -> tuple[List[Dict], List[Dict]]:
        """Combine processed data from all processors.
        
        Returns:
            Tuple of (combined_series, combined_characters)
        """
        combined_series = []
        combined_characters = []
        
        for source_type, result in self.results.items():
            if result['success']:
                combined_series.extend(result['processed_series'])
                combined_characters.extend(result['processed_characters'])
                logger.info("Combined data from %s: %d series, %d characters", 
                           source_type, len(result['processed_series']), len(result['processed_characters']))
        
        logger.info("📊 Total combined: %d series, %d characters", 
                   len(combined_series), len(combined_characters))
        return combined_series, combined_characters

    def _save_intermediate_files(self, series: List[Dict], characters: List[Dict]) -> bool:
        """Save processed data to intermediate CSV files (append mode using pandas).
        
        Args:
            series: List of processed series dictionaries
            characters: List of processed character dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import pandas as pd
            
            # Save series to intermediate/series_processed.csv (append mode)
            if series:
                series_file = os.path.join('data', 'intermediate', 'series_processed.csv')
                new_series_df = pd.DataFrame(series)
                
                if os.path.exists(series_file):
                    # File exists - append new data
                    existing_df = pd.read_csv(series_file)
                    combined_df = pd.concat([existing_df, new_series_df], ignore_index=True)
                    combined_df.to_csv(series_file, index=False, encoding='utf-8')
                    logger.info("💾 Appended %d series to %s (total: %d)", 
                               len(series), series_file, len(combined_df))
                else:
                    # File doesn't exist - create new
                    new_series_df.to_csv(series_file, index=False, encoding='utf-8')
                    logger.info("💾 Created %s with %d series", series_file, len(series))
            
            # Save characters to intermediate/characters_processed.csv (append mode)
            if characters:
                characters_file = os.path.join('data', 'intermediate', 'characters_processed.csv')
                new_characters_df = pd.DataFrame(characters)
                
                if os.path.exists(characters_file):
                    # File exists - append new data
                    existing_df = pd.read_csv(characters_file)
                    combined_df = pd.concat([existing_df, new_characters_df], ignore_index=True)
                    combined_df.to_csv(characters_file, index=False, encoding='utf-8')
                    logger.info("💾 Appended %d characters to %s (total: %d)", 
                               len(characters), characters_file, len(combined_df))
                else:
                    # File doesn't exist - create new
                    new_characters_df.to_csv(characters_file, index=False, encoding='utf-8')
                    logger.info("💾 Created %s with %d characters", characters_file, len(characters))
            
            return True
            
        except Exception as e:
            logger.error("❌ Error saving intermediate files: %s", e)
            return False

    def _generate_report(self) -> Dict[str, Any]:
        """Generate processing report and statistics.
        
        Returns:
            Dictionary with comprehensive processing report
        """
        report = {
            'timestamp': logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None)),
            'processors_run': len(self.results),
            'successful_processors': len([r for r in self.results.values() if r['success']]),
            'failed_processors': len([r for r in self.results.values() if not r['success']]),
            'total_series': sum(len(r['processed_series']) for r in self.results.values()),
            'total_characters': sum(len(r['processed_characters']) for r in self.results.values()),
            'by_source': {},
            'errors': []
        }
        
        # Per-source breakdown
        for source_type, result in self.results.items():
            report['by_source'][source_type] = {
                'success': result['success'],
                'raw_series': len(result['raw_series']),
                'raw_characters': len(result['raw_characters']),
                'processed_series': len(result['processed_series']),
                'processed_characters': len(result['processed_characters']),
                'stats': result['stats'],
                'errors': result['errors']
            }
            report['errors'].extend(result['errors'])
        
        return report

    def _print_summary(self, report: Dict[str, Any]):
        """Print processing summary to console.
        
        Args:
            report: Processing report dictionary
        """
        print("\n" + "="*80)
        print("MULTI-MEDIA COLLECTION & PROCESSING SUMMARY")
        print("="*80)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Processors Run: {report['processors_run']}")
        print(f"  ✅ Successful: {report['successful_processors']}")
        print(f"  ❌ Failed: {report['failed_processors']}")
        print()
        print("📊 TOTAL DATA COLLECTED:")
        print(f"  Series: {report['total_series']}")
        print(f"  Characters: {report['total_characters']}")
        print()
        
        if report['by_source']:
            print("📋 BY SOURCE:")
            for source_type, source_data in report['by_source'].items():
                status = "✅" if source_data['success'] else "❌"
                print(f"  {status} {source_type.upper()}:")
                print(f"    Raw: {source_data['raw_series']} series, {source_data['raw_characters']} characters")
                print(f"    Processed: {source_data['processed_series']} series, {source_data['processed_characters']} characters")
                if source_data['errors']:
                    print(f"    Errors: {len(source_data['errors'])}")
        print()
        
        if report['errors']:
            print("⚠️  ERRORS ENCOUNTERED:")
            for error in report['errors'][:5]:  # Show first 5 errors
                print(f"  • {error}")
            if len(report['errors']) > 5:
                print(f"  ... and {len(report['errors']) - 5} more errors")
        else:
            print("🎉 NO ERRORS!")
        
        print()
        print("📁 OUTPUT FILES:")
        print("  • data/intermediate/series_processed.csv (NEW data appended to existing)")
        print("  • data/intermediate/characters_processed.csv (NEW data appended to existing)")  
        print("  • logs/media_collection.log")
        print("")
        print("🔍 ID TRACKING:")
        print("  • data/registries/anime/existing_anime_ids.json (automatically updated)")
        print("  • data/registries/anime/existing_character_ids.json (automatically updated)")
        print()
        print("🔄 NEXT STEPS:")
        print("  1. Review intermediate files - NEW data has been appended:")
        print("     • data/intermediate/series_processed.csv (contains new scraped series)")
        print("     • data/intermediate/characters_processed.csv (contains new scraped characters)")
        print("  2. Copy to final/ and convert to Excel for editing:")
        print("     • data/intermediate/series_processed.csv → data/final/series_cleaned.xlsx")
        print("     • data/intermediate/characters_processed.csv → data/final/characters_cleaned.xlsx")
        print("  3. Manually edit new data (filter, clean, assign ratings)")
        print("  4. Run LLM processing for character stats (optional)")
        print("  5. Run process_character_final.py (processes your edited data)")
        print("  6. Run upload_to_postgres.py")
        print("")
        print("📝 Note: Only NEW data is added to files. Lookup files prevent re-scraping.")
        print("="*80)

    async def collect_and_process_all(self) -> bool:
        """Main workflow: collect and process data from all configured sources.
        
        Returns:
            True if successful, False if any critical errors occurred
        """
        try:
            logger.info("🎌 Starting Multi-Media Collection & Processing...")
            
            # Step 1: Initialize processors
            logger.info("🔧 Initializing processors...")
            self.processors = self._initialize_processors()
            
            if not self.processors:
                logger.error("❌ No processors configured! Please check your configuration.")
                return False
            
            # Step 2: Run all processors
            logger.info("🚀 Running %d processors...", len(self.processors))
            tasks = []
            
            for source_type, processor in self.processors.items():
                task = self._run_processor(source_type, processor)
                tasks.append(task)
            
            # Run processors concurrently (but MAL processor should run alone due to rate limits)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, (source_type, processor) in enumerate(self.processors.items()):
                result = results[i]
                if isinstance(result, Exception):
                    logger.error("❌ Processor %s failed with exception: %s", source_type, result)
                    self.results[source_type] = {
                        'source_type': source_type,
                        'success': False,
                        'raw_series': [],
                        'raw_characters': [],
                        'processed_series': [],
                        'processed_characters': [],
                        'stats': {},
                        'errors': [str(result)]
                    }
                else:
                    self.results[source_type] = result
            
            # Step 3: Combine all data
            logger.info("🔗 Combining data from all sources...")
            combined_series, combined_characters = self._combine_all_data()
            
            # Step 4: Save intermediate files
            logger.info("💾 Saving intermediate files...")
            save_success = self._save_intermediate_files(combined_series, combined_characters)
            
            # Step 5: Generate and display report
            report = self._generate_report()
            self._print_summary(report)
            
            # Determine overall success
            success = (
                report['successful_processors'] > 0 and
                save_success and
                (combined_series or combined_characters)
            )
            
            if success:
                logger.info("🎉 Multi-Media Collection & Processing completed successfully!")
            else:
                logger.error("❌ Multi-Media Collection & Processing failed!")
            
            return success
            
        except Exception as e:
            logger.error("❌ Fatal error in collection workflow: %s", e)
            logger.debug("Fatal error details:", exc_info=True)
            return False


# ===== COMMAND LINE INTERFACE =====

async def main():
    """Main entry point for the media collection orchestrator."""
    try:
        # Create and run orchestrator
        orchestrator = MediaCollectionOrchestrator()
        success = await orchestrator.collect_and_process_all()
        
        return success
        
    except KeyboardInterrupt:
        logger.info("⏹️  Collection interrupted by user")
        return False
    except Exception as e:
        logger.error("❌ Fatal error: %s", e)
        logger.debug("Fatal error details:", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)