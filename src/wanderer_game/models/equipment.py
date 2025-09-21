"""
Equipment models for the Wanderer Game

Based on the equipment and equipment_sub_slots database schema.
"""


from dataclasses import dataclass, field
from typing import List, Optional
from .encounter import EncounterModifier
from src.wanderer_game.utils.equipment_utils import random_main_stat_modifier, random_sub_stat_modifier
def random_equipment_no_subslots(discord_id: str, equipment_id: int = 0) -> 'Equipment':
    """
    Generate a random Equipment with a main stat and no sub slots.
    """
    return Equipment(
        id=equipment_id,
        discord_id=discord_id,
        main_effect=random_main_stat_modifier(),
        unlocked_sub_slots=0,
        sub_slots=[],
        created_at=None,
        updated_at=None
    )

@dataclass
class EquipmentSubSlot:
    """Represents a sub-slot for equipment, which can be unlocked and have an EncounterModifier effect or be empty."""
    slot_index: int
    effect: Optional[EncounterModifier] = None
    is_unlocked: bool = False

@dataclass

class Equipment:
    """
    Represents a piece of equipment owned by a user.
    - main_effect: The main stat (only allowed ModifierTypes for main stat)
    - sub_slots: List of sub stats (only allowed ModifierTypes for sub stat)
    """
    id: int
    discord_id: str
    main_effect: Optional[EncounterModifier]
    unlocked_sub_slots: int = 0
    sub_slots: List[EquipmentSubSlot] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def add_sub_slot(self, sub_slot: EquipmentSubSlot):
        self.sub_slots.append(sub_slot)

    def get_unlocked_sub_slots(self) -> List[EquipmentSubSlot]:
        return [slot for slot in self.sub_slots if slot.is_unlocked]

    def get_locked_sub_slots(self) -> List[EquipmentSubSlot]:
        return [slot for slot in self.sub_slots if not slot.is_unlocked]

    def unlock_and_roll_substat(self) -> bool:
        """
        Unlocks the next locked sub slot and assigns it a random sub stat EncounterModifier.
        Returns True if a sub slot was unlocked and rolled, False if all are already unlocked.
        """
        for slot in self.sub_slots:
            if not slot.is_unlocked:
                slot.is_unlocked = True
                slot.effect = random_sub_stat_modifier()
                self.unlocked_sub_slots += 1
                return True
        return False

    def roll_main_stat(self):
        """
        Assigns a new random main stat EncounterModifier to this equipment.
        """
        self.main_effect = random_main_stat_modifier()

    def remove_all_substats(self):
        """
        Removes all sub slot effects and locks all sub slots.
        """
        for slot in self.sub_slots:
            slot.is_unlocked = False
            slot.effect = None
        self.unlocked_sub_slots = 0
