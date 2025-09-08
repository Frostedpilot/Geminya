"""
State Component - Handles character battle state and action tracking.

This component manages:
- Current battle state (alive, dead, incapacitated)
- Action gauge and turn readiness
- Last actions and cooldowns
- Character positioning and targets
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import time

from . import BaseComponent
from ..core.event_system import GameEvent, event_bus, EventPhase

logger = logging.getLogger(__name__)

class CharacterState(Enum):
    """Character's current state"""
    ALIVE = "alive"           # Active and can act
    DEAD = "dead"             # Cannot act, out of battle
    INCAPACITATED = "incapacitated"  # Alive but cannot act (stunned, etc.)
    PREPARING = "preparing"   # Preparing for battle
    RETREATED = "retreated"   # Left the battle

class ActionState(Enum):
    """Current action state"""
    IDLE = "idle"             # Not doing anything
    CHARGING = "charging"     # Building action gauge
    READY = "ready"           # Can perform action
    ACTING = "acting"         # Currently performing action
    RECOVERING = "recovering" # Post-action recovery
    WAITING = "waiting"       # Waiting for external event

@dataclass
class ActionRecord:
    """Record of an action taken"""
    action_type: str
    action_id: str
    timestamp: float
    targets: List[str] = field(default_factory=list)
    success: bool = True
    damage_dealt: float = 0.0
    healing_done: float = 0.0
    effects_applied: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Cooldown:
    """Cooldown tracking for abilities"""
    ability_id: str
    remaining_turns: int
    total_turns: int
    
    def is_ready(self) -> bool:
        """Check if cooldown is complete"""
        return self.remaining_turns <= 0
    
    def advance(self) -> bool:
        """Advance cooldown by one turn, returns True if cooldown completed"""
        if self.remaining_turns > 0:
            self.remaining_turns -= 1
            return self.remaining_turns == 0
        return False

