#!/usr/bin/env python3
"""Script to purge all data from the waifu database while keeping the schema intact."""

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


async def purge_database():
    """Purge all data from the database while keeping the schema."""
    
    print("🗑️  Database Purge Script")
    print("=" * 50)
    print("⚠️  WARNING: This will DELETE ALL DATA from the database!")
    print("   - All users will be removed")
    print("   - All waifus will be removed") 
    print("   - All user collections will be removed")
    print("   - All shop data will be removed")
    print("   - All user items will be removed")
    print("   - The database schema will remain intact")
    print("=" * 50)
    
    # Ask for confirmation
    confirmation = input("Type 'PURGE' to confirm deletion: ")
    if confirmation != "PURGE":
        print("❌ Purge cancelled. No changes made.")
        return
    
    # Double confirmation for safety
    final_confirmation = input("Are you absolutely sure? Type 'YES DELETE EVERYTHING': ")
    if final_confirmation != "YES DELETE EVERYTHING":
        print("❌ Purge cancelled. No changes made.")
        return
    
    print("\n🔄 Starting database purge...")
    
    db = None
    try:
        # Initialize database service
        config = Config.create()
        config.set_mode("DEV")  # Use DEV mode for database operations
        db = DatabaseService(config)
        await db.initialize()
        
        # Check if connection pool was created
        if not db.connection_pool:
            raise Exception("Failed to create database connection pool")
        
        # Get table names to purge (in correct order to handle foreign keys)
        tables_to_purge = [
            "user_inventory",           # User inventory items
            "user_purchases",           # Purchase history
            "user_mission_progress",    # Mission progress
            "conversations",            # User-waifu conversations
            "user_waifus",              # User collections (foreign keys to users and waifus)
            "shop_items",               # Shop items
            "daily_missions",           # Daily missions
            "events",                   # Events
            "waifus",                   # Waifu characters
            "users",                    # User accounts
        ]
        
        total_deleted = 0
        
        # Use the connection pool directly for raw SQL operations
        async with db.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for table in tables_to_purge:
                    try:
                        # Count records before deletion
                        await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count_result = await cursor.fetchone()
                        record_count = count_result[0] if count_result else 0
                        
                        if record_count > 0:
                            # Delete all records from table
                            await cursor.execute(f"DELETE FROM {table}")
                            logger.info(f"✅ Purged {record_count} records from {table}")
                            total_deleted += record_count
                        else:
                            logger.info(f"ℹ️  Table {table} was already empty")
                            
                    except Exception as e:
                        logger.error(f"❌ Error purging table {table}: {e}")
                        raise
                
                # Reset auto-increment counters (MySQL specific)
                for table in tables_to_purge:
                    try:
                        await cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
                        logger.debug(f"Reset auto-increment for {table}")
                    except Exception as e:
                        # This might fail for tables without auto-increment, which is fine
                        logger.debug(f"Could not reset auto-increment for {table}: {e}")
                
                # Commit all changes
                await conn.commit()
        
        print(f"\n✅ Database purge completed successfully!")
        print(f"📊 Total records deleted: {total_deleted}")
        print(f"🗃️  Database schema remains intact")
        print(f"🔄 You can now run populate_from_mal.py to add fresh data")
        
    except Exception as e:
        logger.error(f"❌ Error during database purge: {e}")
        print(f"\n❌ Purge failed: {e}")
        sys.exit(1)
        
    finally:
        # Clean up database connection
        if db:
            try:
                await db.close()
                logger.info("🔒 Database connection closed")
            except:
                pass


async def verify_purge():
    """Verify that the database is actually empty."""
    print("\n🔍 Verifying purge results...")
    
    db = None
    try:
        config = Config.create()
        config.set_mode("DEV")
        db = DatabaseService(config)
        await db.initialize()
        
        tables_to_check = [
            "users", "waifus", "user_waifus", 
            "shop_items", "user_inventory", "user_purchases",
            "conversations", "daily_missions", "events"
        ]
        
        all_empty = True
        
        if not db.connection_pool:
            raise Exception("Failed to create database connection pool")
        
        async with db.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for table in tables_to_check:
                    try:
                        await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count_result = await cursor.fetchone()
                        record_count = count_result[0] if count_result else 0
                        
                        if record_count == 0:
                            print(f"✅ {table}: Empty")
                        else:
                            print(f"⚠️  {table}: {record_count} records remaining")
                            all_empty = False
                            
                    except Exception as e:
                        print(f"❌ Error checking {table}: {e}")
                        all_empty = False
        
        if all_empty:
            print("\n✅ Verification complete: Database is clean!")
        else:
            print("\n⚠️  Verification failed: Some data may remain")
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        
    finally:
        if db:
            try:
                await db.close()
            except:
                pass


if __name__ == "__main__":
    try:
        # Run the purge
        asyncio.run(purge_database())
        
        # Ask if user wants verification
        verify_choice = input("\nRun verification check? (y/n): ").lower().strip()
        if verify_choice == 'y':
            asyncio.run(verify_purge())
            
    except KeyboardInterrupt:
        print("\n❌ Purge interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
