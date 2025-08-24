#!/usr/bin/env python3
"""Script to reset all user data but preserve accounts with 2000 sakura crystals."""

import asyncio
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
    
    return database_type, sqlite_path


async def reset_users_to_base(dry_run=False):
    """Reset all users to base state with 2000 sakura crystals."""
    # Load configuration
    db_type, sqlite_path = load_config()

    if dry_run:
        print(f"🔍 DRY RUN: Simulating reset of {db_type.upper()} database...")
    else:
        print(f"🔄 Resetting all users in {db_type.upper()} database to 2000 crystals...")

    if db_type == "postgres":
        return await reset_postgres_users(dry_run)
    else:
        print(f"❌ Only PostgreSQL is supported. Unknown database type: {db_type}")
        return False
# --- PostgreSQL Reset Implementation ---
async def reset_postgres_users(dry_run=False):
    """Reset all users in PostgreSQL database."""
    import asyncpg
    # Load secrets for PostgreSQL connection
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
    pg_config = {
        'host': secrets.get('POSTGRES_HOST', 'localhost'),
        'port': int(secrets.get('POSTGRES_PORT', 5432)),
        'user': secrets.get('POSTGRES_USER'),
        'password': secrets.get('POSTGRES_PASSWORD'),
        'database': secrets.get('POSTGRES_DB', secrets.get('POSTGRES_DATABASE', 'postgres')),
    }
    pool = await asyncpg.create_pool(**pg_config)
    try:
        async with pool.acquire() as conn:
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            if user_count == 0:
                print("ℹ️ No users found in database")
                return True
            print(f"📊 Found {user_count} users in database")
            if dry_run:
                users_list = await conn.fetch("""
                    SELECT discord_id, academy_name, sakura_crystals, quartzs, collector_rank, pity_counter, last_daily_reset
                    FROM users ORDER BY discord_id LIMIT 10
                """)
                print("\n🔍 Users that would be reset:")
                print("=" * 80)
                for i, user in enumerate(users_list):
                    print(f"Discord ID: {user['discord_id']}")
                    print(f"  Academy: {user['academy_name'] or 'None'}")
                    print(f"  Crystals: {user['sakura_crystals']} → 2000")
                    print(f"  Quartz: {user['quartzs']} → 0")
                    print(f"  Rank: {user['collector_rank']} → 1")
                    print(f"  Pity: {user['pity_counter']} → 0")
                    print(f"  Last Daily: {user['last_daily_reset']} → 0")
                    print("-" * 40)
                if user_count > 10:
                    print(f"... and {user_count - 10} more users")
                # Count related data that would be deleted
                waifu_count = await conn.fetchval("SELECT COUNT(*) FROM user_waifus")
                conversation_count = await conn.fetchval("SELECT COUNT(*) FROM conversations")
                mission_count = await conn.fetchval("SELECT COUNT(*) FROM user_mission_progress")
                purchase_count = await conn.fetchval("SELECT COUNT(*) FROM user_purchases")
                inventory_count = await conn.fetchval("SELECT COUNT(*) FROM user_inventory")
                print(f"\n📊 Related data that would be deleted:")
                print(f"  User Waifus: {waifu_count}")
                print(f"  Conversations: {conversation_count}")
                print(f"  Mission Progress: {mission_count}")
                print(f"  User Purchases: {purchase_count}")
                print(f"  User Inventory: {inventory_count}")
                return True
            # --- Actual reset ---
            # Delete related data
            await conn.execute("DELETE FROM user_waifus")
            await conn.execute("DELETE FROM conversations")
            await conn.execute("DELETE FROM user_mission_progress")
            await conn.execute("DELETE FROM user_purchases")
            await conn.execute("DELETE FROM user_inventory")
            print(f"🗑️ Deleted related data for all users")
            # Reset user stats
            await conn.execute("""
                UPDATE users SET 
                    academy_name = NULL,
                    collector_rank = 1,
                    sakura_crystals = 2000,
                    quartzs = 0,
                    pity_counter = 0,
                    last_daily_reset = 0
            """)
            print(f"✅ Reset {user_count} users to base state with 2000 crystals")
        return True
    except Exception as e:
        print(f"❌ Error resetting PostgreSQL users: {e}")
        return False
    finally:
        await pool.close()




## All MySQL/aiomysql support has been removed. Use the main bot/database service for PostgreSQL resets.


def create_backup_log():
    """Create a backup log file with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"reset_operation_{timestamp}.log"
    
    # Log currently have nothing so just don't log for now
    # with open(log_filename, "w", encoding="utf-8") as f:
    #     f.write(f"User Reset Operation Log\n")
    #     f.write(f"Timestamp: {datetime.now().isoformat()}\n")
    #     f.write(f"Operation: Reset all users to 2000 sakura crystals\n")
    #     f.write(f"=" * 50 + "\n\n")
    
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
        print("   • All users will have 0 quartz")
        print("   • All academies will be unnamed")
        print("   • All collector ranks reset to 1")
        print("   • All pity counters reset to 0")
        print("   • All daily login data reset")
        print("   • All user waifus will be deleted")
        print("   • All conversations will be deleted")
        print("   • All mission progress will be deleted")
        print("   • All purchase history will be deleted")
        print("   • All inventory items will be deleted")
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
