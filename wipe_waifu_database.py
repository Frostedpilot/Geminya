#!/usr/bin/env python3
"""Script to completely wipe the waifu database (MySQL only)."""

import asyncio
import aiomysql
import sys
import os
import json
from pathlib import Path


def load_config():
    """Load configuration from files without circular imports."""
    # Load secrets
    secrets_path = Path("secrets.json")
    if not secrets_path.exists():
        raise FileNotFoundError("secrets.json not found")
        
    with open(secrets_path, "r", encoding="utf-8") as f:
        secrets = json.load(f)
    
    # MySQL configuration
    mysql_config = {
        "host": secrets.get("MYSQL_HOST"),
        "port": secrets.get("MYSQL_PORT", 3306),
        "user": secrets.get("MYSQL_USER"),
        "password": secrets.get("MYSQL_PASSWORD"),
        "database": secrets.get("MYSQL_DATABASE"),
        "charset": "utf8mb4",
    }
    
    return mysql_config


async def wipe_database():
    """Completely wipe the MySQL waifu database."""
    try:
        # Load configuration
        mysql_config = load_config()
        
        print("🗑️ Wiping MYSQL waifu database...")
        return await wipe_mysql_database(mysql_config)

    except Exception as e:
        print(f"❌ Error wiping database: {e}")
        return False


async def wipe_mysql_database(mysql_config):
    """Wipe MySQL database by dropping all tables."""
    try:
        # Connect to MySQL
        connection = await aiomysql.connect(
            host=mysql_config["host"],
            port=mysql_config["port"],
            user=mysql_config["user"],
            password=mysql_config["password"],
            db=mysql_config["database"],
            charset=mysql_config.get("charset", "utf8mb4"),
        )

        async with connection.cursor() as cursor:
            # Disable foreign key checks
            await cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

            # Get all table names
            await cursor.execute("SHOW TABLES")
            tables = await cursor.fetchall()

            if tables:
                print(f"📋 Found {len(tables)} tables to drop")

                # Drop each table
                for table in tables:
                    table_name = table[0]
                    print(f"🗑️ Dropping table: {table_name}")
                    await cursor.execute(f"DROP TABLE `{table_name}`")

                # Re-enable foreign key checks
                await cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                await connection.commit()

                print("🧹 MySQL database completely wiped!")
            else:
                print("✅ Database is already empty")

        connection.close()
        return True

    except Exception as e:
        print(f"❌ MySQL Error: {e}")
        return False


def confirm_wipe():
    """Ask for confirmation before wiping."""
    print("⚠️  WARNING: This will PERMANENTLY DELETE all waifu data!")
    print("   - All user accounts and collections")
    print("   - All waifus and their data")
    print("   - All conversations and progress")
    print("   - All shop purchases and inventory")
    print()
    
    response = input("Are you absolutely sure? Type 'YES I WANT TO DELETE EVERYTHING': ")
    return response == "YES I WANT TO DELETE EVERYTHING"


async def main():
    """Main function."""
    print("🗑️ Waifu Database Wiper")
    print("=" * 50)
    
    if not confirm_wipe():
        print("❌ Operation cancelled")
        sys.exit(1)
    
    print("\n🔄 Starting database wipe...")
    success = await wipe_database()
    
    if success:
        print("\n✅ Database wipe completed successfully!")
        print("🔄 You may need to run populate_from_mal.py to re-populate waifus")
    else:
        print("\n❌ Database wipe failed!")
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
