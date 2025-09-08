"""
Core game systems and infrastructure.

This module contains the foundational systems that power the game:
- Event system for game-wide communication
- Battle context for state management
- Base classes and interfaces
"""

from .event_system import (
    EventBus, 
    GameEvent, 
    EventHandler,
    EventPriority, 
    EventPhase,
    event_bus
)
from .battle_context import (
    BattleContext,
    BattlePhase,
    TurnPhase,
    BattleSnapshot,
    BattleRules
)

__all__ = [
    # Event system
    'EventBus',
    'GameEvent', 
    'EventHandler',
    'EventPriority',
    'EventPhase',
    'event_bus',
    
    # Battle context
    'BattleContext',
    'BattlePhase',
    'TurnPhase', 
    'BattleSnapshot',
    'BattleRules'
]
