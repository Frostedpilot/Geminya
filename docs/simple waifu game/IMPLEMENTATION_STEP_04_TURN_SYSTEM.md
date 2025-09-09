# Implementation Guide - Step 4: Turn System and Action Gauge

## Dynamic Turn Order and Action Management

### Overview

This step implements the dynamic turn system with action gauges, turn processing, and the core battle loop. The system handles the complex turn order mechanics described in the game design, including gauge normalization, overflow handling, and turn management.

### Prerequisites

- Completed Step 1 (Foundation Setup)
- Completed Step 2 (Component System)
- Completed Step 3 (Abilities and Skills)
- Understanding of action gauge mechanics

### Step 4.1: State Component Implementation

First, create the state component that tracks character battle state:

**File: `src/game/components/state_component.py`**

```python
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from . import BaseComponent
from ..core.event_system import GameEvent, event_bus

class CharacterState(Enum):
    """Possible character states"""
    ALIVE = "alive"
    DEFEATED = "defeated"
    STUNNED = "stunned"
    ACTING = "acting"
    WAITING = "waiting"

class ActionState(Enum):
    """Action execution states"""
    IDLE = "idle"
    SELECTING = "selecting"
    EXECUTING = "executing"
    RECOVERING = "recovering"

@dataclass
class TurnHistory:
    """Record of actions taken by the character"""
    turn_number: int
    action_type: str
    skill_id: Optional[str] = None
    targets: List[str] = field(default_factory=list)
    result: str = "success"
    timestamp: float = field(default_factory=lambda: __import__('time').time())

class StateComponent(BaseComponent):
    """Component tracking character battle state and turn information"""
    
    def __init__(self, character_id: str):
        super().__init__(character_id)
        self.current_state = CharacterState.ALIVE
        self.action_state = ActionState.IDLE
        self.action_gauge = 0
        self.position = 0
        self.team = 1
        self.current_hp = 0
        self.max_hp = 0
        self.is_leader = False
        
        # Turn tracking
        self.last_action_turn = -1
        self.consecutive_actions = 0
        self.turn_history: List[TurnHistory] = []
        
        # Combat tracking
        self.damage_dealt_this_battle = 0
        self.damage_taken_this_battle = 0
        self.healing_done_this_battle = 0
        self.skills_used_this_battle = 0
        
        # AI decision data
        self.threat_level = 0.0
        self.priority_target_id: Optional[str] = None
        self.last_skill_category = None
        
        self._setup_event_listeners()
    
    def initialize(self, character_data: Dict[str, Any]):
        """Initialize state from character data"""
        self.position = character_data.get("position", 0)
        self.team = character_data.get("team", 1)
        self.is_leader = character_data.get("is_leader", False)
        
        # HP initialization
        stats = character_data.get("stats", {})
        self.max_hp = float(stats.get("hp", 100))
        self.current_hp = character_data.get("current_hp", self.max_hp)
        
        # Action gauge starts at random value between 400-600
        import random
        self.action_gauge = random.randint(400, 600)
        
        # Initialize state
        self.current_state = CharacterState.ALIVE if self.current_hp > 0 else CharacterState.DEFEATED
        
        # Publish initialization event
        event = GameEvent(
            event_type="state_initialized",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "initial_state": self.current_state.value,
                "action_gauge": self.action_gauge,
                "position": self.position,
                "team": self.team,
                "current_hp": self.current_hp,
                "max_hp": self.max_hp
            }
        )
        event_bus.publish(event)
    
    def update(self, delta_time: float = 0.0):
        """Update component state"""
        # Update threat level based on recent actions
        self._update_threat_level()
        
        # Clean old turn history
        current_turn = self._get_current_turn()
        if current_turn > 10:  # Keep last 10 turns
            self.turn_history = [h for h in self.turn_history if h.turn_number > current_turn - 10]
    
    def get_data(self) -> Dict[str, Any]:
        """Get component's current data"""
        return {
            "current_state": self.current_state.value,
            "action_state": self.action_state.value,
            "action_gauge": self.action_gauge,
            "position": self.position,
            "team": self.team,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "is_leader": self.is_leader,
            "last_action_turn": self.last_action_turn,
            "consecutive_actions": self.consecutive_actions,
            "turn_history": [
                {
                    "turn_number": h.turn_number,
                    "action_type": h.action_type,
                    "skill_id": h.skill_id,
                    "targets": h.targets,
                    "result": h.result,
                    "timestamp": h.timestamp
                }
                for h in self.turn_history
            ],
            "damage_dealt_this_battle": self.damage_dealt_this_battle,
            "damage_taken_this_battle": self.damage_taken_this_battle,
            "healing_done_this_battle": self.healing_done_this_battle,
            "skills_used_this_battle": self.skills_used_this_battle,
            "threat_level": self.threat_level,
            "priority_target_id": self.priority_target_id,
            "last_skill_category": self.last_skill_category
        }
    
    def set_data(self, data: Dict[str, Any]):
        """Set component data"""
        self.current_state = CharacterState(data.get("current_state", "alive"))
        self.action_state = ActionState(data.get("action_state", "idle"))
        self.action_gauge = data.get("action_gauge", 0)
        self.position = data.get("position", 0)
        self.team = data.get("team", 1)
        self.current_hp = data.get("current_hp", 0)
        self.max_hp = data.get("max_hp", 100)
        self.is_leader = data.get("is_leader", False)
        self.last_action_turn = data.get("last_action_turn", -1)
        self.consecutive_actions = data.get("consecutive_actions", 0)
        
        # Load turn history
        self.turn_history.clear()
        history_data = data.get("turn_history", [])
        for h_data in history_data:
            history = TurnHistory(
                turn_number=h_data["turn_number"],
                action_type=h_data["action_type"],
                skill_id=h_data.get("skill_id"),
                targets=h_data.get("targets", []),
                result=h_data.get("result", "success"),
                timestamp=h_data.get("timestamp", 0.0)
            )
            self.turn_history.append(history)
        
        # Load battle stats
        self.damage_dealt_this_battle = data.get("damage_dealt_this_battle", 0)
        self.damage_taken_this_battle = data.get("damage_taken_this_battle", 0)
        self.healing_done_this_battle = data.get("healing_done_this_battle", 0)
        self.skills_used_this_battle = data.get("skills_used_this_battle", 0)
        
        # Load AI data
        self.threat_level = data.get("threat_level", 0.0)
        self.priority_target_id = data.get("priority_target_id")
        self.last_skill_category = data.get("last_skill_category")
    
    def set_state(self, new_state: CharacterState):
        """Change character state with event notification"""
        old_state = self.current_state
        self.current_state = new_state
        
        event = GameEvent(
            event_type="character_state_changed",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "old_state": old_state.value,
                "new_state": new_state.value
            }
        )
        event_bus.publish(event)
    
    def set_action_state(self, new_action_state: ActionState):
        """Change action state"""
        old_action_state = self.action_state
        self.action_state = new_action_state
        
        event = GameEvent(
            event_type="action_state_changed",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "old_action_state": old_action_state.value,
                "new_action_state": new_action_state.value
            }
        )
        event_bus.publish(event)
    
    def modify_hp(self, amount: float, source: str = "unknown") -> float:
        """Modify HP and handle state changes"""
        old_hp = self.current_hp
        self.current_hp = max(0, min(self.current_hp + amount, self.max_hp))
        actual_change = self.current_hp - old_hp
        
        # Update battle stats
        if amount > 0:
            self.healing_done_this_battle += actual_change
        else:
            self.damage_taken_this_battle += abs(actual_change)
        
        # Check for defeat
        if self.current_hp <= 0 and self.current_state != CharacterState.DEFEATED:
            self.set_state(CharacterState.DEFEATED)
        elif self.current_hp > 0 and self.current_state == CharacterState.DEFEATED:
            self.set_state(CharacterState.ALIVE)
        
        # Publish HP change event
        event = GameEvent(
            event_type="hp_changed",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "old_hp": old_hp,
                "new_hp": self.current_hp,
                "change": actual_change,
                "source": source,
                "hp_percentage": self.current_hp / self.max_hp if self.max_hp > 0 else 0
            }
        )
        event_bus.publish(event)
        
        return actual_change
    
    def modify_action_gauge(self, amount: int, source: str = "turn_tick"):
        """Modify action gauge value"""
        old_gauge = self.action_gauge
        self.action_gauge += amount
        
        # Handle overflow for turn determination
        overflow = 0
        if self.action_gauge >= 1000:
            overflow = self.action_gauge - 1000
        
        event = GameEvent(
            event_type="action_gauge_changed",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "old_gauge": old_gauge,
                "new_gauge": self.action_gauge,
                "change": amount,
                "source": source,
                "overflow": overflow
            }
        )
        event_bus.publish(event)
    
    def reset_action_gauge(self, overflow: int = 0):
        """Reset action gauge after taking a turn"""
        old_gauge = self.action_gauge
        self.action_gauge = overflow
        
        event = GameEvent(
            event_type="action_gauge_reset",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "old_gauge": old_gauge,
                "new_gauge": self.action_gauge,
                "overflow": overflow
            }
        )
        event_bus.publish(event)
    
    def record_action(self, action_type: str, skill_id: Optional[str] = None, 
                     targets: List[str] = None, result: str = "success"):
        """Record an action taken by this character"""
        current_turn = self._get_current_turn()
        
        history = TurnHistory(
            turn_number=current_turn,
            action_type=action_type,
            skill_id=skill_id,
            targets=targets or [],
            result=result
        )
        self.turn_history.append(history)
        
        # Update tracking
        self.last_action_turn = current_turn
        if action_type == "skill":
            self.skills_used_this_battle += 1
        
        # Update consecutive actions
        if len(self.turn_history) >= 2 and self.turn_history[-2].turn_number == current_turn - 1:
            self.consecutive_actions += 1
        else:
            self.consecutive_actions = 1
        
        # Publish action recorded event
        event = GameEvent(
            event_type="action_recorded",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "action": history,
                "consecutive_actions": self.consecutive_actions
            }
        )
        event_bus.publish(event)
    
    def get_hp_percentage(self) -> float:
        """Get current HP as a percentage of max HP"""
        return self.current_hp / self.max_hp if self.max_hp > 0 else 0.0
    
    def is_alive(self) -> bool:
        """Check if character is alive"""
        return self.current_state != CharacterState.DEFEATED
    
    def can_act(self) -> bool:
        """Check if character can take actions"""
        return (self.is_alive() and 
                self.current_state not in [CharacterState.STUNNED] and
                self.action_state == ActionState.IDLE)
    
    def get_recent_actions(self, turns: int = 3) -> List[TurnHistory]:
        """Get recent actions within the specified number of turns"""
        current_turn = self._get_current_turn()
        cutoff_turn = current_turn - turns
        return [h for h in self.turn_history if h.turn_number > cutoff_turn]
    
    def _get_current_turn(self) -> int:
        """Get current turn number from battle context"""
        # This would be injected or accessed through battle context
        # For now, return a placeholder
        return 0
    
    def _update_threat_level(self):
        """Update threat level based on recent actions and stats"""
        base_threat = 0.0
        
        # Factor in damage dealt
        if self.damage_dealt_this_battle > 0:
            base_threat += min(self.damage_dealt_this_battle / 1000.0, 1.0)
        
        # Factor in recent actions
        recent_actions = self.get_recent_actions(3)
        aggressive_actions = sum(1 for action in recent_actions 
                               if action.action_type in ["attack", "skill"])
        base_threat += aggressive_actions * 0.1
        
        # Factor in HP percentage (lower HP = lower threat)
        hp_factor = self.get_hp_percentage()
        base_threat *= hp_factor
        
        self.threat_level = min(base_threat, 2.0)  # Cap at 2.0
    
    def _setup_event_listeners(self):
        """Set up event listeners for this component"""
        self.register_event_listener(
            "damage_dealt",
            self._on_damage_dealt
        )
        
        self.register_event_listener(
            "healing_applied",
            self._on_healing_applied
        )
        
        self.register_event_listener(
            "turn_started",
            self._on_turn_started
        )
    
    def _on_damage_dealt(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle damage dealt events"""
        if event.get_value("source_id") == self.character_id:
            damage = event.get_value("final_damage", 0)
            self.damage_dealt_this_battle += damage
        
        return event
    
    def _on_healing_applied(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle healing applied events"""
        if event.get_value("source_id") == self.character_id:
            healing = event.get_value("final_healing", 0)
            self.healing_done_this_battle += healing
        
        return event
    
    def _on_turn_started(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle turn started events"""
        if event.get_value("character_id") == self.character_id:
            self.set_action_state(ActionState.SELECTING)
        
        return event
```

