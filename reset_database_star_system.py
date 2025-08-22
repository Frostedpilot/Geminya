#!/usr/bin/env python3
"""
Complete database reset script for the NEW 3★ Star System.

This script will:
1. Purge all existing data
2. Re-run migration scripts for star system
3. Initialize shop with 3★ system items
4. Upload new character data (optional)
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.database import DatabaseService
from services.container import ServiceContainer
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


async def run_database_reset():
    """Complete database reset for new star system."""
    
    print("🌟 NEW STAR SYSTEM DATABASE RESET")
    print("=" * 60)
    print("This script will completely reset your database for the new 3★ system:")
    print("  📊 1. Purge all existing data")
    print("  🔧 2. Run star system migrations")
    print("  🏪 3. Initialize shop with 3★ system items")
    print("  📋 4. Optional: Upload new character data")
    print("=" * 60)
    
    # Ask for confirmation
    confirmation = input("Continue with database reset? Type 'YES': ")
    if confirmation != "YES":
        print("❌ Reset cancelled.")
        return False
    
    try:
        print("\n🔄 Starting database reset process...")
        
        # Step 1: Initialize database service
        print("\n📊 Step 1: Initializing database connection...")
        config = Config.create()
        config.set_mode("DEV")
        
        container = ServiceContainer(config)
        await container.initialize_all()
        
        db = container.database
        
        # Step 2: Purge existing data (but keep schema)
        print("\n🗑️ Step 2: Purging existing data...")
        await purge_data_only(db)
        
        # Step 3: Ensure star system schema is ready
        print("\n🔧 Step 3: Ensuring star system schema...")
        await ensure_star_system_schema(db)
        
        # Step 4: Initialize shop with new items
        print("\n🏪 Step 4: Initializing shop...")
        await initialize_shop_for_star_system(db)
        
        # Step 5: Optional character upload
        print("\n📋 Step 5: Character data upload (optional)")
        upload_chars = input("Upload character data from CSV? (y/n): ").lower() == 'y'
        if upload_chars:
            await upload_character_data()
        
        await container.cleanup_all()
        
        print("\n🎉 Database reset complete!")
        print("✅ Your database is now ready for the new 3★ star system!")
        print("🎮 You can now start the bot and test the new summon commands!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during database reset: {e}")
        print(f"\n❌ Reset failed: {e}")
        return False


async def purge_data_only(db):
    """Purge data while keeping schema intact."""
    # Tables in order for foreign key constraints
    tables_to_purge = [
        "user_inventory",
        "user_purchases", 
        "user_mission_progress",
        "conversations",
        "user_character_shards",  # NEW: Star system table
        "user_waifus",
        "shop_items",
        "daily_missions",
        "events", 
        "waifus",
        "users",
    ]
    
    total_deleted = 0
    
    async with db.connection_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for table in tables_to_purge:
                try:
                    # Count records
                    await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count_result = await cursor.fetchone()
                    record_count = count_result[0] if count_result else 0
                    
                    if record_count > 0:
                        await cursor.execute(f"DELETE FROM {table}")
                        logger.info(f"✅ Purged {record_count} records from {table}")
                        total_deleted += record_count
                    else:
                        logger.info(f"ℹ️ Table {table} was already empty")
                        
                except Exception as e:
                    if "doesn't exist" in str(e):
                        logger.info(f"ℹ️ Table {table} doesn't exist (will be created)")
                    else:
                        logger.error(f"❌ Error purging {table}: {e}")
            
            # Reset auto-increment counters
            for table in tables_to_purge:
                try:
                    await cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
                except:
                    pass  # Ignore errors for missing tables
            
            await conn.commit()
    
    print(f"✅ Purged {total_deleted} total records")


async def ensure_star_system_schema(db):
    """Ensure all star system schema changes are applied."""
    async with db.connection_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Check and add star_shards column to user_waifus
            try:
                await cursor.execute("""
                    SELECT COLUMN_NAME 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'user_waifus' 
                    AND COLUMN_NAME = 'star_shards'
                """)
                if not await cursor.fetchone():
                    await cursor.execute("ALTER TABLE user_waifus ADD COLUMN star_shards INT DEFAULT 0")
                    logger.info("✅ Added star_shards column to user_waifus")
                else:
                    logger.info("ℹ️ star_shards column already exists")
            except Exception as e:
                logger.error(f"Error adding star_shards column: {e}")
            
            # Check and add updated_at column to user_character_shards
            try:
                await cursor.execute("""
                    SELECT COLUMN_NAME 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'user_character_shards' 
                    AND COLUMN_NAME = 'updated_at'
                """)
                if not await cursor.fetchone():
                    await cursor.execute("ALTER TABLE user_character_shards ADD COLUMN updated_at DATETIME DEFAULT NULL")
                    logger.info("✅ Added updated_at column to user_character_shards")
                else:
                    logger.info("ℹ️ updated_at column already exists")
            except Exception as e:
                logger.error(f"Error adding updated_at column: {e}")
            
            await conn.commit()


async def initialize_shop_for_star_system(db):
    """Initialize shop with 3★ system items."""
    # Clear existing shop data
    async with db.connection_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM user_purchases")
            await cursor.execute("DELETE FROM user_inventory") 
            await cursor.execute("DELETE FROM shop_items")
            await conn.commit()
    
    # Add new star system items
    shop_items = [
        {
            "name": "3★ Guarantee Summon Ticket",
            "description": "Immediately summons a guaranteed 3★ waifu! Perfect for the new star system.",
            "item_type": "guarantee_ticket",
            "price": 100,
            "category": "summons",
            "item_data": {
                "currency_type": "quartzs",
                "rarity": "legendary",
                "effects": {"guarantee_rarity": 3, "uses": 1},
                "requirements": {}
            }
        }
    ]
    
    added_count = 0
    for item in shop_items:
        try:
            item_id = await db.add_shop_item(item)
            if item_id > 0:
                logger.info(f"✅ Added shop item: {item['name']}")
                added_count += 1
        except Exception as e:
            logger.error(f"❌ Failed to add {item['name']}: {e}")
    
    print(f"✅ Added {added_count} shop items")


async def upload_character_data():
    """Upload character data from processed CSV."""
    csv_path = Path("data/character_final.csv")
    if not csv_path.exists():
        print("❌ character_final.csv not found. Run process_character_final.py first.")
        return False
    
    print("🔄 Uploading character data...")
    # This would call upload_to_mysql.py functionality
    # For now, just inform the user
    print("ℹ️ Please run: python upload_to_mysql.py")
    return True


async def main():
    """Main function."""
    success = await run_database_reset()
    if success:
        print("\n🌟 Database is ready for the new 3★ star system!")
        print("🎮 Next steps:")
        print("  1. Run: python upload_to_mysql.py (if you haven't uploaded characters)")
        print("  2. Run: python start_geminya.py")
        print("  3. Test the new summon commands in Discord!")
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
