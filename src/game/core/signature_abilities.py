"""
Signature Abilities System

Implements unique character ultimate skills and passive abilities
as described in the design document.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

from ..components.stats_component import StatModifier, StatType, ModifierType

logger = logging.getLogger(__name__)

class SignatureType(Enum):
    """Types of signature abilities"""
    ULTIMATE = "ultimate"        # Active ultimate skill
    PASSIVE = "passive"          # Passive trait
    AWAKENING = "awakening"      # Triggered ability
    SPECIAL = "special"          # Unique mechanic

class TriggerCondition(Enum):
    """Conditions that trigger signature abilities"""
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    HP_THRESHOLD = "hp_threshold"
    ALLY_DEATH = "ally_death"
    ENEMY_DEATH = "enemy_death"
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
        """Initialize signature abilities for various characters"""
        
        # Example signature abilities from different anime series
        abilities = [
            # Attack on Titan - Eren Jaeger
            SignatureAbility(
                ability_id="titan_transformation",
                character_id="eren_jaeger",
                name="Titan Transformation",
                signature_type=SignatureType.AWAKENING,
                description="Transform into Attack Titan when HP falls below 25%",
                effects=[
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="self",
                        stat_affected="atk",
                        value=1.5,
                        duration=5,
                        description="ATK increased by 150% for 5 turns"
                    ),
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="self",
                        stat_affected="hp",
                        value=0.5,
                        description="Restore 50% HP"
                    )
                ],
                trigger_condition=TriggerCondition.HP_THRESHOLD,
                trigger_value=0.25,
                cooldown=10,
                rarity="legendary"
            ),
            
            # Re:Zero - Subaru Natsuki
            SignatureAbility(
                ability_id="return_by_death",
                character_id="subaru_natsuki",
                name="Return by Death",
                signature_type=SignatureType.SPECIAL,
                description="Revive with full HP when killed, gaining knowledge of enemy patterns",
                effects=[
                    SignatureEffect(
                        effect_type="special",
                        target_type="self",
                        description="Revive with full HP"
                    ),
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="self",
                        stat_affected="int",
                        value=0.3,
                        duration=99,
                        description="Permanent +30% INT from gained knowledge"
                    )
                ],
                trigger_condition=TriggerCondition.HP_THRESHOLD,
                trigger_value=0.0,  # When HP reaches 0
                cooldown=1,  # Can only be used once per battle
                rarity="mythic"
            ),
            
            # Demon Slayer - Tanjiro Kamado
            SignatureAbility(
                ability_id="hinokami_kagura",
                character_id="tanjiro_kamado",
                name="Hinokami Kagura",
                signature_type=SignatureType.ULTIMATE,
                description="Unleash the power of sun breathing",
                effects=[
                    SignatureEffect(
                        effect_type="damage",
                        target_type="all_enemies",
                        value=300.0,
                        scaling_stat="atk",
                        description="Deal 300% ATK damage to all enemies"
                    ),
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="self",
                        stat_affected="spd",
                        value=0.5,
                        duration=3,
                        description="SPD increased by 50% for 3 turns"
                    )
                ],
                trigger_condition=TriggerCondition.MANUAL_ACTIVATE,
                cooldown=5,
                cost=50,
                rarity="legendary"
            ),
            
            # K-On! - Yui Hirasawa
            SignatureAbility(
                ability_id="musical_inspiration",
                character_id="yui_hirasawa",
                name="Musical Inspiration",
                signature_type=SignatureType.PASSIVE,
                description="Inspire allies with music, boosting their performance",
                effects=[
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="all_allies",
                        stat_affected="int",
                        value=0.15,
                        description="All allies gain +15% INT"
                    ),
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="all_allies",
                        stat_affected="lck",
                        value=0.20,
                        description="All allies gain +20% LCK"
                    )
                ],
                trigger_condition=TriggerCondition.TURN_START,
                rarity="common"
            ),
            
            # Jujutsu Kaisen - Satoru Gojo
            SignatureAbility(
                ability_id="unlimited_void",
                character_id="satoru_gojo",
                name="Unlimited Void",
                signature_type=SignatureType.ULTIMATE,
                description="Trap enemies in infinite information space",
                effects=[
                    SignatureEffect(
                        effect_type="status_effect",
                        target_type="all_enemies",
                        description="Stun all enemies for 2 turns"
                    ),
                    SignatureEffect(
                        effect_type="damage",
                        target_type="all_enemies",
                        value=500.0,
                        scaling_stat="mag",
                        description="Deal 500% MAG damage to all enemies"
                    )
                ],
                trigger_condition=TriggerCondition.MANUAL_ACTIVATE,
                cooldown=8,
                cost=80,
                rarity="mythic"
            ),
            
            # Konosuba - Megumin
            SignatureAbility(
                ability_id="explosion_magic",
                character_id="megumin",
                name="Explosion Magic",
                signature_type=SignatureType.ULTIMATE,
                description="Ultimate explosion magic that drains all mana",
                effects=[
                    SignatureEffect(
                        effect_type="damage",
                        target_type="all_enemies",
                        value=800.0,
                        scaling_stat="mag",
                        description="Deal 800% MAG damage to all enemies"
                    ),
                    SignatureEffect(
                        effect_type="status_effect",
                        target_type="self",
                        description="Become exhausted (cannot act next turn)"
                    )
                ],
                trigger_condition=TriggerCondition.MANUAL_ACTIVATE,
                cooldown=3,
                cost=100,  # All mana
                rarity="legendary"
            ),
            
            # Generic abilities for common archetypes
            SignatureAbility(
                ability_id="berserker_rage",
                character_id="generic_berserker",
                name="Berserker Rage",
                signature_type=SignatureType.AWAKENING,
                description="Enter berserk state when heavily damaged",
                effects=[
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="self",
                        stat_affected="atk",
                        value=0.75,
                        duration=4,
                        description="ATK increased by 75% for 4 turns"
                    ),
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="self",
                        stat_affected="spd",
                        value=0.50,
                        duration=4,
                        description="SPD increased by 50% for 4 turns"
                    )
                ],
                trigger_condition=TriggerCondition.HP_THRESHOLD,
                trigger_value=0.30,
                cooldown=6,
                rarity="rare"
            ),
            
            SignatureAbility(
                ability_id="mage_mastery",
                character_id="generic_mage",
                name="Arcane Mastery",
                signature_type=SignatureType.PASSIVE,
                description="Deep understanding of magical arts",
                effects=[
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="self",
                        stat_affected="mag",
                        value=0.25,
                        description="MAG increased by 25%"
                    ),
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="self",
                        stat_affected="spr",
                        value=0.20,
                        description="SPR increased by 20%"
                    )
                ],
                trigger_condition=TriggerCondition.TURN_START,
                rarity="common"
            ),
            
            SignatureAbility(
                ability_id="guardian_shield",
                character_id="generic_tank",
                name="Guardian's Shield",
                signature_type=SignatureType.AWAKENING,
                description="Protect allies when they are in danger",
                effects=[
                    SignatureEffect(
                        effect_type="stat_buff",
                        target_type="all_allies",
                        stat_affected="vit",
                        value=0.40,
                        duration=3,
                        description="All allies gain +40% VIT for 3 turns"
                    ),
                    SignatureEffect(
                        effect_type="special",
                        target_type="all_allies",
                        description="Redirect next attack to self"
                    )
                ],
                trigger_condition=TriggerCondition.ALLY_DEATH,
                cooldown=5,
                rarity="rare"
            )
        ]
        
        # Register abilities
        for ability in abilities:
            self.abilities[ability.ability_id] = ability
            
            # Map character to abilities
            if ability.character_id not in self.character_abilities:
                self.character_abilities[ability.character_id] = []
            self.character_abilities[ability.character_id].append(ability.ability_id)
    
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
            if (ability.signature_type == SignatureType.ULTIMATE and 
                ability.trigger_condition == TriggerCondition.MANUAL_ACTIVATE and
                not self._is_on_cooldown(character_id, ability.ability_id)):
                available.append(ability)
        
        return available
    
    def get_all_abilities(self) -> List[SignatureAbility]:
        """Get all signature abilities"""
        return list(self.abilities.values())

# Global signature abilities system instance
signature_abilities_system = SignatureAbilitiesSystem()
