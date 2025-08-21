#!/usr/bin/env python3
"""Simple timestamp migration script."""

import asyncio
import aiosqlite
import sys
from datetime import datetime


async def simple_migrate():
    """Convert existing timestamps to Unix format."""
    try:
        async with aiosqlite.connect("data/waifu_academy.db") as db:
            print("🔄 Migrating timestamps...")

            # Update users table timestamp columns
            cursor = await db.execute(
                "SELECT id, created_at FROM users WHERE created_at_new = 0"
            )
            rows = await cursor.fetchall()

            for user_id, created_at_str in rows:
                try:
                    if created_at_str and isinstance(created_at_str, str):
                        # Parse the timestamp string
                        created_at_dt = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00").replace(" ", "T")
                        )
                        created_at_unix = int(created_at_dt.timestamp())
                    else:
                        created_at_unix = int(datetime.now().timestamp())

                    await db.execute(
                        "UPDATE users SET created_at_new = ? WHERE id = ?",
                        (created_at_unix, user_id),
                    )
                except Exception as e:
                    print(f"⚠️ Error converting user {user_id}: {e}")
                    await db.execute(
                        "UPDATE users SET created_at_new = ? WHERE id = ?",
                        (int(datetime.now().timestamp()), user_id),
                    )

            await db.commit()
            print("✅ Migration completed successfully!")

            # Verify a sample
            cursor = await db.execute(
                "SELECT discord_id, created_at, created_at_new FROM users LIMIT 3"
            )
            rows = await cursor.fetchall()
            print("\n📊 Sample results:")
            for discord_id, old_ts, new_ts in rows:
                print(f"  User {discord_id}: {old_ts} → {new_ts}")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(simple_migrate())
    sys.exit(0 if success else 1)
