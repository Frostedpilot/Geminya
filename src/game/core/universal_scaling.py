"""
Universal Scaling Formula System

Implements the complex scaling system described in the design document
for skills, effects, and damage calculations.
"""

from typing import Dict
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

@dataclass
class ScalingParameters:
    """Parameters for the universal scaling formula"""
    floor: float          # Minimum output value
    ceiling: float        # Maximum output value (for buffs/debuffs)
    softcap_1: float     # First softcap threshold  
    softcap_2: float     # Second softcap threshold
    post_cap_rate: float # Multiplier after second softcap
    
class PotencyType(Enum):
    """Types of potency calculations"""
    PHYSICAL_DAMAGE = "physical_damage"
    MAGICAL_DAMAGE = "magical_damage"
    HEALING = "healing"
    BUFF_DEBUFF = "buff_debuff"

class UniversalScaling:
    """Handles universal scaling formula calculations"""
    
    @staticmethod
    def calculate_potency_value(
        caster_stats: Dict[str, float],
        target_stats: Dict[str, float],
        potency_type: PotencyType,
        skill_multiplier: float = 1.0
    ) -> float:
        """Calculate the base potency value before scaling"""
        
        if potency_type == PotencyType.PHYSICAL_DAMAGE:
            # Initial Physical Damage: (Attacker's ATK * SkillMultiplier) * (1 - (Target's VIT)/(150 + Target's VIT))
            base_damage = caster_stats.get("atk", 0) * skill_multiplier
            target_vit = target_stats.get("vit", 0)
            damage_reduction = target_vit / (150 + target_vit)
            potency = base_damage * (1 - damage_reduction)
            
        elif potency_type == PotencyType.MAGICAL_DAMAGE:
            # Initial Magical Damage: (Attacker's MAG * SkillMultiplier) * (1 - (Target's VIT * 0.6 + Target's SPR * 0.4)/(150 + Target's VIT * 0.6 + Target's SPR * 0.4))
            base_damage = caster_stats.get("mag", 0) * skill_multiplier
            target_vit = target_stats.get("vit", 0)
            target_spr = target_stats.get("spr", 0)
            combined_defense = (target_vit * 0.6) + (target_spr * 0.4)
            damage_reduction = combined_defense / (150 + combined_defense)
            potency = base_damage * (1 - damage_reduction)
            
        elif potency_type == PotencyType.HEALING:
            # Heal Potency: (Caster's INT * 0.5) + (Caster's SPR * 1.25)
            caster_int = caster_stats.get("int", 0)
            caster_spr = caster_stats.get("spr", 0)
            potency = (caster_int * 0.5) + (caster_spr * 1.25)
            
        elif potency_type == PotencyType.BUFF_DEBUFF:
            # Effect Potency: Caster's INT
            potency = caster_stats.get("int", 0)
            
        else:
            logger.warning("Unknown potency type: %s", potency_type)
            potency = 0.0
        
        # Ensure minimum of 1 for damage
        if potency_type in [PotencyType.PHYSICAL_DAMAGE, PotencyType.MAGICAL_DAMAGE]:
            potency = max(potency, 1.0)
        
        logger.debug("Calculated potency value: %.2f (type: %s)", potency, potency_type.value)
        return potency
    
    @staticmethod
    def apply_scaling_formula(
        potency_value: float,
        scaling_params: ScalingParameters,
        is_buff_debuff: bool = False
    ) -> float:
        """Apply the universal scaling formula"""
        
        floor = scaling_params.floor
        sc1 = scaling_params.softcap_1
        sc2 = scaling_params.softcap_2
        post_cap_rate = scaling_params.post_cap_rate
        ceiling = scaling_params.ceiling
        
        # Apply scaling formula
        if potency_value <= sc1:
            # If PotencyValue ≤ SC1: FinalValue = Floor
            final_value = floor
            
        elif sc1 < potency_value <= sc2:
            # If SC1 < PotencyValue ≤ SC2: FinalValue = Floor + (PotencyValue - SC1)
            final_value = floor + (potency_value - sc1)
            
        else:
            # If PotencyValue > SC2: FinalValue = (Floor + (SC2 - SC1)) + ((PotencyValue - SC2) * PostCapRate)
            final_value = (floor + (sc2 - sc1)) + ((potency_value - sc2) * post_cap_rate)
        
        # For buffs/debuffs, apply ceiling cap
        if is_buff_debuff and ceiling > 0:
            final_value = min(final_value, ceiling)
        
        logger.debug("Applied scaling: %.2f -> %.2f (floor: %.2f, sc1: %.2f, sc2: %.2f)", 
                    potency_value, final_value, floor, sc1, sc2)
        
        return final_value
    
    @staticmethod
    def calculate_final_damage(
        caster_stats: Dict[str, float],
        target_stats: Dict[str, float],
        scaling_params: ScalingParameters,
        skill_multiplier: float = 1.0,
        is_magical: bool = False,
        elemental_modifier: float = 1.0,
        critical_modifier: float = 1.0
    ) -> float:
        """Calculate final damage using the complete formula"""
        
        # Step 1: Calculate potency value
        potency_type = PotencyType.MAGICAL_DAMAGE if is_magical else PotencyType.PHYSICAL_DAMAGE
        potency_value = UniversalScaling.calculate_potency_value(
            caster_stats, target_stats, potency_type, skill_multiplier
        )
        
        # Step 2: Apply scaling formula
        scaled_damage = UniversalScaling.apply_scaling_formula(
            potency_value, scaling_params, is_buff_debuff=False
        )
        
        # Step 3: Apply final modifiers
        final_damage = scaled_damage * elemental_modifier * critical_modifier
        
        logger.debug("Final damage calculation: %.2f (scaled: %.2f, elemental: %.2f, crit: %.2f)",
                    final_damage, scaled_damage, elemental_modifier, critical_modifier)
        
        return final_damage
    
    @staticmethod
    def calculate_healing(
        caster_stats: Dict[str, float],
        scaling_params: ScalingParameters
    ) -> float:
        """Calculate healing amount"""
        
        # Calculate healing potency
        potency_value = UniversalScaling.calculate_potency_value(
            caster_stats, {}, PotencyType.HEALING
        )
        
        # Apply scaling
        final_healing = UniversalScaling.apply_scaling_formula(
            potency_value, scaling_params, is_buff_debuff=False
        )
        
        logger.debug("Healing calculation: %.2f -> %.2f", potency_value, final_healing)
        return final_healing
    
    @staticmethod
    def calculate_effect_strength(
        caster_stats: Dict[str, float],
        scaling_params: ScalingParameters
    ) -> float:
        """Calculate buff/debuff effect strength"""
        
        # Calculate effect potency
        potency_value = UniversalScaling.calculate_potency_value(
            caster_stats, {}, PotencyType.BUFF_DEBUFF
        )
        
        # Apply scaling with ceiling
        effect_strength = UniversalScaling.apply_scaling_formula(
            potency_value, scaling_params, is_buff_debuff=True
        )
        
        logger.debug("Effect strength calculation: %.2f -> %.2f", potency_value, effect_strength)
        return effect_strength

