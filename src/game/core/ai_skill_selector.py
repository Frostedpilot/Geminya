"""
AI Skill Selection System - 3-phase intelligent skill selection.

According to the design document, AI should select skills through:
1. Role Selection: Choose the best role based on situation and potency
2. Skill Selection: Pick the optimal skill from that role
3. Target Selection: Choose the best target for the skill
"""

import random
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass

from .universal_skill_library import UniversalSkill, RoleType
from .universal_damage_calculator import universal_damage_calculator

class BattleSituation(Enum):
    """Current battle situation that influences AI decisions"""
    OPENING = "opening"          # Start of battle
    ADVANTAGE = "advantage"      # Winning
    DISADVANTAGE = "disadvantage" # Losing
    DESPERATE = "desperate"      # Critical situation
    FINISHING = "finishing"      # Enemy nearly defeated

@dataclass 
class AIContext:
    """Context information for AI decision making"""
    battle_situation: BattleSituation
    ally_hp_percentage: float       # Average ally HP %
    enemy_hp_percentage: float      # Average enemy HP %
    turn_number: int
    allies_alive: int
    enemies_alive: int
    
    # Team composition analysis
    team_needs_healing: bool = False
    team_needs_buffs: bool = False
    enemies_need_debuffs: bool = False
    
@dataclass
class SkillChoice:
    """A potential skill choice with its reasoning"""
    skill: UniversalSkill
    priority_score: float
    reasoning: str
    target_preferences: List[str]  # Preferred target types

