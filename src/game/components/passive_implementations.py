"""
Passive Ability Implementations

This module contains concrete implementations of common passive abilities.
These serve as examples and basic implementations that can be extended.
"""

from typing import Dict, Any
import logging
import random

from .abilities_component import BasePassive, PassiveType, SkillCondition
from .stats_component import StatModifier, StatType, ModifierType
from ..core.event_system import GameEvent, event_bus

logger = logging.getLogger(__name__)

class StatBoostPassive(BasePassive):
    """Generic passive that provides a permanent stat boost"""
    
    def __init__(
        self, 
        passive_id: str,
        name: str,
        stat_type: StatType, 
        boost_amount: float,
        boost_type: ModifierType = ModifierType.PERCENTAGE
    ):
        description = f"+{int(boost_amount * 100) if boost_type == ModifierType.PERCENTAGE else boost_amount}{'%' if boost_type == ModifierType.PERCENTAGE else ''} {stat_type.value.upper()}"
        
        super().__init__(
            passive_id=passive_id,
            name=name,
            description=description,
            passive_type=PassiveType.GENERIC
        )
        
        self.stat_type = stat_type
        self.boost_amount = boost_amount
        self.boost_type = boost_type
        self._modifier_id = f"{passive_id}_stat_boost"
    
    def apply_effects(self, character):
        """Apply the stat boost modifier"""
        if hasattr(character, 'stats'):
            modifier = StatModifier(
                modifier_id=self._modifier_id,
                stat_type=self.stat_type,
                modifier_type=self.boost_type,
                value=self.boost_amount,
                source=f"passive_{self.passive_id}",
                layer=2  # Passive layer
            )
            character.stats.add_modifier(modifier)
            logger.debug("Applied passive stat boost: %s", self.name)
    
    def remove_effects(self, character):
        """Remove the stat boost modifier"""
        if hasattr(character, 'stats'):
            character.stats.remove_modifier(self._modifier_id)
            logger.debug("Removed passive stat boost: %s", self.name)

class ConditionalStatPassive(BasePassive):
    """Passive that provides stat boosts only when conditions are met"""
    
    def __init__(
        self,
        passive_id: str,
        name: str,
        description: str,
        stat_type: StatType,
        boost_amount: float,
        condition_func,
        boost_type: ModifierType = ModifierType.PERCENTAGE
    ):
        # Add condition to passive
        condition = SkillCondition(
            condition_id=f"{passive_id}_condition",
            description="Passive activation condition",
            check_function=condition_func
        )
        
        super().__init__(
            passive_id=passive_id,
            name=name,
            description=description,
            passive_type=PassiveType.SIGNATURE,
            conditions=[condition]
        )
        
        self.stat_type = stat_type
        self.boost_amount = boost_amount
        self.boost_type = boost_type
        self._modifier_id = f"{passive_id}_conditional_boost"
        self._currently_applied = False
    
    def apply_effects(self, character):
        """Apply conditional stat boost"""
        if not self._currently_applied and hasattr(character, 'stats'):
            modifier = StatModifier(
                modifier_id=self._modifier_id,
                stat_type=self.stat_type,
                modifier_type=self.boost_type,
                value=self.boost_amount,
                source=f"passive_{self.passive_id}",
                layer=2
            )
            character.stats.add_modifier(modifier)
            self._currently_applied = True
            logger.debug("Applied conditional passive: %s", self.name)
    
    def remove_effects(self, character):
        """Remove conditional stat boost"""
        if self._currently_applied and hasattr(character, 'stats'):
            character.stats.remove_modifier(self._modifier_id)
            self._currently_applied = False
            logger.debug("Removed conditional passive: %s", self.name)
    
    def update(self, character, delta_time: float = 1.0):
        """Update passive state based on conditions"""
        is_active = self.is_active(character)
        
        if is_active and not self._currently_applied:
            self.apply_effects(character)
        elif not is_active and self._currently_applied:
            self.remove_effects(character)

