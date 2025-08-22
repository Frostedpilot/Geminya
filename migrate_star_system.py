"""
Migration script for the new star-based upgrade system.

This script migrates the database from the old system to the new
shard-based star upgrade system.

Changes:
1. Add current_star_level and character_shards columns to user_waifus
2. Create user_character_shards table for tracking shards per character
3. Migrate existing data to set current_star_level to base rarity
4. Update gacha rates and pity system in WaifuService
"""

import asyncio
import logging
from services.database import DatabaseService
from services.container import ServiceContainer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StarSystemMigration:
    """Handles migration to the new star-based system."""
    
    def __init__(self, database: DatabaseService):
        self.db = database
        
    async def run_migration(self):
        """Execute the complete migration process."""
        logger.info("🌟 Starting Star System Migration...")
        
        try:
            # Step 1: Add new columns to user_waifus table
            await self._add_user_waifus_columns()
            
            # Step 2: Create user_character_shards table
            await self._create_shards_table()
            
            # Step 3: Migrate existing data
            await self._migrate_existing_data()
            
            # Step 4: Verify migration
            await self._verify_migration()
            
            logger.info("✅ Star System Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise
    
    async def _add_user_waifus_columns(self):
        """Add new columns to user_waifus table."""
        logger.info("📊 Adding new columns to user_waifus table...")
        
        async with self.db.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # Add current_star_level column
                    await cursor.execute("""
                        ALTER TABLE user_waifus 
                        ADD COLUMN current_star_level INT DEFAULT NULL
                    """)
                    logger.info("✅ Added current_star_level column")
                except Exception as e:
                    if "Duplicate column name" in str(e):
                        logger.info("⚠️ current_star_level column already exists")
                    else:
                        raise
                
                try:
                    # Add character_shards column (deprecated, keeping for backwards compatibility)
                    await cursor.execute("""
                        ALTER TABLE user_waifus 
                        ADD COLUMN character_shards INT DEFAULT 0
                    """)
                    logger.info("✅ Added character_shards column")
                except Exception as e:
                    if "Duplicate column name" in str(e):
                        logger.info("⚠️ character_shards column already exists")
                    else:
                        raise
                
                await conn.commit()
    
    async def _create_shards_table(self):
        """Create the user_character_shards table."""
        logger.info("📊 Creating user_character_shards table...")
        
        async with self.db.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_character_shards (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        waifu_id INT NOT NULL,
                        shard_count INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (waifu_id) REFERENCES waifus(id) ON DELETE CASCADE,
                        UNIQUE KEY unique_user_waifu (user_id, waifu_id),
                        INDEX idx_user_shards (user_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                await conn.commit()
                logger.info("✅ Created user_character_shards table")
    
    async def _migrate_existing_data(self):
        """Migrate existing user_waifus data to set current_star_level."""
        logger.info("🔄 Migrating existing user_waifus data...")
        
        async with self.db.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Set current_star_level to base rarity for all existing entries
                await cursor.execute("""
                    UPDATE user_waifus uw 
                    SET current_star_level = (
                        SELECT w.rarity 
                        FROM waifus w 
                        WHERE w.id = uw.waifu_id
                    ) 
                    WHERE current_star_level IS NULL
                """)
                
                affected_rows = cursor.rowcount
                await conn.commit()
                logger.info(f"✅ Updated {affected_rows} user_waifus entries with current_star_level")
    
    async def _verify_migration(self):
        """Verify the migration was successful."""
        logger.info("🔍 Verifying migration...")
        
        async with self.db.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Check if all user_waifus have current_star_level set
                await cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM user_waifus 
                    WHERE current_star_level IS NULL
                """)
                result = await cursor.fetchone()
                null_count = result[0] if result else 0
                
                if null_count > 0:
                    logger.warning(f"⚠️ {null_count} user_waifus entries still have NULL current_star_level")
                else:
                    logger.info("✅ All user_waifus entries have current_star_level set")
                
                # Check user_character_shards table exists
                await cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'user_character_shards'
                """)
                result = await cursor.fetchone()
                table_exists = result[0] > 0 if result else False
                
                if table_exists:
                    logger.info("✅ user_character_shards table exists")
                else:
                    logger.error("❌ user_character_shards table not found")
                    raise Exception("Migration verification failed: missing table")


async def main():
    """Main migration function."""
    print("🌟 Star System Migration Script")
    print("=" * 50)
    
    # Initialize config and services
    from config import Config
    config = Config.create()
    config.set_mode("DEV")  # Set default mode
    
    container = ServiceContainer(config)
    await container.initialize_all()
    
    try:
        # Run migration
        migration = StarSystemMigration(container.database)
        await migration.run_migration()
        
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Update WaifuService with new gacha rates")
        print("2. Implement shard tracking methods")
        print("3. Update commands to show star levels")
        print("4. Test the new system thoroughly")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        logger.exception("Migration error details:")
        
    finally:
        await container.cleanup_all()


if __name__ == "__main__":
    asyncio.run(main())