# Predefined scaling parameters for common skill types
SCALING_PRESETS = {
    # Attacker Skills
    "power_strike": ScalingParameters(floor=20, ceiling=0, softcap_1=50, softcap_2=200, post_cap_rate=0.5),
    "flurry_of_blows": ScalingParameters(floor=15, ceiling=0, softcap_1=40, softcap_2=150, post_cap_rate=0.4),
    "armor_break": ScalingParameters(floor=25, ceiling=0, softcap_1=60, softcap_2=220, post_cap_rate=0.4),
    "heavy_slam": ScalingParameters(floor=40, ceiling=0, softcap_1=80, softcap_2=300, post_cap_rate=0.6),
    "cleave": ScalingParameters(floor=15, ceiling=0, softcap_1=70, softcap_2=250, post_cap_rate=0.3),
    
    # Mage Skills
    "mana_bolt": ScalingParameters(floor=20, ceiling=0, softcap_1=50, softcap_2=200, post_cap_rate=0.5),
    "chain_lightning": ScalingParameters(floor=15, ceiling=0, softcap_1=60, softcap_2=220, post_cap_rate=0.4),
    "fireball": ScalingParameters(floor=20, ceiling=0, softcap_1=70, softcap_2=250, post_cap_rate=0.4),
    "frost_nova": ScalingParameters(floor=10, ceiling=0, softcap_1=60, softcap_2=200, post_cap_rate=0.3),
    
    # Healer Skills
    "lesser_heal": ScalingParameters(floor=50, ceiling=0, softcap_1=50, softcap_2=200, post_cap_rate=0.5),
    "greater_heal": ScalingParameters(floor=120, ceiling=0, softcap_1=100, softcap_2=300, post_cap_rate=0.6),
    "row_heal": ScalingParameters(floor=30, ceiling=0, softcap_1=60, softcap_2=220, post_cap_rate=0.3),
    
    # Buff/Debuff Skills
    "rally_weaken": ScalingParameters(floor=10, ceiling=35, softcap_1=80, softcap_2=250, post_cap_rate=0.4),
    "fortify_break": ScalingParameters(floor=10, ceiling=35, softcap_1=80, softcap_2=250, post_cap_rate=0.4),
    "haste_slow": ScalingParameters(floor=15, ceiling=50, softcap_1=100, softcap_2=300, post_cap_rate=0.4),
    "focus_curse": ScalingParameters(floor=20, ceiling=60, softcap_1=120, softcap_2=320, post_cap_rate=0.4),
}
