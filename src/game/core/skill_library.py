"""
Enhanced Skill Library

Implements the full skill library from the design document with proper
scaling parameters and complex mechanics.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from ..systems.combat_system import CombatAction, ActionType

logger = logging.getLogger(__name__)

class SkillCategory(Enum):
    """Skill categories for AI selection"""
    ATTACKER = "attacker"
    MAGE = "mage"
    HEALER = "healer"
    BUFFER = "buffer"
    DEBUFFER = "debuffer"
    DEFENDER = "defender"
    TACTICIAN = "tactician"

class TargetType(Enum):
    """Skill targeting types"""
    SINGLE_ENEMY = "single_enemy"
    SINGLE_ALLY = "single_ally"
    FRONT_ROW_ENEMIES = "front_row_enemies"
    BACK_ROW_ENEMIES = "back_row_enemies"
    ALL_ENEMIES = "all_enemies"
    ALL_ALLIES = "all_allies"
    SELF = "self"
    ADJACENT_ALLIES = "adjacent_allies"
    ADJACENT_ENEMIES = "adjacent_enemies"
    RANDOM_ENEMIES = "random_enemies"

@dataclass
class SkillEffect:
    """Individual effect within a skill"""
    effect_type: str            # "damage", "heal", "buff", "debuff", "status"
    target_stat: Optional[str] = None  # For stat modifications
    value: float = 0.0          # Base value
    probability: float = 1.0    # Chance to apply (0.0-1.0)
    duration: int = 1           # Duration in turns
    scaling_preset: Optional[str] = None  # Reference to SCALING_PRESETS

@dataclass
class SkillDefinition:
    """Complete skill definition"""
    skill_id: str
    name: str
    category: SkillCategory
    target_type: TargetType
    power_weight: int           # For AI selection
    cooldown: int = 0           # Turns before reuse
    can_target_back_row: bool = False
    skill_multiplier: float = 1.0
    effects: Optional[List[SkillEffect]] = None
    scaling_preset: Optional[str] = None
    description: str = ""
    
    def __post_init__(self):
        if self.effects is None:
            self.effects = []

class SkillLibrary:
    """Manages the complete skill library"""
    
    def __init__(self):
        self.skills: Dict[str, SkillDefinition] = {}
        self._initialize_skill_library()
        logger.info("Initialized skill library with %d skills", len(self.skills))
    
    def _initialize_skill_library(self):
        """Initialize all skills from the design document"""
        
        # ATTACKER SKILLS (Physical)
        self._add_attacker_skills()
        
        # MAGE SKILLS (Magical)
        self._add_mage_skills()
        
        # HEALER SKILLS (Support)
        self._add_healer_skills()
        
        # BUFFER/DEBUFFER SKILLS (Support)
        self._add_buffer_debuffer_skills()
        
        # DEFENDER SKILLS (Defensive)
        self._add_defender_skills()
        
        # TACTICIAN SKILLS (Utility)
        self._add_tactician_skills()
    
    def _add_attacker_skills(self):
        """Add physical attacker skills"""
        
        skills = [
            SkillDefinition(
                skill_id="power_strike",
                name="Power Strike",
                category=SkillCategory.ATTACKER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=50,
                skill_multiplier=1.0,
                scaling_preset="power_strike",
                effects=[SkillEffect(effect_type="damage", value=100)],
                description="100% ATK damage to one front-row enemy."
            ),
            
            SkillDefinition(
                skill_id="flurry_of_blows",
                name="Flurry of Blows",
                category=SkillCategory.ATTACKER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=30,
                skill_multiplier=0.6,  # 60% per hit
                scaling_preset="flurry_of_blows",
                effects=[
                    SkillEffect(effect_type="damage", value=60),
                    SkillEffect(effect_type="damage", value=60)  # Second hit
                ],
                description="Hits one front-row enemy twice for 60% ATK damage each."
            ),
            
            SkillDefinition(
                skill_id="armor_break",
                name="Armor Break",
                category=SkillCategory.ATTACKER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=20,
                skill_multiplier=0.8,
                scaling_preset="armor_break",
                effects=[SkillEffect(effect_type="armor_piercing_damage", value=80)],
                description="80% ATK damage, ignoring 50% of VIT."
            ),
            
            SkillDefinition(
                skill_id="heavy_slam",
                name="Heavy Slam",
                category=SkillCategory.ATTACKER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=15,
                skill_multiplier=1.5,
                scaling_preset="heavy_slam",
                effects=[
                    SkillEffect(effect_type="damage", value=150),
                    SkillEffect(effect_type="debuff", target_stat="spd", value=-50, duration=1, probability=1.0)
                ],
                description="150% ATK damage. User's SPD is halved next round."
            ),
            
            SkillDefinition(
                skill_id="cleave",
                name="Cleave",
                category=SkillCategory.ATTACKER,
                target_type=TargetType.FRONT_ROW_ENEMIES,
                power_weight=25,
                skill_multiplier=0.7,
                scaling_preset="cleave",
                effects=[SkillEffect(effect_type="damage", value=70)],
                description="70% ATK damage to all enemies in the front row."
            ),
            
            SkillDefinition(
                skill_id="execute",
                name="Execute",
                category=SkillCategory.ATTACKER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=15,
                skill_multiplier=1.0,
                scaling_preset="power_strike",
                effects=[SkillEffect(effect_type="execute_damage", value=100)],
                description="100% ATK damage. Damage is doubled if target is below 30% HP."
            ),
            
            SkillDefinition(
                skill_id="rampage",
                name="Rampage",
                category=SkillCategory.ATTACKER,
                target_type=TargetType.RANDOM_ENEMIES,
                power_weight=10,
                skill_multiplier=0.6,
                effects=[
                    SkillEffect(effect_type="damage", value=60),
                    SkillEffect(effect_type="damage", value=60),
                    SkillEffect(effect_type="damage", value=60)
                ],
                description="60% ATK damage to three random enemies, regardless of row."
            ),
            
            SkillDefinition(
                skill_id="bleeding_strike",
                name="Bleeding Strike",
                category=SkillCategory.ATTACKER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=20,
                skill_multiplier=0.75,
                effects=[
                    SkillEffect(effect_type="damage", value=75),
                    SkillEffect(effect_type="status", target_stat="bleed", duration=2, probability=1.0)
                ],
                description="75% ATK damage and applies 'Bleed' for 2 turns."
            )
        ]
        
        for skill in skills:
            self.skills[skill.skill_id] = skill
    
    def _add_mage_skills(self):
        """Add magical attacker skills"""
        
        skills = [
            SkillDefinition(
                skill_id="mana_bolt",
                name="Mana Bolt",
                category=SkillCategory.MAGE,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=50,
                skill_multiplier=1.0,
                scaling_preset="mana_bolt",
                effects=[SkillEffect(effect_type="magical_damage", value=100)],
                description="100% MAG damage to one front-row enemy."
            ),
            
            SkillDefinition(
                skill_id="chain_lightning",
                name="Chain Lightning",
                category=SkillCategory.MAGE,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=25,
                skill_multiplier=0.8,
                scaling_preset="chain_lightning",
                effects=[
                    SkillEffect(effect_type="magical_damage", value=80),
                    SkillEffect(effect_type="chain_damage", value=40)  # Jumps to another
                ],
                description="80% MAG damage to one target, jumps for 40% to another."
            ),
            
            SkillDefinition(
                skill_id="ignite",
                name="Ignite",
                category=SkillCategory.MAGE,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=20,
                skill_multiplier=0.7,
                effects=[
                    SkillEffect(effect_type="magical_damage", value=70),
                    SkillEffect(effect_type="status", target_stat="burn", duration=3, probability=1.0)
                ],
                description="70% MAG damage and applies 'Burn' to one target."
            ),
            
            SkillDefinition(
                skill_id="arcane_overload",
                name="Arcane Overload",
                category=SkillCategory.MAGE,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=15,
                skill_multiplier=1.6,
                effects=[
                    SkillEffect(effect_type="magical_damage", value=160),
                    SkillEffect(effect_type="recoil_damage", value=10)  # Self damage
                ],
                description="160% MAG damage. User suffers 10% recoil damage."
            ),
            
            SkillDefinition(
                skill_id="fireball",
                name="Fireball",
                category=SkillCategory.MAGE,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=25,
                skill_multiplier=0.9,
                scaling_preset="fireball",
                effects=[
                    SkillEffect(effect_type="magical_damage", value=90),
                    SkillEffect(effect_type="splash_damage", value=40)  # Adjacent targets
                ],
                description="90% MAG damage to the target and 40% to adjacent targets."
            ),
            
            SkillDefinition(
                skill_id="frost_nova",
                name="Frost Nova",
                category=SkillCategory.MAGE,
                target_type=TargetType.FRONT_ROW_ENEMIES,
                power_weight=20,
                skill_multiplier=0.6,
                scaling_preset="frost_nova",
                effects=[
                    SkillEffect(effect_type="magical_damage", value=60),
                    SkillEffect(effect_type="status", target_stat="slow", duration=1, probability=0.25)
                ],
                description="60% MAG damage to all front-row enemies; 25% chance to 'Slow'."
            ),
            
            SkillDefinition(
                skill_id="arcane_missile",
                name="Arcane Missile",
                category=SkillCategory.MAGE,
                target_type=TargetType.RANDOM_ENEMIES,
                power_weight=10,
                skill_multiplier=0.5,
                effects=[
                    SkillEffect(effect_type="magical_damage", value=50),
                    SkillEffect(effect_type="magical_damage", value=50),
                    SkillEffect(effect_type="magical_damage", value=50)
                ],
                description="Fires 3 missiles for 50% MAG damage to random enemies."
            ),
            
            SkillDefinition(
                skill_id="silence",
                name="Silence",
                category=SkillCategory.MAGE,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=15,
                skill_multiplier=0.5,
                effects=[
                    SkillEffect(effect_type="magical_damage", value=50),
                    SkillEffect(effect_type="status", target_stat="silence", duration=2, probability=1.0)
                ],
                description="50% MAG damage and prevents target from using Mage skills."
            )
        ]
        
        for skill in skills:
            self.skills[skill.skill_id] = skill
    
    def _add_healer_skills(self):
        """Add healing support skills"""
        
        skills = [
            SkillDefinition(
                skill_id="lesser_heal",
                name="Lesser Heal",
                category=SkillCategory.HEALER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=50,
                scaling_preset="lesser_heal",
                effects=[SkillEffect(effect_type="heal", value=100)],
                description="Restores a moderate amount of HP to one ally."
            ),
            
            SkillDefinition(
                skill_id="regen",
                name="Regen",
                category=SkillCategory.HEALER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=25,
                effects=[SkillEffect(effect_type="status", target_stat="regen", duration=3, probability=1.0)],
                description="Applies a 'Heal Over Time' effect to one ally."
            ),
            
            SkillDefinition(
                skill_id="greater_heal",
                name="Greater Heal",
                category=SkillCategory.HEALER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=20,
                cooldown=1,
                scaling_preset="greater_heal",
                effects=[SkillEffect(effect_type="heal", value=200)],
                description="Restores a large amount of HP. 1-turn cooldown."
            ),
            
            SkillDefinition(
                skill_id="cleanse",
                name="Cleanse",
                category=SkillCategory.HEALER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=15,
                effects=[SkillEffect(effect_type="cleanse_debuffs", value=0)],
                description="Removes all debuffs from one ally."
            ),
            
            SkillDefinition(
                skill_id="row_heal",
                name="Row Heal",
                category=SkillCategory.HEALER,
                target_type=TargetType.FRONT_ROW_ENEMIES,  # Note: Will be modified for allies
                power_weight=30,
                scaling_preset="row_heal",
                effects=[SkillEffect(effect_type="heal", value=60)],
                description="Restores a small amount of HP to all allies in a row."
            ),
            
            SkillDefinition(
                skill_id="mass_heal",
                name="Mass Heal",
                category=SkillCategory.HEALER,
                target_type=TargetType.ALL_ALLIES,
                power_weight=10,
                cooldown=2,
                effects=[SkillEffect(effect_type="heal", value=50)],
                description="Restores a small amount of HP to the entire team. 2-turn cooldown."
            ),
            
            SkillDefinition(
                skill_id="barrier",
                name="Barrier",
                category=SkillCategory.HEALER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=20,
                effects=[SkillEffect(effect_type="shield", value=100, duration=3)],
                description="Grants one ally a temporary HP shield."
            ),
            
            SkillDefinition(
                skill_id="resurrection",
                name="Resurrection",
                category=SkillCategory.HEALER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=5,
                cooldown=999,  # Once per battle
                effects=[SkillEffect(effect_type="revive", value=25)],
                description="Revives a defeated ally with 25% HP. Once per battle."
            )
        ]
        
        for skill in skills:
            self.skills[skill.skill_id] = skill
    
    def _add_buffer_debuffer_skills(self):
        """Add buff and debuff skills"""
        
        skills = [
            SkillDefinition(
                skill_id="rally",
                name="Rally",
                category=SkillCategory.BUFFER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=40,
                scaling_preset="rally_weaken",
                effects=[
                    SkillEffect(effect_type="buff", target_stat="atk", value=20, duration=3),
                    SkillEffect(effect_type="buff", target_stat="mag", value=20, duration=3)
                ],
                description="+20% ATK & MAG for one target."
            ),
            
            SkillDefinition(
                skill_id="weaken",
                name="Weaken",
                category=SkillCategory.DEBUFFER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=40,
                scaling_preset="rally_weaken",
                effects=[
                    SkillEffect(effect_type="debuff", target_stat="atk", value=-20, duration=3),
                    SkillEffect(effect_type="debuff", target_stat="mag", value=-20, duration=3)
                ],
                description="-20% ATK & MAG for one target."
            ),
            
            SkillDefinition(
                skill_id="fortify",
                name="Fortify",
                category=SkillCategory.BUFFER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=40,
                scaling_preset="fortify_break",
                effects=[
                    SkillEffect(effect_type="buff", target_stat="vit", value=20, duration=3),
                    SkillEffect(effect_type="buff", target_stat="spr", value=20, duration=3)
                ],
                description="+20% VIT & SPR for one target."
            ),
            
            SkillDefinition(
                skill_id="break",
                name="Break",
                category=SkillCategory.DEBUFFER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=40,
                scaling_preset="fortify_break",
                effects=[
                    SkillEffect(effect_type="debuff", target_stat="vit", value=-20, duration=3),
                    SkillEffect(effect_type="debuff", target_stat="spr", value=-20, duration=3)
                ],
                description="-20% VIT & SPR for one target."
            ),
            
            SkillDefinition(
                skill_id="haste",
                name="Haste",
                category=SkillCategory.BUFFER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=25,
                scaling_preset="haste_slow",
                effects=[SkillEffect(effect_type="buff", target_stat="spd", value=30, duration=3)],
                description="+30% SPD for one target."
            ),
            
            SkillDefinition(
                skill_id="slow",
                name="Slow",
                category=SkillCategory.DEBUFFER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=25,
                scaling_preset="haste_slow",
                effects=[SkillEffect(effect_type="debuff", target_stat="spd", value=-30, duration=3)],
                description="-30% SPD for one target."
            ),
            
            SkillDefinition(
                skill_id="focus",
                name="Focus",
                category=SkillCategory.BUFFER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=20,
                scaling_preset="focus_curse",
                effects=[SkillEffect(effect_type="buff", target_stat="lck", value=40, duration=3)],
                description="+40% LCK for one target."
            ),
            
            SkillDefinition(
                skill_id="curse",
                name="Curse",
                category=SkillCategory.DEBUFFER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=20,
                scaling_preset="focus_curse",
                effects=[SkillEffect(effect_type="debuff", target_stat="lck", value=-40, duration=3)],
                description="-40% LCK for one target."
            )
        ]
        
        for skill in skills:
            self.skills[skill.skill_id] = skill
    
    def _add_defender_skills(self):
        """Add defensive skills"""
        
        skills = [
            SkillDefinition(
                skill_id="guard_stance",
                name="Guard Stance",
                category=SkillCategory.DEFENDER,
                target_type=TargetType.SELF,
                power_weight=50,
                effects=[
                    SkillEffect(effect_type="buff", target_stat="vit", value=100, duration=1),
                    SkillEffect(effect_type="buff", target_stat="spr", value=100, duration=1)
                ],
                description="User doubles their VIT and SPR until their next turn."
            ),
            
            SkillDefinition(
                skill_id="provoke",
                name="Provoke",
                category=SkillCategory.DEFENDER,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=30,
                effects=[SkillEffect(effect_type="status", target_stat="provoked", duration=1, probability=1.0)],
                description="Forces a single enemy to target the user on their next attack."
            ),
            
            SkillDefinition(
                skill_id="aegis",
                name="Aegis",
                category=SkillCategory.DEFENDER,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=15,
                effects=[SkillEffect(effect_type="status", target_stat="protected", duration=1, probability=1.0)],
                description="User takes all damage intended for one specific ally until their next turn."
            ),
            
            SkillDefinition(
                skill_id="shield_wall",
                name="Shield Wall",
                category=SkillCategory.DEFENDER,
                target_type=TargetType.FRONT_ROW_ENEMIES,  # Will be modified for allies
                power_weight=20,
                effects=[SkillEffect(effect_type="buff", target_stat="vit", value=25, duration=2)],
                description="Increases the VIT of the entire front row by 25% for 2 turns."
            ),
            
            SkillDefinition(
                skill_id="last_stand",
                name="Last Stand",
                category=SkillCategory.DEFENDER,
                target_type=TargetType.SELF,
                power_weight=5,
                cooldown=999,  # Once per battle
                effects=[SkillEffect(effect_type="status", target_stat="immortal", duration=1, probability=1.0)],
                description="For one turn, the user's HP cannot drop below 1. Once per battle."
            )
        ]
        
        for skill in skills:
            self.skills[skill.skill_id] = skill
    
    def _add_tactician_skills(self):
        """Add utility/tactician skills"""
        
        skills = [
            SkillDefinition(
                skill_id="swift_strike",
                name="Swift Strike",
                category=SkillCategory.TACTICIAN,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=30,
                skill_multiplier=0.7,
                effects=[SkillEffect(effect_type="priority_damage", value=70)],
                description="A high-priority 70% ATK damage attack."
            ),
            
            SkillDefinition(
                skill_id="mirage",
                name="Mirage",
                category=SkillCategory.TACTICIAN,
                target_type=TargetType.SELF,
                power_weight=15,
                effects=[SkillEffect(effect_type="status", target_stat="dodge", duration=1, probability=1.0)],
                description="Grants user a 'Guaranteed Dodge' buff against the next single-target attack."
            ),
            
            SkillDefinition(
                skill_id="study_foe",
                name="Study Foe",
                category=SkillCategory.TACTICIAN,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=25,
                effects=[SkillEffect(effect_type="status", target_stat="vulnerable", duration=1, probability=1.0)],
                description="Applies 'Vulnerable' to one enemy (next attack is a guaranteed crit)."
            ),
            
            SkillDefinition(
                skill_id="accelerate",
                name="Accelerate",
                category=SkillCategory.TACTICIAN,
                target_type=TargetType.SINGLE_ALLY,
                power_weight=10,
                effects=[SkillEffect(effect_type="gauge_boost", value=999)],
                description="Target ally's Action Gauge is set to 999."
            ),
            
            SkillDefinition(
                skill_id="snipe",
                name="Snipe",
                category=SkillCategory.TACTICIAN,
                target_type=TargetType.SINGLE_ENEMY,
                power_weight=20,
                skill_multiplier=0.9,
                can_target_back_row=True,
                effects=[SkillEffect(effect_type="damage", value=90)],
                description="Deals 90% ATK damage to a single enemy in the back row."
            ),
            
            SkillDefinition(
                skill_id="smoke_bomb",
                name="Smoke Bomb",
                category=SkillCategory.TACTICIAN,
                target_type=TargetType.FRONT_ROW_ENEMIES,  # Will be modified for allies
                power_weight=15,
                effects=[SkillEffect(effect_type="buff", target_stat="dodge", value=20, duration=1)],
                description="Increases the dodge chance of all allies in the user's row by 20% for 1 turn."
            )
        ]
        
        for skill in skills:
            self.skills[skill.skill_id] = skill
    
    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """Get a skill definition by ID"""
        return self.skills.get(skill_id)
    
    def get_skills_by_category(self, category: SkillCategory) -> List[SkillDefinition]:
        """Get all skills in a category"""
        return [skill for skill in self.skills.values() if skill.category == category]
    
    def get_all_skills(self) -> List[SkillDefinition]:
        """Get all skills"""
        return list(self.skills.values())
    
    def create_combat_action(self, skill_id: str, actor_id: str, target_ids: List[str]) -> Optional[CombatAction]:
        """Convert a skill to a combat action"""
        skill = self.get_skill(skill_id)
        if not skill:
            logger.warning("Unknown skill: %s", skill_id)
            return None
        
        # Determine action type based on skill category
        if skill.category in [SkillCategory.ATTACKER, SkillCategory.MAGE, SkillCategory.TACTICIAN]:
            action_type = ActionType.ATTACK
        elif skill.category == SkillCategory.HEALER:
            action_type = ActionType.SKILL  # Use SKILL for healing
        else:
            action_type = ActionType.SKILL
        
        return CombatAction(
            action_id=f"{skill_id}_{actor_id}",
            actor_id=actor_id,
            action_type=action_type,
            target_ids=target_ids,
            power=skill.skill_multiplier,
            accuracy=1.0,  # Will be modified by specific skill effects
            critical_chance=0.05,  # Base 5%
            metadata={
                "skill_definition": skill,
                "scaling_preset": skill.scaling_preset
            }
        )

# Global skill library instance
skill_library = SkillLibrary()
