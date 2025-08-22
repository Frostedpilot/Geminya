#!/usr/bin/env python3
"""Orchestrator script to run the full MAL to MySQL pipeline."""

import asyncio
import subprocess
import sys
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class MALPipeline:
    """Pipeline orchestrator for MAL data processing."""

    def __init__(self):
        self.scripts = [
            ("pull_from_mal.py", "🎌 Pulling data from MAL..."),
            ("character_edit.py", "🔧 Processing character data..."),
            ("upload_to_mysql.py", "💾 Uploading to MySQL...")
        ]

    def run_script(self, script_name: str, description: str) -> bool:
        """Run a Python script and return success status."""
        try:
            logger.info(description)
            
            # Check if script exists
            if not os.path.exists(script_name):
                logger.error(f"Script {script_name} not found!")
                return False

            # Run the script
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )

            if result.returncode == 0:
                logger.info(f"✅ {script_name} completed successfully!")
                return True
            else:
                logger.error(f"❌ {script_name} failed!")
                logger.error(f"Error output: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Error running {script_name}: {e}")
            return False

    def run_pipeline(self, skip_to: str = None) -> bool:
        """Run the complete pipeline or skip to a specific script."""
        try:
            logger.info("🚀 Starting MAL to MySQL pipeline...")
            
            script_index = 0
            if skip_to:
                script_names = [script[0] for script in self.scripts]
                if skip_to in script_names:
                    script_index = script_names.index(skip_to)
                    logger.info(f"⏭️ Skipping to {skip_to}")
                else:
                    logger.error(f"Unknown script: {skip_to}")
                    return False

            # Run scripts starting from the specified index
            for i in range(script_index, len(self.scripts)):
                script_name, description = self.scripts[i]
                
                if not self.run_script(script_name, description):
                    logger.error(f"❌ Pipeline failed at {script_name}")
                    return False

            logger.info("🎉 Pipeline completed successfully!")
            return True

        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}")
            return False

    def show_status(self):
        """Show pipeline status and available scripts."""
        print("\n" + "="*60)
        print("🎌 MAL TO MYSQL PIPELINE")
        print("="*60)
        print("This pipeline consists of 3 steps:")
        print("")
        
        for i, (script, description) in enumerate(self.scripts, 1):
            status = "✅" if os.path.exists(script) else "❌"
            print(f"{i}. {status} {script}")
            print(f"   {description}")
            print("")
        
        print("Usage:")
        print("  python populate_from_mal.py           # Run full pipeline")
        print("  python populate_from_mal.py --skip-to script.py  # Skip to specific script")
        print("  python populate_from_mal.py --status  # Show this status")
        print("")
        print("Individual scripts:")
        print("  python pull_from_mal.py      # Pull data from MAL → CSV files")
        print("  python character_edit.py     # Edit characters → character_sql.csv")
        print("  python upload_to_mysql.py    # Upload CSV → MySQL database")
        print("="*60)


def main():
    """Main function."""
    pipeline = MALPipeline()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            pipeline.show_status()
            return True
        elif sys.argv[1] == "--skip-to" and len(sys.argv) > 2:
            return pipeline.run_pipeline(skip_to=sys.argv[2])
        elif sys.argv[1] == "--help":
            pipeline.show_status()
            return True
        else:
            logger.error("Invalid arguments. Use --help for usage information.")
            return False
    
    # Run full pipeline
    return pipeline.run_pipeline()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
