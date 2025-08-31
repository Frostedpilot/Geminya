"""Script to initialize daily missions in the database."""
import asyncio
from config.config import Config
from services.database import DatabaseService

# Define your daily missions here. Edit/add as needed.
MISSIONS = [
    {
        "name": "Play a Game!",
        "description": "Play any of the three games (anidle, guess anime, guess character) today.",
        "type": "play_game",
        "target_count": 1,
        "reward_type": "gems",
        "reward_amount": 200,
        "difficulty": "easy",
        "is_active": True
    },
    # Add more missions here as needed
]

async def main():
    config = Config.create()
    db = DatabaseService(config)
    await db.initialize()

    for mission in MISSIONS:
        result = await db.get_or_create_mission(mission)
        print(f"Initialized mission: {result['name']} (ID: {result['id']})")

    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
