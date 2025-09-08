# Implementation Guide - Step 3: Abilities and Skills System

## Character Abilities and Skill Execution

### Overview

This step implements the abilities component and the core skill system. Characters will be able to use skills with dynamic targeting, cooldown management, and effect application. This includes the foundation for the universal skill library described in the game design.

### Prerequisites

- Completed Step 1 (Foundation Setup)
- Completed Step 2 (Component System)
- Understanding of skill definitions and targeting systems

### Step 3.1: Abilities Component Implementation

Create the abilities component that manages skill availability and cooldowns:

**File: `src/game/components/abilities_component.py`**

```python
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

from . import BaseComponent
from ..core.event_system import GameEvent, event_bus

class SkillType(Enum):
    """Types of skills"""
    ACTIVE = "active"
    PASSIVE = "passive"
    SIGNATURE = "signature"
    REACTION = "reaction"

class TargetType(Enum):
    """Valid targeting options"""
    SINGLE_ENEMY = "single_enemy"
    SINGLE_ALLY = "single_ally"
    SINGLE_ANY = "single_any"
    ALL_ENEMIES = "all_enemies"
    ALL_ALLIES = "all_allies"
    ALL_CHARACTERS = "all_characters"
    FRONT_ROW_ENEMIES = "front_row_enemies"
    BACK_ROW_ENEMIES = "back_row_enemies"
    FRONT_ROW_ALLIES = "front_row_allies"
    BACK_ROW_ALLIES = "back_row_allies"
    SELF = "self"
    RANDOM_ENEMY = "random_enemy"
    RANDOM_ALLY = "random_ally"

@dataclass
class SkillInstance:
    """An available skill instance for a character"""
    skill_id: str
    skill_type: SkillType
    base_data: Dict[str, Any] = field(default_factory=dict)
    current_cooldown: int = 0
    max_cooldown: int = 0
    uses_remaining: Optional[int] = None  # None = unlimited
    max_uses: Optional[int] = None
    disabled: bool = False
    modifications: Dict[str, Any] = field(default_factory=dict)
    
    def is_available(self) -> bool:
        """Check if skill can be used"""
        return (not self.disabled and 
                self.current_cooldown == 0 and
                (self.uses_remaining is None or self.uses_remaining > 0))
    
    def use_skill(self):
        """Mark skill as used (apply cooldown and decrease uses)"""
        modified_cooldown = self.modifications.get("cooldown_override", self.max_cooldown)
        self.current_cooldown = max(0, modified_cooldown)
        
        if self.uses_remaining is not None:
            self.uses_remaining -= 1
    
    def tick_cooldown(self):
        """Decrease cooldown by 1"""
        if self.current_cooldown > 0:
            self.current_cooldown -= 1

@dataclass
class SignatureState:
    """State tracking for signature abilities"""
    skill_id: str
    conditions: Dict[str, Any]
    primed: bool = False
    used: bool = False
    trigger_data: Dict[str, Any] = field(default_factory=dict)

class AbilitiesComponent(BaseComponent):
    """Component managing character skills and abilities"""
    
    def __init__(self, character_id: str):
        super().__init__(character_id)
        self.available_skills: Dict[str, SkillInstance] = {}
        self.signature_states: Dict[str, SignatureState] = {}
        self.skill_modifications: Dict[str, Dict[str, Any]] = {}
        self.global_skill_modifiers: Dict[str, Any] = {}
        
        self._setup_event_listeners()
    
    def initialize(self, character_data: Dict[str, Any]):
        """Initialize abilities from character data"""
        # Load basic skills based on potencies
        potencies = character_data.get("potencies", {})
        self._load_skills_from_potencies(potencies)
        
        # Load signature abilities
        signature_skill = character_data.get("signature_skill")
        if signature_skill:
            self._load_signature_skill(signature_skill)
        
        signature_passive = character_data.get("signature_passive")
        if signature_passive:
            self._load_signature_passive(signature_passive)
        
        # Load any custom skills
        custom_skills = character_data.get("custom_skills", [])
        for skill_data in custom_skills:
            self._add_skill(skill_data)
    
    def update(self, delta_time: float = 0.0):
        """Update component state - called each turn"""
        # Tick cooldowns
        for skill in self.available_skills.values():
            skill.tick_cooldown()
        
        # Check signature skill conditions
        self._check_signature_conditions()
    
    def get_data(self) -> Dict[str, Any]:
        """Get component's current data"""
        return {
            "available_skills": {
                skill_id: {
                    "skill_id": skill.skill_id,
                    "skill_type": skill.skill_type.value,
                    "base_data": skill.base_data,
                    "current_cooldown": skill.current_cooldown,
                    "max_cooldown": skill.max_cooldown,
                    "uses_remaining": skill.uses_remaining,
                    "max_uses": skill.max_uses,
                    "disabled": skill.disabled,
                    "modifications": skill.modifications
                }
                for skill_id, skill in self.available_skills.items()
            },
            "signature_states": {
                sig_id: {
                    "skill_id": sig.skill_id,
                    "conditions": sig.conditions,
                    "primed": sig.primed,
                    "used": sig.used,
                    "trigger_data": sig.trigger_data
                }
                for sig_id, sig in self.signature_states.items()
            },
            "skill_modifications": self.skill_modifications,
            "global_skill_modifiers": self.global_skill_modifiers
        }
    
    def set_data(self, data: Dict[str, Any]):
        """Set component data"""
        # Load skills
        self.available_skills.clear()
        skills_data = data.get("available_skills", {})
        
        for skill_id, skill_data in skills_data.items():
            skill = SkillInstance(
                skill_id=skill_data["skill_id"],
                skill_type=SkillType(skill_data["skill_type"]),
                base_data=skill_data.get("base_data", {}),
                current_cooldown=skill_data.get("current_cooldown", 0),
                max_cooldown=skill_data.get("max_cooldown", 0),
                uses_remaining=skill_data.get("uses_remaining"),
                max_uses=skill_data.get("max_uses"),
                disabled=skill_data.get("disabled", False),
                modifications=skill_data.get("modifications", {})
            )
            self.available_skills[skill_id] = skill
        
        # Load signature states
        self.signature_states.clear()
        sig_data = data.get("signature_states", {})
        
        for sig_id, sig_state_data in sig_data.items():
            sig_state = SignatureState(
                skill_id=sig_state_data["skill_id"],
                conditions=sig_state_data["conditions"],
                primed=sig_state_data.get("primed", False),
                used=sig_state_data.get("used", False),
                trigger_data=sig_state_data.get("trigger_data", {})
            )
            self.signature_states[sig_id] = sig_state
        
        self.skill_modifications = data.get("skill_modifications", {})
        self.global_skill_modifiers = data.get("global_skill_modifiers", {})
    
    def get_available_skills(self, skill_type: Optional[SkillType] = None) -> List[SkillInstance]:
        """Get all available skills, optionally filtered by type"""
        skills = [skill for skill in self.available_skills.values() if skill.is_available()]
        
        if skill_type is not None:
            skills = [skill for skill in skills if skill.skill_type == skill_type]
        
        return skills
    
    def get_skill(self, skill_id: str) -> Optional[SkillInstance]:
        """Get a specific skill by ID"""
        return self.available_skills.get(skill_id)
    
    def can_use_skill(self, skill_id: str) -> bool:
        """Check if a specific skill can be used"""
        skill = self.get_skill(skill_id)
        return skill is not None and skill.is_available()
    
    def use_skill(self, skill_id: str) -> bool:
        """Mark a skill as used"""
        skill = self.get_skill(skill_id)
        if skill and skill.is_available():
            skill.use_skill()
            
            # Publish skill used event
            event = GameEvent(
                event_type="skill_used",
                source=self,
                target=self.character_id,
                data={
                    "character_id": self.character_id,
                    "skill_id": skill_id,
                    "skill_data": skill.base_data
                }
            )
            event_bus.publish(event)
            return True
        return False
    
    def modify_skill(self, skill_id: str, modifications: Dict[str, Any]):
        """Apply modifications to a skill"""
        if skill_id not in self.skill_modifications:
            self.skill_modifications[skill_id] = {}
        
        self.skill_modifications[skill_id].update(modifications)
        
        # Apply to skill instance if it exists
        if skill_id in self.available_skills:
            self.available_skills[skill_id].modifications.update(modifications)
    
    def add_global_modifier(self, modifier_id: str, modifier_data: Dict[str, Any]):
        """Add a global skill modifier"""
        self.global_skill_modifiers[modifier_id] = modifier_data
        
        # Apply to all existing skills
        for skill in self.available_skills.values():
            self._apply_global_modifiers(skill)
    
    def remove_global_modifier(self, modifier_id: str):
        """Remove a global skill modifier"""
        if modifier_id in self.global_skill_modifiers:
            del self.global_skill_modifiers[modifier_id]
            
            # Recalculate all skill modifications
            for skill in self.available_skills.values():
                skill.modifications.clear()
                if skill.skill_id in self.skill_modifications:
                    skill.modifications.update(self.skill_modifications[skill.skill_id])
                self._apply_global_modifiers(skill)
    
    def disable_skill(self, skill_id: str):
        """Disable a specific skill"""
        skill = self.get_skill(skill_id)
        if skill:
            skill.disabled = True
    
    def enable_skill(self, skill_id: str):
        """Enable a specific skill"""
        skill = self.get_skill(skill_id)
        if skill:
            skill.disabled = False
    
    def reset_cooldowns(self):
        """Reset all skill cooldowns"""
        for skill in self.available_skills.values():
            skill.current_cooldown = 0
    
    def get_primed_signature(self) -> Optional[str]:
        """Get the ID of any primed signature skill"""
        for sig_id, sig_state in self.signature_states.items():
            if sig_state.primed and not sig_state.used:
                return sig_id
        return None
    
    def prime_signature(self, signature_id: str, trigger_data: Dict[str, Any] = None):
        """Prime a signature skill for use"""
        if signature_id in self.signature_states:
            sig_state = self.signature_states[signature_id]
            if not sig_state.used:
                sig_state.primed = True
                sig_state.trigger_data = trigger_data or {}
                
                # Publish signature primed event
                event = GameEvent(
                    event_type="signature_primed",
                    source=self,
                    target=self.character_id,
                    data={
                        "character_id": self.character_id,
                        "signature_id": signature_id,
                        "skill_id": sig_state.skill_id,
                        "trigger_data": trigger_data
                    }
                )
                event_bus.publish(event)
    
    def use_signature(self, signature_id: str) -> bool:
        """Use a primed signature skill"""
        if signature_id in self.signature_states:
            sig_state = self.signature_states[signature_id]
            if sig_state.primed and not sig_state.used:
                sig_state.used = True
                sig_state.primed = False
                
                # Publish signature used event
                event = GameEvent(
                    event_type="signature_used",
                    source=self,
                    target=self.character_id,
                    data={
                        "character_id": self.character_id,
                        "signature_id": signature_id,
                        "skill_id": sig_state.skill_id,
                        "trigger_data": sig_state.trigger_data
                    }
                )
                event_bus.publish(event)
                return True
        return False
    
    def _load_skills_from_potencies(self, potencies: Dict[str, str]):
        """Load basic skills based on character potencies"""
        # Import skill definitions (this would come from data files)
        from ..data.skill_definitions import get_skills_for_potency
        
        for potency_type, rating in potencies.items():
            skills = get_skills_for_potency(potency_type, rating)
            for skill_data in skills:
                self._add_skill(skill_data)
    
    def _load_signature_skill(self, signature_data: Dict[str, Any]):
        """Load a signature skill"""
        sig_id = f"signature_{signature_data['id']}"
        
        # Add the skill itself
        skill_data = signature_data.copy()
        skill_data["skill_type"] = "signature"
        skill_data["max_uses"] = 1
        self._add_skill(skill_data)
        
        # Add signature state tracking
        self.signature_states[sig_id] = SignatureState(
            skill_id=signature_data["id"],
            conditions=signature_data.get("conditions", {})
        )
    
    def _load_signature_passive(self, passive_data: Dict[str, Any]):
        """Load a signature passive"""
        skill_data = passive_data.copy()
        skill_data["skill_type"] = "passive"
        self._add_skill(skill_data)
        
        # Passives are automatically "activated" at battle start
        self._apply_passive(skill_data)
    
    def _add_skill(self, skill_data: Dict[str, Any]):
        """Add a skill to available skills"""
        skill_id = skill_data["id"]
        skill_type = SkillType(skill_data.get("skill_type", "active"))
        
        skill = SkillInstance(
            skill_id=skill_id,
            skill_type=skill_type,
            base_data=skill_data.copy(),
            max_cooldown=skill_data.get("cooldown", 0),
            max_uses=skill_data.get("max_uses"),
            uses_remaining=skill_data.get("max_uses")
        )
        
        # Apply any existing modifications
        if skill_id in self.skill_modifications:
            skill.modifications.update(self.skill_modifications[skill_id])
        
        # Apply global modifiers
        self._apply_global_modifiers(skill)
        
        self.available_skills[skill_id] = skill
    
    def _apply_global_modifiers(self, skill: SkillInstance):
        """Apply global modifiers to a skill"""
        for modifier_data in self.global_skill_modifiers.values():
            # Check if modifier applies to this skill
            conditions = modifier_data.get("conditions", {})
            applies = True
            
            for condition_key, condition_value in conditions.items():
                if condition_key == "skill_type":
                    if skill.skill_type.value != condition_value:
                        applies = False
                        break
                elif condition_key == "skill_id":
                    if skill.skill_id != condition_value:
                        applies = False
                        break
                # Add more condition types as needed
            
            if applies:
                modifications = modifier_data.get("modifications", {})
                skill.modifications.update(modifications)
    
    def _apply_passive(self, passive_data: Dict[str, Any]):
        """Apply a passive ability effect"""
        # Publish passive activation event
        event = GameEvent(
            event_type="passive_activated",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "passive_data": passive_data
            }
        )
        event_bus.publish(event)
    
    def _check_signature_conditions(self):
        """Check if any signature skills should be primed"""
        for sig_id, sig_state in self.signature_states.items():
            if not sig_state.primed and not sig_state.used:
                if self._evaluate_signature_conditions(sig_state.conditions):
                    self.prime_signature(sig_id)
    
    def _evaluate_signature_conditions(self, conditions: Dict[str, Any]) -> bool:
        """Evaluate if signature conditions are met"""
        # This would integrate with battle context to check conditions
        # For now, return False - will be implemented with battle system
        return False
    
    def _setup_event_listeners(self):
        """Set up event listeners for this component"""
        self.register_event_listener(
            "turn_started",
            self._on_turn_started
        )
        
        self.register_event_listener(
            "effect_applied",
            self._on_effect_applied
        )
        
        self.register_event_listener(
            "hp_changed",
            self._on_hp_changed
        )
    
    def _on_turn_started(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle turn started events"""
        if event.get_value("character_id") == self.character_id:
            self.update()
        return event
    
    def _on_effect_applied(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle effect applied events that might affect skills"""
        if event.get_value("target_id") == self.character_id:
            effect_data = event.get_value("effect_data", {})
            
            # Check for skill modifications
            skill_mods = effect_data.get("skill_modifications", {})
            for skill_id, modifications in skill_mods.items():
                self.modify_skill(skill_id, modifications)
        
        return event
    
    def _on_hp_changed(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle HP change events for signature condition checking"""
        if event.get_value("character_id") == self.character_id:
            # This could trigger signature skills based on HP thresholds
            self._check_signature_conditions()
        
        return event
```

