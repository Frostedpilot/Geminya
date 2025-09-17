"""Base effect interface for all status effects."""

from abc import ABC, abstractmethod

class BaseEffect(ABC):
    """Abstract base class for all status effects."""
    
    def __init__(self, source_character, target_character, duration, effect_data=None):
        """Initialize the effect.
        
        Args:
            source_character: Character who applied this effect
            target_character: Character affected by this effect
            duration: Number of turns this effect lasts
            effect_data: Dictionary containing effect-specific data
        """
        self.source_character = source_character
        self.target_character = target_character
        self.duration = duration
        self.effect_data = effect_data or {}
        self.effect_type = self.__class__.__name__
        self.is_active = True
    
    @abstractmethod
    def apply_effect(self, event_bus):
        """Apply the effect's main functionality.
        
        Args:
            event_bus: EventBus for publishing events
        """
        pass
    
    @abstractmethod
    def on_turn_start(self, event_bus):
        """Called when the affected character's turn starts.
        
        Args:
            event_bus: EventBus for publishing events
        """
        pass
    
    def on_turn_end(self, event_bus):
        """Called when the affected character's turn ends.
        
        Args:
            event_bus: EventBus for publishing events
        """
        # Default implementation: decrease duration
        self.duration -= 1
        if self.duration <= 0:
            self.remove_effect(event_bus)
    
    def remove_effect(self, event_bus):
        """Remove this effect from the character.
        
        Args:
            event_bus: EventBus for publishing events
        """
        self.is_active = False
        event_bus.publish("OnEffectExpired", {
            "effect": self,
            "character": self.target_character
        })
    
    def get_description(self):
        """Get a human-readable description of this effect."""
        return f"{self.effect_type} (Duration: {self.duration})"
    
    def serialize(self):
        """Serialize effect data for save/load."""
        return {
            "effect_type": self.effect_type,
            "duration": self.duration,
            "effect_data": self.effect_data,
            "is_active": self.is_active
        }