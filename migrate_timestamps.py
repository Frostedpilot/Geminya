#!/usr/bin/env python3
"""Database migration script to convert timestamp fields to Unix timestamps."""

import asyncio
import aiosqlite
import sys
from datetime import datetime


async def migrate_timestamps():
    """Convert string timestamps to Unix timestamps."""
    try:
        async with aiosqlite.connect("data/waifu_academy.db") as db:
            print("🔄 Starting timestamp migration...")

            # First, add new columns with INTEGER type
            try:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN created_at_new INTEGER DEFAULT 0"
                )
                await db.execute(
                    "ALTER TABLE users ADD COLUMN last_daily_reset_new INTEGER DEFAULT 0"
                )
                await db.execute(
                    "ALTER TABLE waifus ADD COLUMN created_at_new INTEGER DEFAULT 0"
                )
                await db.commit()
                print("✅ Added new timestamp columns")
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"⚠️ Warning adding columns: {e}")

            # Convert users table timestamps
            cursor = await db.execute(
                "SELECT id, created_at, last_daily_reset FROM users"
            )
            rows = await cursor.fetchall()

            updated_users = 0
            for user_id, created_at_str, last_daily_str in rows:
                try:
                    # Convert created_at
                    if created_at_str and isinstance(created_at_str, str):
                        created_at_dt = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00").replace(" ", "T")
                        )
                        created_at_unix = int(created_at_dt.timestamp())
                    else:
                        created_at_unix = int(datetime.now().timestamp())

                    # Convert last_daily_reset
                    if last_daily_str and isinstance(last_daily_str, str):
                        last_daily_dt = datetime.fromisoformat(
                            last_daily_str.replace("Z", "+00:00").replace(" ", "T")
                        )
                        last_daily_unix = int(last_daily_dt.timestamp())
                    else:
                        last_daily_unix = 0

                    await db.execute(
                        "UPDATE users SET created_at_new = ?, last_daily_reset_new = ? WHERE id = ?",
                        (created_at_unix, last_daily_unix, user_id),
                    )
                    updated_users += 1

                except Exception as e:
                    print(f"⚠️ Error converting user {user_id}: {e}")
                    # Set default values for problematic records
                    await db.execute(
                        "UPDATE users SET created_at_new = ?, last_daily_reset_new = ? WHERE id = ?",
                        (int(datetime.now().timestamp()), 0, user_id),
                    )

            # Convert waifus table timestamps
            cursor = await db.execute("SELECT id, created_at FROM waifus")
            rows = await cursor.fetchall()

            updated_waifus = 0
            for waifu_id, created_at_str in rows:
                try:
                    if created_at_str and isinstance(created_at_str, str):
                        created_at_dt = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00").replace(" ", "T")
                        )
                        created_at_unix = int(created_at_dt.timestamp())
                    else:
                        created_at_unix = int(datetime.now().timestamp())

                    await db.execute(
                        "UPDATE waifus SET created_at_new = ? WHERE id = ?",
                        (created_at_unix, waifu_id),
                    )
                    updated_waifus += 1

                except Exception as e:
                    print(f"⚠️ Error converting waifu {waifu_id}: {e}")
                    await db.execute(
                        "UPDATE waifus SET created_at_new = ? WHERE id = ?",
                        (int(datetime.now().timestamp()), waifu_id),
                    )

            await db.commit()

            # Now drop old columns and rename new ones
            print("🔄 Updating table schema...")

            # For users table
            await db.execute(
                """
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT UNIQUE NOT NULL,
                    academy_name TEXT,
                    collector_rank INTEGER DEFAULT 1,
                    sakura_crystals INTEGER DEFAULT 100,
                    pity_counter INTEGER DEFAULT 0,
                    last_daily_reset INTEGER DEFAULT 0,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """
            )

            await db.execute(
                """
                INSERT INTO users_new (id, discord_id, academy_name, collector_rank, sakura_crystals, pity_counter, last_daily_reset, created_at)
                SELECT id, discord_id, academy_name, collector_rank, sakura_crystals, pity_counter, 
                       COALESCE(last_daily_reset_new, 0), COALESCE(created_at_new, strftime('%s', 'now'))
                FROM users
            """
            )

            await db.execute("DROP TABLE users")
            await db.execute("ALTER TABLE users_new RENAME TO users")

            # For waifus table
            await db.execute(
                """
                CREATE TABLE waifus_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mal_id INTEGER,
                    name TEXT NOT NULL,
                    anime_title TEXT,
                    image_url TEXT,
                    description TEXT,
                    rarity INTEGER NOT NULL,
                    base_stats TEXT,
                    birthday DATE,
                    favorite_gifts TEXT,
                    special_dialogue TEXT,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """
            )

            await db.execute(
                """
                INSERT INTO waifus_new (id, mal_id, name, anime_title, image_url, description, rarity, base_stats, birthday, favorite_gifts, special_dialogue, created_at)
                SELECT id, mal_id, name, anime_title, image_url, description, rarity, base_stats, birthday, favorite_gifts, special_dialogue,
                       COALESCE(created_at_new, strftime('%s', 'now'))
                FROM waifus
            """
            )

            await db.execute("DROP TABLE waifus")
            await db.execute("ALTER TABLE waifus_new RENAME TO waifus")

            await db.commit()

            print(f"✅ Migration completed successfully!")
            print(f"  📊 Updated {updated_users} users")
            print(f"  📊 Updated {updated_waifus} waifus")
            print(f"  🕒 All timestamps are now Unix integers")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(migrate_timestamps())
    sys.exit(0 if success else 1)