class StateComponent(BaseComponent):
    """Component handling character state and action tracking"""
    
    def __init__(self, character_id: str):
        super().__init__(character_id)
        
        # Core state
        self.character_state = CharacterState.ALIVE
        self.action_state = ActionState.IDLE
        
        # Action gauge system
        self.action_gauge = 0.0
        self.action_gauge_max = 600.0  # Default max from design
        self.gauge_speed = 1.0  # Speed multiplier
        
        # Battle tracking
        self.battle_id: Optional[str] = None
        self.team_id: Optional[str] = None
        self.position: Optional[int] = None
        self.last_action_turn = 0
        self.turns_active = 0
        
        # Action history and cooldowns
        self.action_history: List[ActionRecord] = []
        self.max_history = 50
        self.cooldowns: Dict[str, Cooldown] = {}
        
        # Targeting and relationships
        self.current_target: Optional[str] = None
        self.threat_table: Dict[str, float] = {}  # character_id -> threat level
        self.allies: List[str] = []
        self.enemies: List[str] = []
        
        # Performance tracking
        self.total_damage_dealt = 0.0
        self.total_damage_taken = 0.0
        self.total_healing_done = 0.0
        self.skills_used = 0
        self.kills = 0
        self.deaths = 0
        
        # Setup event listeners
        self._setup_event_listeners()
    
    def initialize(self, character_data: Dict[str, Any]):
        """Initialize state from character data"""
        state_data = character_data.get("state", {})
        
        # Set initial state
        initial_state = state_data.get("character_state", "alive")
        try:
            self.character_state = CharacterState(initial_state)
        except ValueError:
            self.character_state = CharacterState.ALIVE
        
        # Set action gauge properties
        self.action_gauge = float(state_data.get("action_gauge", 0.0))
        self.action_gauge_max = float(state_data.get("action_gauge_max", 600.0))
        self.gauge_speed = float(state_data.get("gauge_speed", 1.0))
        
        # Set battle info if provided
        self.battle_id = state_data.get("battle_id")
        self.team_id = state_data.get("team_id")
        self.position = state_data.get("position")
        
        logger.debug("Initialized state for character %s", self.character_id)
    
    def update(self, delta_time: float = 0.0):
        """Update component state"""
        # Update action gauge if alive and not incapacitated
        if self.character_state == CharacterState.ALIVE and self.action_state in [ActionState.IDLE, ActionState.CHARGING]:
            self._update_action_gauge(delta_time)
        
        # Update cooldowns
        self._update_cooldowns()
        
        # Check if ready to act
        if (self.action_gauge >= self.action_gauge_max and 
            self.character_state == CharacterState.ALIVE and
            self.action_state == ActionState.CHARGING):
            self.set_action_state(ActionState.READY)
    
    def get_data(self) -> Dict[str, Any]:
        """Get component's current data"""
        return {
            "component_type": self.component_type,
            "character_state": self.character_state.value,
            "action_state": self.action_state.value,
            "action_gauge": self.action_gauge,
            "action_gauge_max": self.action_gauge_max,
            "gauge_speed": self.gauge_speed,
            "battle_id": self.battle_id,
            "team_id": self.team_id,
            "position": self.position,
            "last_action_turn": self.last_action_turn,
            "turns_active": self.turns_active,
            "cooldowns": {
                cd_id: {
                    "ability_id": cd.ability_id,
                    "remaining_turns": cd.remaining_turns,
                    "total_turns": cd.total_turns
                }
                for cd_id, cd in self.cooldowns.items()
            },
            "current_target": self.current_target,
            "threat_table": dict(self.threat_table),
            "allies": list(self.allies),
            "enemies": list(self.enemies),
            "performance": {
                "total_damage_dealt": self.total_damage_dealt,
                "total_damage_taken": self.total_damage_taken,
                "total_healing_done": self.total_healing_done,
                "skills_used": self.skills_used,
                "kills": self.kills,
                "deaths": self.deaths
            }
        }
    
    def set_data(self, data: Dict[str, Any]):
        """Set component data"""
        # Set states
        try:
            self.character_state = CharacterState(data.get("character_state", "alive"))
            self.action_state = ActionState(data.get("action_state", "idle"))
        except ValueError as e:
            logger.warning("Invalid state in data: %s", e)
        
        # Set action gauge
        self.action_gauge = float(data.get("action_gauge", 0.0))
        self.action_gauge_max = float(data.get("action_gauge_max", 600.0))
        self.gauge_speed = float(data.get("gauge_speed", 1.0))
        
        # Set battle info
        self.battle_id = data.get("battle_id")
        self.team_id = data.get("team_id")
        self.position = data.get("position")
        self.last_action_turn = data.get("last_action_turn", 0)
        self.turns_active = data.get("turns_active", 0)
        
        # Set cooldowns
        cooldowns_data = data.get("cooldowns", {})
        self.cooldowns.clear()
        for cd_id, cd_data in cooldowns_data.items():
            cooldown = Cooldown(
                ability_id=cd_data["ability_id"],
                remaining_turns=cd_data["remaining_turns"],
                total_turns=cd_data["total_turns"]
            )
            self.cooldowns[cd_id] = cooldown
        
        # Set targeting info
        self.current_target = data.get("current_target")
        self.threat_table = dict(data.get("threat_table", {}))
        self.allies = list(data.get("allies", []))
        self.enemies = list(data.get("enemies", []))
        
        # Set performance data
        performance = data.get("performance", {})
        self.total_damage_dealt = performance.get("total_damage_dealt", 0.0)
        self.total_damage_taken = performance.get("total_damage_taken", 0.0)
        self.total_healing_done = performance.get("total_healing_done", 0.0)
        self.skills_used = performance.get("skills_used", 0)
        self.kills = performance.get("kills", 0)
        self.deaths = performance.get("deaths", 0)
    
    def set_character_state(self, new_state: Union[CharacterState, str]):
        """Set the character's state"""
        if isinstance(new_state, str):
            try:
                new_state = CharacterState(new_state)
            except ValueError:
                logger.warning("Invalid character state: %s", new_state)
                return
        
        old_state = self.character_state
        self.character_state = new_state
        
        # Publish state change event
        event = GameEvent(
            event_type="character.state_changed",
            source=self.character_id,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "old_state": old_state.value,
                "new_state": new_state.value
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.debug("Character %s state changed from %s to %s", 
                    self.character_id, old_state.value, new_state.value)
    
    def set_action_state(self, new_state: Union[ActionState, str]):
        """Set the action state"""
        if isinstance(new_state, str):
            try:
                new_state = ActionState(new_state)
            except ValueError:
                logger.warning("Invalid action state: %s", new_state)
                return
        
        old_state = self.action_state
        self.action_state = new_state
        
        # Publish action state change event
        event = GameEvent(
            event_type="character.action_state_changed",
            source=self.character_id,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "old_action_state": old_state.value,
                "new_action_state": new_state.value
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.debug("Character %s action state changed from %s to %s", 
                    self.character_id, old_state.value, new_state.value)
    
    def is_alive(self) -> bool:
        """Check if character is alive"""
        return self.character_state == CharacterState.ALIVE
    
    def is_ready_to_act(self) -> bool:
        """Check if character can perform an action"""
        return (self.character_state == CharacterState.ALIVE and 
                self.action_state == ActionState.READY)
    
    def can_use_ability(self, ability_id: str) -> bool:
        """Check if an ability is available (not on cooldown)"""
        cooldown = self.cooldowns.get(ability_id)
        return cooldown is None or cooldown.is_ready()
    
    def start_cooldown(self, ability_id: str, turns: int):
        """Start a cooldown for an ability"""
        self.cooldowns[ability_id] = Cooldown(
            ability_id=ability_id,
            remaining_turns=turns,
            total_turns=turns
        )
        
        logger.debug("Started %d turn cooldown for ability %s on character %s", 
                    turns, ability_id, self.character_id)
    
    def reset_action_gauge(self):
        """Reset action gauge to 0"""
        self.action_gauge = 0.0
        self.set_action_state(ActionState.CHARGING)
    
    def modify_action_gauge(self, amount: float):
        """Modify action gauge by amount"""
        old_gauge = self.action_gauge
        self.action_gauge = max(0.0, self.action_gauge + amount)
        
        # Publish gauge change event
        event = GameEvent(
            event_type="character.action_gauge_changed",
            source=self.character_id,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "old_gauge": old_gauge,
                "new_gauge": self.action_gauge,
                "change": amount
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
    
    def record_action(self, action_type: str, action_id: str, targets: Optional[List[str]] = None, **kwargs):
        """Record an action taken by this character"""
        record = ActionRecord(
            action_type=action_type,
            action_id=action_id,
            timestamp=time.time(),
            targets=targets or [],
            success=kwargs.get("success", True),
            damage_dealt=kwargs.get("damage_dealt", 0.0),
            healing_done=kwargs.get("healing_done", 0.0),
            effects_applied=kwargs.get("effects_applied", []),
            data=kwargs.get("data", {})
        )
        
        self.action_history.append(record)
        
        # Limit history size
        if len(self.action_history) > self.max_history:
            self.action_history.pop(0)
        
        # Update statistics
        self.skills_used += 1
        self.total_damage_dealt += record.damage_dealt
        self.total_healing_done += record.healing_done
        
        logger.debug("Recorded action %s for character %s", action_id, self.character_id)
    
    def set_target(self, target_id: Optional[str]):
        """Set current target"""
        old_target = self.current_target
        self.current_target = target_id
        
        if old_target != target_id:
            # Publish target change event
            event = GameEvent(
                event_type="character.target_changed",
                source=self.character_id,
                target=target_id,
                data={
                    "character_id": self.character_id,
                    "old_target": old_target,
                    "new_target": target_id
                },
                phase=EventPhase.PROCESS
            )
            event_bus.publish(event)
    
    def add_threat(self, character_id: str, threat_amount: float):
        """Add threat toward a character"""
        if character_id not in self.threat_table:
            self.threat_table[character_id] = 0.0
        self.threat_table[character_id] += threat_amount
        
        logger.debug("Added %f threat toward %s for character %s", 
                    threat_amount, character_id, self.character_id)
    
    def get_highest_threat_target(self) -> Optional[str]:
        """Get the character with highest threat"""
        if not self.threat_table:
            return None
        return max(self.threat_table.items(), key=lambda x: x[1])[0]
    
    def _setup_event_listeners(self):
        """Set up event listeners for this component"""
        def on_damage_dealt(event: GameEvent) -> GameEvent:
            if event.data.get("source_id") == self.character_id:
                damage = event.get_value("damage_amount", 0.0)
                self.total_damage_dealt += damage
                
                # Add threat to target
                target_id = event.data.get("target_id")
                if target_id:
                    self.add_threat(target_id, damage * 0.1)  # 10% of damage as threat
            return event
        
        def on_damage_taken(event: GameEvent) -> GameEvent:
            if event.data.get("target_id") == self.character_id:
                damage = event.get_value("damage_amount", 0.0)
                self.total_damage_taken += damage
                
                # Add threat toward attacker
                source_id = event.data.get("source_id")
                if source_id:
                    self.add_threat(source_id, damage * 0.2)  # 20% of damage taken as threat
            return event
        
        def on_turn_start(event: GameEvent) -> GameEvent:
            if event.data.get("character_id") == self.character_id:
                self.turns_active += 1
                self.last_action_turn = event.data.get("turn_number", 0)
            return event
        
        self.register_event_listener("damage.dealt", on_damage_dealt)
        self.register_event_listener("damage.dealt", on_damage_taken)  # Same event, different handler
        self.register_event_listener("turn.start", on_turn_start)
    
    def _update_action_gauge(self, delta_time: float):  # pylint: disable=unused-argument
        """Update the action gauge"""
        # Base gauge increase (design specifies gauge speed affects this)
        gauge_increase = self.gauge_speed * 10.0  # Base 10 points per update
        
        old_gauge = self.action_gauge
        self.action_gauge = min(self.action_gauge_max, self.action_gauge + gauge_increase)
        
        # Check if gauge became full
        if old_gauge < self.action_gauge_max and self.action_gauge >= self.action_gauge_max:
            # Publish gauge full event
            event = GameEvent(
                event_type="character.action_gauge_full",
                source=self.character_id,
                target=self.character_id,
                data={
                    "character_id": self.character_id,
                    "action_gauge": self.action_gauge
                },
                phase=EventPhase.PROCESS
            )
            event_bus.publish(event)
    
    def _update_cooldowns(self):
        """Update all cooldowns"""
        completed_cooldowns = []
        
        for cd_id, cooldown in self.cooldowns.items():
            if cooldown.advance():
                completed_cooldowns.append(cd_id)
        
        # Remove completed cooldowns
        for cd_id in completed_cooldowns:
            del self.cooldowns[cd_id]
            
            # Publish cooldown completed event
            event = GameEvent(
                event_type="character.cooldown_completed",
                source=self.character_id,
                target=self.character_id,
                data={
                    "character_id": self.character_id,
                    "ability_id": cd_id
                },
                phase=EventPhase.PROCESS
            )
            event_bus.publish(event)
