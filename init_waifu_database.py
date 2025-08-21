"""Initialize Waifu Academy database with initial data."""

import asyncio
import logging
from services.database import DatabaseService
from services.waifu_service import WaifuService


async def initialize_waifu_database():
    """Initialize the waifu database with sample data."""
    print("🌸 Initializing Waifu Academy Database...")

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create services
    database = DatabaseService()
    waifu_service = WaifuService(database)

    try:
        # Initialize database
        await waifu_service.initialize()
        print("✅ Database schema created successfully!")

        # Populate with initial waifu data
        print("📚 Populating database with initial waifus...")
        await waifu_service.populate_initial_waifus()
        print("✅ Initial waifus added successfully!")

        # Add some sample users for testing
        print("👥 Creating sample users...")
        test_users = ["123456789", "987654321"]  # Sample Discord IDs

        for user_id in test_users:
            user = await database.get_or_create_user(user_id)
            print(f"✅ Created user: {user['academy_name']}")

        print("\n🎉 Waifu Academy database initialization complete!")
        print("You can now use the following commands:")
        print("  • /nwnl_summon - Summon new waifus")
        print("  • /nwnl_collection - View your collection")
        print("  • /nwnl_profile <name> - View waifu details")
        print("  • /nwnl_status - Check academy status")
        print("  • /nwnl_daily - Claim daily rewards")

    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        logging.error(f"Initialization error: {e}")

    finally:
        # Cleanup
        await waifu_service.close()
        print("🔒 Database connection closed.")


if __name__ == "__main__":
    asyncio.run(initialize_waifu_database())
