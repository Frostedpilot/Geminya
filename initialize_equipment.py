

import asyncio
import random
import json
from services.database import DatabaseService
from src.wanderer_game.models.encounter import EncounterModifier, ModifierType
from config.config import Config

from src.wanderer_game.models.equipment import random_equipment_no_subslots, Equipment, EquipmentSubSlot
from src.wanderer_game.utils.equipment_utils import random_main_stat_modifier, random_sub_stat_modifier

async def initialize_equipment():
    config = Config.create()
    db = DatabaseService(config)
    await db.initialize()
    print("Fetching all users...")
    async with db.connection_pool.acquire() as conn:
        users = await conn.fetch("SELECT discord_id FROM users")
    print(f"Found {len(users)} users. Generating equipment...")
    for user in users:
        discord_id = user['discord_id']
        # Generate a random main stat for main_effect
        main_effect = random_main_stat_modifier()
        main_effect_json = json.dumps({
            "type": main_effect.type.value,
            "affinity": main_effect.affinity,
            "category": main_effect.category,
            "value": main_effect.value,
            "stat": main_effect.stat
        })
        # Add equipment with all slots unlocked (assume 3 slots)
        equipment_id = await db.add_equipment(discord_id, main_effect_json, unlocked_sub_slots=3)
        # Add 3 sub slots, each with a random sub stat effect (slot_index 1, 2, 3)
        for slot_index in range(1, 4):
            effect = random_sub_stat_modifier()
            effect_json = json.dumps({
                "type": effect.type.value,
                "affinity": effect.affinity,
                "category": effect.category,
                "value": effect.value,
                "stat": effect.stat
            })
            await db.add_equipment_sub_slot(equipment_id, slot_index, effect_json, is_unlocked=True)
        print(f"Initialized equipment for user {discord_id} (equipment_id={equipment_id})")
    print("All users have been given random equipment with all slots unlocked.")


if __name__ == "__main__":
    asyncio.run(initialize_equipment())
