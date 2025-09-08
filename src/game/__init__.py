"""
Anime Character Auto-Battler Game Module

This module implements a complete auto-battler system with:
- Event-driven architecture
- Component-based character system
- Dynamic turn order with action gauges
- Extensible skill and effect system
"""

__version__ = "0.1.0"
__author__ = "Geminya Team"

from .core.event_system import event_bus, GameEvent, EventPhase, EventPriority, EventBus, EventHandler
from .core.battle_context import BattleContext, BattlePhase, TurnPhase, BattleRules, BattleSnapshot

__all__ = [
    "event_bus",
    "GameEvent", 
    "EventPhase",
    "EventPriority",
    "EventBus",
    "EventHandler",
    "BattleContext",
    "BattlePhase",
    "TurnPhase",
    "BattleRules",
    "BattleSnapshot"
]
