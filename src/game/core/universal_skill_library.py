"""
Universal Skill Library - Core skill system implementation.

According to the design document, all characters share the same pool of skills
but have different effectiveness based on their archetype potency ratings.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)

class RoleType(Enum):
    """Character roles that determine skill access"""
    ATTACKER = "attacker"
    MAGE = "mage" 
    HEALER = "healer"
    BUFFER = "buffer"
    DEBUFFER = "debuffer"
    DEFENDER = "defender"
    SPECIALIST = "specialist"

class PotencyRank(Enum):
    """Potency rankings for role effectiveness"""
    S = "S"  # Excellent (10 weight)
    A = "A"  # Good (8 weight)
    B = "B"  # Above Average (6 weight)
    C = "C"  # Average (4 weight)
    D = "D"  # Below Average (2 weight)
    F = "F"  # Terrible (0 weight - cannot use)

@dataclass
class ScalingParameters:
    """Universal scaling parameters for skills"""
    power_weight: int
    floor: float
    ceiling: float = 0  # 0 means no ceiling
    sc1: float = 50  # Softcap 1
    sc2: float = 200  # Softcap 2
    post_cap_rate: float = 0.5

@dataclass
class UniversalSkill:
    """A skill from the universal library that all characters can potentially use"""
    skill_id: str
    name: str
    description: str
    role: RoleType
    scaling: ScalingParameters
    target_type: str
    effects: List[Dict[str, Any]]
    
    # Optional properties
    hits: int = 1
    damage_type: str = "physical"
    status_effects: Optional[List[str]] = None
    special_properties: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.status_effects is None:
            self.status_effects = []
        if self.special_properties is None:
            self.special_properties = {}

class UniversalSkillLibrary:
    """Manages the universal skill library that all characters share"""
    
    def __init__(self):
        self.skills: Dict[str, UniversalSkill] = {}
        self.skills_by_role: Dict[RoleType, List[UniversalSkill]] = {
            role: [] for role in RoleType
        }
        self._initialize_from_data()
    
    def _initialize_from_data(self):
        """Load skills from the general_skills.json file"""
        try:
            with open('data/general_skills.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Process each skill category
            for category, skills_data in data['skills'].items():
                role = self._category_to_role(category)
                
                for skill_id, skill_data in skills_data.items():
                    skill = self._create_skill_from_data(skill_id, skill_data, role)
                    if skill:
                        self.add_skill(skill)
                        
            logger.info("Loaded %d skills into universal library", len(self.skills))
            
        except FileNotFoundError:
            logger.error("Skills file not found: data/general_skills.json")
            self._create_fallback_skills()
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in skills file: %s", e)
            self._create_fallback_skills()
        except KeyError as e:
            logger.error("Missing key in skills file: %s", e)
            self._create_fallback_skills()
    
    def _category_to_role(self, category: str) -> RoleType:
        """Convert skill category to role type"""
        role_mapping = {
            "attacker_potency": RoleType.ATTACKER,
            "mage_potency": RoleType.MAGE,
            "healer_potency": RoleType.HEALER,
            "buffer_potency": RoleType.BUFFER,
            "debuffer_potency": RoleType.DEBUFFER,
            "defender_potency": RoleType.DEFENDER,
            "tactician_potency": RoleType.SPECIALIST
        }
        
        return role_mapping.get(category, RoleType.ATTACKER)
    
    def _create_skill_from_data(self, skill_id: str, skill_data: Dict, role: RoleType) -> Optional[UniversalSkill]:
        """Create a UniversalSkill from JSON data"""
        try:
            scaling = ScalingParameters(
                power_weight=skill_data.get('power_weight', 50),
                floor=skill_data.get('floor', 20),
                ceiling=skill_data.get('ceiling', 0),
                sc1=skill_data.get('sc1', 50),
                sc2=skill_data.get('sc2', 200),
                post_cap_rate=skill_data.get('post_cap_rate', 0.5)
            )
            
            return UniversalSkill(
                skill_id=skill_id,
                name=skill_data.get('name', skill_id.replace('_', ' ').title()),
                description=skill_data.get('description', ''),
                role=role,
                scaling=scaling,
                target_type=skill_data.get('target_type', 'single_enemy'),
                effects=skill_data.get('effects', []),
                hits=skill_data.get('hits', 1),
                damage_type=skill_data.get('damage_type', 'physical'),
                status_effects=skill_data.get('status_effects', []),
                special_properties=skill_data.get('special_properties', {})
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error("Failed to create skill %s: %s", skill_id, e)
            return None
    
    def _create_fallback_skills(self):
        """Create basic fallback skills if file loading fails"""
        fallback_skills = [
            UniversalSkill(
                skill_id="power_strike",
                name="Power Strike",
                description="100% ATK damage to one front-row enemy",
                role=RoleType.ATTACKER,
                scaling=ScalingParameters(50, 20, 0, 50, 200, 0.5),
                target_type="single_front_enemy",
                effects=[{"type": "damage", "damage_type": "physical"}]
            ),
            UniversalSkill(
                skill_id="mana_bolt",
                name="Mana Bolt", 
                description="100% MAG damage to one front-row enemy",
                role=RoleType.MAGE,
                scaling=ScalingParameters(50, 20, 0, 50, 200, 0.5),
                target_type="single_front_enemy",
                effects=[{"type": "damage", "damage_type": "magical"}]
            ),
            UniversalSkill(
                skill_id="lesser_heal",
                name="Lesser Heal",
                description="Restores a moderate amount of HP to one ally",
                role=RoleType.HEALER,
                scaling=ScalingParameters(50, 50, 0, 50, 200, 0.5),
                target_type="single_ally",
                effects=[{"type": "heal"}]
            )
        ]
        
        for skill in fallback_skills:
            self.add_skill(skill)
    
    def add_skill(self, skill: UniversalSkill):
        """Add a skill to the library"""
        self.skills[skill.skill_id] = skill
        self.skills_by_role[skill.role].append(skill)
    
    def get_skill(self, skill_id: str) -> Optional[UniversalSkill]:
        """Get a specific skill by ID"""
        return self.skills.get(skill_id)
    
    def get_skills_by_role(self, role: RoleType) -> List[UniversalSkill]:
        """Get all skills for a specific role"""
        return self.skills_by_role[role].copy()
    
    def get_available_skills_for_character(self, potency_ratings: Dict[str, str]) -> Dict[RoleType, List[UniversalSkill]]:
        """Get all skills a character can use based on their potency ratings"""
        available = {}
        
        for role in RoleType:
            role_name = role.value.title()
            potency = potency_ratings.get(role_name, "F")
            
            # Characters with F rank cannot use skills from that role
            if potency != "F":
                available[role] = self.get_skills_by_role(role)
            else:
                available[role] = []
        
        return available
    
    def get_role_effectiveness(self, potency_ratings: Dict[str, str], role: RoleType) -> float:
        """Get the effectiveness multiplier for a role based on potency"""
        role_name = role.value.title()
        potency = potency_ratings.get(role_name, "C")
        
        # Convert potency rank to effectiveness multiplier
        # Values from WAIFU_CORE_GAME.md specification
        multipliers = {
            "S": 2.0,   # 200% effectiveness
            "A": 1.5,   # 150% effectiveness
            "B": 1.2,   # 120% effectiveness
            "C": 1.0,   # 100% effectiveness (baseline)
            "D": 0.7,   # 70% effectiveness
            "F": 0.5    # 50% effectiveness
        }
        
        return multipliers.get(potency, 1.0)
    
    def get_all_skills(self) -> Dict[str, UniversalSkill]:
        """Get all skills in the library"""
        return self.skills.copy()
    
    def get_library_stats(self) -> Dict[str, Any]:
        """Get statistics about the skill library"""
        return {
            "total_skills": len(self.skills),
            "skills_by_role": {
                role.value: len(skills) for role, skills in self.skills_by_role.items()
            },
            "roles_available": list(role.value for role in RoleType)
        }

# Global instance
universal_skill_library = UniversalSkillLibrary()
