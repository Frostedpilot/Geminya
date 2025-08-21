"""Update existing waifu rarities with improved logic."""

import asyncio
import logging
import aiosqlite
from services.database import DatabaseService
from services.waifu_service import WaifuService


async def update_waifu_rarities():
    """Update existing waifus with improved rarity logic."""
    print("🔄 Updating waifu rarities...")

    db_service = DatabaseService()
    waifu_service = WaifuService(db_service)

    try:
        await waifu_service.initialize()

        # Get all waifus
        async with aiosqlite.connect(db_service.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute("SELECT * FROM waifus") as cursor:
                waifus = await cursor.fetchall()

            updated_count = 0

            for waifu in waifus:
                # Apply new rarity logic
                # We'll assume main characters based on common names
                role = (
                    "Main"
                    if any(
                        name in waifu["name"].lower()
                        for name in [
                            "eren",
                            "mikasa",
                            "armin",
                            "gon",
                            "killua",
                            "kurapika",
                            "leorio",
                            "light",
                            "l",
                            "kurisu",
                            "okabe",
                            "saitama",
                            "genos",
                            "tanjiro",
                            "nezuko",
                            "zenitsu",
                            "inosuke",
                            "gojo",
                            "yuji",
                            "megumi",
                            "nobara",
                        ]
                    )
                    else "Supporting"
                )

                new_rarity = waifu_service._determine_character_rarity(
                    role, 1000, waifu["name"]  # Assume 1000 favorites for update
                )

                if new_rarity != waifu["rarity"]:
                    await db.execute(
                        "UPDATE waifus SET rarity = ? WHERE id = ?",
                        (new_rarity, waifu["id"]),
                    )
                    updated_count += 1
                    print(
                        f"  Updated {waifu['name']}: {waifu['rarity']}⭐ → {new_rarity}⭐"
                    )

            await db.commit()

        print(f"\n✅ Updated {updated_count} waifus")

        # Show new distribution
        print("\n📊 New rarity distribution:")
        for rarity in range(1, 6):
            waifus = await db_service.get_waifus_by_rarity(rarity, 1000)
            print(f"  {rarity}⭐ waifus: {len(waifus)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        logging.error(f"Update error: {e}")

    finally:
        await waifu_service.close()


if __name__ == "__main__":
    asyncio.run(update_waifu_rarities())
