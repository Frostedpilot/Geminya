"""
Signature Abilities System

Implements unique character ultimate skills and passive abilities
as described in the design document.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json

from ..components.stats_component import StatModifier, StatType, ModifierType

logger = logging.getLogger(__name__)

class SignatureType(Enum):
    """Types of signature abilities"""
    SKILL = "skill"              # Triggered signature skills (once per game)
    PASSIVE = "passive"          # Always-on passive traits

class TriggerCondition(Enum):
    """Conditions that trigger signature abilities"""
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    HP_THRESHOLD = "hp_threshold"
    ALLY_DEATH = "ally_death"
    ENEMY_DEATH = "enemy_death"
    ENEMY_DODGE = "enemy_dodge"
    ALLY_DEFEATED_BY_CRIT = "ally_defeated_by_crit"
    CRITICAL_HIT = "critical_hit"
    SKILL_USE = "skill_use"
    DAMAGE_TAKEN = "damage_taken"
    MANUAL_ACTIVATE = "manual_activate"

@dataclass
class SignatureEffect:
    """Individual effect within a signature ability"""
    effect_type: str            # "damage", "heal", "stat_buff", "status_effect", "special"
    target_type: str            # "self", "ally", "enemy", "all_allies", "all_enemies"
    value: float = 0.0
    duration: Optional[int] = None
    stat_affected: Optional[str] = None
    scaling_stat: Optional[str] = None
    description: str = ""

@dataclass
class SignatureAbility:
    """Complete signature ability definition"""
    ability_id: str
    character_id: str
    name: str
    signature_type: SignatureType
    description: str
    effects: List[SignatureEffect]
    trigger_condition: TriggerCondition
    cooldown: int = 0           # Turns between uses
    cost: int = 0               # Resource cost (if applicable)
    trigger_value: float = 0.0  # Threshold value for triggers
    rarity: str = "common"      # "common", "rare", "legendary", "mythic"

class SignatureAbilitiesSystem:
    """Manages signature abilities for characters"""
    
    def __init__(self):
        self.abilities: Dict[str, SignatureAbility] = {}
        self.character_abilities: Dict[str, List[str]] = {}
        self.ability_cooldowns: Dict[str, int] = {}
        self._initialize_signature_abilities()
        logger.info("Initialized signature abilities system with %d abilities", len(self.abilities))
    
    def _initialize_signature_abilities(self):
        """Load signature abilities from the character_abilities.json file"""
        try:
            with open('data/character_abilities.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Helper function to convert string enums
            def get_signature_type(type_str: str) -> SignatureType:
                # Map from JSON type to our enum
                if type_str == "triggered_skill":
                    return SignatureType.SKILL
                elif type_str in ["turn_start_trigger", "conditional_stats", "immunity_and_quirk", "round_end_trigger"]:
                    return SignatureType.PASSIVE
                else:
                    return SignatureType.SKILL  # Default fallback
            
            def get_trigger_condition(trigger_str: str) -> TriggerCondition:
                mapping = {
                    "hp_threshold": TriggerCondition.HP_THRESHOLD,
                    "enemy_dodge": TriggerCondition.ENEMY_DODGE,
                    "ally_defeated": TriggerCondition.ALLY_DEATH,
                    "ally_defeated_by_crit": TriggerCondition.ALLY_DEFEATED_BY_CRIT,
                    "turn_start": TriggerCondition.TURN_START,
                    "turn_end": TriggerCondition.TURN_END,
                    "critical_hit": TriggerCondition.CRITICAL_HIT,
                    "skill_use": TriggerCondition.SKILL_USE,
                    "damage_taken": TriggerCondition.DAMAGE_TAKEN,
                    "manual_activate": TriggerCondition.MANUAL_ACTIVATE
                }
                return mapping.get(trigger_str, TriggerCondition.MANUAL_ACTIVATE)
            
            # Process each character's abilities
            for character_id, char_data in data.items():
                # Process signature skills
                for skill_data in char_data.get('signature_abilities', []):
                    try:
                        # Create effects list
                        effects = []
                        for effect_data in skill_data.get('effects', []):
                            effect = SignatureEffect(
                                effect_type=effect_data.get('effect_type', 'special'),
                                target_type=effect_data.get('target_type', 'self'),
                                value=effect_data.get('base_damage', effect_data.get('scaling_multiplier', effect_data.get('magnitude', 0.0))),
                                duration=effect_data.get('duration'),
                                stat_affected=effect_data.get('stat_affected'),
                                scaling_stat=effect_data.get('scaling'),
                                description=effect_data.get('description', skill_data.get('description', ''))
                            )
                            effects.append(effect)
                        
                        # Create signature skill
                        ability = SignatureAbility(
                            ability_id=skill_data['ability_id'],
                            character_id=character_id,
                            name=skill_data['name'],
                            signature_type=SignatureType.SKILL,  # All in signature_abilities are skills
                            description=skill_data['description'],
                            effects=effects,
                            trigger_condition=get_trigger_condition(skill_data.get('trigger_condition', 'manual_activate')),
                            cooldown=skill_data.get('cooldown', -1),  # -1 means once per game
                            cost=skill_data.get('cost', 0),
                            trigger_value=skill_data.get('trigger_value', 0.0),
                            rarity=skill_data.get('rarity', 'common')
                        )
                        
                        self.abilities[ability.ability_id] = ability
                        
                        # Map character to abilities
                        if character_id not in self.character_abilities:
                            self.character_abilities[character_id] = []
                        self.character_abilities[character_id].append(ability.ability_id)
                        
                    except KeyError as e:
                        logger.warning("Missing key in signature skill data for %s: %s", character_id, e)
                        continue
                
                # Process signature passives
                for passive_data in char_data.get('signature_passives', []):
                    try:
                        # Create effects list
                        effects = []
                        for effect_data in passive_data.get('effects', []):
                            effect = SignatureEffect(
                                effect_type=effect_data.get('effect_type', 'stat_modifier'),
                                target_type=effect_data.get('target_type', 'self'),
                                value=effect_data.get('value', effect_data.get('effect_magnitude', 0.0)),
                                duration=effect_data.get('duration'),
                                stat_affected=effect_data.get('stat_affected'),
                                scaling_stat=None,
                                description=effect_data.get('description', passive_data.get('description', ''))
                            )
                            effects.append(effect)
                        
                        # Create signature passive
                        ability = SignatureAbility(
                            ability_id=passive_data['passive_id'],
                            character_id=character_id,
                            name=passive_data['name'],
                            signature_type=SignatureType.PASSIVE,  # All in signature_passives are passives
                            description=passive_data['description'],
                            effects=effects,
                            trigger_condition=TriggerCondition.TURN_START,  # Default for passives
                            cooldown=0,  # Passives don't have cooldowns
                            cost=0,
                            trigger_value=0.0,
                            rarity=passive_data.get('rarity', 'common')
                        )
                        
                        self.abilities[ability.ability_id] = ability
                        
                        # Map character to abilities
                        if character_id not in self.character_abilities:
                            self.character_abilities[character_id] = []
                        self.character_abilities[character_id].append(ability.ability_id)
                        
                    except KeyError as e:
                        logger.warning("Missing key in signature passive data for %s: %s", character_id, e)
                        continue
                        
            logger.info("Loaded %d signature abilities from JSON", len(self.abilities))
            
        except FileNotFoundError:
            logger.error("Character abilities file not found: data/character_abilities.json")
            self._create_fallback_abilities()
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in character abilities file: %s", e)
            self._create_fallback_abilities()
        except KeyError as e:
            logger.error("Missing key in character abilities file: %s", e)
            self._create_fallback_abilities()
    
    def _create_fallback_abilities(self):
        """Create basic fallback abilities if JSON loading fails"""
        logger.warning("Creating fallback signature abilities")
        
        # Basic fallback ability
        fallback_ability = SignatureAbility(
            ability_id="emergency_skill",
            character_id="generic",
            name="Emergency Skill",
            signature_type=SignatureType.SKILL,
            description="Basic emergency ability when JSON loading fails",
            effects=[
                SignatureEffect(
                    effect_type="damage",
                    target_type="enemy",
                    value=100.0,
                    description="Deal basic damage"
                )
            ],
            trigger_condition=TriggerCondition.MANUAL_ACTIVATE,
            cooldown=-1,
            rarity="common"
        )
        
        self.abilities["emergency_skill"] = fallback_ability
    
    def assign_signature_ability(self, character_id: str, ability_id: str) -> bool:
        """Assign a signature ability to a character"""
        if ability_id not in self.abilities:
            logger.warning("Unknown signature ability: %s", ability_id)
            return False
        
        if character_id not in self.character_abilities:
            self.character_abilities[character_id] = []
        
        if ability_id not in self.character_abilities[character_id]:
            self.character_abilities[character_id].append(ability_id)
            logger.info("Assigned signature ability '%s' to character '%s'", ability_id, character_id)
            return True
        
        return False
    
    def get_character_abilities(self, character_id: str) -> List[SignatureAbility]:
        """Get all signature abilities for a character"""
        ability_ids = self.character_abilities.get(character_id, [])
        return [self.abilities[aid] for aid in ability_ids if aid in self.abilities]
    
    def check_trigger_conditions(self, character, battle_state: Dict) -> List[SignatureAbility]:
        """Check which signature abilities should trigger"""
        triggered_abilities = []
        character_abilities = self.get_character_abilities(character.character_id)
        
        for ability in character_abilities:
            if self._is_ability_triggered(character, ability, battle_state):
                if not self._is_on_cooldown(character.character_id, ability.ability_id):
                    triggered_abilities.append(ability)
        
        return triggered_abilities
    
    def _is_ability_triggered(self, character, ability: SignatureAbility, battle_state: Dict) -> bool:
        """Check if specific ability trigger condition is met"""
        trigger = ability.trigger_condition
        
        if trigger == TriggerCondition.HP_THRESHOLD:
            current_hp_ratio = getattr(character, 'current_hp', 100) / getattr(character, 'max_hp', 100)
            return current_hp_ratio <= ability.trigger_value
        
        elif trigger == TriggerCondition.TURN_START:
            return battle_state.get('phase') == 'turn_start'
        
        elif trigger == TriggerCondition.TURN_END:
            return battle_state.get('phase') == 'turn_end'
        
        elif trigger == TriggerCondition.ALLY_DEATH:
            return battle_state.get('ally_died', False)
        
        elif trigger == TriggerCondition.ENEMY_DEATH:
            return battle_state.get('enemy_died', False)
        
        elif trigger == TriggerCondition.CRITICAL_HIT:
            return battle_state.get('critical_hit', False)
        
        elif trigger == TriggerCondition.DAMAGE_TAKEN:
            return battle_state.get('damage_taken', 0) > 0
        
        elif trigger == TriggerCondition.MANUAL_ACTIVATE:
            return battle_state.get('manual_trigger', {}).get(ability.ability_id, False)
        
        return False
    
    def _is_on_cooldown(self, character_id: str, ability_id: str) -> bool:
        """Check if ability is on cooldown"""
        cooldown_key = f"{character_id}_{ability_id}"
        return self.ability_cooldowns.get(cooldown_key, 0) > 0
    
    def activate_signature_ability(self, character, ability: SignatureAbility, targets: Optional[List] = None) -> Dict[str, Any]:
        """Activate a signature ability and return results"""
        if self._is_on_cooldown(character.character_id, ability.ability_id):
            return {"success": False, "reason": "ability_on_cooldown"}
        
        # Check resource costs
        if ability.cost > 0:
            current_resource = getattr(character, 'current_mana', 0)
            if current_resource < ability.cost:
                return {"success": False, "reason": "insufficient_resources"}
        
        # Apply effects
        results = {
            "success": True,
            "ability_name": ability.name,
            "effects_applied": [],
            "targets_affected": []
        }
        
        for effect in ability.effects:
            effect_result = self._apply_signature_effect(character, effect, targets)
            results["effects_applied"].append(effect_result)
        
        # Set cooldown
        cooldown_key = f"{character.character_id}_{ability.ability_id}"
        self.ability_cooldowns[cooldown_key] = ability.cooldown
        
        # Consume resources
        if ability.cost > 0:
            setattr(character, 'current_mana', getattr(character, 'current_mana', 0) - ability.cost)
        
        logger.info("Activated signature ability '%s' for character '%s'", 
                   ability.name, character.character_id)
        return results
    
    def _apply_signature_effect(self, character, effect: SignatureEffect, targets: Optional[List] = None) -> Dict[str, Any]:
        """Apply individual signature effect"""
        result = {
            "effect_type": effect.effect_type,
            "description": effect.description,
            "value": effect.value
        }
        
        if effect.effect_type == "stat_buff":
            self._apply_stat_buff_effect(character, effect, targets)
        elif effect.effect_type == "damage":
            result["damage_dealt"] = self._apply_damage_effect(character, effect, targets)
        elif effect.effect_type == "heal":
            result["healing_done"] = self._apply_heal_effect(character, effect, targets)
        elif effect.effect_type == "status_effect":
            self._apply_status_effect(character, effect, targets)
        elif effect.effect_type == "special":
            self._apply_special_effect(character, effect, targets)
        
        return result
    
    def _apply_stat_buff_effect(self, character, effect: SignatureEffect, targets: Optional[List] = None):
        """Apply stat buff from signature ability"""
        if not effect.stat_affected:
            return
        
        # Determine targets based on effect target type
        affected_characters = self._get_effect_targets(character, effect.target_type, targets)
        
        for target in affected_characters:
            if hasattr(target, 'stats'):
                modifier = StatModifier(
                    modifier_id=f"signature_{character.character_id}_{effect.stat_affected}",
                    stat_type=getattr(StatType, effect.stat_affected.upper()),
                    modifier_type=ModifierType.PERCENTAGE,
                    value=effect.value,
                    source="signature_ability",
                    layer=4,  # Signature abilities have high priority
                    duration=effect.duration
                )
                target.stats.add_modifier(modifier)
    
    def _apply_damage_effect(self, character, effect: SignatureEffect, targets: Optional[List] = None) -> float:
        """Apply damage from signature ability"""
        total_damage = 0.0
        affected_characters = self._get_effect_targets(character, effect.target_type, targets)
        
        for target in affected_characters:
            base_damage = effect.value
            
            # Scale with character stats if specified
            if effect.scaling_stat and hasattr(character, 'stats'):
                scaling_value = getattr(character.stats, effect.scaling_stat, 100)
                base_damage = (base_damage / 100.0) * scaling_value
            
            # Apply damage (in real implementation, this would go through damage calculation)
            damage_dealt = base_damage
            total_damage += damage_dealt
            
            # Reduce target HP (simplified)
            if hasattr(target, 'current_hp'):
                target.current_hp = max(0, target.current_hp - damage_dealt)
        
        return total_damage
    
    def _apply_heal_effect(self, character, effect: SignatureEffect, targets: Optional[List] = None) -> float:
        """Apply healing from signature ability"""
        total_healing = 0.0
        affected_characters = self._get_effect_targets(character, effect.target_type, targets)
        
        for target in affected_characters:
            heal_amount = effect.value
            
            if effect.scaling_stat and hasattr(character, 'stats'):
                scaling_value = getattr(character.stats, effect.scaling_stat, 100)
                heal_amount = (heal_amount / 100.0) * scaling_value
            
            # Apply healing
            if hasattr(target, 'current_hp') and hasattr(target, 'max_hp'):
                target.current_hp = min(target.max_hp, target.current_hp + heal_amount)
                total_healing += heal_amount
        
        return total_healing
    
    def _apply_status_effect(self, character, effect: SignatureEffect, targets: Optional[List] = None):
        """Apply status effect from signature ability"""
        # In full implementation, this would integrate with status effect system
        affected_characters = self._get_effect_targets(character, effect.target_type, targets)
        logger.debug("Applied status effect to %d characters: %s", len(affected_characters), effect.description)
    
    def _apply_special_effect(self, character, effect: SignatureEffect, targets: Optional[List] = None):
        """Apply special effect from signature ability"""
        # Handle unique mechanics
        affected_characters = self._get_effect_targets(character, effect.target_type, targets)
        logger.debug("Applied special effect to %d characters: %s", len(affected_characters), effect.description)
    
    def _get_effect_targets(self, character, target_type: str, targets: Optional[List] = None) -> List:
        """Determine targets for an effect based on target type"""
        if target_type == "self":
            return [character]
        elif target_type == "all_allies" and targets:
            return [t for t in targets if getattr(t, 'team', None) == getattr(character, 'team', None)]
        elif target_type == "all_enemies" and targets:
            return [t for t in targets if getattr(t, 'team', None) != getattr(character, 'team', None)]
        elif targets:
            return targets
        else:
            return [character]
    
    def update_cooldowns(self):
        """Update all ability cooldowns (call each turn)"""
        for key in list(self.ability_cooldowns.keys()):
            if self.ability_cooldowns[key] > 0:
                self.ability_cooldowns[key] -= 1
                if self.ability_cooldowns[key] <= 0:
                    del self.ability_cooldowns[key]
    
    def get_available_ultimates(self, character_id: str) -> List[SignatureAbility]:
        """Get ultimate abilities that can be manually activated"""
        character_abilities = self.get_character_abilities(character_id)
        available = []
        
        for ability in character_abilities:
            if (ability.signature_type == SignatureType.SKILL and 
                ability.trigger_condition == TriggerCondition.MANUAL_ACTIVATE and
                not self._is_on_cooldown(character_id, ability.ability_id)):
                available.append(ability)
        
        return available
    
    def get_all_abilities(self) -> List[SignatureAbility]:
        """Get all signature abilities"""
        return list(self.abilities.values())

# Global signature abilities system instance
signature_abilities_system = SignatureAbilitiesSystem()
