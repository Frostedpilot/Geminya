"""
Skill Implementations

This module contains concrete implementations of common skills.
These serve as examples and basic implementations that can be extended.
"""

from typing import Dict, List, Any
import logging

from .abilities_component import (
    BaseSkill, SkillType, TargetType, SkillCost, SkillState
)
from ..core.event_system import GameEvent, event_bus

logger = logging.getLogger(__name__)

class BasicAttackSkill(BaseSkill):
    """Universal basic attack skill that all characters have"""
    
    def __init__(self):
        super().__init__(
            skill_id="basic_attack",
            name="Basic Attack",
            description="A simple attack that deals damage based on ATK stat",
            skill_type=SkillType.BASIC_ATTACK,
            target_type=TargetType.SINGLE_ENEMY,
            cooldown=0,  # No cooldown
            cost=SkillCost(),  # No cost
            priority=10  # Low priority
        )
    
    def validate_execution(self, caster, targets: List, battle_context) -> bool:
        """Validate basic attack can be executed"""
        # Basic attack can always be used if there are valid targets
        return len(targets) > 0
    
    def execute_effects(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """Execute basic attack effects"""
        result = {
            "success": True,
            "damage_dealt": 0.0,
            "healing_done": 0.0,
            "effects": []
        }
        
        if not targets:
            result["success"] = False
            return result
        
        target = targets[0]  # Single target
        
        # Calculate damage: 100% of ATK stat
        base_damage = caster.get_stat("atk")
        
        # Apply damage
        if hasattr(target, 'take_damage'):
            actual_damage = target.take_damage(base_damage, "physical", caster.character_id)
            result["damage_dealt"] = actual_damage
            result["effects"].append({
                "type": "damage",
                "target": target.character_id if hasattr(target, 'character_id') else str(target),
                "amount": actual_damage
            })
        
        return result

class HealSkill(BaseSkill):
    """Example healing skill"""
    
    def __init__(self, heal_amount: float = 50.0, mag_scaling: float = 0.8):
        super().__init__(
            skill_id="heal",
            name="Heal",
            description=f"Restores {heal_amount} + {mag_scaling * 100}% MAG as HP to target ally",
            skill_type=SkillType.NORMAL,
            target_type=TargetType.SINGLE_ALLY,
            cooldown=3,
            cost=SkillCost(action_cost=50),
            priority=80
        )
        self.heal_amount = heal_amount
        self.mag_scaling = mag_scaling
    
    def validate_execution(self, caster, targets: List, battle_context) -> bool:
        """Validate heal can be executed"""
        return len(targets) > 0 and all(hasattr(t, 'heal') for t in targets)
    
    def execute_effects(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """Execute healing effects"""
        result = {
            "success": True,
            "damage_dealt": 0.0,
            "healing_done": 0.0,
            "effects": []
        }
        
        if not targets:
            result["success"] = False
            return result
        
        target = targets[0]
        
        # Calculate healing: base + MAG scaling
        healing = self.heal_amount + (caster.get_stat("mag") * self.mag_scaling)
        
        # Apply healing
        if hasattr(target, 'heal'):
            actual_healing = target.heal(healing, caster.character_id)
            result["healing_done"] = actual_healing
            result["effects"].append({
                "type": "healing",
                "target": target.character_id if hasattr(target, 'character_id') else str(target),
                "amount": actual_healing
            })
        
        return result

class FireballSkill(BaseSkill):
    """Example magical damage skill with status effect"""
    
    def __init__(self, base_damage: float = 80.0, mag_scaling: float = 1.2, burn_chance: float = 0.3):
        super().__init__(
            skill_id="fireball",
            name="Fireball",
            description=f"Deals {base_damage} + {mag_scaling * 100}% MAG magical damage. {burn_chance * 100}% chance to burn.",
            skill_type=SkillType.NORMAL,
            target_type=TargetType.SINGLE_ENEMY,
            cooldown=2,
            cost=SkillCost(action_cost=80),
            priority=70
        )
        self.base_damage = base_damage
        self.mag_scaling = mag_scaling
        self.burn_chance = burn_chance
    
    def validate_execution(self, caster, targets: List, battle_context) -> bool:
        """Validate fireball can be executed"""
        return len(targets) > 0 and all(hasattr(t, 'take_damage') for t in targets)
    
    def execute_effects(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """Execute fireball effects"""
        result = {
            "success": True,
            "damage_dealt": 0.0,
            "healing_done": 0.0,
            "effects": []
        }
        
        if not targets:
            result["success"] = False
            return result
        
        target = targets[0]
        
        # Calculate damage: base + MAG scaling
        damage = self.base_damage + (caster.get_stat("mag") * self.mag_scaling)
        
        # Apply damage
        if hasattr(target, 'take_damage'):
            actual_damage = target.take_damage(damage, "magical", caster.character_id)
            result["damage_dealt"] = actual_damage
            result["effects"].append({
                "type": "damage",
                "target": target.character_id if hasattr(target, 'character_id') else str(target),
                "amount": actual_damage,
                "damage_type": "magical"
            })
        
        # Apply burn effect if chance succeeds
        import random
        if random.random() < self.burn_chance and hasattr(target, 'apply_effect'):
            # Create burn status effect
            from .effects_component import StatusEffect, EffectType
            burn_effect = StatusEffect(
                effect_id="burn_from_fireball",
                effect_type=EffectType.DEBUFF,
                name="Burn",
                description="Takes fire damage over time",
                source=caster.character_id,
                duration=3,
                power=15.0
            )
            
            if target.apply_effect(burn_effect):
                result["effects"].append({
                    "type": "status_effect",
                    "target": target.character_id if hasattr(target, 'character_id') else str(target),
                    "effect": "burn",
                    "duration": 3
                })
        
        return result

class BuffSkill(BaseSkill):
    """Example buff skill that enhances ally stats"""
    
    def __init__(self, stat_boost: float = 0.25, duration: int = 5):
        super().__init__(
            skill_id="battle_fury",
            name="Battle Fury",
            description=f"Increases ally's ATK by {stat_boost * 100}% for {duration} turns",
            skill_type=SkillType.NORMAL,
            target_type=TargetType.SINGLE_ALLY,
            cooldown=4,
            cost=SkillCost(action_cost=60),
            priority=60
        )
        self.stat_boost = stat_boost
        self.duration = duration
    
    def validate_execution(self, caster, targets: List, battle_context) -> bool:
        """Validate buff can be executed"""
        return len(targets) > 0 and all(hasattr(t, 'apply_effect') for t in targets)
    
    def execute_effects(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """Execute buff effects"""
        result = {
            "success": True,
            "damage_dealt": 0.0,
            "healing_done": 0.0,
            "effects": []
        }
        
        if not targets:
            result["success"] = False
            return result
        
        target = targets[0]
        
        # Create ATK buff using stats modifier
        if hasattr(target, 'stats') and hasattr(target.stats, 'add_modifier'):
            from .stats_component import StatModifier, StatType, ModifierType
            
            buff_modifier = StatModifier(
                modifier_id="battle_fury_buff",
                stat_type=StatType.ATK,
                modifier_type=ModifierType.PERCENTAGE,
                value=self.stat_boost,
                source=f"skill_{self.skill_id}",
                layer=3,  # Temporary layer
                duration=self.duration
            )
            
            target.stats.add_modifier(buff_modifier)
            result["effects"].append({
                "type": "stat_buff",
                "target": target.character_id if hasattr(target, 'character_id') else str(target),
                "stat": "ATK",
                "amount": f"+{self.stat_boost * 100}%",
                "duration": self.duration
            })
        
        return result
