"""
Turn System

Manages action gauge, turn order, and turn processing for battle participants.
Coordinates with the battle context to execute actions in proper sequence.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import heapq
from ..core.event_system import GameEvent, event_bus
from ..core.battle_context import BattleContext
from ..components.character import Character

logger = logging.getLogger(__name__)

class TurnEventType(Enum):
    """Turn-related event types"""
    TURN_STARTED = "turn.started"
    TURN_PROCESSING = "turn.processing"
    TURN_COMPLETED = "turn.completed"
    TURN_SKIPPED = "turn.skipped"
    ACTION_GAUGE_UPDATED = "action_gauge.updated"
    TURN_ORDER_CHANGED = "turn_order.changed"

@dataclass
class TurnEvent:
    """Turn event data structure"""
    event_type: TurnEventType
    character_id: str
    turn_number: int
    action_gauge: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TurnQueueEntry:
    """Entry in the turn queue with priority"""
    character_id: str
    action_gauge: float
    priority: int = 0  # Higher priority goes first if gauge is tied
    turn_number: int = 0
    
    def __lt__(self, other):
        """Compare for heap priority (highest gauge first)"""
        # Negative because heapq is min-heap but we want max-heap behavior
        if self.action_gauge == other.action_gauge:
            return self.priority > other.priority  # Higher priority first
        return self.action_gauge > other.action_gauge

class TurnQueue:
    """
    Priority queue for managing turn order based on action gauge.
    Characters with higher action gauge get to act first.
    """
    
    def __init__(self):
        self._queue: List[TurnQueueEntry] = []
        self._character_entries: Dict[str, TurnQueueEntry] = {}
        
    def add_character(self, character_id: str, action_gauge: float, priority: int = 0) -> None:
        """Add or update a character in the turn queue"""
        # Remove existing entry if present
        if character_id in self._character_entries:
            self.remove_character(character_id)
        
        entry = TurnQueueEntry(character_id, action_gauge, priority)
        self._character_entries[character_id] = entry
        heapq.heappush(self._queue, entry)
    
    def remove_character(self, character_id: str) -> bool:
        """Remove a character from the turn queue"""
        if character_id not in self._character_entries:
            return False
        
        entry = self._character_entries[character_id]
        # Mark as removed (lazy deletion)
        entry.character_id = ""
        del self._character_entries[character_id]
        return True
    
    def peek_next(self) -> Optional[str]:
        """Peek at the next character without removing them"""
        self._clean_queue()
        if not self._queue:
            return None
        return self._queue[0].character_id
    
    def pop_next(self) -> Optional[TurnQueueEntry]:
        """Get and remove the next character to act"""
        self._clean_queue()
        if not self._queue:
            return None
        
        entry = heapq.heappop(self._queue)
        if entry.character_id in self._character_entries:
            del self._character_entries[entry.character_id]
        return entry
    
    def update_action_gauge(self, character_id: str, new_gauge: float) -> bool:
        """Update a character's action gauge"""
        if character_id not in self._character_entries:
            return False
        
        entry = self._character_entries[character_id]
        priority = entry.priority
        self.remove_character(character_id)
        self.add_character(character_id, new_gauge, priority)
        return True
    
    def get_action_gauge(self, character_id: str) -> Optional[float]:
        """Get a character's current action gauge"""
        entry = self._character_entries.get(character_id)
        return entry.action_gauge if entry else None
    
    def has_character(self, character_id: str) -> bool:
        """Check if character is in the queue"""
        return character_id in self._character_entries
    
    def is_empty(self) -> bool:
        """Check if the queue is empty"""
        self._clean_queue()
        return len(self._queue) == 0
    
    def size(self) -> int:
        """Get the number of characters in the queue"""
        self._clean_queue()
        return len(self._queue)
    
    def get_turn_order(self) -> List[str]:
        """Get the current turn order without modifying the queue"""
        self._clean_queue()
        return [entry.character_id for entry in sorted(self._queue, reverse=True)]
    
    def clear(self) -> None:
        """Clear the entire queue"""
        self._queue.clear()
        self._character_entries.clear()
    
    def _clean_queue(self) -> None:
        """Remove invalidated entries from the queue"""
        while self._queue and not self._queue[0].character_id:
            heapq.heappop(self._queue)

