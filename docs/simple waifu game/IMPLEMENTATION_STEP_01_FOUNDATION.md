# Implementation Guide - Step 1: Foundation Setup
## Anime Character Auto-Battler Implementation

### Overview
This document covers the foundational setup for implementing the anime character auto-battler system. This step focuses on establishing the core architecture, event system, and basic data structures that will support all subsequent features.

### Prerequisites
- Python 3.11+
- Discord.py library
- PostgreSQL database
- Basic understanding of event-driven architecture

### Project Structure Setup

First, create the core directory structure for the game module:

```
src/game/
├── __init__.py
├── core/                     # Core battle systems
│   ├── __init__.py
│   ├── battle_context.py     # Central state manager
│   ├── event_system.py       # Event bus and handlers
│   ├── effect_registry.py    # Global effect management
│   └── rule_engine.py        # Dynamic game rule management
├── components/               # Character component system
│   ├── __init__.py
│   ├── stats_component.py    # Dynamic stat calculations
│   ├── effects_component.py  # Active effects management
│   ├── abilities_component.py # Skill availability & cooldowns
│   └── state_component.py    # Character state tracking
├── systems/                  # Core game logic systems
│   ├── __init__.py
│   ├── turn_system.py        # Action gauge & turn processing
│   ├── combat_system.py      # Damage/healing resolution
│   ├── ai_system.py          # Decision making engine
│   └── victory_system.py     # Win condition evaluation
├── effects/                  # Effect implementation framework
│   ├── __init__.py
│   ├── base_effect.py        # Abstract effect interface
│   ├── modifiers/            # Stat/calculation modifiers
│   │   └── __init__.py
│   ├── triggers/             # Event-based triggers
│   │   └── __init__.py
│   ├── rules/                # Game rule modifications
│   │   └── __init__.py
│   └── complex/              # Multi-system effects
│       └── __init__.py
├── data/                     # Data-driven content
│   ├── __init__.py
│   ├── skill_definitions/    # JSON skill configurations
│   ├── effect_library/       # Reusable effect templates
│   └── expansion_hooks/      # Plugin registration points
└── plugins/                  # Hot-loadable extensions
    ├── __init__.py
    ├── rule_mods/            # Game rule modifications
    │   └── __init__.py
    └── ai_behaviors/         # Custom AI strategies
        └── __init__.py
```

### Step 1.1: Core Event System Implementation

Create the central event bus that will handle all game interactions:

**File: `src/game/core/event_system.py`**

