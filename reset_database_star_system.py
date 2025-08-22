#!/usr/bin/env python3
"""
Database reset script - purges all data and recreates schema.

This script will:
1. Purge all existing data
2. Recreate database schema
"""

import asyncio
import logging
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.database import DatabaseService
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


async def run_database_reset():
    """Complete database reset - purge and recreate schema."""
    
    print("🗑️ DATABASE RESET")
    print("=" * 40)
    print("This will completely purge all data and recreate the schema.")
    print("=" * 40)
    
    # Ask for confirmation
    confirmation = input("Continue with database reset? Type 'YES': ")
    if confirmation != "YES":
        print("❌ Reset cancelled.")
        return False
    
    try:
        print("\n🔄 Starting database reset...")
        
        # Initialize database service directly
        print("\n📊 Initializing database connection...")
        config = Config.create()
        config.set_mode("DEV")
        
        db = DatabaseService(config)
        await db.initialize()
        
        # Purge all data
        print("\n🗑️ Purging all database data...")
        await purge_all_data(db)
        
        await db.close()
        
        print("\n✅ Database reset complete!")
        print("🔧 Schema has been recreated and is ready for use.")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during database reset: {e}")
        print(f"\n❌ Reset failed: {e}")
        return False


async def purge_all_data(db):
    """Purge all data from the database."""
    # Get all table names
    async with db.connection_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Disable foreign key checks temporarily
            await cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            # Get all tables
            await cursor.execute("SHOW TABLES")
            tables = await cursor.fetchall()
            
            total_deleted = 0
            for (table_name,) in tables:
                try:
                    # Count records
                    await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = await cursor.fetchone()
                    record_count = count_result[0] if count_result else 0
                    
                    if record_count > 0:
                        await cursor.execute(f"DELETE FROM {table_name}")
                        logger.info(f"✅ Purged {record_count} records from {table_name}")
                        total_deleted += record_count
                    else:
                        logger.info(f"ℹ️ Table {table_name} was already empty")
                        
                except Exception as e:
                    logger.error(f"❌ Error purging {table_name}: {e}")
            
            # Re-enable foreign key checks
            await cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            await conn.commit()
    
    print(f"✅ Purged {total_deleted} total records")


async def main():
    """Main function."""
    success = await run_database_reset()
    if success:
        print("\n🔧 Database has been reset and schema recreated!")
        print("📝 Next steps:")
        print("  1. Upload data if needed")
        print("  2. Start your application")
    else:
        print("\n❌ Database reset failed!")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
