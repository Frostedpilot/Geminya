

import asyncio
import random
import json
from services.database import DatabaseService
from config.constants import MAX_EQUIPMENT_PER_USER
from src.wanderer_game.models.encounter import EncounterModifier, ModifierType
from config.config import Config

from src.wanderer_game.models.equipment import random_equipment_no_subslots, Equipment, EquipmentSubSlot
from src.wanderer_game.utils.equipment_utils import random_main_stat_modifier, random_sub_stat_modifier

async def initialize_equipment():
    config = Config.create()
    db = DatabaseService(config)
    await db.initialize()
    async with db.connection_pool.acquire() as conn:
        await conn.execute("DELETE FROM equipment_sub_slots;")
        await conn.execute("DELETE FROM equipment;")
        #reset id start from 1 again
        await conn.execute("ALTER SEQUENCE equipment_id_seq RESTART WITH 1;")
    print("Fetching all users...")
    users = [{'discord_id':"598693507393257497"}]
    print(f"Found {len(users)} users. Generating equipment...")
    for user in users:
        discord_id = user['discord_id']
        # Generate a random main stat for main_effect
        for _ in range(MAX_EQUIPMENT_PER_USER):
            main_effect = random_main_stat_modifier()
            main_effect_json = json.dumps({
                "type": main_effect.type.value,
                "affinity": main_effect.affinity,
                "category": main_effect.category,
                "value": main_effect.value,
                "stat": main_effect.stat
            })
            sub_value = 0
            equipment_id = await db.add_equipment(discord_id, main_effect_json, unlocked_sub_slots=sub_value)
            # Add 3 sub slots, each with a random sub stat effect (slot_index 1, 2, 3)
            for slot_index in range(1, sub_value + 1):
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
