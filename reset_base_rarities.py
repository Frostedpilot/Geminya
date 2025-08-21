"""Reset all waifus to base rarities (1-3 stars only)."""

import asyncio
import logging
import aiosqlite
from services.database import DatabaseService
from services.waifu_service import WaifuService


async def reset_to_base_rarities():
    """Reset all waifus to base rarities (1-3 stars only)."""
    print("🔄 Resetting all waifus to base rarities (1-3 stars only)...")

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
                # Apply base rarity logic (1-3 stars only)
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

        print(f"\n✅ Updated {updated_count} waifus to base rarities")

        # Show new distribution
        print("\n📊 New rarity distribution (base rarities only):")
        for rarity in range(1, 6):
            waifus = await db_service.get_waifus_by_rarity(rarity, 1000)
            print(f"  {rarity}⭐ waifus: {len(waifus)}")

        print("\n📝 Note: 4⭐ and 5⭐ rarities are now achieved through:")
        print("  • Constellation upgrades (duplicate summons)")
        print("  • Bond level increases")
        print("  • Special events and upgrades")

    except Exception as e:
        print(f"❌ Error: {e}")
        logging.error(f"Reset error: {e}")

    finally:
        await waifu_service.close()


if __name__ == "__main__":
    asyncio.run(reset_to_base_rarities())