class AISkillSelector:
    """Intelligent 3-phase skill selection system"""
    
    def __init__(self):
        self.role_priorities = self._initialize_role_priorities()
    
    def _initialize_role_priorities(self) -> Dict[BattleSituation, Dict[RoleType, float]]:
        """Initialize role priority weights for different battle situations"""
        return {
            BattleSituation.OPENING: {
                RoleType.BUFFER: 0.3,
                RoleType.DEBUFFER: 0.25,
                RoleType.ATTACKER: 0.2,
                RoleType.MAGE: 0.15,
                RoleType.HEALER: 0.05,
                RoleType.DEFENDER: 0.05
            },
            BattleSituation.ADVANTAGE: {
                RoleType.ATTACKER: 0.35,
                RoleType.MAGE: 0.3,
                RoleType.DEBUFFER: 0.2,
                RoleType.BUFFER: 0.1,
                RoleType.HEALER: 0.03,
                RoleType.DEFENDER: 0.02
            },
            BattleSituation.DISADVANTAGE: {
                RoleType.HEALER: 0.4,
                RoleType.DEFENDER: 0.25,
                RoleType.BUFFER: 0.15,
                RoleType.DEBUFFER: 0.1,
                RoleType.ATTACKER: 0.07,
                RoleType.MAGE: 0.03
            },
            BattleSituation.DESPERATE: {
                RoleType.HEALER: 0.5,
                RoleType.DEFENDER: 0.3,
                RoleType.ATTACKER: 0.1,
                RoleType.MAGE: 0.05,
                RoleType.BUFFER: 0.03,
                RoleType.DEBUFFER: 0.02
            },
            BattleSituation.FINISHING: {
                RoleType.ATTACKER: 0.5,
                RoleType.MAGE: 0.4,
                RoleType.DEBUFFER: 0.05,
                RoleType.BUFFER: 0.03,
                RoleType.HEALER: 0.01,
                RoleType.DEFENDER: 0.01
            }
        }
    
    def select_skill(self, 
                    character_potency: Dict[str, str],
                    character_stats: Dict[str, float], 
                    ai_context: AIContext,
                    available_skills: Dict[RoleType, List[UniversalSkill]]) -> Optional[SkillChoice]:
        """
        3-phase skill selection:
        1. Choose optimal role based on situation and character potency
        2. Select best skill from that role
        3. Determine target preferences
        """
        
        # Phase 1: Role Selection
        selected_role = self._select_role(character_potency, ai_context, available_skills)
        if not selected_role:
            return None
            
        # Phase 2: Skill Selection
        role_skills = available_skills.get(selected_role, [])
        if not role_skills:
            return None
            
        selected_skill = self._select_skill_from_role(
            role_skills, character_stats, character_potency, ai_context
        )
        
        if not selected_skill:
            return None
            
        # Phase 3: Target Preference Calculation
        target_preferences = self._calculate_target_preferences(selected_skill, ai_context)
        
        # Calculate overall priority score
        priority_score = self._calculate_priority_score(
            selected_skill, selected_role, character_potency, ai_context
        )
        
        reasoning = self._generate_reasoning(selected_skill, selected_role, ai_context)
        
        return SkillChoice(
            skill=selected_skill,
            priority_score=priority_score,
            reasoning=reasoning,
            target_preferences=target_preferences
        )
    
    def _select_role(self, 
                    character_potency: Dict[str, str],
                    ai_context: AIContext,
                    available_skills: Dict[RoleType, List[UniversalSkill]]) -> Optional[RoleType]:
        """Phase 1: Select the best role based on situation and character abilities"""
        
        situation_priorities = self.role_priorities[ai_context.battle_situation]
        role_scores = {}
        
        for role, base_priority in situation_priorities.items():
            # Skip roles with no available skills
            if not available_skills.get(role, []):
                continue
                
            # Get character's potency for this role
            role_name = role.value.title()
            potency = character_potency.get(role_name, "C")
            
            # Skip roles with F potency (character cannot use)
            if potency == "F":
                continue
                
            # Calculate potency modifier
            potency_modifiers = {
                "S": 2.0, "A": 1.5, "B": 1.2, "C": 1.0, "D": 0.6, "F": 0.0
            }
            potency_modifier = potency_modifiers.get(potency, 1.0)
            
            # Apply situational modifiers
            situational_modifier = self._get_situational_modifier(role, ai_context)
            
            # Final score = base_priority × potency_modifier × situational_modifier
            role_scores[role] = base_priority * potency_modifier * situational_modifier
        
        if not role_scores:
            return None
            
        # Select role with highest score (with some randomness for variety)
        return self._weighted_random_choice(role_scores)
    
    def _get_situational_modifier(self, role: RoleType, ai_context: AIContext) -> float:
        """Get additional situational modifiers for role selection"""
        modifier = 1.0
        
        # Healing becomes more important when team is hurt
        if role == RoleType.HEALER:
            if ai_context.ally_hp_percentage < 0.3:
                modifier *= 3.0
            elif ai_context.ally_hp_percentage < 0.6:
                modifier *= 1.5
                
        # Buffing is less useful if team is already buffed (simplified)
        elif role == RoleType.BUFFER:
            if ai_context.turn_number > 5:  # Assume buffs already applied
                modifier *= 0.5
                
        # Debuffing is more useful against healthy enemies
        elif role == RoleType.DEBUFFER:
            if ai_context.enemy_hp_percentage > 0.7:
                modifier *= 1.3
                
        # Attacking is more valuable when enemies are weakened
        elif role in [RoleType.ATTACKER, RoleType.MAGE]:
            if ai_context.enemy_hp_percentage < 0.5:
                modifier *= 1.2
        
        return modifier
    
    def _select_skill_from_role(self, 
                               role_skills: List[UniversalSkill],
                               character_stats: Dict[str, float],
                               character_potency: Dict[str, str],
                               ai_context: AIContext) -> Optional[UniversalSkill]:
        """Phase 2: Select the best skill from the chosen role"""
        
        if not role_skills:
            return None
            
        skill_scores = []
        
        for skill in role_skills:
            # Calculate damage/effectiveness potential
            effectiveness = universal_damage_calculator.compare_skill_effectiveness(
                character_stats, skill, character_potency
            )
            
            base_score = effectiveness["preview"]["estimated_damage"]
            
            # Apply skill-specific situational modifiers
            situational_modifier = self._get_skill_situational_modifier(skill, ai_context)
            
            final_score = base_score * situational_modifier
            skill_scores.append((skill, final_score))
        
        if not skill_scores:
            return None
            
        # Use weighted selection based on scores
        skills = [item[0] for item in skill_scores]
        weights = [max(0.1, item[1]) for item in skill_scores]
        
        # Add randomness factor to prevent predictable behavior
        for i in range(len(weights)):
            weights[i] *= random.uniform(0.8, 1.2)
        
        return random.choices(skills, weights=weights)[0]
    
    def _get_skill_situational_modifier(self, skill: UniversalSkill, ai_context: AIContext) -> float:
        """Get situational modifiers for specific skills"""
        modifier = 1.0
        
        # AOE skills are better against multiple enemies
        if "all" in skill.target_type and ai_context.enemies_alive > 2:
            modifier *= 1.5
        
        # Single target skills are better for finishing
        elif "single" in skill.target_type and ai_context.battle_situation == BattleSituation.FINISHING:
            modifier *= 1.3
            
        # Healing skills prioritized when team is hurt
        if any(effect.get("type") == "heal" for effect in skill.effects):
            if ai_context.ally_hp_percentage < 0.4:
                modifier *= 2.0
                
        # Buff skills less valuable in late game
        if any(effect.get("type") == "buff" for effect in skill.effects):
            if ai_context.turn_number > 8:
                modifier *= 0.7
        
        return modifier
    
    def _calculate_target_preferences(self, skill: UniversalSkill, ai_context: AIContext) -> List[str]:
        """Phase 3: Calculate target preferences for the selected skill"""
        preferences = []
        
        # Basic targeting based on skill type
        if "enemy" in skill.target_type:
            if ai_context.battle_situation == BattleSituation.FINISHING:
                preferences = ["lowest_hp_enemy", "front_row_enemy", "any_enemy"]
            else:
                preferences = ["front_row_enemy", "highest_atk_enemy", "any_enemy"]
                
        elif "ally" in skill.target_type:
            if any(effect.get("type") == "heal" for effect in skill.effects):
                preferences = ["lowest_hp_ally", "most_valuable_ally", "any_ally"]
            else:
                preferences = ["highest_stat_ally", "front_row_ally", "any_ally"]
        
        return preferences
    
    def _calculate_priority_score(self, 
                                 selected_skill: UniversalSkill,
                                 role: RoleType, 
                                 character_potency: Dict[str, str],
                                 ai_context: AIContext) -> float:
        """Calculate overall priority score for the skill choice"""
        
        # Base score from role priority in current situation
        base_score = self.role_priorities[ai_context.battle_situation].get(role, 0.1)
        
        # Character potency modifier
        role_name = role.value.title()
        potency = character_potency.get(role_name, "C")
        potency_modifiers = {"S": 2.0, "A": 1.5, "B": 1.2, "C": 1.0, "D": 0.6, "F": 0.0}
        potency_modifier = potency_modifiers.get(potency, 1.0)
        
        # Skill effectiveness bonus (more effective skills get higher priority)
        skill_bonus = 1.0
        if hasattr(selected_skill, 'scaling') and selected_skill.scaling.power_weight > 60:
            skill_bonus = 1.2
        
        # Situational urgency
        urgency_modifier = 1.0
        if ai_context.battle_situation == BattleSituation.DESPERATE:
            urgency_modifier = 2.0
        elif ai_context.battle_situation == BattleSituation.FINISHING:
            urgency_modifier = 1.5
            
        return base_score * potency_modifier * skill_bonus * urgency_modifier
    
    def _generate_reasoning(self, skill: UniversalSkill, role: RoleType, ai_context: AIContext) -> str:
        """Generate human-readable reasoning for the skill choice"""
        situation_reasons = {
            BattleSituation.OPENING: "opening gambit",
            BattleSituation.ADVANTAGE: "pressing advantage", 
            BattleSituation.DISADVANTAGE: "defensive response",
            BattleSituation.DESPERATE: "emergency action",
            BattleSituation.FINISHING: "finishing move"
        }
        
        return f"Using {skill.name} ({role.value} role) for {situation_reasons[ai_context.battle_situation]}"
    
    def _weighted_random_choice(self, scores: Dict) -> Optional[Any]:
        """Select item based on weighted scores with some randomness"""
        if not scores:
            return None
            
        # Convert scores to weights (ensure positive)
        items = list(scores.keys())
        weights = [max(0.1, score) for score in scores.values()]
        
        # Add randomness factor to prevent predictable behavior
        for i in range(len(weights)):
            weights[i] *= random.uniform(0.8, 1.2)
        
        return random.choices(items, weights=weights)[0]
    
    def analyze_character_ai_potential(self, character_potency: Dict[str, str]) -> Dict[str, Any]:
        """Analyze a character's AI decision-making potential"""
        analysis = {
            "primary_roles": [],
            "secondary_roles": [],
            "versatility_score": 0,
            "situational_adaptability": {}
        }
        
        # Categorize roles by potency
        for role_name, potency in character_potency.items():
            if potency in ["S", "A"]:
                analysis["primary_roles"].append(role_name)
            elif potency in ["B", "C"]:
                analysis["secondary_roles"].append(role_name)
        
        # Calculate versatility (how many roles they can effectively use)
        effective_roles = len([p for p in character_potency.values() if p != "F"])
        analysis["versatility_score"] = effective_roles / len(RoleType)
        
        # Analyze adaptability to different situations
        for situation in BattleSituation:
            situation_priorities = self.role_priorities[situation]
            character_effectiveness = 0
            
            for role, priority in situation_priorities.items():
                role_name = role.value.title()
                potency = character_potency.get(role_name, "C")
                potency_values = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
                character_effectiveness += priority * potency_values.get(potency, 0)
            
            analysis["situational_adaptability"][situation.value] = character_effectiveness
        
        return analysis

# Global instance
ai_skill_selector = AISkillSelector()
