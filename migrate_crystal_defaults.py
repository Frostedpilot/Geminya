#!/usr/bin/env python3
"""
Migration script to update existing users table default crystal value from 100 to 2000.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from services.database import DatabaseService


async def migrate_crystal_defaults():
    """Migrate the existing database to use 2000 as the default crystal value."""
    print("🔧 Migrating database to use 2000 default crystals...")
    
    # Load config
    config = Config.from_file()
    
    # Initialize database service
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        if db.db_type == "mysql":
            print("📊 Updating MySQL table schema...")
            async with db.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Change the default value for sakura_crystals column
                    await cursor.execute(
                        "ALTER TABLE users ALTER COLUMN sakura_crystals SET DEFAULT 2000"
                    )
                    await conn.commit()
                    print("✅ MySQL schema updated successfully!")
        else:
            print("📊 SQLite doesn't support ALTER COLUMN DEFAULT, but new users will use updated schema.")
            print("✅ SQLite will use new defaults for new users!")
            
        print("🎯 Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False
    finally:
        # Close database connections
        if hasattr(db, 'connection_pool') and db.connection_pool:
            db.connection_pool.close()
            await db.connection_pool.wait_closed()


async def main():
    """Main migration function."""
    print("=" * 60)
    print("🔧 DATABASE MIGRATION: CRYSTAL DEFAULTS")
    print("=" * 60)
    
    success = await migrate_crystal_defaults()
    
    print("=" * 60)
    if success:
        print("🎉 MIGRATION COMPLETED!")
        print("💡 New users will now start with 2000 crystals")
        sys.exit(0)
    else:
        print("💥 MIGRATION FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
