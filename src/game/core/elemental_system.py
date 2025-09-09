"""
Elemental System - Handles elemental damage calculations and interactions.

This system manages:
- Elemental damage multiplier calculations
- Multi-element attack logic
- Resistance/weakness interactions
- Element-based skill modifiers
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)

class ElementType(Enum):
    """All available element types in the game"""
    FIRE = "fire"
    WATER = "water"
    EARTH = "earth"
    WIND = "wind"
    NATURE = "nature"
    LIGHT = "light"
    DARK = "dark"
    VOID = "void"
    NEUTRAL = "neutral"

class ResistanceType(Enum):
    """Types of elemental resistance"""
    RESIST = "resist"    # Takes reduced damage
    WEAK = "weak"        # Takes increased damage  
    NEUTRAL = "neutral"  # Normal damage

class ElementalCalculator:
    """Core elemental damage calculation system"""
    
    # Damage multipliers for resistance types
    RESISTANCE_MULTIPLIERS = {
        ResistanceType.RESIST: 0.5,    # 50% damage (resistant)
        ResistanceType.WEAK: 1.5,      # 150% damage (weak)
        ResistanceType.NEUTRAL: 1.0    # 100% damage (normal)
    }
    
    # Multi-element calculation modes
    MULTI_ELEMENT_MODES = {
        "average": "Calculate average of all element modifiers",
        "best": "Use the most favorable modifier for attacker", 
        "worst": "Use the least favorable modifier for attacker",
        "additive": "Sum all modifiers and divide by element count"
    }
    
    def __init__(self, multi_element_mode: str = "average"):
        """
        Initialize elemental calculator.
        
        Args:
            multi_element_mode: How to handle multi-element attacks
        """
        if multi_element_mode not in self.MULTI_ELEMENT_MODES:
            logger.warning("Invalid multi-element mode '%s', using 'average'", multi_element_mode)
            multi_element_mode = "average"
        
        self.multi_element_mode = multi_element_mode
        logger.info("Initialized elemental calculator with mode: %s", multi_element_mode)
    
    def calculate_elemental_modifier(
        self, 
        attacker_elements: List[str],
        target_resistances: Dict[str, str],
        skill_element_override: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate elemental damage modifier.
        
        Args:
            attacker_elements: List of attacker's elements (e.g., ["fire", "wind"])
            target_resistances: Target's resistance mapping (e.g., {"fire": "weak", "wind": "resist"})
            skill_element_override: Override element for specific skills
            
        Returns:
            Tuple of (final_modifier, calculation_details)
        """
        # Use skill override if provided
        if skill_element_override:
            elements_to_use = [skill_element_override]
            logger.debug("Using skill element override: %s", skill_element_override)
        else:
            elements_to_use = attacker_elements
        
        # Handle empty elements (neutral damage)
        if not elements_to_use:
            elements_to_use = ["neutral"]
        
        # Calculate modifier for each element
        element_modifiers = {}
        for element in elements_to_use:
            resistance = target_resistances.get(element, "neutral")
            try:
                resistance_type = ResistanceType(resistance)
                modifier = self.RESISTANCE_MULTIPLIERS[resistance_type]
                element_modifiers[element] = {
                    "resistance": resistance,
                    "modifier": modifier
                }
            except ValueError:
                logger.warning("Invalid resistance type '%s' for element '%s', using neutral", 
                             resistance, element)
                element_modifiers[element] = {
                    "resistance": "neutral",
                    "modifier": 1.0
                }
        
        # Calculate final modifier based on multi-element mode
        final_modifier = self._calculate_multi_element_modifier(element_modifiers)
        
        calculation_details = {
            "elements_used": elements_to_use,
            "element_modifiers": element_modifiers,
            "multi_element_mode": self.multi_element_mode,
            "final_modifier": final_modifier,
            "skill_override": skill_element_override is not None
        }
        
        logger.debug("Elemental calculation: %s -> %.2fx damage", 
                    calculation_details, final_modifier)
        
        return final_modifier, calculation_details
    
    def _calculate_multi_element_modifier(self, element_modifiers: Dict[str, Dict[str, Any]]) -> float:
        """Calculate final modifier from multiple elements"""
        if not element_modifiers:
            return 1.0
        
        modifiers = [data["modifier"] for data in element_modifiers.values()]
        
        if self.multi_element_mode == "average":
            return sum(modifiers) / len(modifiers)
        elif self.multi_element_mode == "best":
            return max(modifiers)  # Best for attacker (highest damage)
        elif self.multi_element_mode == "worst":
            return min(modifiers)  # Worst for attacker (lowest damage)
        elif self.multi_element_mode == "additive":
            # Sum all but cap at reasonable limits
            total = sum(modifiers)
            return max(0.1, min(3.0, total))  # Cap between 10% and 300%
        else:
            return 1.0
    
    def get_element_effectiveness(
        self, 
        attacker_element: str, 
        target_resistances: Dict[str, str]
    ) -> str:
        """
        Get human-readable effectiveness description.
        
        Returns:
            String describing effectiveness ("super effective", "not very effective", "normal")
        """
        resistance = target_resistances.get(attacker_element, "neutral")
        
        if resistance == "weak":
            return "super effective"
        elif resistance == "resist":
            return "not very effective"
        else:
            return "normal"
    
    def analyze_elemental_matchup(
        self,
        attacker_elements: List[str],
        target_resistances: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Analyze elemental matchup and provide detailed breakdown.
        
        Returns:
            Detailed analysis of the elemental interaction
        """
        analysis = {
            "attacker_elements": attacker_elements,
            "target_resistances": target_resistances,
            "element_effectiveness": {},
            "overall_rating": "neutral",
            "recommendations": []
        }
        
        total_effectiveness = 0.0
        for element in attacker_elements:
            resistance = target_resistances.get(element, "neutral")
            effectiveness = self.get_element_effectiveness(element, target_resistances)
            modifier = self.RESISTANCE_MULTIPLIERS.get(ResistanceType(resistance), 1.0)
            
            analysis["element_effectiveness"][element] = {
                "resistance": resistance,
                "effectiveness": effectiveness,
                "modifier": modifier
            }
            total_effectiveness += modifier
        
        # Overall rating
        avg_effectiveness = total_effectiveness / max(1, len(attacker_elements))
        if avg_effectiveness > 1.2:
            analysis["overall_rating"] = "advantageous"
            analysis["recommendations"].append("Strong elemental advantage - press the attack!")
        elif avg_effectiveness < 0.8:
            analysis["overall_rating"] = "disadvantageous"
            analysis["recommendations"].append("Consider switching elements or using neutral attacks")
        else:
            analysis["overall_rating"] = "neutral"
            analysis["recommendations"].append("Balanced matchup - focus on strategy")
        
        return analysis
    
    @staticmethod
    def parse_character_elements(elemental_type_data: Any) -> List[str]:
        """
        Parse character elemental_type data from various formats.
        
        Args:
            elemental_type_data: Can be string, list, or JSON string
            
        Returns:
            List of element strings
        """
        if isinstance(elemental_type_data, list):
            return elemental_type_data
        elif isinstance(elemental_type_data, str):
            try:
                # Try parsing as JSON array
                parsed = json.loads(elemental_type_data)
                if isinstance(parsed, list):
                    return parsed
                else:
                    return [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                # Single element string
                return [elemental_type_data]
        else:
            logger.warning("Unknown elemental_type format: %s", type(elemental_type_data))
            return ["neutral"]
    
    @staticmethod
    def parse_character_resistances(resistances_data: Any) -> Dict[str, str]:
        """
        Parse character elemental_resistances data from various formats.
        
        Args:
            resistances_data: Can be dict, JSON string, etc.
            
        Returns:
            Dict mapping element to resistance type
        """
        if isinstance(resistances_data, dict):
            return resistances_data
        elif isinstance(resistances_data, str):
            try:
                parsed = json.loads(resistances_data)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Default neutral resistances
        logger.warning("Could not parse resistances data: %s", resistances_data)
        return {element.value: "neutral" for element in ElementType}

# Global elemental calculator instance
elemental_calculator = ElementalCalculator(multi_element_mode="average")
