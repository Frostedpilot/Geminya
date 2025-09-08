"""
Character Archetype System

Implements character archetypes and their passive bonuses as described
in the design document.
"""

from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass
import logging

from ..components.stats_component import StatModifier, StatType, ModifierType

logger = logging.getLogger(__name__)

class ArchetypeGroup(Enum):
    """Character archetype groups"""
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
    DEBUFFER = "debuffer"
    TRICKSTER = "trickster"
    ILLUSIONIST = "illusionist"
    BUFFER = "buffer"
    DANCER = "dancer"
    BARD = "bard"
    SPECIALIST = "specialist"
    NINJA = "ninja"
    ASSASSIN = "assassin"
    GUNSLINGER = "gunslinger"
    SAGE = "sage"
    ORACLE = "oracle"
    ENGINEER = "engineer"

@dataclass
class ArchetypePassive:
    """Definition of an archetype passive ability"""
    archetype_group: ArchetypeGroup
    name: str
    description: str
    effect_type: str  # "stat_modifier", "conditional", "immunity", "status_chance"
    parameters: Dict

class ArchetypeSystem:
    """Manages character archetypes and their passive effects"""
    
    def __init__(self):
        self.archetype_passives: Dict[ArchetypeGroup, ArchetypePassive] = {}
        self._initialize_archetype_passives()
        logger.info("Initialized archetype system with %d archetypes", len(self.archetype_passives))
    
    def _initialize_archetype_passives(self):
        """Initialize all archetype passives from the design document"""
        
        passives = [
            ArchetypePassive(
                archetype_group=ArchetypeGroup.PHYSICAL_ATTACKER,
                name="Berserker Rage",
                description="Gains +2% ATK for every 10% of missing HP.",
                effect_type="conditional_stat_modifier",
                parameters={
                    "stat": "atk",
                    "modifier_type": "percentage",
                    "scaling": "missing_hp_percentage",
                    "rate": 0.2  # 2% per 10% missing HP
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.BERSERKER,
                name="Berserker Rage",
                description="Gains +2% ATK for every 10% of missing HP.",
                effect_type="conditional_stat_modifier",
                parameters={
                    "stat": "atk",
                    "modifier_type": "percentage", 
                    "scaling": "missing_hp_percentage",
                    "rate": 0.2
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.MAGE,
                name="Arcane Resistance",
                description="Starts the battle with +15% magical resistance (SPR).",
                effect_type="stat_modifier",
                parameters={
                    "stat": "spr",
                    "modifier_type": "percentage",
                    "value": 0.15
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.WARLOCK,
                name="Arcane Resistance",
                description="Starts the battle with +15% magical resistance (SPR).",
                effect_type="stat_modifier",
                parameters={
                    "stat": "spr",
                    "modifier_type": "percentage",
                    "value": 0.15
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.SORCERER,
                name="Arcane Resistance",
                description="Starts the battle with +15% magical resistance (SPR).",
                effect_type="stat_modifier",
                parameters={
                    "stat": "spr",
                    "modifier_type": "percentage",
                    "value": 0.15
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.HEALER,
                name="Enhanced Healing",
                description="Increases all healing they perform by 10%.",
                effect_type="healing_modifier",
                parameters={
                    "healing_multiplier": 1.10
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.PRIEST,
                name="Enhanced Healing", 
                description="Increases all healing they perform by 10%.",
                effect_type="healing_modifier",
                parameters={
                    "healing_multiplier": 1.10
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.DEFENDER,
                name="Defender's Resolve",
                description="The first time this character is hit, they gain a +20% VIT buff for 2 turns.",
                effect_type="first_hit_trigger",
                parameters={
                    "trigger_stat": "vit",
                    "modifier_value": 0.20,
                    "duration": 2
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.KNIGHT,
                name="Defender's Resolve",
                description="The first time this character is hit, they gain a +20% VIT buff for 2 turns.",
                effect_type="first_hit_trigger",
                parameters={
                    "trigger_stat": "vit",
                    "modifier_value": 0.20,
                    "duration": 2
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.TEMPLAR,
                name="Defender's Resolve",
                description="The first time this character is hit, they gain a +20% VIT buff for 2 turns.",
                effect_type="first_hit_trigger",
                parameters={
                    "trigger_stat": "vit",
                    "modifier_value": 0.20,
                    "duration": 2
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.DEBUFFER,
                name="Opening Gambit",
                description="At the start of the battle, has a 25% chance to apply 'Slow' to a random front-row enemy for 1 turn.",
                effect_type="battle_start_trigger",
                parameters={
                    "status_effect": "slow",
                    "target": "random_front_enemy",
                    "probability": 0.25,
                    "duration": 1
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.TRICKSTER,
                name="Opening Gambit",
                description="At the start of the battle, has a 25% chance to apply 'Slow' to a random front-row enemy for 1 turn.",
                effect_type="battle_start_trigger",
                parameters={
                    "status_effect": "slow",
                    "target": "random_front_enemy",
                    "probability": 0.25,
                    "duration": 1
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.ILLUSIONIST,
                name="Opening Gambit",
                description="At the start of the battle, has a 25% chance to apply 'Slow' to a random front-row enemy for 1 turn.",
                effect_type="battle_start_trigger",
                parameters={
                    "status_effect": "slow",
                    "target": "random_front_enemy",
                    "probability": 0.25,
                    "duration": 1
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.BUFFER,
                name="Extended Support",
                description="Buffs cast by this character last for one additional turn.",
                effect_type="buff_duration_modifier",
                parameters={
                    "duration_bonus": 1
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.DANCER,
                name="Extended Support",
                description="Buffs cast by this character last for one additional turn.",
                effect_type="buff_duration_modifier",
                parameters={
                    "duration_bonus": 1
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.BARD,
                name="Extended Support",
                description="Buffs cast by this character last for one additional turn.",
                effect_type="buff_duration_modifier",
                parameters={
                    "duration_bonus": 1
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.SPECIALIST,
                name="Specialized Training",
                description="Has a permanent +10% bonus to SPD and LCK.",
                effect_type="stat_modifier",
                parameters={
                    "stats": ["spd", "lck"],
                    "modifier_type": "percentage",
                    "value": 0.10
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.NINJA,
                name="Specialized Training",
                description="Has a permanent +10% bonus to SPD and LCK.",
                effect_type="stat_modifier",
                parameters={
                    "stats": ["spd", "lck"],
                    "modifier_type": "percentage",
                    "value": 0.10
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.ASSASSIN,
                name="Specialized Training",
                description="Has a permanent +10% bonus to SPD and LCK.",
                effect_type="stat_modifier",
                parameters={
                    "stats": ["spd", "lck"],
                    "modifier_type": "percentage",
                    "value": 0.10
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.GUNSLINGER,
                name="Specialized Training",
                description="Has a permanent +10% bonus to SPD and LCK.",
                effect_type="stat_modifier",
                parameters={
                    "stats": ["spd", "lck"],
                    "modifier_type": "percentage",
                    "value": 0.10
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.SAGE,
                name="Mental Fortitude",
                description="Immune to the 'Silence' status effect.",
                effect_type="immunity",
                parameters={
                    "immune_to": ["silence"]
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.ORACLE,
                name="Mental Fortitude",
                description="Immune to the 'Silence' status effect.",
                effect_type="immunity",
                parameters={
                    "immune_to": ["silence"]
                }
            ),
            
            ArchetypePassive(
                archetype_group=ArchetypeGroup.ENGINEER,
                name="Mental Fortitude",
                description="Immune to the 'Silence' status effect.",
                effect_type="immunity",
                parameters={
                    "immune_to": ["silence"]
                }
            )
        ]
        
        for passive in passives:
            self.archetype_passives[passive.archetype_group] = passive
    
    def get_archetype_passive(self, archetype: ArchetypeGroup) -> Optional[ArchetypePassive]:
        """Get the passive for an archetype"""
        return self.archetype_passives.get(archetype)
    
    def apply_archetype_passive(self, character_id: str, archetype: ArchetypeGroup, character_stats):
        """Apply archetype passive effects to a character"""
        passive = self.get_archetype_passive(archetype)
        if not passive:
            logger.warning("No passive found for archetype: %s", archetype)
            return
        
        if passive.effect_type == "stat_modifier":
            self._apply_stat_modifier_passive(character_id, passive, character_stats)
        elif passive.effect_type == "conditional_stat_modifier":
            self._apply_conditional_modifier_passive(character_id, passive, character_stats)
        elif passive.effect_type == "healing_modifier":
            # This would be handled by the combat system during healing
            logger.debug("Healing modifier passive applied for %s", character_id)
        elif passive.effect_type == "immunity":
            # This would be handled by the status effect system
            logger.debug("Immunity passive applied for %s", character_id)
        elif passive.effect_type == "first_hit_trigger":
            # This would be handled by the combat system on first damage
            logger.debug("First hit trigger passive applied for %s", character_id)
        elif passive.effect_type == "battle_start_trigger":
            # This would be handled at battle start
            logger.debug("Battle start trigger passive applied for %s", character_id)
        elif passive.effect_type == "buff_duration_modifier":
            # This would be handled by the status effect system
            logger.debug("Buff duration modifier passive applied for %s", character_id)
        
        logger.info("Applied archetype passive '%s' to character %s", passive.name, character_id)
    
    def _apply_stat_modifier_passive(self, character_id: str, passive: ArchetypePassive, character_stats):
        """Apply basic stat modifier passive"""
        params = passive.parameters
        
        if "stats" in params:
            # Multiple stats
            for stat_name in params["stats"]:
                modifier = StatModifier(
                    modifier_id=f"archetype_{passive.archetype_group.value}_{stat_name}",
                    stat_type=getattr(StatType, stat_name.upper()),
                    modifier_type=getattr(ModifierType, params["modifier_type"].upper()),
                    value=params["value"],
                    source=f"archetype_{passive.archetype_group.value}",
                    layer=0,  # Archetype passives apply early
                    duration=None  # Permanent
                )
                character_stats.add_modifier(modifier)
                logger.debug("Added stat modifier for %s: %s", character_id, stat_name)
        else:
            # Single stat
            modifier = StatModifier(
                modifier_id=f"archetype_{passive.archetype_group.value}_{params['stat']}",
                stat_type=getattr(StatType, params["stat"].upper()),
                modifier_type=getattr(ModifierType, params["modifier_type"].upper()),
                value=params["value"],
                source=f"archetype_{passive.archetype_group.value}",
                layer=0,
                duration=None
            )
            character_stats.add_modifier(modifier)
            logger.debug("Added stat modifier for %s: %s", character_id, params["stat"])
    
    def _apply_conditional_modifier_passive(self, character_id: str, passive: ArchetypePassive, character_stats):
        """Apply conditional modifier passive (like berserker rage)"""
        # This would need more complex implementation to track HP changes
        # For now, just log that it's been registered
        logger.debug("Registered conditional modifier passive for %s: %s", 
                    character_id, passive.name)
        # In a full implementation, we'd register event handlers here
        # character_stats would be used to apply dynamic modifiers based on conditions
        _ = character_stats  # Acknowledge parameter
    
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