```python
from typing import Dict, List, Callable, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """Event handler priority levels"""
    HIGHEST = 1000
    HIGH = 750
    NORMAL = 500
    LOW = 250
    LOWEST = 0

class EventPhase(Enum):
    """Event processing phases"""
    PRE_PROCESS = "pre_process"
    PROCESS = "process"
    POST_PROCESS = "post_process"
    ON_EVENT = "on_event"
    CONTINUOUS = "continuous"
    CONDITIONAL = "conditional"

@dataclass
class GameEvent:
    """Base class for all game events"""
    event_type: str
    source: Optional[Any] = None
    target: Optional[Any] = None
    data: Dict[str, Any] = field(default_factory=dict)
    phase: EventPhase = EventPhase.PROCESS
    cancellable: bool = True
    cancelled: bool = False
    modified_data: Dict[str, Any] = field(default_factory=dict)
    
    def cancel(self):
        """Cancel this event if it's cancellable"""
        if self.cancellable:
            self.cancelled = True
    
    def modify(self, key: str, value: Any):
        """Modify event data"""
        self.modified_data[key] = value
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get value from modified data first, then original data"""
        return self.modified_data.get(key, self.data.get(key, default))

@dataclass
class EventHandler:
    """Event handler registration"""
    callback: Callable[[GameEvent], Optional[GameEvent]]
    priority: int
    conditions: Dict[str, Any] = field(default_factory=dict)
    handler_id: str = ""
    
    def can_handle(self, event: GameEvent) -> bool:
        """Check if this handler can process the given event"""
        for condition_key, condition_value in self.conditions.items():
            if hasattr(event, condition_key):
                event_value = getattr(event, condition_key)
                if event_value != condition_value:
                    return False
            elif condition_key in event.data:
                if event.data[condition_key] != condition_value:
                    return False
            else:
                return False
        return True

class EventBus:
    """Central event bus for the game system"""
    
    def __init__(self):
        self.handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self.global_handlers: List[EventHandler] = []
        self.event_history: List[GameEvent] = []
        self.max_history = 1000
        self._handler_counter = 0
    
    def register_handler(
        self,
        event_type: str,
        callback: Callable[[GameEvent], Optional[GameEvent]],
        priority: int = EventPriority.NORMAL.value,
        conditions: Optional[Dict[str, Any]] = None,
        handler_id: Optional[str] = None
    ) -> str:
        """Register an event handler"""
        if handler_id is None:
            handler_id = f"handler_{self._handler_counter}"
            self._handler_counter += 1
        
        handler = EventHandler(
            callback=callback,
            priority=priority,
            conditions=conditions or {},
            handler_id=handler_id
        )
        
        self.handlers[event_type].append(handler)
        # Sort by priority (highest first)
        self.handlers[event_type].sort(key=lambda h: h.priority, reverse=True)
        
        logger.debug(f"Registered handler {handler_id} for event {event_type} with priority {priority}")
        return handler_id
    
    def register_global_handler(
        self,
        callback: Callable[[GameEvent], Optional[GameEvent]],
        priority: int = EventPriority.NORMAL.value,
        conditions: Optional[Dict[str, Any]] = None,
        handler_id: Optional[str] = None
    ) -> str:
        """Register a global event handler that receives all events"""
        if handler_id is None:
            handler_id = f"global_handler_{self._handler_counter}"
            self._handler_counter += 1
        
        handler = EventHandler(
            callback=callback,
            priority=priority,
            conditions=conditions or {},
            handler_id=handler_id
        )
        
        self.global_handlers.append(handler)
        self.global_handlers.sort(key=lambda h: h.priority, reverse=True)
        
        logger.debug(f"Registered global handler {handler_id} with priority {priority}")
        return handler_id
    
    def unregister_handler(self, event_type: str, handler_id: str) -> bool:
        """Unregister a specific event handler"""
        handlers = self.handlers.get(event_type, [])
        for i, handler in enumerate(handlers):
            if handler.handler_id == handler_id:
                del handlers[i]
                logger.debug(f"Unregistered handler {handler_id} for event {event_type}")
                return True
        return False
    
    def unregister_global_handler(self, handler_id: str) -> bool:
        """Unregister a global event handler"""
        for i, handler in enumerate(self.global_handlers):
            if handler.handler_id == handler_id:
                del self.global_handlers[i]
                logger.debug(f"Unregistered global handler {handler_id}")
                return True
        return False
    
    def publish(self, event: GameEvent) -> GameEvent:
        """Publish an event and process all handlers"""
        logger.debug(f"Publishing event: {event.event_type}")
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Process global handlers first
        for handler in self.global_handlers:
            if event.cancelled:
                break
            if handler.can_handle(event):
                try:
                    result = handler.callback(event)
                    if result is not None:
                        event = result
                except Exception as e:
                    logger.error(f"Error in global handler {handler.handler_id}: {e}")
        
        # Process specific event handlers
        handlers = self.handlers.get(event.event_type, [])
        for handler in handlers:
            if event.cancelled:
                break
            if handler.can_handle(event):
                try:
                    result = handler.callback(event)
                    if result is not None:
                        event = result
                except Exception as e:
                    logger.error(f"Error in handler {handler.handler_id}: {e}")
        
        logger.debug(f"Event {event.event_type} processed by {len([h for h in handlers if h.can_handle(event)])} handlers")
        return event
    
    def clear_handlers(self):
        """Clear all registered handlers"""
        self.handlers.clear()
        self.global_handlers.clear()
        logger.debug("Cleared all event handlers")
    
    def get_recent_events(self, count: int = 10) -> List[GameEvent]:
        """Get recent events from history"""
        return self.event_history[-count:]

# Global event bus instance
event_bus = EventBus()
```

### Step 1.2: Battle Context Implementation

Create the central battle state manager:

**File: `src/game/core/battle_context.py`**

