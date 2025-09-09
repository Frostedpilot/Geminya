"""
Abilities Component System

This module implements the character abilities system including:
- Active skills (Basic, Normal, Signature, Ultimate, Series)
- Passive abilities (Generic, Signature, Series)
- Skill execution pipeline with validation and effects
- Cooldown and cost management
- Event-driven skill triggers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Set, Any, Optional, Callable, Union
import logging

from . import BaseComponent
from ..core.event_system import GameEvent, event_bus

# Set up logging
logger = logging.getLogger(__name__)

class SkillType(Enum):
    """Types of active skills"""
    BASIC_ATTACK = "basic_attack"
    NORMAL = "normal"
    SIGNATURE = "signature"
    ULTIMATE = "ultimate"
    SERIES = "series"

class PassiveType(Enum):
    """Types of passive abilities"""
    GENERIC = "generic"
    SIGNATURE = "signature"
    SERIES = "series"

class TargetType(Enum):
    """Skill targeting types"""
    SINGLE_ENEMY = "single_enemy"
    SINGLE_ALLY = "single_ally"
    SELF = "self"
    ALL_ENEMIES = "all_enemies"
    ALL_ALLIES = "all_allies"
    ALL_CHARACTERS = "all_characters"
    RANDOM_ENEMY = "random_enemy"
    RANDOM_ALLY = "random_ally"
    FRONT_ROW = "front_row"
    BACK_ROW = "back_row"
    
    # New target types for advanced skills system
    SINGLE_FRONT_ENEMY = "single_front_enemy"
    SINGLE_BACK_ENEMY = "single_back_enemy"
    FRONT_ROW_ENEMIES = "front_row_enemies"
    FRONT_ROW_ALLIES = "front_row_allies"
    ROW_ALLIES = "row_allies"
    ROW_ENEMIES = "row_enemies"
    THREE_RANDOM_ENEMIES = "three_random_enemies"
    RANDOM_ENEMIES = "random_enemies"
    DEFEATED_ALLY = "defeated_ally"

class SkillEffectType(Enum):
    """Types of skill effects"""
    # Basic effects
    DAMAGE = "damage"
    HEAL = "heal"
    STATUS_EFFECT = "status_effect"
    
    # Advanced damage effects
    CHAIN_DAMAGE = "chain_damage"
    SPLASH_DAMAGE = "splash_damage"
    RECOIL_DAMAGE = "recoil_damage"
    
    # Conditional effects
    CONDITIONAL_MULTIPLIER = "conditional_multiplier"
    
    # Armor/Defense effects
    ARMOR_PENETRATION = "armor_penetration"
    
    # Combat mechanics
    COUNTER_ATTACK = "counter_attack"
    DAMAGE_REDIRECT = "damage_redirect"
    
    # Utility effects
    CLEANSE_DEBUFFS = "cleanse_debuffs"
    DISPEL_BUFF = "dispel_buff"
    SHIELD = "shield"
    GUARANTEED_DODGE = "guaranteed_dodge"
    ACTION_GAUGE_BOOST = "action_gauge_boost"
    
    # Magic effects
    REFLECT_MAGIC = "reflect_magic"
    
    # Special effects
    REVIVE = "revive"

class SkillState(Enum):
    """Skill availability states"""
    AVAILABLE = auto()
    ON_COOLDOWN = auto()
    INSUFFICIENT_RESOURCES = auto()
    CONDITIONS_NOT_MET = auto()
    DISABLED = auto()

@dataclass
class SkillCost:
    """Represents the cost to use a skill"""
    hp_cost: float = 0.0
    action_cost: float = 0.0  # Action gauge cost
    special_cost: Dict[str, float] = field(default_factory=dict)  # Custom resource costs
    
    def can_afford(self, character) -> bool:
        """Check if character can afford this cost"""
        # Check HP cost
        if self.hp_cost > 0 and character.get_stat("hp") <= self.hp_cost:
            return False
            
        # Check action gauge cost
        if self.action_cost > 0 and character.state.action_gauge < self.action_cost:
            return False
            
        # Check special costs (future expansion)
        for resource, cost in self.special_cost.items():
            if not character.has_resource(resource, cost):
                return False
                
        return True
    
    def pay_cost(self, character) -> bool:
        """Pay the skill cost"""
        if not self.can_afford(character):
            return False
            
        # Pay HP cost
        if self.hp_cost > 0:
            character.take_damage(self.hp_cost, "skill_cost", character.character_id)
            
        # Pay action gauge cost
        if self.action_cost > 0:
            character.state.action_gauge = max(0, character.state.action_gauge - self.action_cost)
            
        # Pay special costs
        for resource, cost in self.special_cost.items():
            character.consume_resource(resource, cost)
            
        return True

@dataclass
class SkillCondition:
    """Represents a condition that must be met to use a skill"""
    condition_id: str
    description: str
    check_function: Callable[['Character'], bool]  # Function that returns True if condition is met
    
    def is_met(self, character) -> bool:
        """Check if the condition is currently met"""
        try:
            return self.check_function(character)
        except Exception as e:
            logger.warning("Error checking skill condition %s: %s", self.condition_id, e)
            return False

class BaseSkill(ABC):
    """Base class for all active skills"""
    
    def __init__(
        self,
        skill_id: str,
        name: str,
        description: str,
        skill_type: SkillType,
        target_type: TargetType,
        cooldown: int = 0,
        cost: Optional[SkillCost] = None,
        conditions: Optional[List[SkillCondition]] = None,
        priority: int = 100  # Higher = more priority
    ):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.skill_type = skill_type
        self.target_type = target_type
        self.cooldown = cooldown
        self.cost = cost or SkillCost()
        self.conditions = conditions or []
        self.priority = priority
        
        # Runtime state
        self.current_cooldown = 0
        self.times_used = 0
        self.total_damage_dealt = 0.0
        self.total_healing_done = 0.0
        
    def get_state(self, character) -> SkillState:
        """Get the current availability state of this skill"""
        if self.current_cooldown > 0:
            return SkillState.ON_COOLDOWN
            
        if not self.cost.can_afford(character):
            return SkillState.INSUFFICIENT_RESOURCES
            
        for condition in self.conditions:
            if not condition.is_met(character):
                return SkillState.CONDITIONS_NOT_MET
                
        return SkillState.AVAILABLE
    
    def can_use(self, character) -> bool:
        """Check if this skill can be used"""
        return self.get_state(character) == SkillState.AVAILABLE
    
    def get_valid_targets(self, caster, battle_context) -> List:
        """Get list of valid targets for this skill"""
        if not battle_context:
            return []
            
        try:
            # Get all characters in battle
            all_characters = battle_context.get_all_characters()
            if not all_characters:
                return []
            
            # Filter based on targeting rules
            valid_targets = []
            
            # Determine targeting based on skill properties
            target_type = getattr(self, 'target_type', 'enemy')
            target_count = getattr(self, 'target_count', 1)
            
            if target_type == 'self':
                valid_targets = [caster]
            elif target_type == 'ally':
                valid_targets = [char for char in all_characters 
                               if char.team_id == caster.team_id and char.is_alive()]
            elif target_type == 'enemy':
                enemy_team = 'team_2' if caster.team_id == 'team_1' else 'team_1'
                valid_targets = [char for char in all_characters 
                               if char.team_id == enemy_team and char.is_alive()]
            elif target_type == 'all':
                valid_targets = [char for char in all_characters if char.is_alive()]
            
            # Limit to target count if specified
            if target_count > 0 and len(valid_targets) > target_count:
                valid_targets = valid_targets[:target_count]
                
            return valid_targets
            
        except Exception as e:
            logger.warning(f"Failed to get valid targets for skill {self.skill_id}: {e}")
            return []
    
    def execute(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """Execute the skill with full pipeline"""
        result = {
            "success": False,
            "skill_id": self.skill_id,
            "caster_id": caster.character_id,
            "targets": [t.character_id if hasattr(t, 'character_id') else str(t) for t in targets],
            "effects": [],
            "damage_dealt": 0.0,
            "healing_done": 0.0,
            "error": None
        }
        
        try:
            # Phase 1: Validation
            if not self.validate_execution(caster, targets, battle_context):
                result["error"] = "Validation failed"
                return result
            
            # Phase 2: Pay costs
            if not self.cost.pay_cost(caster):
                result["error"] = "Could not pay skill cost"
                return result
            
            # Phase 3: Execute skill effects
            skill_result = self.execute_effects(caster, targets, battle_context)
            result.update(skill_result)
            
            # Phase 4: Apply cooldown and update stats
            if result["success"]:
                self.current_cooldown = self.cooldown
                self.times_used += 1
                self.total_damage_dealt += result.get("damage_dealt", 0)
                self.total_healing_done += result.get("healing_done", 0)
                
                # Publish skill used event
                skill_event = GameEvent(
                    event_type="skill.used",
                    source=caster.character_id,
                    data={
                        "skill_id": self.skill_id,
                        "caster_id": caster.character_id,
                        "targets": result["targets"],
                        "result": result
                    }
                )
                event_bus.publish(skill_event)
                
        except Exception as e:
            logger.error("Error executing skill %s: %s", self.skill_id, e)
            result["error"] = str(e)
            
        return result
    
    @abstractmethod
    def validate_execution(self, caster, targets: List, battle_context) -> bool:
        """Validate that the skill can be executed"""
        raise NotImplementedError
    
    @abstractmethod
    def execute_effects(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """Execute the main skill effects"""
        raise NotImplementedError
    
    def update(self, delta_time: float = 1.0):
        """Update skill state (mainly cooldowns)"""
        if self.current_cooldown > 0:
            self.current_cooldown = max(0, self.current_cooldown - delta_time)
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize skill state for persistence"""
        return {
            "skill_id": self.skill_id,
            "current_cooldown": self.current_cooldown,
            "times_used": self.times_used,
            "total_damage_dealt": self.total_damage_dealt,
            "total_healing_done": self.total_healing_done
        }
    
    def deserialize(self, data: Dict[str, Any]):
        """Restore skill state from data"""
        self.current_cooldown = data.get("current_cooldown", 0)
        self.times_used = data.get("times_used", 0)
        self.total_damage_dealt = data.get("total_damage_dealt", 0.0)
        self.total_healing_done = data.get("total_healing_done", 0.0)
    
    def __str__(self) -> str:
        return f"Skill({self.skill_id}: {self.name})"

