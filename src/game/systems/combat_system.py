"""
Combat System - Handles battle action execution and damage resolution.

This system manages:
- Battle action execution pipeline  
- Damage calculation with modifier events
- Healing resolution with overheal protection
- Status effect application and management
- Integration with Turn System and Abilities System
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging
import math

from ..core.event_system import GameEvent, event_bus, EventPhase
from ..core.battle_context import BattleContext
from ..core.elemental_system import elemental_calculator
from ..components.character import Character

logger = logging.getLogger(__name__)

class ActionType(Enum):
    """Types of combat actions"""
    ATTACK = "attack"           # Basic or weapon attacks
    SKILL = "skill"             # Ability/skill usage
    ITEM = "item"               # Item consumption
    DEFEND = "defend"           # Defensive stance
    MOVE = "move"               # Position change
    WAIT = "wait"               # Skip turn

class DamageType(Enum):
    """Types of damage"""
    PHYSICAL = "physical"       # Reduced by VIT
    MAGICAL = "magical"         # Reduced by SPR
    TRUE = "true"               # Cannot be reduced
    HEALING = "healing"         # Restores HP

class TargetType(Enum):
    """Target selection types"""
    SINGLE_ALLY = "single_ally"
    SINGLE_ENEMY = "single_enemy"
    SINGLE_ANY = "single_any"
    ALL_ALLIES = "all_allies"
    ALL_ENEMIES = "all_enemies"
    ALL_CHARACTERS = "all_characters"
    SELF = "self"
    AREA_ALLIES = "area_allies"
    AREA_ENEMIES = "area_enemies"

@dataclass
class CombatAction:
    """Represents a combat action to be executed"""
    action_id: str
    actor_id: str
    action_type: ActionType
    target_ids: List[str]
    skill_id: Optional[str] = None
    item_id: Optional[str] = None
    power: float = 1.0
    accuracy: float = 1.0
    critical_chance: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class DamageInfo:
    """Information about damage/healing calculation"""
    base_amount: float
    final_amount: float
    damage_type: DamageType
    is_critical: bool = False
    is_blocked: bool = False
    is_dodged: bool = False
    elemental_modifier: float = 1.0
    elemental_details: Optional[Dict[str, Any]] = None
    modifiers: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = []

@dataclass
class ActionResult:
    """Result of executing a combat action"""
    action: CombatAction
    success: bool
    damage_results: Dict[str, DamageInfo]
    status_effects_applied: List[str]
    events_triggered: List[str]
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.damage_results is None:
            self.damage_results = {}
        if self.status_effects_applied is None:
            self.status_effects_applied = []
        if self.events_triggered is None:
            self.events_triggered = []

class CombatSystem:
    """Main combat system for battle action execution"""
    
    def __init__(self, battle_context: BattleContext):
        self.battle_context = battle_context
        self.action_history: List[ActionResult] = []
        self.current_action: Optional[CombatAction] = None
        
        # Combat parameters
        self.critical_multiplier = 1.5
        self.defense_reduction_factor = 0.02  # 2% damage reduction per defense point
        self.accuracy_base = 0.95
        self.evasion_factor = 0.01  # 1% dodge chance per speed difference
        
        logger.info("Initialized combat system for battle %s", battle_context.battle_id)
    
    def execute_action(self, action: CombatAction) -> ActionResult:
        """Execute a combat action and return the result"""
        logger.info("Executing action %s: %s uses %s on %s", 
                   action.action_id, action.actor_id, action.action_type.value, action.target_ids)
        
        self.current_action = action
        
        # Pre-execution validation
        if not self._validate_action(action):
            return ActionResult(
                action=action,
                success=False,
                damage_results={},
                status_effects_applied=[],
                events_triggered=[],
                error_message="Action validation failed"
            )
        
        # Publish pre-execution event
        self._publish_action_event("combat.action.pre_execution", action)
        
        try:
            # Execute action based on type
            if action.action_type == ActionType.ATTACK:
                result = self._execute_attack(action)
            elif action.action_type == ActionType.SKILL:
                result = self._execute_skill(action)
            elif action.action_type == ActionType.ITEM:
                result = self._execute_item(action)
            elif action.action_type == ActionType.DEFEND:
                result = self._execute_defend(action)
            elif action.action_type == ActionType.WAIT:
                result = self._execute_wait(action)
            else:
                result = ActionResult(
                    action=action,
                    success=False,
                    damage_results={},
                    status_effects_applied=[],
                    events_triggered=[],
                    error_message=f"Unknown action type: {action.action_type}"
                )
            
            # Store in history
            self.action_history.append(result)
            
            # Publish post-execution event
            self._publish_action_event("combat.action.post_execution", action, result)
            
            logger.info("Action %s completed: success=%s", action.action_id, result.success)
            return result
            
        except Exception as e:
            logger.error("Error executing action %s: %s", action.action_id, str(e))
            return ActionResult(
                action=action,
                success=False,
                damage_results={},
                status_effects_applied=[],
                events_triggered=[],
                error_message=f"Execution error: {str(e)}"
            )
        finally:
            self.current_action = None
    
    def _validate_action(self, action: CombatAction) -> bool:
        """Validate that an action can be executed"""
        # Check if actor exists and is alive
        actor = self.battle_context.get_character(action.actor_id)
        if not actor or actor.is_defeated():
            logger.warning("Actor %s not found or defeated", action.actor_id)
            return False
        
        # Check if targets exist and are valid for action type
        for target_id in action.target_ids:
            target = self.battle_context.get_character(target_id)
            if not target:
                logger.warning("Target %s not found", target_id)
                return False
        
        # Validate skill availability
        if action.action_type == ActionType.SKILL and action.skill_id:
            skill = actor.abilities.get_skill(action.skill_id)
            if not skill:
                logger.warning("Actor %s does not have skill %s", action.actor_id, action.skill_id)
                return False
        
        return True
    
    def _execute_attack(self, action: CombatAction) -> ActionResult:
        """Execute a basic attack action"""
        actor = self.battle_context.get_character(action.actor_id)
        if not actor:
            return ActionResult(
                action=action,
                success=False,
                damage_results={},
                status_effects_applied=[],
                events_triggered=[],
                error_message="Actor not found"
            )
        
        damage_results = {}
        
        for target_id in action.target_ids:
            target = self.battle_context.get_character(target_id)
            if not target or target.is_defeated():
                continue
            
            # Calculate attack damage
            base_damage = actor.get_stat("atk") * action.power
            damage_info = self._calculate_damage(
                attacker=actor,
                target=target,
                base_damage=base_damage,
                damage_type=DamageType.PHYSICAL,
                accuracy=action.accuracy,
                critical_chance=action.critical_chance
            )
            
            # Apply damage
            if not damage_info.is_dodged:
                self._apply_damage(target, damage_info)
            
            damage_results[target_id] = damage_info
        
        return ActionResult(
            action=action,
            success=True,
            damage_results=damage_results,
            status_effects_applied=[],
            events_triggered=[]
        )
    
    def _execute_skill(self, action: CombatAction) -> ActionResult:
        """Execute a skill action"""
        actor = self.battle_context.get_character(action.actor_id)
        if not actor:
            return ActionResult(
                action=action,
                success=False,
                damage_results={},
                status_effects_applied=[],
                events_triggered=[],
                error_message="Actor not found"
            )
        
        if not action.skill_id:
            return ActionResult(
                action=action,
                success=False,
                damage_results={},
                status_effects_applied=[],
                events_triggered=[],
                error_message="No skill specified"
            )
        
        skill = actor.abilities.get_skill(action.skill_id)
        if not skill:
            return ActionResult(
                action=action,
                success=False,
                damage_results={},
                status_effects_applied=[],
                events_triggered=[],
                error_message=f"Skill {action.skill_id} not found"
            )
        
        # Use the abilities system to execute the skill
        targets = [self.battle_context.get_character(tid) for tid in action.target_ids]
        targets = [t for t in targets if t is not None]
        
        # Execute skill using the abilities component
        result = skill.execute(actor, targets, self.battle_context)
        
        # Convert abilities result to combat result format
        damage_results = {}
        for target in targets:
            damage_amount = 0.0
            
            # Check if result contains damage information
            if isinstance(result, dict):
                if 'damage_dealt' in result:
                    # Handle both single damage value and per-target dictionary
                    damage_dealt = result['damage_dealt']
                    if isinstance(damage_dealt, dict):
                        # Dictionary format: {character_id: damage_amount}
                        damage_amount = damage_dealt.get(target.character_id, 0.0)
                    elif isinstance(damage_dealt, (int, float)):
                        # Single damage value (for single-target skills)
                        damage_amount = float(damage_dealt)
                    
                    if damage_amount > 0:
                        damage_results[target.character_id] = DamageInfo(
                            base_amount=damage_amount,
                            final_amount=damage_amount,
                            damage_type=DamageType.PHYSICAL  # Default to physical for basic attacks
                        )
        
        return ActionResult(
            action=action,
            success=isinstance(result, dict) and result.get('success', True),
            damage_results=damage_results,
            status_effects_applied=[],
            events_triggered=[]
        )
    
    def _execute_item(self, action: CombatAction) -> ActionResult:
        """Execute an item usage action"""
        try:
            # Basic item system implementation
            item_id = action.target_id  # Using target_id to store item_id
            caster = action.character
            
            # Simple item effects
            item_effects = {
                'healing_potion': {'type': 'heal', 'value': 50},
                'mana_potion': {'type': 'restore_mp', 'value': 30},
                'strength_buff': {'type': 'buff_atk', 'value': 20, 'duration': 3},
                'speed_buff': {'type': 'buff_spd', 'value': 15, 'duration': 3},
                'antidote': {'type': 'cleanse', 'effects': ['poison', 'burn']},
                'smoke_bomb': {'type': 'escape', 'success_rate': 0.8}
            }
            
            item_data = item_effects.get(item_id, {'type': 'unknown'})
            effects = []
            
            if item_data['type'] == 'heal':
                heal_amount = min(item_data['value'], caster.max_hp - caster.current_hp)
                caster.current_hp += heal_amount
                effects.append(f"Healed {heal_amount} HP")
                
            elif item_data['type'] == 'restore_mp':
                # MP restoration (if MP system exists)
                effects.append(f"Restored {item_data['value']} MP")
                
            elif item_data['type'].startswith('buff_'):
                stat_type = item_data['type'].split('_')[1]
                duration = item_data.get('duration', 3)
                if hasattr(caster, 'effects'):
                    # Apply stat buff effect
                    effects.append(f"Applied {stat_type.upper()} buff for {duration} turns")
                    
            elif item_data['type'] == 'cleanse':
                if hasattr(caster, 'effects'):
                    # Remove specified debuffs
                    cleansed = item_data.get('effects', [])
                    effects.append(f"Cleansed effects: {', '.join(cleansed)}")
                    
            elif item_data['type'] == 'escape':
                success_rate = item_data.get('success_rate', 0.5)
                import random
                if random.random() < success_rate:
                    effects.append("Successfully escaped from battle!")
                else:
                    effects.append("Failed to escape!")
            else:
                effects.append(f"Used unknown item: {item_id}")
                
            return ActionResult(
                action=action,
                success=True,
                damage_results={},
                healing_results={caster.character_id: item_data.get('value', 0)} if item_data['type'] == 'heal' else {},
                status_effects_applied=effects,
                events_triggered=[]
            )
            
        except Exception as e:
            logger.warning(f"Failed to execute item {action.target_id}: {e}")
            return ActionResult(
                action=action,
                success=False,
                damage_results={},
                healing_results={},
                status_effects_applied=[f"Item usage failed: {str(e)}"],
                events_triggered=[]
            )
    
    def _execute_defend(self, action: CombatAction) -> ActionResult:
        """Execute a defend action"""
        actor = self.battle_context.get_character(action.actor_id)
        if not actor:
            return ActionResult(
                action=action,
                success=False,
                damage_results={},
                status_effects_applied=[],
                events_triggered=[],
                error_message="Actor not found"
            )
        
        # Apply defense buff (this would be a temporary status effect)
        # For now, just log the action
        logger.info("%s takes a defensive stance", actor.name)
        
        return ActionResult(
            action=action,
            success=True,
            damage_results={},
            status_effects_applied=["defend_stance"],
            events_triggered=[]
        )
    
    def _execute_wait(self, action: CombatAction) -> ActionResult:
        """Execute a wait/skip action"""
        actor = self.battle_context.get_character(action.actor_id)
        if not actor:
            return ActionResult(
                action=action,
                success=False,
                damage_results={},
                status_effects_applied=[],
                events_triggered=[],
                error_message="Actor not found"
            )
        
        logger.info("%s waits", actor.name)
        
        return ActionResult(
            action=action,
            success=True,
            damage_results={},
            status_effects_applied=[],
            events_triggered=[]
        )
    
    def _calculate_damage(self, attacker: Character, target: Character, 
                         base_damage: float, damage_type: DamageType,
                         accuracy: float = 1.0, critical_chance: float = 0.0,
                         skill_element_override: Optional[str] = None) -> DamageInfo:
        """Calculate final damage amount with all modifiers"""
        
        # Accuracy check
        hit_chance = self._calculate_hit_chance(attacker, target, accuracy)
        if not self._roll_success(hit_chance):
            return DamageInfo(
                base_amount=base_damage,
                final_amount=0.0,
                damage_type=damage_type,
                is_dodged=True
            )
        
        # Critical hit check
        crit_chance = self._calculate_critical_chance(attacker, target, critical_chance)
        is_critical = self._roll_success(crit_chance)
        
        # Base damage calculation
        final_damage = base_damage
        
        # Apply critical multiplier
        if is_critical:
            final_damage *= self.critical_multiplier
        
        # Apply elemental modifier
        elemental_modifier, elemental_details = attacker.calculate_elemental_modifier_against(
            target, skill_element_override
        )
        final_damage *= elemental_modifier
        
        # Apply damage type modifiers
        if damage_type == DamageType.PHYSICAL:
            defense = target.get_stat("vit")
            reduction = 1.0 - (defense * self.defense_reduction_factor)
            final_damage *= max(0.1, reduction)  # Minimum 10% damage
        elif damage_type == DamageType.MAGICAL:
            defense = target.get_stat("spr")
            reduction = 1.0 - (defense * self.defense_reduction_factor)
            final_damage *= max(0.1, reduction)  # Minimum 10% damage
        # TRUE damage ignores defense
        
        # Ensure minimum damage
        final_damage = max(1.0, final_damage)
        
        # Publish damage calculation event for modifiers
        damage_info = DamageInfo(
            base_amount=base_damage,
            final_amount=final_damage,
            damage_type=damage_type,
            is_critical=is_critical,
            elemental_modifier=elemental_modifier,
            elemental_details=elemental_details
        )
        
        self._publish_damage_event("combat.damage.calculation", attacker, target, damage_info)
        
        return damage_info
    
    def _calculate_hit_chance(self, attacker: Character, target: Character, base_accuracy: float) -> float:
        """Calculate the chance for an attack to hit"""
        # Base accuracy modified by speed difference
        attacker_speed = attacker.get_stat("spd")
        target_speed = target.get_stat("spd")
        
        speed_modifier = (attacker_speed - target_speed) * self.evasion_factor
        final_accuracy = base_accuracy + speed_modifier
        
        return max(0.05, min(0.99, final_accuracy))  # 5% minimum, 99% maximum
    
    def _calculate_critical_chance(self, attacker: Character, _target: Character, base_crit: float) -> float:
        """Calculate critical hit chance"""
        # Base critical chance modified by luck
        luck_modifier = attacker.get_stat("lck") * 0.005  # 0.5% per luck point
        final_crit = base_crit + luck_modifier
        
        return max(0.0, min(0.5, final_crit))  # 0% minimum, 50% maximum
    
    def _roll_success(self, chance: float) -> bool:
        """Roll for success based on chance (0.0 to 1.0)"""
        import random
        return random.random() < chance
    
    def _apply_damage(self, target: Character, damage_info: DamageInfo):
        """Apply damage/healing to a character"""
        if damage_info.damage_type == DamageType.HEALING:
            # Healing
            old_hp = target.current_hp
            max_hp = target.get_stat("hp")
            target.current_hp = min(max_hp, target.current_hp + damage_info.final_amount)
            actual_healing = target.current_hp - old_hp
            
            logger.info("%s healed for %.1f HP (%.1f -> %.1f)", 
                       target.name, actual_healing, old_hp, target.current_hp)
        else:
            # Damage
            old_hp = target.current_hp
            target.current_hp = max(0, target.current_hp - damage_info.final_amount)
            actual_damage = old_hp - target.current_hp
            
            # Build damage description
            damage_desc = f"{damage_info.damage_type.value}"
            if damage_info.elemental_modifier != 1.0:
                if damage_info.elemental_modifier > 1.0:
                    damage_desc += " (super effective!)"
                elif damage_info.elemental_modifier < 1.0:
                    damage_desc += " (not very effective)"
            
            logger.info("%s takes %.1f %s damage (%.1f -> %.1f)%s%s", 
                       target.name, actual_damage, damage_desc,
                       old_hp, target.current_hp,
                       " CRITICAL!" if damage_info.is_critical else "",
                       f" [Elemental: {damage_info.elemental_modifier:.1f}x]" if damage_info.elemental_modifier != 1.0 else "")
            
            # Check if character is defeated
            if target.current_hp <= 0:
                logger.info("%s is defeated!", target.name)
    
    def _publish_action_event(self, event_type: str, action: CombatAction, result: Optional[ActionResult] = None):
        """Publish a combat action event"""
        event_data = {
            "action": action,
            "battle_id": self.battle_context.battle_id
        }
        
        if result:
            event_data["result"] = result
        
        event = GameEvent(
            event_type=event_type,
            source=action.actor_id,
            data=event_data,
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
    
    def _publish_damage_event(self, event_type: str, attacker: Character, target: Character, damage_info: DamageInfo):
        """Publish a damage calculation event"""
        event = GameEvent(
            event_type=event_type,
            source=attacker.character_id,
            target=target.character_id,
            data={
                "attacker": attacker,
                "target": target,
                "damage_info": damage_info,
                "battle_id": self.battle_context.battle_id
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
    
    def _handle_damage_pre_calculation(self, event: GameEvent):
        """Handle damage pre-calculation event for modifiers"""
        # Event handler for passive abilities and modifiers
        logger.debug("Damage pre-calculation event: %s", event.event_type)
    
    def _handle_damage_post_calculation(self, event: GameEvent):
        """Handle damage post-calculation event for modifiers"""
        # Event handler for passive abilities and modifiers
        logger.debug("Damage post-calculation event: %s", event.event_type)
    
    def _handle_action_pre_execution(self, event: GameEvent):
        """Handle action pre-execution event"""
        # Event handler for passive abilities and modifiers
        logger.debug("Action pre-execution event: %s", event.event_type)
    
    def _handle_action_post_execution(self, event: GameEvent):
        """Handle action post-execution event"""
        # Event handler for passive abilities and modifiers
        logger.debug("Action post-execution event: %s", event.event_type)
    
    def get_action_history(self) -> List[ActionResult]:
        """Get the history of all actions executed in this battle"""
        return self.action_history.copy()
    
    def get_battle_stats(self) -> Dict[str, Any]:
        """Get statistics about the current battle"""
        total_actions = len(self.action_history)
        successful_actions = sum(1 for result in self.action_history if result.success)
        
        total_damage = 0.0
        total_healing = 0.0
        
        for result in self.action_history:
            for damage_info in result.damage_results.values():
                if damage_info.damage_type == DamageType.HEALING:
                    total_healing += damage_info.final_amount
                else:
                    total_damage += damage_info.final_amount
        
        return {
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "success_rate": successful_actions / max(1, total_actions),
            "total_damage_dealt": total_damage,
            "total_healing_done": total_healing,
            "battle_id": self.battle_context.battle_id
        }
