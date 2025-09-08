"""
Game Systems Module

This module contains the core battle and game logic systems that coordinate
character components and abilities into a functional battle experience.

Systems include:
- Turn System: Action gauge and turn order management ✅
- Combat System: Battle flow and action execution ✅
- Victory System: Battle end conditions and results
- AI System: Automated decision making for NPCs
"""

# Import implemented systems
from .turn_system import TurnSystem, TurnQueue, TurnEvent
from .combat_system import (
    CombatSystem, 
    CombatAction, 
    DamageInfo, 
    ActionResult,
    ActionType,
    DamageType,
    TargetType
)
from .victory_system import (
    VictorySystem,
    VictoryCondition,
    BattleResult,
    BattleOutcome,
    VictoryConditionType
)
from .ai_system import (
    AISystem,
    AIPersonality,
    AIDecision,
    AIBehavior,
    ThreatAssessment
)

__all__ = [
    # Turn System
    'TurnSystem', 
    'TurnQueue', 
    'TurnEvent',
    # Combat System
    'CombatSystem',
    'CombatAction',
    'DamageInfo', 
    'ActionResult',
    'ActionType',
    'DamageType',
    'TargetType',
    # Victory System
    'VictorySystem',
    'VictoryCondition',
    'BattleResult',
    'BattleOutcome',
    'VictoryConditionType',
    # AI System
    'AISystem',
    'AIPersonality',
    'AIDecision',
    'AIBehavior',
    'ThreatAssessment'
]

# from .ai_system import AISystem, AIBehavior, AIDecision