### Step 3.2: Base Skill System Implementation

Create the core skill execution system:

**File: `src/game/systems/skill_system.py`**

```python
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random

from ..core.event_system import GameEvent, event_bus
from ..core.battle_context import BattleContext
from ..components.abilities_component import TargetType

class SkillExecutionResult(Enum):
    """Results of skill execution attempts"""
    SUCCESS = "success"
    FAILED_VALIDATION = "failed_validation"
    FAILED_TARGETING = "failed_targeting"
    FAILED_COST = "failed_cost"
    CANCELLED = "cancelled"

@dataclass
class SkillExecution:
    """A skill execution request"""
    caster_id: str
    skill_id: str
    target_ids: List[str]
    skill_data: Dict[str, Any]
    modifications: Dict[str, Any]
    execution_id: str
    result: SkillExecutionResult = SkillExecutionResult.SUCCESS

class SkillSystem:
    """System for executing skills and managing skill interactions"""
    
    def __init__(self, battle_context: BattleContext):
        self.battle_context = battle_context
        self.pending_executions: List[SkillExecution] = []
        self.execution_history: List[SkillExecution] = []
        self._setup_event_listeners()
    
    def execute_skill(self, caster_id: str, skill_id: str, target_hint: Optional[str] = None) -> SkillExecutionResult:
        """Execute a skill with automatic targeting"""
        import uuid
        execution_id = str(uuid.uuid4())
        
        # Get caster
        caster = self.battle_context.get_character(caster_id)
        if not caster:
            return SkillExecutionResult.FAILED_VALIDATION
        
        # Get caster's abilities component
        abilities_comp = caster.get("components", {}).get("abilities")
        if not abilities_comp:
            return SkillExecutionResult.FAILED_VALIDATION
        
        # Check if skill can be used
        if not abilities_comp.can_use_skill(skill_id):
            return SkillExecutionResult.FAILED_VALIDATION
        
        # Get skill data
        skill = abilities_comp.get_skill(skill_id)
        if not skill:
            return SkillExecutionResult.FAILED_VALIDATION
        
        skill_data = skill.base_data.copy()
        skill_data.update(skill.modifications)
        
        # Phase 1: Validation
        validation_event = GameEvent(
            event_type="skill_validation",
            source=caster_id,
            data={
                "caster_id": caster_id,
                "skill_id": skill_id,
                "skill_data": skill_data,
                "execution_id": execution_id
            }
        )
        validation_event = event_bus.publish(validation_event)
        
        if validation_event.cancelled:
            return SkillExecutionResult.FAILED_VALIDATION
        
        # Phase 2: Targeting
        target_ids = self._resolve_targets(caster_id, skill_data, target_hint)
        if not target_ids:
            return SkillExecutionResult.FAILED_TARGETING
        
        targeting_event = GameEvent(
            event_type="skill_targeting",
            source=caster_id,
            data={
                "caster_id": caster_id,
                "skill_id": skill_id,
                "skill_data": skill_data,
                "target_ids": target_ids,
                "execution_id": execution_id
            }
        )
        targeting_event = event_bus.publish(targeting_event)
        
        if targeting_event.cancelled:
            return SkillExecutionResult.FAILED_TARGETING
        
        # Update target list if modified by events
        target_ids = targeting_event.get_value("target_ids", target_ids)
        
        # Phase 3: Cost checking (for future implementation)
        cost_event = GameEvent(
            event_type="skill_cost_check",
            source=caster_id,
            data={
                "caster_id": caster_id,
                "skill_id": skill_id,
                "skill_data": skill_data,
                "target_ids": target_ids,
                "execution_id": execution_id
            }
        )
        cost_event = event_bus.publish(cost_event)
        
        if cost_event.cancelled:
            return SkillExecutionResult.FAILED_COST
        
        # Phase 4: Pre-execution modifications
        pre_execution_event = GameEvent(
            event_type="skill_pre_execution",
            source=caster_id,
            data={
                "caster_id": caster_id,
                "skill_id": skill_id,
                "skill_data": skill_data,
                "target_ids": target_ids,
                "execution_id": execution_id
            }
        )
        pre_execution_event = event_bus.publish(pre_execution_event)
        
        if pre_execution_event.cancelled:
            return SkillExecutionResult.CANCELLED
        
        # Apply any modifications from events
        skill_data.update(pre_execution_event.get_value("skill_modifications", {}))
        
        # Create execution record
        execution = SkillExecution(
            caster_id=caster_id,
            skill_id=skill_id,
            target_ids=target_ids,
            skill_data=skill_data,
            modifications=skill.modifications,
            execution_id=execution_id
        )
        
        # Phase 5: Execute skill effects
        execution_result = self._execute_skill_effects(execution)
        execution.result = execution_result
        
        # Mark skill as used
        if execution_result == SkillExecutionResult.SUCCESS:
            abilities_comp.use_skill(skill_id)
        
        # Add to history
        self.execution_history.append(execution)
        
        # Phase 6: Post-execution
        post_execution_event = GameEvent(
            event_type="skill_post_execution",
            source=caster_id,
            data={
                "caster_id": caster_id,
                "skill_id": skill_id,
                "skill_data": skill_data,
                "target_ids": target_ids,
                "execution_id": execution_id,
                "result": execution_result.value
            }
        )
        event_bus.publish(post_execution_event)
        
        return execution_result
    
    def _resolve_targets(self, caster_id: str, skill_data: Dict[str, Any], target_hint: Optional[str] = None) -> List[str]:
        """Resolve skill targets based on targeting rules"""
        target_type = TargetType(skill_data.get("target_type", "single_enemy"))
        caster = self.battle_context.get_character(caster_id)
        caster_team = caster.get("team") if caster else 1
        
        all_characters = self.battle_context.get_all_characters()
        living_characters = [char for char in all_characters if char.get("current_hp", 0) > 0]
        
        enemies = [char for char in living_characters if char.get("team") != caster_team]
        allies = [char for char in living_characters if char.get("team") == caster_team]
        
        # Filter by position if needed
        front_row_enemies = [char for char in enemies if char.get("position", 0) < 3]
        back_row_enemies = [char for char in enemies if char.get("position", 0) >= 3]
        front_row_allies = [char for char in allies if char.get("position", 0) < 3]
        back_row_allies = [char for char in allies if char.get("position", 0) >= 3]
        
        targets = []
        
        if target_type == TargetType.SELF:
            targets = [caster_id]
        
        elif target_type == TargetType.SINGLE_ENEMY:
            # Target front row first, unless it's empty
            available_enemies = front_row_enemies if front_row_enemies else back_row_enemies
            if target_hint and target_hint in [char["id"] for char in available_enemies]:
                targets = [target_hint]
            elif available_enemies:
                targets = [available_enemies[0]["id"]]  # AI will choose best target
        
        elif target_type == TargetType.SINGLE_ALLY:
            if target_hint and target_hint in [char["id"] for char in allies]:
                targets = [target_hint]
            elif allies:
                targets = [allies[0]["id"]]  # AI will choose best target
        
        elif target_type == TargetType.ALL_ENEMIES:
            targets = [char["id"] for char in enemies]
        
        elif target_type == TargetType.ALL_ALLIES:
            targets = [char["id"] for char in allies]
        
        elif target_type == TargetType.ALL_CHARACTERS:
            targets = [char["id"] for char in living_characters]
        
        elif target_type == TargetType.FRONT_ROW_ENEMIES:
            targets = [char["id"] for char in front_row_enemies]
        
        elif target_type == TargetType.BACK_ROW_ENEMIES:
            targets = [char["id"] for char in back_row_enemies]
        
        elif target_type == TargetType.FRONT_ROW_ALLIES:
            targets = [char["id"] for char in front_row_allies]
        
        elif target_type == TargetType.BACK_ROW_ALLIES:
            targets = [char["id"] for char in back_row_allies]
        
        elif target_type == TargetType.RANDOM_ENEMY:
            if enemies:
                targets = [random.choice(enemies)["id"]]
        
        elif target_type == TargetType.RANDOM_ALLY:
            if allies:
                targets = [random.choice(allies)["id"]]
        
        return targets
    
    def _execute_skill_effects(self, execution: SkillExecution) -> SkillExecutionResult:
        """Execute the actual effects of a skill"""
        skill_data = execution.skill_data
        
        # Publish skill execution event
        execution_event = GameEvent(
            event_type="skill_execution",
            source=execution.caster_id,
            data={
                "execution": execution,
                "caster_id": execution.caster_id,
                "skill_id": execution.skill_id,
                "skill_data": skill_data,
                "target_ids": execution.target_ids,
                "execution_id": execution.execution_id
            }
        )
        execution_event = event_bus.publish(execution_event)
        
        if execution_event.cancelled:
            return SkillExecutionResult.CANCELLED
        
        # Execute individual effects
        effects = skill_data.get("effects", [])
        
        for effect in effects:
            self._execute_effect(execution, effect)
        
        return SkillExecutionResult.SUCCESS
    
    def _execute_effect(self, execution: SkillExecution, effect: Dict[str, Any]):
        """Execute a single effect from a skill"""
        effect_type = effect.get("type", "damage")
        
        if effect_type == "damage":
            self._execute_damage_effect(execution, effect)
        elif effect_type == "heal":
            self._execute_heal_effect(execution, effect)
        elif effect_type == "apply_status":
            self._execute_status_effect(execution, effect)
        elif effect_type == "modify_stats":
            self._execute_stat_modification(execution, effect)
        # Add more effect types as needed
    
    def _execute_damage_effect(self, execution: SkillExecution, effect: Dict[str, Any]):
        """Execute a damage effect"""
        for target_id in execution.target_ids:
            damage_event = GameEvent(
                event_type="damage_calculated",
                source=execution.caster_id,
                target=target_id,
                data={
                    "caster_id": execution.caster_id,
                    "target_id": target_id,
                    "skill_id": execution.skill_id,
                    "effect": effect,
                    "execution_id": execution.execution_id,
                    "base_damage": effect.get("base_damage", 0),
                    "damage_type": effect.get("damage_type", "physical")
                }
            )
            event_bus.publish(damage_event)
    
    def _execute_heal_effect(self, execution: SkillExecution, effect: Dict[str, Any]):
        """Execute a healing effect"""
        for target_id in execution.target_ids:
            heal_event = GameEvent(
                event_type="heal_calculated",
                source=execution.caster_id,
                target=target_id,
                data={
                    "caster_id": execution.caster_id,
                    "target_id": target_id,
                    "skill_id": execution.skill_id,
                    "effect": effect,
                    "execution_id": execution.execution_id,
                    "base_heal": effect.get("base_heal", 0)
                }
            )
            event_bus.publish(heal_event)
    
    def _execute_status_effect(self, execution: SkillExecution, effect: Dict[str, Any]):
        """Execute a status effect application"""
        for target_id in execution.target_ids:
            status_event = GameEvent(
                event_type="status_effect_applied",
                source=execution.caster_id,
                target=target_id,
                data={
                    "caster_id": execution.caster_id,
                    "target_id": target_id,
                    "skill_id": execution.skill_id,
                    "effect": effect,
                    "execution_id": execution.execution_id,
                    "status_id": effect.get("status_id"),
                    "duration": effect.get("duration", 1)
                }
            )
            event_bus.publish(status_event)
    
    def _execute_stat_modification(self, execution: SkillExecution, effect: Dict[str, Any]):
        """Execute a stat modification effect"""
        for target_id in execution.target_ids:
            stat_mod_event = GameEvent(
                event_type="stat_modification_applied",
                source=execution.caster_id,
                target=target_id,
                data={
                    "caster_id": execution.caster_id,
                    "target_id": target_id,
                    "skill_id": execution.skill_id,
                    "effect": effect,
                    "execution_id": execution.execution_id,
                    "stat_type": effect.get("stat_type"),
                    "modifier_type": effect.get("modifier_type", "flat"),
                    "value": effect.get("value", 0),
                    "duration": effect.get("duration")
                }
            )
            event_bus.publish(stat_mod_event)
    
    def _setup_event_listeners(self):
        """Set up event listeners for the skill system"""
        event_bus.register_handler(
            "skill_execution_requested",
            self._on_skill_execution_requested
        )
    
    def _on_skill_execution_requested(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle skill execution requests"""
        caster_id = event.get_value("caster_id")
        skill_id = event.get_value("skill_id")
        target_hint = event.get_value("target_hint")
        
        if caster_id and skill_id:
            result = self.execute_skill(caster_id, skill_id, target_hint)
            event.modify("execution_result", result)
        
        return event
```

