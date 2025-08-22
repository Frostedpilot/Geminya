#!/usr/bin/env python3
"""Script to reset all user data but preserve accounts with 2000 sakura crystals."""

import asyncio
import aiosqlite
import aiomysql
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime


def load_config():
    """Load configuration from files without circular imports."""
    # Load secrets
    secrets_path = Path("secrets.json")
    if not secrets_path.exists():
        raise FileNotFoundError("secrets.json not found")
        
    with open(secrets_path, "r", encoding="utf-8") as f:
        secrets = json.load(f)
    
    # Load config.yml if available
    config_data = {}
    config_path = Path("config.yml")
    if config_path.exists():
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
        except ImportError:
            pass  # yaml not available
    
    # Get database configuration
    database_config = config_data.get("database", {})
    database_type = database_config.get("type", "sqlite")
    sqlite_config = database_config.get("sqlite", {})
    sqlite_path = sqlite_config.get("path", "data/waifu_academy.db")
    
    # MySQL configuration
    mysql_config = {
        "host": secrets.get("MYSQL_HOST"),
        "port": secrets.get("MYSQL_PORT", 3306),
        "user": secrets.get("MYSQL_USER"),
        "password": secrets.get("MYSQL_PASSWORD"),
        "database": secrets.get("MYSQL_DATABASE"),
        "charset": "utf8mb4",
    }
    
    return database_type, sqlite_path, mysql_config


async def reset_users_to_base(dry_run=False):
    """Reset all users to base state with 2000 sakura crystals."""
    try:
        # Load configuration
        db_type, sqlite_path, mysql_config = load_config()
        
        if dry_run:
            print(f"🔍 DRY RUN: Simulating reset of {db_type.upper()} database...")
        else:
            print(f"🔄 Resetting all users in {db_type.upper()} database to 2000 crystals...")

        if db_type == "sqlite":
            return await reset_sqlite_users(sqlite_path, dry_run)
        elif db_type == "mysql":
            return await reset_mysql_users(mysql_config, dry_run)
        else:
            print(f"❌ Unknown database type: {db_type}")
            return False

    except Exception as e:
        print(f"❌ Error resetting users: {e}")
        return False


