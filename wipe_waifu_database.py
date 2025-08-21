#!/usr/bin/env python3
"""Script to completely wipe the waifu database."""

import asyncio
import aiosqlite
import sys
import os


async def wipe_database():
    """Completely wipe the waifu database."""
    try:
        db_path = "data/waifu_academy.db"

        print("🗑️ Wiping waifu database...")

        # Remove the database file if it exists
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"✅ Removed existing database: {db_path}")
        else:
            print(f"ℹ️ Database file doesn't exist: {db_path}")

        # Remove any backup files
        backup_files = [
            f
            for f in os.listdir("data")
            if f.startswith("waifu_academy")
            and f.endswith((".db", ".db-journal", ".db-wal", ".db-shm"))
        ]
        for backup in backup_files:
            backup_path = os.path.join("data", backup)
            os.remove(backup_path)
            print(f"✅ Removed backup: {backup}")

        print("🧹 Database completely wiped!")
        return True

    except Exception as e:
        print(f"❌ Error wiping database: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(wipe_database())
    sys.exit(0 if success else 1)
