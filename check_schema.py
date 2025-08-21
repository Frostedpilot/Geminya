import asyncio
import aiosqlite


async def check_schema():
    async with aiosqlite.connect("data/waifu_academy.db") as db:
        cursor = await db.execute("PRAGMA table_info(users)")
        rows = await cursor.fetchall()
        print("Users table schema:")
        for row in rows:
            print(f"  {row}")

        cursor = await db.execute("PRAGMA table_info(waifus)")
        rows = await cursor.fetchall()
        print("\nWaifus table schema:")
        for row in rows:
            print(f"  {row}")


asyncio.run(check_schema())