class TurnSystem:
    """
    Turn management system that handles action gauge progression,
    turn order calculation, and turn execution coordination.
    """
    
    def __init__(self, battle_context: BattleContext):
        self.battle_context = battle_context
        self.turn_queue = TurnQueue()
        self.current_turn = 0
        self.round_number = 0
        
        # Configuration
        self.action_gauge_increment = 10.0  # Base increment per tick
        self.max_action_gauge = 100.0      # Gauge needed to act
        self.speed_multiplier = 1.0        # Speed affects gauge increment
        
        # State tracking
        self.active_character_id: Optional[str] = None
        self.turn_in_progress = False
        
        # Callbacks
        self.action_handlers: Dict[str, Callable] = {}
        
        logger.info("Initialized turn system for battle %s", battle_context.battle_id)
    
    def initialize_participants(self) -> None:
        """Initialize all battle participants in the turn system"""
        self.turn_queue.clear()
        
        # Characters start with 0 action gauge, so don't add them to queue yet
        # They'll be added when they reach 100+ action gauge in tick_action_gauges()
        
        self._publish_turn_order_changed()
    
    def tick_action_gauges(self) -> None:
        """Increment action gauges for all participants"""
        updated_characters = []
        
        for character in self.battle_context.characters.values():
            if character.is_defeated():
                continue
            
            # Calculate increment based on speed
            speed = character.get_stat("spd")
            increment = self.action_gauge_increment * (speed / 100.0) * self.speed_multiplier
            
            # Update character's action gauge
            old_gauge = character.state.action_gauge
            character.state.action_gauge = min(
                character.state.action_gauge + increment,
                self.max_action_gauge * 2  # Allow overflow for multiple actions
            )
            
            # If character is not in queue and can act, add them
            if not self.turn_queue.has_character(character.character_id) and character.state.action_gauge >= 100.0:
                speed = character.get_stat("spd")
                priority = int(speed)
                self.turn_queue.add_character(character.character_id, character.state.action_gauge, priority)
                logger.debug("Added %s to turn queue (gauge: %.1f)", character.name, character.state.action_gauge)
            
            updated_characters.append({
                "character_id": character.character_id,
                "old_gauge": old_gauge,
                "new_gauge": character.state.action_gauge,
                "increment": increment
            })
        
        # Publish gauge update event
        if updated_characters:
            event_bus.publish(GameEvent(
                event_type=TurnEventType.ACTION_GAUGE_UPDATED.value,
                source=self.battle_context.battle_id,
                data={
                    "updates": updated_characters,
                    "round": self.round_number
                }
            ))
    
    def get_next_actor(self) -> Optional[str]:
        """Get the next character ID that should act"""
        while not self.turn_queue.is_empty():
            character_id = self.turn_queue.peek_next()
            if not character_id:
                break
            
            character = self.battle_context.get_character(character_id)
            if character and not character.is_defeated() and character.state.action_gauge >= 100.0:
                return character_id
            
            # Remove characters that can't act
            self.turn_queue.pop_next()
        
        return None
    
    def start_turn(self, character: Character) -> bool:
        """Start a turn for the specified character"""
        if self.turn_in_progress:
            logger.warning("Turn already in progress for %s", self.active_character_id)
            return False
        
        if character.is_defeated():
            logger.warning("Cannot start turn for defeated character %s", character.name)
            return False
        
        self.current_turn += 1
        self.active_character_id = character.character_id
        self.turn_in_progress = True
        
        # Remove from turn queue (they'll be re-added after action)
        self.turn_queue.remove_character(character.character_id)
        
        logger.info("Started turn %d for %s (gauge: %.1f)", 
                   self.current_turn, character.name, character.state.action_gauge)
        
        # Publish turn started event
        turn_event = TurnEvent(
            event_type=TurnEventType.TURN_STARTED,
            character_id=character.character_id,
            turn_number=self.current_turn,
            action_gauge=character.state.action_gauge
        )
        
        self._publish_turn_event(turn_event)
        
        return True
    
    def process_turn(self, character: Character, action_cost: Optional[float] = None) -> bool:
        """Process the current turn and consume action gauge"""
        if not self.turn_in_progress or self.active_character_id != character.character_id:
            logger.warning("No active turn for character %s", character.name)
            return False
        
        # Default action cost is full gauge
        if action_cost is None:
            action_cost = self.max_action_gauge
        
        # Consume action gauge
        character.state.action_gauge = max(0, character.state.action_gauge - action_cost)
        
        logger.debug("Processed turn for %s, consumed %.1f gauge (remaining: %.1f)", 
                    character.name, action_cost, character.state.action_gauge)
        
        # Publish processing event
        turn_event = TurnEvent(
            event_type=TurnEventType.TURN_PROCESSING,
            character_id=character.character_id,
            turn_number=self.current_turn,
            action_gauge=character.state.action_gauge,
            metadata={"action_cost": action_cost}
        )
        
        self._publish_turn_event(turn_event)
        
        return True
    
    def end_turn(self, character: Character) -> bool:
        """End the current turn"""
        if not self.turn_in_progress or self.active_character_id != character.character_id:
            logger.warning("No active turn for character %s", character.name)
            return False
        
        # Re-add to queue if they have remaining gauge and aren't defeated
        if not character.is_defeated() and character.state.action_gauge > 0:
            speed = character.get_stat("spd")
            priority = int(speed)
            self.turn_queue.add_character(character.character_id, character.state.action_gauge, priority)
        
        self.turn_in_progress = False
        self.active_character_id = None
        
        logger.debug("Ended turn for %s", character.name)
        
        # Publish turn completed event
        turn_event = TurnEvent(
            event_type=TurnEventType.TURN_COMPLETED,
            character_id=character.character_id,
            turn_number=self.current_turn,
            action_gauge=character.state.action_gauge
        )
        
        self._publish_turn_event(turn_event)
        
        return True
    
    def skip_turn(self, character: Character, reason: str = "skipped") -> bool:
        """Skip a character's turn"""
        if not self.turn_in_progress or self.active_character_id != character.character_id:
            return False
        
        logger.info("Skipped turn for %s: %s", character.name, reason)
        
        # Publish skip event
        turn_event = TurnEvent(
            event_type=TurnEventType.TURN_SKIPPED,
            character_id=character.character_id,
            turn_number=self.current_turn,
            action_gauge=character.state.action_gauge,
            metadata={"reason": reason}
        )
        
        self._publish_turn_event(turn_event)
        
        # End the turn normally
        return self.end_turn(character)
    
    def advance_round(self) -> int:
        """Advance to the next round and tick action gauges"""
        self.round_number += 1
        logger.info("Advanced to round %d", self.round_number)
        
        # Tick action gauges for all participants
        self.tick_action_gauges()
        
        # Process any characters who can now act
        self._process_ready_characters()
        
        return self.round_number
    
    def _process_ready_characters(self) -> None:
        """Check for characters who have reached action threshold"""
        while True:
            next_actor_id = self.get_next_actor()
            if not next_actor_id:
                break
                
            character = self.battle_context.get_character(next_actor_id)
            if character and character.state.action_gauge >= self.max_action_gauge:
                logger.debug("Character %s ready to act (gauge: %.1f)", 
                           character.name, character.state.action_gauge)
                # Character is ready but we don't auto-start their turn
                # The battle system will call start_turn when ready
                break
            else:
                break
    
    def get_turn_order(self) -> List[str]:
        """Get the current turn order"""
        return self.turn_queue.get_turn_order()
    
    def get_active_character(self) -> Optional[Character]:
        """Get the currently active character"""
        if self.active_character_id:
            return self.battle_context.get_character(self.active_character_id)
        return None
    
    def is_turn_available(self) -> bool:
        """Check if any character can take a turn"""
        return not self.turn_in_progress and self.get_next_actor() is not None
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get turn system status"""
        return {
            "current_turn": self.current_turn,
            "round_number": self.round_number,
            "turn_in_progress": self.turn_in_progress,
            "active_character": self.active_character_id,
            "queue_size": self.turn_queue.size(),
            "turn_order": self.get_turn_order()
        }
    
    def _publish_turn_event(self, turn_event: TurnEvent) -> None:
        """Publish a turn event"""
        event_bus.publish(GameEvent(
            event_type=turn_event.event_type.value,
            source=self.battle_context.battle_id,
            data={
                "character_id": turn_event.character_id,
                "turn_number": turn_event.turn_number,
                "action_gauge": turn_event.action_gauge,
                "metadata": turn_event.metadata
            }
        ))
    
    def _publish_turn_order_changed(self) -> None:
        """Publish turn order changed event"""
        event_bus.publish(GameEvent(
            event_type=TurnEventType.TURN_ORDER_CHANGED.value,
            source=self.battle_context.battle_id,
            data={
                "turn_order": self.get_turn_order(),
                "round": self.round_number
            }
        ))