async def reset_sqlite_users(db_path, dry_run=False):
    """Reset all users in SQLite database."""
    if not os.path.exists(db_path):
        print(f"❌ Database file doesn't exist: {db_path}")
        return False

    try:
        async with aiosqlite.connect(db_path) as db:
            # Count existing users
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            result = await cursor.fetchone()
            user_count = result[0] if result else 0
            
            if user_count == 0:
                print("ℹ️ No users found in database")
                return True
                
            print(f"📊 Found {user_count} users in database")
            
            if dry_run:
                # Show what would be reset
                cursor = await db.execute("""
                    SELECT discord_id, academy_name, sakura_crystals, collector_rank, 
                           pity_counter, last_daily_reset
                    FROM users 
                    ORDER BY discord_id
                    LIMIT 10
                """)
                users_list = await cursor.fetchall()
                
                print("\n🔍 Users that would be reset:")
                print("=" * 80)
                for i, user in enumerate(users_list):
                    if i >= 10:  # Safety check
                        break
                    discord_id, academy_name, crystals, rank, pity, last_daily = user
                    print(f"Discord ID: {discord_id}")
                    print(f"  Academy: {academy_name or 'None'}")
                    print(f"  Crystals: {crystals} → 2000")
                    print(f"  Rank: {rank} → 1")
                    print(f"  Pity: {pity} → 0")
                    print(f"  Last Daily: {last_daily} → 0")
                    print(f"  Login Streak: 0 → 0")
                    print("-" * 40)
                
                if user_count > 10:
                    print(f"... and {user_count - 10} more users")
                
                # Count related data that would be deleted
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM user_waifus uw 
                    JOIN users u ON uw.user_id = u.id
                """)
                result = await cursor.fetchone()
                waifu_count = result[0] if result else 0
                
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM conversations c 
                    JOIN users u ON c.user_id = u.id
                """)
                result = await cursor.fetchone()
                conversation_count = result[0] if result else 0
                
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM user_mission_progress ump 
                    JOIN users u ON ump.user_id = u.id
                """)
                result = await cursor.fetchone()
                mission_count = result[0] if result else 0
                
                print(f"\n📊 Related data that would be deleted:")
                print(f"  User Waifus: {waifu_count}")
                print(f"  Conversations: {conversation_count}")
                print(f"  Mission Progress: {mission_count}")
                
                return True
            
            else:
                # Perform actual reset
                
                # Step 1: Get all user IDs for foreign key operations
                cursor = await db.execute("SELECT id FROM users")
                user_ids = [row[0] for row in await cursor.fetchall()]
                
                # Step 2: Delete all related user data
                for user_id in user_ids:
                    await db.execute("DELETE FROM user_waifus WHERE user_id = ?", (user_id,))
                    await db.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
                    await db.execute("DELETE FROM user_mission_progress WHERE user_id = ?", (user_id,))
                
                print(f"🗑️ Deleted related data for {len(user_ids)} users")
                
                # Step 3: Reset all user stats to defaults with 2000 crystals
                await db.execute("""
                    UPDATE users SET 
                        academy_name = NULL,
                        collector_rank = 1,
                        sakura_crystals = 2000,
                        pity_counter = 0,
                        last_daily_reset = 0,
                        login_streak = 0
                """)
                
                # Step 4: Commit changes
                await db.commit()
                
                print(f"✅ Reset {user_count} users to base state with 2000 crystals")
                return True
                
    except Exception as e:
        print(f"❌ Error resetting SQLite users: {e}")
        return False


async def reset_mysql_users(mysql_config, dry_run=False):
    """Reset all users in MySQL database."""
    try:
        # Connect to MySQL
        conn = await aiomysql.connect(
            host=mysql_config["host"],
            port=mysql_config["port"],
            user=mysql_config["user"],
            password=mysql_config["password"],
            db=mysql_config["database"],
            charset=mysql_config.get("charset", "utf8mb4"),
            autocommit=False,  # Use transactions for safety
        )
        
        async with conn.cursor() as cursor:
            # Count existing users
            await cursor.execute("SELECT COUNT(*) FROM users")
            result = await cursor.fetchone()
            user_count = result[0] if result else 0
            
            if user_count == 0:
                print("ℹ️ No users found in database")
                await conn.ensure_closed()
                return True
                
            print(f"📊 Found {user_count} users in database")
            
            if dry_run:
                # Show what would be reset
                await cursor.execute("""
                    SELECT discord_id, academy_name, sakura_crystals, collector_rank, 
                           pity_counter, last_daily_reset
                    FROM users 
                    ORDER BY discord_id
                    LIMIT 10
                """)
                users_list = await cursor.fetchall()
                
                print("\n🔍 Users that would be reset:")
                print("=" * 80)
                for user in users_list:
                    discord_id, academy_name, crystals, rank, pity, last_daily = user
                    print(f"Discord ID: {discord_id}")
                    print(f"  Academy: {academy_name or 'None'}")
                    print(f"  Crystals: {crystals} → 2000")
                    print(f"  Rank: {rank} → 1")
                    print(f"  Pity: {pity} → 0")
                    print(f"  Last Daily: {last_daily} → 0")
                    print("-" * 40)
                
                if user_count > 10:
                    print(f"... and {user_count - 10} more users")
                
                # Count related data that would be deleted
                await cursor.execute("""
                    SELECT COUNT(*) FROM user_waifus uw 
                    JOIN users u ON uw.user_id = u.id
                """)
                result = await cursor.fetchone()
                waifu_count = result[0] if result else 0
                
                await cursor.execute("""
                    SELECT COUNT(*) FROM conversations c 
                    JOIN users u ON c.user_id = u.id
                """)
                result = await cursor.fetchone()
                conversation_count = result[0] if result else 0
                
                await cursor.execute("""
                    SELECT COUNT(*) FROM user_mission_progress ump 
                    JOIN users u ON ump.user_id = u.id
                """)
                result = await cursor.fetchone()
                mission_count = result[0] if result else 0
                
                print(f"\n📊 Related data that would be deleted:")
                print(f"  User Waifus: {waifu_count}")
                print(f"  Conversations: {conversation_count}")
                print(f"  Mission Progress: {mission_count}")
                
                await conn.ensure_closed()
                return True
            
            else:
                # Perform actual reset in a transaction
                try:
                    # Step 1: Delete all related user data (CASCADE should handle this)
                    await cursor.execute("DELETE FROM user_waifus")
                    await cursor.execute("DELETE FROM conversations")
                    await cursor.execute("DELETE FROM user_mission_progress")
                    
                    print(f"🗑️ Deleted related data for all users")
                    
                    # Step 2: Reset all user stats to defaults with 2000 crystals
                    await cursor.execute("""
                        UPDATE users SET 
                            academy_name = NULL,
                            collector_rank = 1,
                            sakura_crystals = 2000,
                            pity_counter = 0,
                            last_daily_reset = 0
                    """)
                    
                    # Step 3: Commit transaction
                    await conn.commit()
                    
                    print(f"✅ Reset {user_count} users to base state with 2000 crystals")
                    
                except Exception as e:
                    # Rollback on error
                    await conn.rollback()
                    print(f"❌ Error during reset, rolled back: {e}")
                    return False
                finally:
                    await conn.ensure_closed()
                
                return True
        
    except Exception as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return False


def create_backup_log():
    """Create a backup log file with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"reset_operation_{timestamp}.log"
    
    with open(log_filename, "w", encoding="utf-8") as f:
        f.write(f"User Reset Operation Log\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Operation: Reset all users to 2000 sakura crystals\n")
        f.write(f"=" * 50 + "\n\n")
    
    return log_filename


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(description="Reset all users to base state with 2000 crystals")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be changed without making actual changes"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt (use with caution!)"
    )
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.confirm:
        print("⚠️  WARNING: This will reset ALL user data!")
        print("   • All users will have 2000 sakura crystals")
        print("   • All academies will be unnamed")
        print("   • All collector ranks reset to 1")
        print("   • All pity counters reset to 0")
        print("   • All daily login streaks reset")
        print("   • All user waifus will be deleted")
        print("   • All conversations will be deleted")
        print("   • All mission progress will be deleted")
        print()
        
        confirmation = input("Type 'RESET' to confirm this operation: ")
        if confirmation != "RESET":
            print("❌ Operation cancelled")
            return False
    
    # Create backup log
    if not args.dry_run:
        log_file = create_backup_log()
        print(f"📝 Created operation log: {log_file}")
    
    # Run the reset operation
    success = asyncio.run(reset_users_to_base(dry_run=args.dry_run))
    
    if success:
        if args.dry_run:
            print("\n✅ Dry run completed successfully")
            print("💡 Use without --dry-run to perform the actual reset")
        else:
            print("\n🎉 User reset operation completed successfully!")
            print("📊 All users now have 2000 sakura crystals and reset stats")
    else:
        print("\n❌ Operation failed")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
