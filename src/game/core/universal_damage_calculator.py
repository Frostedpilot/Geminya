"""
Universal Damage Calculator - Implements the complex universal scaling formula.

This calculator uses the original design's universal scaling formula with floor,
softcaps, and post-cap scaling to ensure balanced damage across all characters.
"""

from typing import Dict, Any
from dataclasses import dataclass

from .universal_skill_library import UniversalSkill, RoleType
from .elemental_system import ElementalCalculator

@dataclass
class DamageParameters:
    """Parameters for damage calculation"""
    base_stat: float  # ATK, MAG, etc.
    skill: UniversalSkill
    potency_effectiveness: float  # Based on character's role potency
    elemental_modifier: float = 1.0
    level_modifier: float = 1.0
    critical_hit: bool = False
    critical_multiplier: float = 1.5

@dataclass
class DamageResult:
    """Result of damage calculation"""
    final_damage: float
    base_damage: float
    floor_component: float
    stat_component: float
    potency_modifier: float
    elemental_modifier: float
    critical_applied: bool
    breakdown: Dict[str, Any]

class UniversalDamageCalculator:
    """
    Implements the universal scaling formula from the design document:
    
    Formula: floor + (stat * sc1 / 100) with softcaps and post-cap scaling
    - floor: minimum damage guaranteed
    - sc1: primary scaling coefficient  
    - sc2: softcap threshold
    - post_cap_rate: scaling rate after softcap
    - ceiling: maximum damage (0 = no ceiling)
    """
    
    def __init__(self):
        self.elemental_calculator = ElementalCalculator()
    
    def calculate_damage(self, params: DamageParameters) -> DamageResult:
        """Calculate damage using the universal scaling formula"""
        
        # Step 1: Apply universal scaling formula
        base_damage = self._apply_universal_scaling(
            stat=params.base_stat,
            scaling=params.skill.scaling
        )
        
        # Step 2: Apply potency effectiveness
        potency_damage = base_damage * params.potency_effectiveness
        
        # Step 3: Apply elemental modifier
        elemental_damage = potency_damage * params.elemental_modifier
        
        # Step 4: Apply level modifier
        level_damage = elemental_damage * params.level_modifier
        
        # Step 5: Apply critical hit if applicable
        final_damage = level_damage
        critical_applied = False
        if params.critical_hit:
            final_damage *= params.critical_multiplier
            critical_applied = True
        
        # Round to reasonable precision
        final_damage = round(final_damage, 1)
        
        return DamageResult(
            final_damage=final_damage,
            base_damage=base_damage,
            floor_component=params.skill.scaling.floor,
            stat_component=potency_damage - params.skill.scaling.floor,
            potency_modifier=params.potency_effectiveness,
            elemental_modifier=params.elemental_modifier,
            critical_applied=critical_applied,
            breakdown={
                "step1_universal_scaling": base_damage,
                "step2_potency_applied": potency_damage,
                "step3_elemental_applied": elemental_damage,
                "step4_level_applied": level_damage,
                "step5_critical_applied": final_damage if critical_applied else level_damage,
                "formula_used": f"floor({params.skill.scaling.floor}) + (stat({params.base_stat}) * sc1({params.skill.scaling.sc1}) / 100)",
                "potency_effectiveness": f"{params.potency_effectiveness:.2f}x",
                "elemental_effectiveness": f"{params.elemental_modifier:.2f}x"
            }
        )
    
    def _apply_universal_scaling(self, stat: float, scaling) -> float:
        """
        Apply the universal scaling formula with softcaps.
        
        Formula: floor + (stat * sc1 / 100) with softcap handling
        """
        # Base calculation: floor + (stat * sc1 / 100)
        stat_contribution = stat * scaling.sc1 / 100
        pre_softcap = scaling.floor + stat_contribution
        
        # Apply softcap if sc2 is set and damage exceeds it
        if scaling.sc2 > 0 and pre_softcap > scaling.sc2:
            # Excess damage above softcap is reduced by post_cap_rate
            excess = pre_softcap - scaling.sc2
            reduced_excess = excess * scaling.post_cap_rate
            post_softcap = scaling.sc2 + reduced_excess
        else:
            post_softcap = pre_softcap
        
        # Apply ceiling if set
        if scaling.ceiling > 0:
            final_damage = min(post_softcap, scaling.ceiling)
        else:
            final_damage = post_softcap
        
        return final_damage
    
    def calculate_healing(self, params: DamageParameters) -> DamageResult:
        """Calculate healing using the same universal formula"""
        # Healing uses the same formula but is always positive
        result = self.calculate_damage(params)
        
        # Update breakdown to indicate this is healing
        result.breakdown["calculation_type"] = "healing"
        
        return result
    
    def get_damage_preview(self, 
                          character_stat: float,
                          skill: UniversalSkill, 
                          potency_effectiveness: float,
                          elemental_modifier: float = 1.0) -> Dict[str, Any]:
        """Get a damage preview without creating full parameters"""
        
        params = DamageParameters(
            base_stat=character_stat,
            skill=skill,
            potency_effectiveness=potency_effectiveness,
            elemental_modifier=elemental_modifier
        )
        
        result = self.calculate_damage(params)
        
        return {
            "estimated_damage": result.final_damage,
            "damage_range": {
                "normal": result.final_damage,
                "critical": result.final_damage * 1.5
            },
            "effectiveness": f"{potency_effectiveness:.1f}x potency, {elemental_modifier:.1f}x elemental",
            "formula_breakdown": result.breakdown
        }
    
    def compare_skill_effectiveness(self, 
                                  character_stats: Dict[str, float],
                                  skill: UniversalSkill,
                                  potency_ratings: Dict[str, str]) -> Dict[str, Any]:
        """Compare how effective a skill would be for this character"""
        
        # Determine which stat to use based on skill role
        stat_mapping = {
            RoleType.ATTACKER: "atk",
            RoleType.MAGE: "mag", 
            RoleType.HEALER: "mag",
            RoleType.BUFFER: "mag",
            RoleType.DEBUFFER: "mag",
            RoleType.DEFENDER: "def",
            RoleType.SPECIALIST: "mag"
        }
        
        stat_name = stat_mapping.get(skill.role, "atk")
        character_stat = character_stats.get(stat_name, 50)  # Default if missing
        
        # Get potency effectiveness for this role
        role_name = skill.role.value.title()
        potency = potency_ratings.get(role_name, "C")
        
        # Values from WAIFU_CORE_GAME.md specification
        potency_multipliers = {
            "S": 2.0, "A": 1.5, "B": 1.2, "C": 1.0, "D": 0.7, "F": 0.5
        }
        
        potency_effectiveness = potency_multipliers.get(potency, 1.0)
        
        # Calculate effectiveness
        preview = self.get_damage_preview(
            character_stat=character_stat,
            skill=skill,
            potency_effectiveness=potency_effectiveness
        )
        
        return {
            "skill_name": skill.name,
            "role_required": skill.role.value,
            "character_potency": potency,
            "stat_used": stat_name,
            "stat_value": character_stat,
            "effectiveness_rating": self._rate_effectiveness(potency_effectiveness),
            "preview": preview
        }
    
    def _rate_effectiveness(self, multiplier: float) -> str:
        """Convert effectiveness multiplier to readable rating"""
        if multiplier >= 1.4:
            return "Excellent"
        elif multiplier >= 1.2:
            return "Good"
        elif multiplier >= 1.0:
            return "Average"
        elif multiplier >= 0.7:
            return "Poor"
        else:
            return "Terrible"

# Global instance
universal_damage_calculator = UniversalDamageCalculator()