### Step 4.2: Turn System Implementation

Create the core turn system that manages action gauges and turn order:

**File: `src/game/systems/turn_system.py`**

```python
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from ..core.event_system import GameEvent, event_bus
from ..core.battle_context import BattleContext, BattlePhase
from ..components.state_component import CharacterState, ActionState

logger = logging.getLogger(__name__)

@dataclass
class TurnCandidate:
    """A character eligible to take a turn"""
    character_id: str
    action_gauge: int
    overflow: int
    speed: float
    priority_modifier: float = 0.0
    
    @property
    def effective_priority(self) -> float:
        """Calculate effective priority for turn order"""
        return self.overflow + self.priority_modifier

class TurnPhase(Enum):
    """Phases of turn processing"""
    GAUGE_TICK = "gauge_tick"
    TURN_SELECTION = "turn_selection"
    TURN_EXECUTION = "turn_execution"
    TURN_CLEANUP = "turn_cleanup"
    ROUND_END = "round_end"

class TurnSystem:
    """System managing turn order and action gauge mechanics"""
    
    def __init__(self, battle_context: BattleContext):
        self.battle_context = battle_context
        self.current_phase = TurnPhase.GAUGE_TICK
        self.current_turn_character: Optional[str] = None
        self.turn_queue: List[TurnCandidate] = []
        self.round_action_gauge_total = 0
        self.round_threshold = 0
        self.turn_timeout = 30.0  # seconds
        self.turn_start_time = 0.0
        
        self._setup_event_listeners()
        self._calculate_round_threshold()
    
    def start_battle(self):
        """Initialize the turn system for battle start"""
        # Normalize initial action gauges
        self._normalize_initial_gauges()
        
        # Start the turn processing loop
        self.current_phase = TurnPhase.GAUGE_TICK
        
        # Publish battle start event
        event = GameEvent(
            event_type="battle_turn_system_started",
            source=self,
            data={
                "battle_id": self.battle_context.battle_id,
                "round_threshold": self.round_threshold
            }
        )
        event_bus.publish(event)
        
        # Process first turn
        self.process_turn_cycle()
    
    def process_turn_cycle(self):
        """Process one complete turn cycle"""
        while self.current_phase != TurnPhase.ROUND_END:
            if self.current_phase == TurnPhase.GAUGE_TICK:
                self._tick_action_gauges()
                self.current_phase = TurnPhase.TURN_SELECTION
            
            elif self.current_phase == TurnPhase.TURN_SELECTION:
                if self._select_next_turn():
                    self.current_phase = TurnPhase.TURN_EXECUTION
                else:
                    self.current_phase = TurnPhase.GAUGE_TICK
            
            elif self.current_phase == TurnPhase.TURN_EXECUTION:
                self._execute_current_turn()
                self.current_phase = TurnPhase.TURN_CLEANUP
            
            elif self.current_phase == TurnPhase.TURN_CLEANUP:
                self._cleanup_turn()
                self._check_round_end()
                if self.current_phase != TurnPhase.ROUND_END:
                    self.current_phase = TurnPhase.GAUGE_TICK
        
        # Process round end
        self._process_round_end()
    
    def force_turn_end(self):
        """Force the current turn to end (for timeouts)"""
        if self.current_turn_character:
            logger.warning(f"Forcing turn end for character {self.current_turn_character}")
            
            # Record timeout action
            character = self.battle_context.get_character(self.current_turn_character)
            if character and "components" in character:
                state_comp = character["components"].get("state")
                if state_comp:
                    state_comp.record_action("timeout", result="timeout")
            
            self._cleanup_turn()
            self.current_phase = TurnPhase.GAUGE_TICK
    
    def get_turn_order_preview(self, turns_ahead: int = 5) -> List[str]:
        """Get a preview of upcoming turn order"""
        # Simulate gauge ticking to predict turn order
        preview_characters = []
        simulated_gauges = {}
        
        # Get current gauges
        for character in self.battle_context.get_living_characters():
            char_id = character["id"]
            state_comp = character.get("components", {}).get("state")
            stats_comp = character.get("components", {}).get("stats")
            
            if state_comp and stats_comp:
                simulated_gauges[char_id] = {
                    "gauge": state_comp.action_gauge,
                    "speed": stats_comp.get_stat("spd")
                }
        
        # Simulate turns
        for _ in range(turns_ahead):
            # Tick gauges
            for char_id, data in simulated_gauges.items():
                data["gauge"] += data["speed"]
            
            # Find next character to act
            next_char = None
            highest_gauge = 0
            highest_overflow = 0
            
            for char_id, data in simulated_gauges.items():
                if data["gauge"] >= 1000:
                    overflow = data["gauge"] - 1000
                    if overflow > highest_overflow or (overflow == highest_overflow and data["gauge"] > highest_gauge):
                        next_char = char_id
                        highest_gauge = data["gauge"]
                        highest_overflow = overflow
            
            if next_char:
                preview_characters.append(next_char)
                simulated_gauges[next_char]["gauge"] = highest_overflow
            else:
                break
        
        return preview_characters
    
    def _normalize_initial_gauges(self):
        """Set initial action gauges to random values between 400-600"""
        import random
        
        for character in self.battle_context.get_all_characters():
            state_comp = character.get("components", {}).get("state")
            if state_comp:
                initial_gauge = random.randint(400, 600)
                state_comp.action_gauge = initial_gauge
                
                # Publish initialization event
                event = GameEvent(
                    event_type="action_gauge_initialized",
                    source=self,
                    target=character["id"],
                    data={
                        "character_id": character["id"],
                        "initial_gauge": initial_gauge
                    }
                )
                event_bus.publish(event)
    
    def _tick_action_gauges(self):
        """Increase all living characters' action gauges by their speed"""
        living_characters = self.battle_context.get_living_characters()
        
        for character in living_characters:
            char_id = character["id"]
            state_comp = character.get("components", {}).get("state")
            stats_comp = character.get("components", {}).get("stats")
            
            if state_comp and stats_comp and state_comp.can_act():
                speed = stats_comp.get_stat("spd")
                state_comp.modify_action_gauge(int(speed), "turn_tick")
                
                # Track for round calculation
                self.round_action_gauge_total += int(speed)
        
        # Publish gauge tick event
        event = GameEvent(
            event_type="action_gauges_ticked",
            source=self,
            data={
                "living_character_count": len(living_characters),
                "round_gauge_total": self.round_action_gauge_total,
                "round_threshold": self.round_threshold
            }
        )
        event_bus.publish(event)
    
    def _select_next_turn(self) -> bool:
        """Select the next character to take a turn"""
        candidates = []
        
        for character in self.battle_context.get_living_characters():
            char_id = character["id"]
            state_comp = character.get("components", {}).get("state")
            stats_comp = character.get("components", {}).get("stats")
            
            if state_comp and stats_comp and state_comp.can_act():
                if state_comp.action_gauge >= 1000:
                    overflow = state_comp.action_gauge - 1000
                    speed = stats_comp.get_stat("spd")
                    
                    candidate = TurnCandidate(
                        character_id=char_id,
                        action_gauge=state_comp.action_gauge,
                        overflow=overflow,
                        speed=speed
                    )
                    candidates.append(candidate)
        
        if not candidates:
            return False  # No one ready to act
        
        # Sort by overflow (highest first), then by speed if tied
        candidates.sort(key=lambda c: (c.overflow, c.speed), reverse=True)
        
        # Select the first candidate
        selected = candidates[0]
        self.current_turn_character = selected.character_id
        
        # Reset the selected character's gauge to overflow
        character = self.battle_context.get_character(selected.character_id)
        if character:
            state_comp = character.get("components", {}).get("state")
            if state_comp:
                state_comp.reset_action_gauge(selected.overflow)
        
        # Publish turn start event
        event = GameEvent(
            event_type="turn_started",
            source=self,
            target=selected.character_id,
            data={
                "character_id": selected.character_id,
                "turn_number": self.battle_context.turn_number,
                "action_gauge": selected.action_gauge,
                "overflow": selected.overflow,
                "candidates": [c.character_id for c in candidates]
            }
        )
        event_bus.publish(event)
        
        self.battle_context.turn_number += 1
        self.battle_context.active_character_id = selected.character_id
        self.turn_start_time = __import__('time').time()
        
        return True
    
    def _execute_current_turn(self):
        """Execute the current character's turn"""
        if not self.current_turn_character:
            return
        
        character = self.battle_context.get_character(self.current_turn_character)
        if not character:
            return
        
        state_comp = character.get("components", {}).get("state")
        if state_comp:
            state_comp.set_action_state(ActionState.ACTING)
        
        # Publish turn execution event
        event = GameEvent(
            event_type="turn_executing",
            source=self,
            target=self.current_turn_character,
            data={
                "character_id": self.current_turn_character,
                "turn_number": self.battle_context.turn_number - 1
            }
        )
        event_bus.publish(event)
        
        # The actual turn execution (AI decision, skill selection, etc.)
        # will be handled by other systems listening to the turn_executing event
    
    def _cleanup_turn(self):
        """Clean up after a turn is complete"""
        if not self.current_turn_character:
            return
        
        character = self.battle_context.get_character(self.current_turn_character)
        if character:
            state_comp = character.get("components", {}).get("state")
            if state_comp:
                state_comp.set_action_state(ActionState.IDLE)
        
        # Publish turn end event
        event = GameEvent(
            event_type="turn_ended",
            source=self,
            target=self.current_turn_character,
            data={
                "character_id": self.current_turn_character,
                "turn_number": self.battle_context.turn_number - 1
            }
        )
        event_bus.publish(event)
        
        self.battle_context.active_character_id = None
        self.current_turn_character = None
        self.turn_start_time = 0.0
    
    def _check_round_end(self):
        """Check if a round has ended based on action gauge accumulation"""
        if self.round_action_gauge_total >= self.round_threshold:
            self.current_phase = TurnPhase.ROUND_END
    
    def _process_round_end(self):
        """Process end of round effects"""
        self.battle_context.round_number += 1
        self.round_action_gauge_total = 0
        self._calculate_round_threshold()
        
        # Publish round end event
        event = GameEvent(
            event_type="round_ended",
            source=self,
            data={
                "round_number": self.battle_context.round_number - 1,
                "new_round": self.battle_context.round_number
            }
        )
        event_bus.publish(event)
        
        # Check for sudden death
        if self.battle_context.round_number >= 20:
            self._apply_sudden_death()
        
        # Check battle limits
        if self.battle_context.round_number >= self.battle_context.max_rounds:
            self._trigger_battle_timeout()
        else:
            # Continue to next round
            self.current_phase = TurnPhase.GAUGE_TICK
    
    def _calculate_round_threshold(self):
        """Calculate the action gauge threshold for round completion"""
        living_count = len(self.battle_context.get_living_characters())
        self.round_threshold = living_count * 1000
    
    def _apply_sudden_death(self):
        """Apply sudden death stat modifications"""
        round_num = self.battle_context.round_number
        if round_num < 20:
            return
        
        multiplier_power = round_num - 20
        stat_multiplier = 1.1 ** multiplier_power
        resistance_multiplier = 0.9 ** multiplier_power
        
        # Apply to all living characters
        for character in self.battle_context.get_living_characters():
            stats_comp = character.get("components", {}).get("stats")
            if stats_comp:
                # Apply sudden death modifiers
                from ..components.stats_component import StatModifier, StatType, ModifierType
                
                # Remove old sudden death modifiers
                stats_comp.remove_modifiers_by_source("sudden_death")
                
                # Add new modifiers
                atk_mod = StatModifier(
                    modifier_id=f"sudden_death_atk_{round_num}",
                    stat_type=StatType.ATK,
                    modifier_type=ModifierType.MULTIPLICATIVE,
                    value=stat_multiplier,
                    source="sudden_death",
                    layer=6
                )
                
                mag_mod = StatModifier(
                    modifier_id=f"sudden_death_mag_{round_num}",
                    stat_type=StatType.MAG,
                    modifier_type=ModifierType.MULTIPLICATIVE,
                    value=stat_multiplier,
                    source="sudden_death",
                    layer=6
                )
                
                spr_mod = StatModifier(
                    modifier_id=f"sudden_death_spr_{round_num}",
                    stat_type=StatType.SPR,
                    modifier_type=ModifierType.MULTIPLICATIVE,
                    value=resistance_multiplier,
                    source="sudden_death",
                    layer=6
                )
                
                stats_comp.add_modifier(atk_mod)
                stats_comp.add_modifier(mag_mod)
                stats_comp.add_modifier(spr_mod)
        
        # Publish sudden death event
        event = GameEvent(
            event_type="sudden_death_applied",
            source=self,
            data={
                "round_number": round_num,
                "stat_multiplier": stat_multiplier,
                "resistance_multiplier": resistance_multiplier
            }
        )
        event_bus.publish(event)
    
    def _trigger_battle_timeout(self):
        """Handle battle timeout"""
        # Publish battle timeout event
        event = GameEvent(
            event_type="battle_timeout",
            source=self,
            data={
                "round_number": self.battle_context.round_number,
                "max_rounds": self.battle_context.max_rounds
            }
        )
        event_bus.publish(event)
        
        # Set battle phase to completed
        self.battle_context.set_phase(BattlePhase.COMPLETED)
    
    def _setup_event_listeners(self):
        """Set up event listeners for the turn system"""
        event_bus.register_handler(
            "action_completed",
            self._on_action_completed
        )
        
        event_bus.register_handler(
            "character_defeated",
            self._on_character_defeated
        )
    
    def _on_action_completed(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle action completion to continue turn processing"""
        character_id = event.get_value("character_id")
        if character_id == self.current_turn_character:
            # Turn action is complete, proceed to cleanup
            if self.current_phase == TurnPhase.TURN_EXECUTION:
                self.current_phase = TurnPhase.TURN_CLEANUP
        
        return event
    
    def _on_character_defeated(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle character defeat"""
        # Recalculate round threshold when characters are defeated
        self._calculate_round_threshold()
        
        # If the current acting character was defeated, end their turn
        character_id = event.get_value("character_id")
        if character_id == self.current_turn_character:
            if self.current_phase == TurnPhase.TURN_EXECUTION:
                self.current_phase = TurnPhase.TURN_CLEANUP
        
        return event
```

