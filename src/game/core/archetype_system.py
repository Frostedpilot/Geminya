"""
Character Archetype System

Implements character archetypes enumeration for character classification.
Archetype passive system has been removed.
"""

from typing import Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ArchetypeGroup(Enum):
    """Character archetype groups - All 59 archetypes from archetypes.json"""
    # Original 23 archetypes
    PHYSICAL_ATTACKER = "physical_attacker"
    BERSERKER = "berserker"
    MAGE = "mage"
    WARLOCK = "warlock"
    SORCERER = "sorcerer"
    HEALER = "healer"
    PRIEST = "priest"
    DEFENDER = "defender"
    KNIGHT = "knight"
    TEMPLAR = "templar"
    TRICKSTER = "trickster"
    ILLUSIONIST = "illusionist"
    DANCER = "dancer"
    BARD = "bard"
    NINJA = "ninja"
    ASSASSIN = "assassin"
    GUNSLINGER = "gunslinger"
    SAGE = "sage"
    ORACLE = "oracle"
    ENGINEER = "engineer"
    
    # Additional 36 archetypes from JSON
    PALADIN = "paladin"
    ALCHEMIST = "alchemist"
    SAMURAI = "samurai"
    SUMMONER = "summoner"
    DRUID = "druid"
    MONK = "monk"
    ELEMENTALIST = "elementalist"
    VAMPIRE = "vampire"
    SHAMAN = "shaman"
    BEASTMASTER = "beastmaster"
    NECROMANCER = "necromancer"
    WITCH = "witch"
    PIRATE = "pirate"
    HUNTER = "hunter"
    SWORDSMAN = "swordsman"
    ENCHANTER = "enchanter"
    GLADIATOR = "gladiator"
    ARCHER = "archer"
    MYSTIC = "mystic"
    SAGE_OF_LIGHT = "sage_of_light"
    SHADOWBLADE = "shadowblade"
    GEOMANCER = "geomancer"
    WARDEN = "warden"
    REAPER = "reaper"
    ALLY = "ally"
    CHAMPION = "champion"
    WARLORD = "warlord"
    CRUSADER = "crusader"
    INVOKER = "invoker"
    SENTINEL = "sentinel"
    RUNESMITH = "runesmith"
    WITCH_DOCTOR = "witch_doctor"
    DRAGOON = "dragoon"
    ILLUMINATOR = "illuminator"
    SELLSWORD = "sellsword"
    HERALD = "herald"
    WITCH_HUNTER = "witch_hunter"
    PROPHET = "prophet"
    CHAMPION_OF_CHAOS = "champion_of_chaos"

class ArchetypeSystem:
    """Manages character archetypes for character classification"""
    
    def __init__(self):
        logger.info("Initialized archetype system for character classification")
    
    def get_all_archetypes(self) -> List[ArchetypeGroup]:
        """Get all available archetypes"""
        return list(ArchetypeGroup)
    
    def get_archetype_by_name(self, name: str) -> Optional[ArchetypeGroup]:
        """Get archetype by string name"""
        try:
            return ArchetypeGroup(name.lower())
        except ValueError:
            return None

# Global archetype system instance
archetype_system = ArchetypeSystem()