```python
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from copy import deepcopy
import uuid
from enum import Enum

from .event_system import GameEvent, event_bus, EventPhase

class BattlePhase(Enum):
    """Current phase of the battle"""
    SETUP = "setup"
    PRE_BATTLE = "pre_battle"
    BATTLE = "battle"
    POST_BATTLE = "post_battle"
    COMPLETED = "completed"

@dataclass
class BattleSnapshot:
    """Immutable snapshot of battle state"""
    battle_id: str
    phase: BattlePhase
    round_number: int
    turn_number: int
    active_character_id: Optional[str]
    team_1_characters: Dict[str, Any]
    team_2_characters: Dict[str, Any]
    global_effects: Dict[str, Any]
    battlefield_conditions: Dict[str, Any]
    action_history: List[Dict[str, Any]]
    timestamp: float = field(default_factory=lambda: __import__('time').time())

class BattleContext:
    """Central battle state manager"""
    
    def __init__(self, battle_id: Optional[str] = None):
        self.battle_id = battle_id or str(uuid.uuid4())
        self.phase = BattlePhase.SETUP
        self.round_number = 0
        self.turn_number = 0
        self.active_character_id: Optional[str] = None
        
        # Team data
        self.team_1_characters: Dict[str, Any] = {}
        self.team_2_characters: Dict[str, Any] = {}
        self.team_1_leader_id: Optional[str] = None
        self.team_2_leader_id: Optional[str] = None
        
        # Global state
        self.global_effects: Dict[str, Any] = {}
        self.battlefield_conditions: Dict[str, Any] = {}
        self.synergy_bonuses: Dict[str, Any] = {}
        
        # History and tracking
        self.action_history: List[Dict[str, Any]] = []
        self.state_snapshots: List[BattleSnapshot] = []
        self.max_snapshots = 50
        
        # Battle parameters
        self.max_rounds = 30
        self.round_equivalent_threshold = 0
        self.sudden_death_round = 20
        
        # Event tracking
        self.event_listeners: List[str] = []
    
    def create_snapshot(self) -> BattleSnapshot:
        """Create an immutable snapshot of current state"""
        return BattleSnapshot(
            battle_id=self.battle_id,
            phase=self.phase,
            round_number=self.round_number,
            turn_number=self.turn_number,
            active_character_id=self.active_character_id,
            team_1_characters=deepcopy(self.team_1_characters),
            team_2_characters=deepcopy(self.team_2_characters),
            global_effects=deepcopy(self.global_effects),
            battlefield_conditions=deepcopy(self.battlefield_conditions),
            action_history=deepcopy(self.action_history)
        )
    
    def save_snapshot(self):
        """Save current state as a snapshot"""
        snapshot = self.create_snapshot()
        self.state_snapshots.append(snapshot)
        
        if len(self.state_snapshots) > self.max_snapshots:
            self.state_snapshots.pop(0)
        
        # Publish snapshot event
        event = GameEvent(
            event_type="battle_snapshot_created",
            source=self,
            data={"snapshot": snapshot}
        )
        event_bus.publish(event)
    
    def restore_snapshot(self, snapshot: BattleSnapshot):
        """Restore state from a snapshot"""
        self.phase = snapshot.phase
        self.round_number = snapshot.round_number
        self.turn_number = snapshot.turn_number
        self.active_character_id = snapshot.active_character_id
        self.team_1_characters = deepcopy(snapshot.team_1_characters)
        self.team_2_characters = deepcopy(snapshot.team_2_characters)
        self.global_effects = deepcopy(snapshot.global_effects)
        self.battlefield_conditions = deepcopy(snapshot.battlefield_conditions)
        self.action_history = deepcopy(snapshot.action_history)
        
        # Publish restore event
        event = GameEvent(
            event_type="battle_snapshot_restored",
            source=self,
            data={"snapshot": snapshot}
        )
        event_bus.publish(event)
    
    def set_phase(self, new_phase: BattlePhase):
        """Change battle phase with event notification"""
        old_phase = self.phase
        self.phase = new_phase
        
        event = GameEvent(
            event_type="battle_phase_changed",
            source=self,
            data={
                "old_phase": old_phase,
                "new_phase": new_phase,
                "battle_id": self.battle_id
            }
        )
        event_bus.publish(event)
    
    def add_character(self, team: int, character_data: Dict[str, Any], position: int):
        """Add a character to a team"""
        character_id = character_data.get("id", str(uuid.uuid4()))
        
        if team == 1:
            self.team_1_characters[character_id] = {
                **character_data,
                "position": position,
                "team": 1,
                "action_gauge": 0,
                "active_effects": {},
                "cooldowns": {}
            }
        elif team == 2:
            self.team_2_characters[character_id] = {
                **character_data,
                "position": position,
                "team": 2,
                "action_gauge": 0,
                "active_effects": {},
                "cooldowns": {}
            }
        
        event = GameEvent(
            event_type="character_added",
            source=self,
            data={
                "character_id": character_id,
                "team": team,
                "position": position,
                "character_data": character_data
            }
        )
        event_bus.publish(event)
    
    def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get character data by ID"""
        if character_id in self.team_1_characters:
            return self.team_1_characters[character_id]
        elif character_id in self.team_2_characters:
            return self.team_2_characters[character_id]
        return None
    
    def get_all_characters(self) -> List[Dict[str, Any]]:
        """Get all characters from both teams"""
        all_chars = []
        all_chars.extend(self.team_1_characters.values())
        all_chars.extend(self.team_2_characters.values())
        return all_chars
    
    def get_living_characters(self, team: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all living characters, optionally filtered by team"""
        all_chars = self.get_all_characters()
        living = [char for char in all_chars if char.get("current_hp", 0) > 0]
        
        if team is not None:
            living = [char for char in living if char.get("team") == team]
        
        return living
    
    def set_leader(self, team: int, character_id: str):
        """Set team leader"""
        if team == 1 and character_id in self.team_1_characters:
            self.team_1_leader_id = character_id
        elif team == 2 and character_id in self.team_2_characters:
            self.team_2_leader_id = character_id
        
        event = GameEvent(
            event_type="leader_set",
            source=self,
            data={
                "team": team,
                "character_id": character_id
            }
        )
        event_bus.publish(event)
    
    def apply_global_effect(self, effect_id: str, effect_data: Dict[str, Any]):
        """Apply a global effect to the battle"""
        self.global_effects[effect_id] = effect_data
        
        event = GameEvent(
            event_type="global_effect_applied",
            source=self,
            data={
                "effect_id": effect_id,
                "effect_data": effect_data
            }
        )
        event_bus.publish(event)
    
    def remove_global_effect(self, effect_id: str):
        """Remove a global effect"""
        if effect_id in self.global_effects:
            effect_data = self.global_effects.pop(effect_id)
            
            event = GameEvent(
                event_type="global_effect_removed",
                source=self,
                data={
                    "effect_id": effect_id,
                    "effect_data": effect_data
                }
            )
            event_bus.publish(event)
    
    def log_action(self, action_data: Dict[str, Any]):
        """Log an action to the battle history"""
        action_entry = {
            "turn": self.turn_number,
            "round": self.round_number,
            "timestamp": __import__('time').time(),
            **action_data
        }
        self.action_history.append(action_entry)
        
        event = GameEvent(
            event_type="action_logged",
            source=self,
            data={"action": action_entry}
        )
        event_bus.publish(event)
    
    def cleanup(self):
        """Clean up battle context and unregister event listeners"""
        for listener_id in self.event_listeners:
            event_bus.unregister_global_handler(listener_id)
        self.event_listeners.clear()
        
        event = GameEvent(
            event_type="battle_cleanup",
            source=self,
            data={"battle_id": self.battle_id}
        )
        event_bus.publish(event)
```

### Next Steps

This completes Step 1 of the implementation, establishing the foundation with:

1. **Event System**: A robust, priority-based event bus for handling all game interactions
2. **Battle Context**: Central state management with snapshotting and rollback capabilities
3. **Core Data Structures**: Battle phases, events, and character management

The next step (Step 2) will focus on implementing the character component system and basic stat calculations.

### Integration Notes

- All systems should use the event bus for communication
- Battle context provides centralized state management
- Events are immutable and can be modified through the event system
- The foundation supports the extensible architecture described in the technical design

### Testing Recommendations

Create unit tests for:
- Event registration and publishing
- Event handler priority ordering
- Battle context state management
- Snapshot creation and restoration
- Character addition and management

This foundation will support all subsequent game systems and features.