### Step 4.3: Integration with Battle Context

Update the battle context to work with the turn system:

**File: `src/game/core/battle_manager.py`**

```python
from typing import Dict, Any, List, Optional
import logging

from .battle_context import BattleContext, BattlePhase
from .event_system import GameEvent, event_bus
from ..systems.turn_system import TurnSystem
from ..systems.skill_system import SkillSystem
from ..components.state_component import StateComponent
from ..components.stats_component import StatsComponent
from ..components.effects_component import EffectsComponent
from ..components.abilities_component import AbilitiesComponent

logger = logging.getLogger(__name__)

class BattleManager:
    """High-level battle management and coordination"""
    
    def __init__(self):
        self.battle_context: Optional[BattleContext] = None
        self.turn_system: Optional[TurnSystem] = None
        self.skill_system: Optional[SkillSystem] = None
        self.active_battle = False
        
        self._setup_event_listeners()
    
    def create_battle(self, team1_data: List[Dict[str, Any]], team2_data: List[Dict[str, Any]], 
                     battle_config: Dict[str, Any] = None) -> str:
        """Create a new battle"""
        self.battle_context = BattleContext()
        
        # Add team 1 characters
        for i, char_data in enumerate(team1_data):
            self._create_character(char_data, team=1, position=i)
        
        # Add team 2 characters  
        for i, char_data in enumerate(team2_data):
            self._create_character(char_data, team=2, position=i)
        
        # Apply battle configuration
        if battle_config:
            self._apply_battle_config(battle_config)
        
        # Initialize systems
        self.turn_system = TurnSystem(self.battle_context)
        self.skill_system = SkillSystem(self.battle_context)
        
        # Set battle phase
        self.battle_context.set_phase(BattlePhase.PRE_BATTLE)
        
        return self.battle_context.battle_id
    
    def start_battle(self) -> bool:
        """Start the battle"""
        if not self.battle_context or not self.turn_system:
            return False
        
        # Apply pre-battle effects (leader bonuses, synergies, etc.)
        self._apply_pre_battle_effects()
        
        # Set battle phase
        self.battle_context.set_phase(BattlePhase.BATTLE)
        self.active_battle = True
        
        # Start turn system
        self.turn_system.start_battle()
        
        logger.info(f"Battle {self.battle_context.battle_id} started")
        return True
    
    def end_battle(self, winner_team: Optional[int] = None, reason: str = "victory"):
        """End the current battle"""
        if not self.battle_context:
            return
        
        self.active_battle = False
        self.battle_context.set_phase(BattlePhase.POST_BATTLE)
        
        # Publish battle end event
        event = GameEvent(
            event_type="battle_ended",
            source=self,
            data={
                "battle_id": self.battle_context.battle_id,
                "winner_team": winner_team,
                "reason": reason,
                "rounds": self.battle_context.round_number,
                "turns": self.battle_context.turn_number
            }
        )
        event_bus.publish(event)
        
        # Cleanup
        self._cleanup_battle()
        
        logger.info(f"Battle {self.battle_context.battle_id} ended - Winner: Team {winner_team}, Reason: {reason}")
    
    def get_battle_state(self) -> Dict[str, Any]:
        """Get current battle state"""
        if not self.battle_context:
            return {}
        
        return {
            "battle_id": self.battle_context.battle_id,
            "phase": self.battle_context.phase.value,
            "round_number": self.battle_context.round_number,
            "turn_number": self.battle_context.turn_number,
            "active_character_id": self.battle_context.active_character_id,
            "team1_characters": list(self.battle_context.team_1_characters.keys()),
            "team2_characters": list(self.battle_context.team_2_characters.keys()),
            "active_battle": self.active_battle
        }
    
    def _create_character(self, char_data: Dict[str, Any], team: int, position: int):
        """Create a character with all components"""
        character_id = char_data.get("id", f"char_{team}_{position}")
        
        # Create components
        components = {
            "state": StateComponent(character_id),
            "stats": StatsComponent(character_id),
            "effects": EffectsComponent(character_id),
            "abilities": AbilitiesComponent(character_id)
        }
        
        # Initialize components
        for component in components.values():
            component.initialize(char_data)
        
        # Add components to character data
        char_data["id"] = character_id
        char_data["components"] = components
        
        # Add to battle context
        self.battle_context.add_character(team, char_data, position)
        
        logger.debug(f"Created character {character_id} for team {team} at position {position}")
    
    def _apply_battle_config(self, config: Dict[str, Any]):
        """Apply battle configuration"""
        # Set leaders
        team1_leader = config.get("team1_leader_position")
        if team1_leader is not None:
            leader_chars = [char for char in self.battle_context.team_1_characters.values() 
                          if char.get("position") == team1_leader]
            if leader_chars:
                self.battle_context.set_leader(1, leader_chars[0]["id"])
        
        team2_leader = config.get("team2_leader_position")
        if team2_leader is not None:
            leader_chars = [char for char in self.battle_context.team_2_characters.values()
                          if char.get("position") == team2_leader]
            if leader_chars:
                self.battle_context.set_leader(2, leader_chars[0]["id"])
        
        # Apply battlefield conditions
        battlefield_condition = config.get("battlefield_condition")
        if battlefield_condition:
            self.battle_context.apply_global_effect("battlefield_condition", battlefield_condition)
    
    def _apply_pre_battle_effects(self):
        """Apply leader bonuses, synergies, and other pre-battle effects"""
        # Apply leader bonuses
        if self.battle_context.team_1_leader_id:
            self._apply_leader_bonus(self.battle_context.team_1_leader_id)
        
        if self.battle_context.team_2_leader_id:
            self._apply_leader_bonus(self.battle_context.team_2_leader_id)
        
        # Apply synergy bonuses
        self._apply_synergy_bonuses()
    
    def _apply_leader_bonus(self, leader_id: str):
        """Apply +10% bonus to all base stats for the leader"""
        character = self.battle_context.get_character(leader_id)
        if character:
            stats_comp = character.get("components", {}).get("stats")
            if stats_comp:
                from ..components.stats_component import StatModifier, StatType, ModifierType
                
                # Apply 10% bonus to all base stats
                for stat_type in StatType:
                    modifier = StatModifier(
                        modifier_id=f"leader_bonus_{stat_type.value}",
                        stat_type=stat_type,
                        modifier_type=ModifierType.PERCENTAGE,
                        value=0.1,  # 10% bonus
                        source="leader_bonus",
                        layer=1  # Equipment layer
                    )
                    stats_comp.add_modifier(modifier)
                
                logger.debug(f"Applied leader bonus to {leader_id}")
    
    def _apply_synergy_bonuses(self):
        """Apply series synergy bonuses"""
        # Count characters by series for each team
        team1_series = {}
        team2_series = {}
        
        for char in self.battle_context.team_1_characters.values():
            series = char.get("series", "unknown")
            team1_series[series] = team1_series.get(series, 0) + 1
        
        for char in self.battle_context.team_2_characters.values():
            series = char.get("series", "unknown")
            team2_series[series] = team2_series.get(series, 0) + 1
        
        # Apply bonuses based on series counts
        # This would be expanded with the full synergy table
        pass
    
    def _cleanup_battle(self):
        """Clean up battle resources"""
        if self.battle_context:
            self.battle_context.cleanup()
        
        if self.turn_system:
            # Turn system cleanup if needed
            pass
        
        if self.skill_system:
            # Skill system cleanup if needed
            pass
        
        self.battle_context = None
        self.turn_system = None
        self.skill_system = None
    
    def _setup_event_listeners(self):
        """Set up event listeners for battle management"""
        event_bus.register_handler(
            "all_enemies_defeated",
            self._on_victory_condition
        )
        
        event_bus.register_handler(
            "battle_timeout",
            self._on_battle_timeout
        )
    
    def _on_victory_condition(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle victory conditions"""
        winner_team = event.get_value("winner_team")
        if winner_team and self.active_battle:
            self.end_battle(winner_team, "victory")
        
        return event
    
    def _on_battle_timeout(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle battle timeout"""
        if self.active_battle:
            # Determine winner by remaining HP
            team1_hp = sum(char.get("components", {}).get("state", type('', (), {"current_hp": 0})).current_hp 
                          for char in self.battle_context.team_1_characters.values())
            team2_hp = sum(char.get("components", {}).get("state", type('', (), {"current_hp": 0})).current_hp 
                          for char in self.battle_context.team_2_characters.values())
            
            if team1_hp > team2_hp:
                winner = 1
            elif team2_hp > team1_hp:
                winner = 2
            else:
                winner = None  # Draw
            
            self.end_battle(winner, "timeout")
        
        return event
```

### Next Steps

This completes Step 4 of the implementation, establishing the turn system with:

1. **State Component**: Complete character state tracking with action gauges and turn history
2. **Turn System**: Dynamic turn order with action gauge mechanics and round management
3. **Battle Manager**: High-level coordination of battle flow and systems integration

The next step (Step 5) will focus on implementing the combat system for damage calculation and resolution.

### Integration Notes

- Action gauges start randomized between 400-600 for balanced first turns
- Turn order is determined by overflow values and speed for tiebreaking
- Round tracking uses accumulated action gauge totals
- Sudden death mechanics automatically apply after round 20
- Complete event-driven architecture for extensibility

### Testing Recommendations

Create unit tests for:

- Action gauge ticking and overflow calculation
- Turn order determination with various speed values
- Round threshold calculation and sudden death
- Battle timeout and victory condition handling
- State component HP and action tracking