class BasePassive(ABC):
    """Base class for all passive abilities"""
    
    def __init__(
        self,
        passive_id: str,
        name: str,
        description: str,
        passive_type: PassiveType,
        conditions: Optional[List[SkillCondition]] = None
    ):
        self.passive_id = passive_id
        self.name = name
        self.description = description
        self.passive_type = passive_type
        self.conditions = conditions or []
        
        # Runtime state
        self.active = True
        self.times_triggered = 0
        
    def is_active(self, character) -> bool:
        """Check if this passive is currently active"""
        if not self.active:
            return False
            
        for condition in self.conditions:
            if not condition.is_met(character):
                return False
                
        return True
    
    @abstractmethod
    def apply_effects(self, character):
        """Apply the passive's effects to the character"""
        raise NotImplementedError
    
    @abstractmethod
    def remove_effects(self, character):
        """Remove the passive's effects from the character"""
        raise NotImplementedError
    
    def on_event(self, event: GameEvent, character) -> GameEvent:
        """Handle game events (for reactive passives)"""
        return event
    
    def update(self, character, delta_time: float = 1.0):
        """Update passive state"""
        pass
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize passive state"""
        return {
            "passive_id": self.passive_id,
            "active": self.active,
            "times_triggered": self.times_triggered
        }
    
    def deserialize(self, data: Dict[str, Any]):
        """Restore passive state"""
        self.active = data.get("active", True)
        self.times_triggered = data.get("times_triggered", 0)
    
    def __str__(self) -> str:
        return f"Passive({self.passive_id}: {self.name})"

class DataDrivenSkill(BaseSkill):
    """A skill implementation that uses data from the new skills system"""
    
    def __init__(self, skill_id: str, name: str, description: str, skill_type: SkillType,
                 target_type: TargetType, cooldown: int, cost: SkillCost, skill_data: Dict[str, Any]):
        super().__init__(skill_id, name, description, skill_type, target_type, cooldown, cost)
        self.skill_data = skill_data
        
        # Extract scaling parameters
        self.power_weight = skill_data.get("power_weight", 50)
        self.floor = skill_data.get("floor", 20)
        self.sc1 = skill_data.get("sc1", 50)
        self.sc2 = skill_data.get("sc2", 200)
        self.post_cap_rate = skill_data.get("post_cap_rate", 0.5)
        
        # Extract scaling info
        scaling = skill_data.get("scaling", {})
        self.primary_stat = scaling.get("primary_stat", "atk")
        self.skill_multiplier = scaling.get("skill_multiplier", 1.0)
        
        # Extract effects
        self.effects = skill_data.get("effects", [])
    
    def calculate_damage(self, caster, target) -> float:
        """Calculate damage using the universal scaling system"""
        from ..core.universal_scaling import UniversalScaling, ScalingParameters
        
        # Get stats as dict
        caster_stats = {
            "atk": getattr(caster.stats, 'get_stat', lambda x: 100)("atk"),
            "mag": getattr(caster.stats, 'get_stat', lambda x: 100)("mag"),
            "int": getattr(caster.stats, 'get_stat', lambda x: 100)("int"),
            "spr": getattr(caster.stats, 'get_stat', lambda x: 100)("spr"),
        }
        
        target_stats = {
            "vit": getattr(target.stats, 'get_stat', lambda x: 50)("vit"),
            "spr": getattr(target.stats, 'get_stat', lambda x: 50)("spr"),
        }
        
        # Create scaling parameters
        scaling_params = ScalingParameters(
            floor=self.floor,
            ceiling=0,
            softcap_1=self.sc1,
            softcap_2=self.sc2,
            post_cap_rate=self.post_cap_rate
        )
        
        # Determine if magical damage
        is_magical = self.primary_stat == "mag"
        
        # Calculate final damage
        damage = UniversalScaling.calculate_final_damage(
            caster_stats=caster_stats,
            target_stats=target_stats,
            scaling_params=scaling_params,
            skill_multiplier=self.skill_multiplier,
            is_magical=is_magical
        )
        
        return damage
    
    def validate_execution(self, caster, targets: List, battle_context) -> bool:
        """Validate that the skill can be executed"""
        return len(targets) > 0
    
    def get_ai_priority(self, caster, battle_context) -> float:
        """Get AI priority for this skill"""
        return 1.0
    
    def execute_effects(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """Execute all skill effects using the dedicated effect handler"""
        from .skill_effects import SkillEffectHandler
        
        result = SkillEffectHandler.execute_skill_effects(
            effects=self.effects,
            caster=caster,
            targets=targets,
            battle_context=battle_context
        )
        
        # Add success flag
        result["success"] = True
        
        return result

class AbilitiesComponent(BaseComponent):
    """Component that manages character's skills and passive abilities"""
    
    def __init__(self, character_id: str):
        super().__init__(character_id)
        
        # Character reference (set after initialization to avoid circular imports)
        self._character = None
        
        # Skill storage by type
        self.skills: Dict[SkillType, List[BaseSkill]] = {
            skill_type: [] for skill_type in SkillType
        }
        self.skills_by_id: Dict[str, BaseSkill] = {}
        
        # Passive storage by type
        self.passives: Dict[PassiveType, List[BasePassive]] = {
            passive_type: [] for passive_type in PassiveType
        }
        self.passives_by_id: Dict[str, BasePassive] = {}
        
        # Quick access lists
        self.available_skills: List[BaseSkill] = []
        self.active_passives: List[BasePassive] = []
        
        # Statistics
        self.total_skills_used = 0
        self.total_damage_dealt = 0.0
        self.total_healing_done = 0.0
        
        # Register for events
        self.register_event_handlers()
    
    def initialize(self, character_data: Dict[str, Any]):
        """Initialize abilities from character data"""
        # Add basic attack skill (all characters have this)
        self.add_basic_attack()
        
        # Load skills from data
        skills_data = character_data.get("skills", {})
        for skill_type_str, skill_list in skills_data.items():
            skill_type = SkillType(skill_type_str)
            for skill_data in skill_list:
                skill = self.create_skill_from_data(skill_data, skill_type)
                if skill:
                    self.add_skill(skill)
        
        # Load passives from data
        passives_data = character_data.get("passives", {})
        for passive_type_str, passive_list in passives_data.items():
            passive_type = PassiveType(passive_type_str)
            for passive_data in passive_list:
                passive = self.create_passive_from_data(passive_data, passive_type)
                if passive:
                    self.add_passive(passive)
        
        # Apply all passive effects
        self.refresh_passive_effects()
    
    def add_basic_attack(self):
        """Add the universal basic attack skill"""
        from .skill_implementations import BasicAttackSkill
        basic_attack = BasicAttackSkill()
        self.add_skill(basic_attack)
    
    def create_skill_from_data(self, skill_data: Dict[str, Any], skill_type: SkillType) -> Optional[BaseSkill]:
        """Create a skill instance from data"""
        # Create a data-driven skill from the new skill format
        logger.info("Creating skill from data: %s", skill_data.get("name", "unknown"))
        
        # Extract basic skill info
        skill_id = skill_data.get("name", "unknown").lower().replace(" ", "_")
        name = skill_data.get("name", "Unknown Skill")
        description = skill_data.get("description", "")
        target_type_str = skill_data.get("target_type", "single_enemy")
        
        # Convert target type string to enum
        try:
            target_type = TargetType(target_type_str)
        except ValueError:
            logger.warning("Unknown target type: %s, defaulting to single_enemy", target_type_str)
            target_type = TargetType.SINGLE_ENEMY
        
        # Create skill cost
        cooldown = skill_data.get("cooldown", 0)
        cost = SkillCost()  # Default cost for now
        
        # Create the data-driven skill
        skill = DataDrivenSkill(
            skill_id=skill_id,
            name=name,
            description=description,
            skill_type=skill_type,
            target_type=target_type,
            cooldown=cooldown,
            cost=cost,
            skill_data=skill_data
        )
        
        return skill
    
    def create_passive_from_data(self, passive_data: Dict[str, Any], passive_type: PassiveType) -> Optional[BasePassive]:
        """Create a passive instance from data"""
        try:
            passive_id = passive_data.get("passive_id")
            if not passive_id:
                logger.warning("Passive data missing 'passive_id'")
                return None
            
            # Import here to avoid circular imports
            from ..core.universal_skill_library import UniversalSkillLibrary
            
            # Try to get passive from universal library
            skill_lib = UniversalSkillLibrary()
            passive_template = skill_lib.get_passive_by_id(passive_id)
            
            if passive_template:
                # Create passive instance from template
                passive = BasePassive(
                    passive_id=passive_id,
                    name=passive_template.get("name", passive_id),
                    description=passive_template.get("description", ""),
                    passive_type=passive_type,
                    triggers=passive_template.get("triggers", []),
                    effects=passive_template.get("effects", [])
                )
                logger.info(f"Created passive from universal library: {passive_id}")
                return passive
            
            # Fallback: create basic passive from data
            passive = BasePassive(
                passive_id=passive_id,
                name=passive_data.get("name", passive_id),
                description=passive_data.get("description", ""),
                passive_type=passive_type,
                triggers=passive_data.get("triggers", []),
                effects=passive_data.get("effects", [])
            )
            
            logger.info(f"Created basic passive from data: {passive_id}")
            return passive
            
        except Exception as e:
            logger.error(f"Failed to create passive from data: {e}")
            return None
    
    def add_skill(self, skill: BaseSkill):
        """Add a skill to the character"""
        if skill.skill_id in self.skills_by_id:
            logger.warning("Skill %s already exists, replacing", skill.skill_id)
        
        self.skills[skill.skill_type].append(skill)
        self.skills_by_id[skill.skill_id] = skill
        self.refresh_available_skills()
        
        logger.info("Added skill %s to character %s", skill.skill_id, self.character_id)
    
    def remove_skill(self, skill_id: str) -> bool:
        """Remove a skill from the character"""
        if skill_id not in self.skills_by_id:
            return False
        
        skill = self.skills_by_id[skill_id]
        self.skills[skill.skill_type].remove(skill)
        del self.skills_by_id[skill_id]
        self.refresh_available_skills()
        
        logger.info("Removed skill %s from character %s", skill_id, self.character_id)
        return True
    
    def add_passive(self, passive: BasePassive):
        """Add a passive ability to the character"""
        if passive.passive_id in self.passives_by_id:
            logger.warning("Passive %s already exists, replacing", passive.passive_id)
            self.remove_passive(passive.passive_id)
        
        self.passives[passive.passive_type].append(passive)
        self.passives_by_id[passive.passive_id] = passive
        
        # Apply passive effects immediately
        character = self.get_character()
        if character and passive.is_active(character):
            passive.apply_effects(character)
            self.active_passives.append(passive)
        
        logger.info("Added passive %s to character %s", passive.passive_id, self.character_id)
    
    def remove_passive(self, passive_id: str) -> bool:
        """Remove a passive ability from the character"""
        if passive_id not in self.passives_by_id:
            return False
        
        passive = self.passives_by_id[passive_id]
        
        # Remove effects first
        character = self.get_character()
        if character:
            passive.remove_effects(character)
        
        # Remove from storage
        self.passives[passive.passive_type].remove(passive)
        del self.passives_by_id[passive_id]
        
        if passive in self.active_passives:
            self.active_passives.remove(passive)
        
        logger.info("Removed passive %s from character %s", passive_id, self.character_id)
        return True
    
    def get_character(self):
        """Get the character this component belongs to"""
        return self._character
    
    def set_character(self, character):
        """Set the character reference for this component"""
        self._character = character
    
    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        """Get a skill by ID"""
        return self.skills_by_id.get(skill_id)
    
    def get_passive(self, passive_id: str) -> Optional[BasePassive]:
        """Get a passive by ID"""
        return self.passives_by_id.get(passive_id)
    
    def get_available_skills(self, character=None) -> List[BaseSkill]:
        """Get all currently available skills"""
        if not character:
            character = self.get_character()
        
        if not character:
            return []
        
        available = []
        for skill in self.skills_by_id.values():
            if skill.can_use(character):
                available.append(skill)
        
        # Sort by priority (higher priority first)
        available.sort(key=lambda s: (s.skill_type.value, -s.priority))
        return available
    
    def get_skills_by_type(self, skill_type: SkillType) -> List[BaseSkill]:
        """Get all skills of a specific type"""
        return self.skills[skill_type].copy()
    
    def get_passives_by_type(self, passive_type: PassiveType) -> List[BasePassive]:
        """Get all passives of a specific type"""
        return self.passives[passive_type].copy()
    
    def refresh_available_skills(self):
        """Refresh the list of available skills"""
        character = self.get_character()
        if character:
            self.available_skills = self.get_available_skills(character)
    
    def refresh_passive_effects(self):
        """Refresh all passive effects"""
        character = self.get_character()
        if not character:
            return
        
        # Remove all passive effects first
        for passive in self.active_passives:
            passive.remove_effects(character)
        
        # Reapply active passives
        self.active_passives.clear()
        for passive in self.passives_by_id.values():
            if passive.is_active(character):
                passive.apply_effects(character)
                self.active_passives.append(passive)
    
    def update(self, delta_time: float = 1.0):
        """Update all skills and passives"""
        character = self.get_character()
        
        # Update skill cooldowns
        for skill in self.skills_by_id.values():
            skill.update(delta_time)
        
        # Update passives
        if character:
            for passive in self.passives_by_id.values():
                passive.update(character, delta_time)
        
        # Refresh availability
        self.refresh_available_skills()
    
    def register_event_handlers(self):
        """Register event handlers for abilities"""
        # Register for events that passives might care about
        handler_id = event_bus.register_global_handler(self.on_global_event, priority=500)
        self.event_listeners.append(handler_id)
    
    def on_global_event(self, event: GameEvent) -> GameEvent:
        """Handle events for passive abilities"""
        character = self.get_character()
        if not character:
            return event
        
        # Let active passives handle the event
        for passive in self.active_passives:
            event = passive.on_event(event, character)
            if event.cancelled:
                break
        
        return event
    
    def get_data(self) -> Dict[str, Any]:
        """Get component data for serialization"""
        skills_data = {}
        for skill_type, skill_list in self.skills.items():
            skills_data[skill_type.value] = [skill.serialize() for skill in skill_list]
        
        passives_data = {}
        for passive_type, passive_list in self.passives.items():
            passives_data[passive_type.value] = [passive.serialize() for passive in passive_list]
        
        return {
            "skills": skills_data,
            "passives": passives_data,
            "total_skills_used": self.total_skills_used,
            "total_damage_dealt": self.total_damage_dealt,
            "total_healing_done": self.total_healing_done
        }
    
    def set_data(self, data: Dict[str, Any]):
        """Set component data from deserialization"""
        # Restore statistics
        self.total_skills_used = data.get("total_skills_used", 0)
        self.total_damage_dealt = data.get("total_damage_dealt", 0.0)
        self.total_healing_done = data.get("total_healing_done", 0.0)
        
        # Restore skill states
        skills_data = data.get("skills", {})
        for skill_type_str, skill_list in skills_data.items():
            skill_type = SkillType(skill_type_str)
            for i, skill_data in enumerate(skill_list):
                if i < len(self.skills[skill_type]):
                    self.skills[skill_type][i].deserialize(skill_data)
        
        # Restore passive states
        passives_data = data.get("passives", {})
        for passive_type_str, passive_list in passives_data.items():
            passive_type = PassiveType(passive_type_str)
            for i, passive_data in enumerate(passive_list):
                if i < len(self.passives[passive_type]):
                    self.passives[passive_type][i].deserialize(passive_data)
        
        # Refresh states
        self.refresh_available_skills()
        self.refresh_passive_effects()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of abilities for display"""
        return {
            "total_skills": len(self.skills_by_id),
            "total_passives": len(self.passives_by_id),
            "available_skills": len(self.available_skills),
            "active_passives": len(self.active_passives),
            "skills_by_type": {
                skill_type.value: len(skill_list) 
                for skill_type, skill_list in self.skills.items()
            },
            "passives_by_type": {
                passive_type.value: len(passive_list)
                for passive_type, passive_list in self.passives.items()
            },
            "total_skills_used": self.total_skills_used,
            "total_damage_dealt": self.total_damage_dealt,
            "total_healing_done": self.total_healing_done
        }
    
    def __str__(self) -> str:
        return f"AbilitiesComponent({self.character_id}: {len(self.skills_by_id)} skills, {len(self.passives_by_id)} passives)"