class BerserkerRagePassive(ConditionalStatPassive):
    """Example: ATK boost when HP is low"""
    
    def __init__(self, atk_boost: float = 0.5, hp_threshold: float = 0.3):
        def low_hp_condition(character) -> bool:
            current_hp = character.get_stat("hp")
            max_hp = character.stats.get_base_stat("hp")
            return (current_hp / max_hp) <= hp_threshold
        
        super().__init__(
            passive_id="berserker_rage",
            name="Berserker Rage",
            description=f"Gain +{int(atk_boost * 100)}% ATK when HP is below {int(hp_threshold * 100)}%",
            stat_type=StatType.ATK,
            boost_amount=atk_boost,
            condition_func=low_hp_condition,
            boost_type=ModifierType.PERCENTAGE
        )

class ReactivePassive(BasePassive):
    """Base class for passives that react to events"""
    
    def __init__(self, passive_id: str, name: str, description: str, event_types: list):
        super().__init__(
            passive_id=passive_id,
            name=name,
            description=description,
            passive_type=PassiveType.SIGNATURE
        )
        self.event_types = event_types
        self.trigger_count = 0
    
    def on_event(self, event: GameEvent, character) -> GameEvent:
        """Handle relevant events"""
        if event.event_type in self.event_types:
            return self.handle_trigger(event, character)
        return event
    
    def handle_trigger(self, event: GameEvent, character) -> GameEvent:
        """Override this to implement specific reactive behavior"""
        self.trigger_count += 1
        self.times_triggered += 1
        return event

class CounterAttackPassive(ReactivePassive):
    """Example: Counter-attack when taking damage"""
    
    def __init__(self, counter_chance: float = 0.3, counter_damage: float = 0.5):
        super().__init__(
            passive_id="counter_attack",
            name="Counter Attack",
            description=f"{int(counter_chance * 100)}% chance to counter-attack for {int(counter_damage * 100)}% ATK when taking damage",
            event_types=["damage.taken"]
        )
        self.counter_chance = counter_chance
        self.counter_damage = counter_damage
    
    def apply_effects(self, character):
        """Counter-attack is reactive only, no persistent effects"""
        return  # Explicit return instead of pass
    
    def remove_effects(self, character):
        """Counter-attack is reactive only, no persistent effects"""
        return  # Explicit return instead of pass
    
    def handle_trigger(self, event: GameEvent, character) -> GameEvent:
        """Handle damage taken event for counter-attack"""
        super().handle_trigger(event, character)
        
        # Check if this character took damage
        if event.get_value("target_id") != character.character_id:
            return event
        
        # Check counter chance
        if random.random() > self.counter_chance:
            return event
        
        # Get the attacker
        attacker_id = event.get_value("source_id")
        if not attacker_id:
            return event
        
        # Calculate counter damage
        counter_dmg = character.get_stat("atk") * self.counter_damage
        
        # Create counter-attack event
        counter_event = GameEvent(
            event_type="damage.counter",
            source=character.character_id,
            data={
                "target_id": attacker_id,
                "damage_amount": counter_dmg,
                "damage_type": "physical",
                "source_passive": self.passive_id
            }
        )
        
        # Publish counter event (would be handled by battle system)
        event_bus.publish(counter_event)
        
        logger.info("Counter-attack triggered by %s for %f damage", character.character_id, counter_dmg)
        return event

