"""
Script to reset World Threat tables and initialize a new boss.
Usage: python initialize_world_threat.py
"""

import asyncio
from services.database import DatabaseService
from config import Config
from datetime import datetime

async def main():
    config = Config.create()
    db = DatabaseService(config)
    await db.initialize()

    # Clear World Threat tables
    async with db.connection_pool.acquire() as conn:
        await conn.execute("DELETE FROM world_threat_player_status;")
        await conn.execute("DELETE FROM world_threat_boss;")
        print("Cleared world_threat_player_status and world_threat_boss tables.")

        # Boss configuration as a dictionary
        # Valid elemental types (lowercase): fire, water, wind, earth, nature, neutral, void, light, dark
        # Valid archetypes: Check character archetypes in data/final/characters_final.csv
        # Valid genres: Check anime genres in character data
        import json
        boss = {
            'boss_name': "Void Leviathan",
            'dominant_stats': json.dumps(["atk", "spd"]),
            'cursed_stat': "int",  # String, not a list
            'buffs': json.dumps({"elemental": ["fire"], "archetype": ["Ally"]}),
            'curses': json.dumps({"genre": ["Shounen"]}),
            'buff_cap': 5,
            'curse_cap': 4,
            'server_total_points': 0,
            'total_research_actions': 0,
            'adaptation_level': 0
        }
        await conn.execute(
            """
            INSERT INTO world_threat_boss (
                id, boss_name, dominant_stats, cursed_stat, buffs, curses, buff_cap, curse_cap, server_total_points, total_research_actions, adaptation_level
            ) VALUES (
                1, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
            )
            """,
            boss['boss_name'], boss['dominant_stats'], boss['cursed_stat'], boss['buffs'], boss['curses'], boss['buff_cap'], boss['curse_cap'], boss['server_total_points'], boss['total_research_actions'], boss['adaptation_level']
        )
        print(f"Initialized new World Threat boss: {boss['boss_name']}")

    await db.close()
    print("World Threat tables reset and boss initialized.")

if __name__ == "__main__":
    asyncio.run(main())
