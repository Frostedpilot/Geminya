"""
Abilities Component - Manages character abilities using the universal skill library.

This component provides access to skills from the universal library based on
character potency ratings, implementing the correct design from SIMPLE_WAIFU_GAME.md.
"""

from typing import Dict, List, Optional, Any
import logging

from ..core.universal_skill_library import (
    UniversalSkill, RoleType, universal_skill_library
)
from ..core.ai_skill_selector import ai_skill_selector, AIContext, BattleSituation

logger = logging.getLogger(__name__)

class UniversalAbilitiesComponent:
    """
    Manages character abilities through the universal skill library.
    
    Key principles from design document:
    - All characters share the same universal skill pool
    - Effectiveness determined by archetype potency ratings (S/A/B/C/D/F)
    - No character-specific skills or basic attacks
    - AI selects skills through 3-phase system
    """
    
    def __init__(self, character_data: Dict[str, Any]):
        self.character_data = character_data
        self.potency_ratings = self._parse_potency_ratings()
        self.available_skills = self._load_available_skills()
        self.skill_cooldowns = {}  # skill_id -> turns remaining
        
        logger.debug("Initialized abilities for %s with potency: %s", 
                    character_data.get('name', 'Unknown'), self.potency_ratings)
    
    def _parse_potency_ratings(self) -> Dict[str, str]:
        """Parse potency ratings from character data"""
        potency_data = self.character_data.get('potency', {})
        
        # Handle string format "{'Attacker': 'B', 'Mage': 'S', ...}"
        if isinstance(potency_data, str):
            try:
                # Clean up the string and parse it
                import ast
                potency_data = ast.literal_eval(potency_data)
            except (ValueError, SyntaxError):
                logger.warning("Could not parse potency data for %s: %s", 
                              self.character_data.get('name'), potency_data)
                potency_data = {}
        
        # Ensure all roles have a rating (default to C)
        default_potency = {
            "Attacker": "C",
            "Mage": "C", 
            "Healer": "C",
            "Buffer": "C",
            "Debuffer": "C",
            "Defender": "C",
            "Specialist": "C"
        }
        
        # Update with actual potency data
        if isinstance(potency_data, dict):
            default_potency.update(potency_data)
        
        return default_potency
    
    def _load_available_skills(self) -> Dict[RoleType, List[UniversalSkill]]:
        """Load all skills this character can use based on potency ratings"""
        return universal_skill_library.get_available_skills_for_character(self.potency_ratings)
    
    def get_available_skills(self) -> Dict[RoleType, List[UniversalSkill]]:
        """Get all skills available to this character"""
        return self.available_skills.copy()
    
    def get_usable_skills(self) -> Dict[RoleType, List[UniversalSkill]]:
        """Get skills that are not on cooldown"""
        usable = {}
        
        for role, skills in self.available_skills.items():
            usable_in_role = []
            for skill in skills:
                if not self.is_skill_on_cooldown(skill.skill_id):
                    usable_in_role.append(skill)
            usable[role] = usable_in_role
        
        return usable
    
    def get_skills_by_role(self, role: RoleType) -> List[UniversalSkill]:
        """Get all skills for a specific role"""
        return self.available_skills.get(role, []).copy()
    
    def get_skill_effectiveness(self, skill: UniversalSkill) -> float:
        """Get the effectiveness multiplier for this character using a skill"""
        return universal_skill_library.get_role_effectiveness(self.potency_ratings, skill.role)
    
    def can_use_skill(self, skill_id: str) -> bool:
        """Check if character can use a specific skill"""
        # Check if skill exists in any of our available roles
        for role_skills in self.available_skills.values():
            if any(skill.skill_id == skill_id for skill in role_skills):
                return not self.is_skill_on_cooldown(skill_id)
        return False
    
    def is_skill_on_cooldown(self, skill_id: str) -> bool:
        """Check if a skill is on cooldown"""
        return self.skill_cooldowns.get(skill_id, 0) > 0
    
    def get_skill_cooldown(self, skill_id: str) -> int:
        """Get remaining cooldown turns for a skill"""
        return self.skill_cooldowns.get(skill_id, 0)
    
    def use_skill(self, skill_id: str) -> Optional[UniversalSkill]:
        """Use a skill (put it on cooldown) and return the skill object"""
        # Find the skill in our available skills
        for role_skills in self.available_skills.values():
            for skill in role_skills:
                if skill.skill_id == skill_id:
                    if not self.is_skill_on_cooldown(skill_id):
                        # Put skill on cooldown (simplified: all skills have 3 turn cooldown)
                        self.skill_cooldowns[skill_id] = 3
                        return skill
                    else:
                        logger.warning("Skill %s is on cooldown for %d turns", 
                                     skill_id, self.get_skill_cooldown(skill_id))
                        return None
        
        logger.warning("Skill %s not available for character %s", 
                      skill_id, self.character_data.get('name'))
        return None
    
    def advance_cooldowns(self):
        """Advance all skill cooldowns by one turn"""
        for skill_id in list(self.skill_cooldowns.keys()):
            self.skill_cooldowns[skill_id] -= 1
            if self.skill_cooldowns[skill_id] <= 0:
                del self.skill_cooldowns[skill_id]
    
    def ai_select_skill(self, 
                       character_stats: Dict[str, float],
                       battle_context: Optional[Dict[str, Any]] = None) -> Optional[UniversalSkill]:
        """Use AI to select the best skill for current situation"""
        
        # Create AI context from battle information
        ai_context = self._create_ai_context(battle_context)
        
        # Get skills that are not on cooldown
        usable_skills = self.get_usable_skills()
        
        # Use AI selector to choose skill
        choice = ai_skill_selector.select_skill(
            character_potency=self.potency_ratings,
            character_stats=character_stats,
            ai_context=ai_context,
            available_skills=usable_skills
        )
        
        if choice:
            logger.info("AI selected %s: %s", choice.skill.name, choice.reasoning)
            return choice.skill
        else:
            logger.warning("AI could not select a skill for %s", 
                          self.character_data.get('name'))
            return None
    
    def _create_ai_context(self, battle_context: Optional[Dict[str, Any]]) -> AIContext:
        """Create AI context from battle information"""
        if not battle_context:
            # Default context for testing
            return AIContext(
                battle_situation=BattleSituation.OPENING,
                ally_hp_percentage=1.0,
                enemy_hp_percentage=1.0,
                turn_number=1,
                allies_alive=3,
                enemies_alive=3
            )
        
        # Parse actual battle context
        return AIContext(
            battle_situation=battle_context.get('situation', BattleSituation.OPENING),
            ally_hp_percentage=battle_context.get('ally_hp_pct', 1.0),
            enemy_hp_percentage=battle_context.get('enemy_hp_pct', 1.0),
            turn_number=battle_context.get('turn', 1),
            allies_alive=battle_context.get('allies_alive', 3),
            enemies_alive=battle_context.get('enemies_alive', 3),
            team_needs_healing=battle_context.get('needs_healing', False),
            team_needs_buffs=battle_context.get('needs_buffs', False),
            enemies_need_debuffs=battle_context.get('needs_debuffs', False)
        )
    
    def get_character_analysis(self) -> Dict[str, Any]:
        """Get detailed analysis of this character's skill potential"""
        analysis = {
            "potency_ratings": self.potency_ratings,
            "available_skills_count": {
                role.value: len(skills) for role, skills in self.available_skills.items()
            },
            "total_skills": sum(len(skills) for skills in self.available_skills.values()),
            "primary_roles": [],
            "secondary_roles": [],
            "weakest_roles": []
        }
        
        # Categorize roles by potency
        for role_name, potency in self.potency_ratings.items():
            if potency in ["S", "A"]:
                analysis["primary_roles"].append(f"{role_name} ({potency})")
            elif potency in ["B", "C"]:
                analysis["secondary_roles"].append(f"{role_name} ({potency})")
            else:  # D, F
                analysis["weakest_roles"].append(f"{role_name} ({potency})")
        
        # AI analysis
        analysis["ai_potential"] = ai_skill_selector.analyze_character_ai_potential(self.potency_ratings)
        
        return analysis
    
    def get_skill_recommendations(self, 
                                character_stats: Dict[str, float],
                                situation: str = "general") -> List[Dict[str, Any]]:
        """Get recommended skills for different situations"""
        recommendations = []
        
        # Get top skills from each role the character is good at
        for role, skills in self.available_skills.items():
            role_name = role.value.title()
            potency = self.potency_ratings.get(role_name, "C")
            
            # Only recommend from roles where character has decent potency
            if potency in ["S", "A", "B"]:
                # Get top 2 skills from this role
                for skill in skills[:2]:
                    effectiveness = universal_skill_library.get_role_effectiveness(
                        self.potency_ratings, skill.role
                    )
                    
                    # Use character stats to estimate damage potential
                    from ..core.universal_damage_calculator import universal_damage_calculator
                    damage_preview = universal_damage_calculator.compare_skill_effectiveness(
                        character_stats, skill, self.potency_ratings
                    )
                    
                    recommendations.append({
                        "skill": skill,
                        "role": role_name,
                        "potency": potency,
                        "effectiveness": f"{effectiveness:.1f}x",
                        "estimated_damage": damage_preview["preview"]["estimated_damage"],
                        "recommended_for": f"{situation} situations"
                    })
        
        # Sort by estimated damage potential
        recommendations.sort(key=lambda x: x["estimated_damage"], reverse=True)
        
        return recommendations[:5]  # Top 5 recommendations


# For backwards compatibility, alias the new component to the old name
AbilitiesComponent = UniversalAbilitiesComponent