### Step 3.3: Skill Definitions Data Structure

Create the data structure for skill definitions:

**File: `src/game/data/skill_definitions.py`**

```python
from typing import Dict, List, Any
from enum import Enum

# This would eventually be loaded from JSON files
# For now, implementing as Python data structures

class PotencyRating(Enum):
    """Potency ratings for character abilities"""
    S = "S"
    A = "A" 
    B = "B"
    C = "C"
    D = "D"
    F = "F"

# Universal Skill Library based on the game design
SKILL_LIBRARY = {
    "attacker": {
        "power_strike": {
            "id": "power_strike",
            "name": "Power Strike",
            "description": "100% ATK damage to one front-row enemy",
            "target_type": "single_enemy",
            "power_weight": 50,
            "floor": 20,
            "softcap_1": 50,
            "softcap_2": 200,
            "post_cap_rate": 0.5,
            "effects": [
                {
                    "type": "damage",
                    "damage_type": "physical",
                    "base_damage": 100,
                    "scaling": "atk",
                    "scaling_multiplier": 1.0
                }
            ]
        },
        "flurry_of_blows": {
            "id": "flurry_of_blows",
            "name": "Flurry of Blows",
            "description": "Hits one front-row enemy twice for 60% ATK damage each",
            "target_type": "single_enemy",
            "power_weight": 30,
            "floor": 15,
            "softcap_1": 40,
            "softcap_2": 150,
            "post_cap_rate": 0.4,
            "effects": [
                {
                    "type": "damage",
                    "damage_type": "physical",
                    "base_damage": 60,
                    "scaling": "atk",
                    "scaling_multiplier": 1.0,
                    "hits": 2
                }
            ]
        },
        "armor_break": {
            "id": "armor_break",
            "name": "Armor Break",
            "description": "80% ATK damage, ignoring 50% of VIT",
            "target_type": "single_enemy",
            "power_weight": 20,
            "floor": 25,
            "softcap_1": 60,
            "softcap_2": 220,
            "post_cap_rate": 0.4,
            "effects": [
                {
                    "type": "damage",
                    "damage_type": "physical",
                    "base_damage": 80,
                    "scaling": "atk",
                    "scaling_multiplier": 1.0,
                    "defense_penetration": 0.5
                }
            ]
        }
    },
    "mage": {
        "mana_bolt": {
            "id": "mana_bolt",
            "name": "Mana Bolt",
            "description": "100% MAG damage to one front-row enemy",
            "target_type": "single_enemy",
            "power_weight": 50,
            "floor": 20,
            "softcap_1": 50,
            "softcap_2": 200,
            "post_cap_rate": 0.5,
            "effects": [
                {
                    "type": "damage",
                    "damage_type": "magical",
                    "base_damage": 100,
                    "scaling": "mag",
                    "scaling_multiplier": 1.0
                }
            ]
        },
        "chain_lightning": {
            "id": "chain_lightning",
            "name": "Chain Lightning",
            "description": "80% MAG damage to one target, jumps for 40% to another",
            "target_type": "single_enemy",
            "power_weight": 25,
            "floor": 15,
            "softcap_1": 60,
            "softcap_2": 220,
            "post_cap_rate": 0.4,
            "effects": [
                {
                    "type": "damage",
                    "damage_type": "magical",
                    "base_damage": 80,
                    "scaling": "mag",
                    "scaling_multiplier": 1.0
                },
                {
                    "type": "chain_damage",
                    "damage_type": "magical", 
                    "base_damage": 40,
                    "scaling": "mag",
                    "scaling_multiplier": 1.0,
                    "chain_targets": 1
                }
            ]
        }
    },
    "healer": {
        "lesser_heal": {
            "id": "lesser_heal",
            "name": "Lesser Heal",
            "description": "Restores a moderate amount of HP to one ally",
            "target_type": "single_ally",
            "power_weight": 50,
            "floor": 50,
            "softcap_1": 50,
            "softcap_2": 200,
            "post_cap_rate": 0.5,
            "effects": [
                {
                    "type": "heal",
                    "base_heal": 100,
                    "scaling": "int",
                    "scaling_multiplier": 0.5,
                    "spr_scaling": 1.25
                }
            ]
        },
        "regen": {
            "id": "regen",
            "name": "Regen",
            "description": "Applies a heal over time effect to one ally",
            "target_type": "single_ally",
            "power_weight": 25,
            "floor": 20,
            "softcap_1": 40,
            "softcap_2": 150,
            "post_cap_rate": 0.4,
            "effects": [
                {
                    "type": "apply_status",
                    "status_id": "regen",
                    "duration": 3
                }
            ]
        }
    },
    "defender": {
        "guard_stance": {
            "id": "guard_stance",
            "name": "Guard Stance",
            "description": "User doubles their VIT and SPR until their next turn",
            "target_type": "self",
            "power_weight": 50,
            "effects": [
                {
                    "type": "apply_status",
                    "status_id": "guard_stance",
                    "duration": 1
                }
            ]
        },
        "provoke": {
            "id": "provoke",
            "name": "Provoke",
            "description": "Forces a single enemy to target the user on their next attack",
            "target_type": "single_enemy",
            "power_weight": 30,
            "effects": [
                {
                    "type": "apply_status",
                    "status_id": "provoked",
                    "duration": 1,
                    "provoke_target": "caster"
                }
            ]
        }
    }
}

POTENCY_WEIGHTS = {
    PotencyRating.S: [50, 30, 25, 20, 15, 10],
    PotencyRating.A: [50, 30, 25, 20, 15],
    PotencyRating.B: [50, 30, 25, 20],
    PotencyRating.C: [50, 30, 25],
    PotencyRating.D: [50, 30],
    PotencyRating.F: [50]
}

def get_skills_for_potency(potency_type: str, rating: str) -> List[Dict[str, Any]]:
    """Get available skills for a character's potency"""
    if potency_type not in SKILL_LIBRARY:
        return []
    
    try:
        rating_enum = PotencyRating(rating.upper())
    except ValueError:
        return []
    
    available_weights = POTENCY_WEIGHTS[rating_enum]
    potency_skills = SKILL_LIBRARY[potency_type]
    
    # Filter skills by available power weights
    available_skills = []
    for skill_id, skill_data in potency_skills.items():
        if skill_data.get("power_weight", 0) in available_weights:
            available_skills.append(skill_data.copy())
    
    return available_skills

def get_skill_by_id(skill_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific skill by ID"""
    for potency_type, skills in SKILL_LIBRARY.items():
        if skill_id in skills:
            return skills[skill_id].copy()
    return None
```

### Next Steps

This completes Step 3 of the implementation, establishing the abilities and skill system with:

1. **Abilities Component**: Complete skill management with cooldowns, modifications, and signature abilities
2. **Skill System**: Multi-phase skill execution with event-driven validation and targeting
3. **Skill Definitions**: Data-driven skill library based on the game design

The next step (Step 4) will focus on implementing the turn system and action gauge mechanics.

### Integration Notes

- Skills are executed through a multi-phase validation system
- All skill effects are published as events for other systems to handle
- Signature abilities have condition checking and priming mechanics
- The skill library supports the potency-based character progression

### Testing Recommendations

Create unit tests for:

- Skill validation and targeting
- Cooldown and usage tracking
- Signature ability condition checking
- Skill effect execution
- Multi-target skill resolution
