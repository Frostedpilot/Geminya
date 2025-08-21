#!/usr/bin/env python3
"""Script to completely wipe the waifu database (SQLite or MySQL)."""

import asyncio
import aiosqlite
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


async def wipe_database():
    """Completely wipe the waifu database."""
    try:
        # Load configuration
        db_type, sqlite_path, mysql_config = load_config()
        
        print(f"🗑️ Wiping {db_type.upper()} waifu database...")

        if db_type == "sqlite":
            return await wipe_sqlite_database(sqlite_path)
        elif db_type == "mysql":
            return await wipe_mysql_database(mysql_config)
        else:
            print(f"❌ Unknown database type: {db_type}")
            return False

    except Exception as e:
        print(f"❌ Error wiping database: {e}")
        return False


async def wipe_sqlite_database(db_path):
    """Wipe SQLite database."""

    # Remove the database file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✅ Removed existing database: {db_path}")
    else:
        print(f"ℹ️ Database file doesn't exist: {db_path}")

    # Remove any backup files
    data_dir = os.path.dirname(db_path)
    if os.path.exists(data_dir):
        backup_files = [
            f
            for f in os.listdir(data_dir)
            if f.startswith("waifu_academy")
            and f.endswith((".db", ".db-journal", ".db-wal", ".db-shm"))
        ]
        for backup in backup_files:
            backup_path = os.path.join(data_dir, backup)
            os.remove(backup_path)
            print(f"✅ Removed backup: {backup}")

    print("🧹 SQLite database completely wiped!")
    return True


async def wipe_mysql_database(mysql_config):
    """Wipe MySQL database by dropping all waifu tables."""
    
    try:
        # Connect to MySQL
        conn = await aiomysql.connect(
            host=mysql_config["host"],
            port=mysql_config["port"],
            user=mysql_config["user"],
            password=mysql_config["password"],
            db=mysql_config["database"],
            charset=mysql_config.get("charset", "utf8mb4"),
            autocommit=True,
        )
        
        # List of tables to drop (in correct order due to foreign keys)
        tables_to_drop = [
            "user_mission_progress",
            "conversations", 
            "user_waifus",
            "users",
            "waifus",
            "daily_missions",
            "events"
        ]
        
        async with conn.cursor() as cursor:
            # Disable foreign key checks temporarily
            await cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            for table in tables_to_drop:
                try:
                    await cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    print(f"✅ Dropped table: {table}")
                except Exception as e:
                    print(f"⚠️ Could not drop table {table}: {e}")
            
            # Re-enable foreign key checks
            await cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        conn.close()
        print("🧹 MySQL database completely wiped!")
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(wipe_database())
    sys.exit(0 if success else 1)
