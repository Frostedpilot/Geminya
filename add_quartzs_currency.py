#!/usr/bin/env python3
"""
Migration script to add quartzs currency column to users table.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from services.database import DatabaseService


async def add_quartzs_column():
    """Add quartzs column to users table if it doesn't exist."""
    print("🔄 Adding quartzs currency column to database...")
    
    config = Config.from_file()
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        if db.db_type == "mysql":
            async with db.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Check if column exists
                    await cursor.execute("""
                        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_NAME = 'users' 
                        AND COLUMN_NAME = 'quartzs'
                        AND TABLE_SCHEMA = DATABASE()
                    """)
                    result = await cursor.fetchone()
                    
                    if result[0] == 0:
                        print("➕ Adding quartzs column to users table...")
                        await cursor.execute("""
                            ALTER TABLE users 
                            ADD COLUMN quartzs INT DEFAULT 0 AFTER sakura_crystals
                        """)
                        await conn.commit()
                        print("✅ Quartzs column added successfully!")
                    else:
                        print("ℹ️ Quartzs column already exists")
        else:
            # SQLite - check if column exists and add if needed
            import aiosqlite
            async with aiosqlite.connect(db.db_path) as conn:
                cursor = await conn.execute("PRAGMA table_info(users)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if 'quartzs' not in column_names:
                    print("➕ Adding quartzs column to users table...")
                    await conn.execute("ALTER TABLE users ADD COLUMN quartzs INTEGER DEFAULT 0")
                    await conn.commit()
                    print("✅ Quartzs column added successfully!")
                else:
                    print("ℹ️ Quartzs column already exists")
        
        print("\n🎉 Database migration completed!")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False
    finally:
        if hasattr(db, 'connection_pool') and db.connection_pool:
            db.connection_pool.close()
            await db.connection_pool.wait_closed()
    
    return True


async def main():
    """Main function."""
    print("=" * 70)
    print("🗃️ DATABASE MIGRATION: QUARTZS CURRENCY")
    print("=" * 70)
    
    success = await add_quartzs_column()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("📝 QUARTZS CURRENCY SYSTEM:")
        print("  • Duplicate waifus at max constellation (6) convert to quartzs")
        print("  • Conversion rates: 1★=1, 2★=2, 3★=5, 4★=15, 5★=50 quartzs")
        print("  • Shop items can now use quartzs as currency")
        print("  • Users start with 0 quartzs (earned through gameplay)")
        print("=" * 70)
    else:
        print("\n❌ Migration failed!")


if __name__ == "__main__":
    asyncio.run(main())
