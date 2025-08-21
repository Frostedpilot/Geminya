"""Test script to verify waifu database and perform a test summon."""

import asyncio
import logging
from services.database import DatabaseService
from services.waifu_service import WaifuService


async def test_waifu_system():
    """Test the waifu system functionality."""
    print("🧪 Testing Waifu Academy System...")

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create services
    database = DatabaseService()
    waifu_service = WaifuService(database)

    try:
        await waifu_service.initialize()

        # Test 1: Check database contents
        print("\n📊 Database Statistics:")

        # Count waifus by rarity
        for rarity in range(1, 6):
            waifus = await database.get_waifus_by_rarity(rarity, 1000)
            print(f"  {rarity}⭐ waifus: {len(waifus)}")

        # Test 2: Create a test user and perform summons
        test_user_id = "test_user_123"
        print(f"\n🎯 Testing summons for user {test_user_id}:")

        user = await database.get_or_create_user(test_user_id)
        print(f"  Created user with {user['sakura_crystals']} crystals")

        # Perform 5 test summons
        for i in range(5):
            result = await waifu_service.perform_summon(test_user_id)
            if result["success"]:
                waifu = result["waifu"]
                status = (
                    "NEW" if result["is_new"] else f"C{result['constellation_level']}"
                )
                print(
                    f"  Summon {i+1}: {waifu['name']} ({waifu['rarity']}⭐) - {status}"
                )
            else:
                print(f"  Summon {i+1}: {result['message']}")

        # Test 3: Check user's collection
        collection = await database.get_user_collection(test_user_id)
        print(f"\n📚 User collection: {len(collection)} waifus")

        # Test 4: Get user stats
        stats = await waifu_service.get_user_stats(test_user_id)
        print(f"  Total: {stats['total_waifus']}, Unique: {stats['unique_waifus']}")
        print(f"  Collection Power: {stats['collection_power']}")
        print(f"  Crystals remaining: {stats['user']['sakura_crystals']}")

        # Test 5: Search functionality
        print(f"\n🔍 Testing search functionality:")
        search_results = await database.search_waifus("Eren", 3)
        for waifu in search_results:
            print(
                f"  Found: {waifu['name']} from {waifu['series']} ({waifu['rarity']}⭐)"
            )

        print("\n✅ All tests completed successfully!")
        print("\n🎮 Your waifu gacha system is ready to use!")
        print("\nTo use in Discord:")
        print("  1. Start your Discord bot")
        print("  2. Use /nwnl_summon to summon waifus")
        print("  3. Use /nwnl_collection to see your collection")
        print("  4. Use /nwnl_status to check your academy")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        logging.error(f"Test error: {e}")

    finally:
        await waifu_service.close()
        print("🔒 Test completed.")


if __name__ == "__main__":
    asyncio.run(test_waifu_system())
