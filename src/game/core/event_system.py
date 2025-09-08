from typing import Dict, List, Callable, Any, Optional
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
        
        logger.debug("Registered handler %s for event %s with priority %s", 
                    handler_id, event_type, priority)
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
        
        logger.debug("Registered global handler %s with priority %s", 
                    handler_id, priority)
        return handler_id
    
    def unregister_handler(self, event_type: str, handler_id: str) -> bool:
        """Unregister a specific event handler"""
        handlers = self.handlers.get(event_type, [])
        for i, handler in enumerate(handlers):
            if handler.handler_id == handler_id:
                del handlers[i]
                logger.debug("Unregistered handler %s for event %s", 
                           handler_id, event_type)
                return True
        return False
    
    def unregister_global_handler(self, handler_id: str) -> bool:
        """Unregister a global event handler"""
        for i, handler in enumerate(self.global_handlers):
            if handler.handler_id == handler_id:
                del self.global_handlers[i]
                logger.debug("Unregistered global handler %s", handler_id)
                return True
        return False
    
    def publish(self, event: GameEvent) -> GameEvent:
        """Publish an event and process all handlers"""
        logger.debug("Publishing event: %s", event.event_type)
        
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
                except (ValueError, TypeError, AttributeError) as e:
                    logger.error("Error in global handler %s: %s", 
                               handler.handler_id, e)
        
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
                except (ValueError, TypeError, AttributeError) as e:
                    logger.error("Error in handler %s: %s", 
                               handler.handler_id, e)
        
        num_handlers = len([h for h in handlers if h.can_handle(event)])
        logger.debug("Event %s processed by %d handlers", 
                    event.event_type, num_handlers)
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