class RegenerationPassive(ReactivePassive):
    """Example: Heal at start of each turn"""
    
    def __init__(self, heal_amount: float = 0.05, heal_type: str = "percentage"):
        super().__init__(
            passive_id="regeneration",
            name="Regeneration",
            description=f"Restore {int(heal_amount * 100) if heal_type == 'percentage' else heal_amount}{'% HP' if heal_type == 'percentage' else ' HP'} at start of turn",
            event_types=["turn.start"]
        )
        self.heal_amount = heal_amount
        self.heal_type = heal_type
    
    def apply_effects(self, character):
        """Regeneration is reactive only, no persistent effects"""
        return  # Explicit return instead of pass
    
    def remove_effects(self, character):
        """Regeneration is reactive only, no persistent effects"""
        return  # Explicit return instead of pass
    
    def handle_trigger(self, event: GameEvent, character) -> GameEvent:
        """Handle turn start for regeneration"""
        super().handle_trigger(event, character)
        
        # Check if it's this character's turn
        if event.get_value("character_id") != character.character_id:
            return event
        
        # Calculate healing
        if self.heal_type == "percentage":
            max_hp = character.stats.get_base_stat("hp")
            healing = max_hp * self.heal_amount
        else:
            healing = self.heal_amount
        
        # Apply healing
        if hasattr(character, 'heal'):
            actual_healing = character.heal(healing, character.character_id)
            logger.info("Regeneration healed %s for %f HP", character.character_id, actual_healing)
        
        return event

class CriticalStrikePassive(ReactivePassive):
    """Example: Increase critical hit chance and damage"""
    
    def __init__(self, crit_chance_bonus: float = 0.15, crit_damage_bonus: float = 0.3):
        super().__init__(
            passive_id="critical_strike_mastery",
            name="Critical Strike Mastery",
            description=f"+{crit_chance_bonus * 100}% crit chance, +{crit_damage_bonus * 100}% crit damage",
            event_types=["damage.before_calculation"]
        )
        self.crit_chance_bonus = crit_chance_bonus
        self.crit_damage_bonus = crit_damage_bonus
    
    def apply_effects(self, character):
        """Apply base critical chance boost"""
        if hasattr(character, 'stats'):
            # Add crit chance modifier (using LCK as base for crit)
            crit_modifier = StatModifier(
                modifier_id=f"{self.passive_id}_crit_chance",
                stat_type=StatType.LCK,
                modifier_type=ModifierType.PERCENTAGE,
                value=self.crit_chance_bonus,
                source=f"passive_{self.passive_id}",
                layer=2
            )
            character.stats.add_modifier(crit_modifier)
    
    def remove_effects(self, character):
        """Remove critical chance boost"""
        if hasattr(character, 'stats'):
            character.stats.remove_modifier(f"{self.passive_id}_crit_chance")
    
    def handle_trigger(self, event: GameEvent, character) -> GameEvent:
        """Handle damage calculation for critical strike bonus"""
        super().handle_trigger(event, character)
        
        # Check if this character is dealing damage
        if event.get_value("source_id") != character.character_id:
            return event
        
        # Check if it's a critical hit
        is_critical = event.get_value("is_critical", False)
        if is_critical:
            # Boost critical damage
            current_damage = event.get_value("damage_amount", 0)
            boosted_damage = current_damage * (1 + self.crit_damage_bonus)
            event.modify("damage_amount", boosted_damage)
            
            logger.debug("Critical strike mastery boosted damage from %f to %f", 
                        current_damage, boosted_damage)
        
        return event

# Factory functions for easy creation
def create_hp_boost_passive(boost_amount: float = 0.1) -> StatBoostPassive:
    """Create an HP boost passive"""
    return StatBoostPassive(
        passive_id="hp_up",
        name="HP Up",
        stat_type=StatType.HP,
        boost_amount=boost_amount
    )

def create_atk_boost_passive(boost_amount: float = 0.1) -> StatBoostPassive:
    """Create an ATK boost passive"""
    return StatBoostPassive(
        passive_id="attack_up",
        name="Attack Up",
        stat_type=StatType.ATK,
        boost_amount=boost_amount
    )

def create_spd_boost_passive(boost_amount: float = 0.15) -> StatBoostPassive:
    """Create a SPD boost passive"""
    return StatBoostPassive(
        passive_id="speed_up",
        name="Speed Up",
        stat_type=StatType.SPD,
        boost_amount=boost_amount
    )
