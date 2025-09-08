"""
Common game event types and factory functions.

This module defines standard events used throughout the game system.
"""

from typing import Any, Dict, Optional
from .event_system import GameEvent, EventPhase

# Battle Events
def create_battle_start_event(battle_id: str, participants: Dict[str, Any]) -> GameEvent:
    """Create a battle start event"""
    return GameEvent(
        event_type="battle.start",
        data={
            "battle_id": battle_id,
            "participants": participants
        },
        phase=EventPhase.PRE_PROCESS
    )

def create_battle_end_event(battle_id: str, winners: list, reason: str) -> GameEvent:
    """Create a battle end event"""
    return GameEvent(
        event_type="battle.end",
        data={
            "battle_id": battle_id,
            "winners": winners,
            "reason": reason
        },
        phase=EventPhase.POST_PROCESS
    )

def create_turn_start_event(battle_id: str, turn_number: int, character_id: str) -> GameEvent:
    """Create a turn start event"""
    return GameEvent(
        event_type="turn.start",
        data={
            "battle_id": battle_id,
            "turn_number": turn_number,
            "character_id": character_id
        },
        phase=EventPhase.PRE_PROCESS
    )

def create_turn_end_event(battle_id: str, turn_number: int, character_id: str) -> GameEvent:
    """Create a turn end event"""
    return GameEvent(
        event_type="turn.end",
        data={
            "battle_id": battle_id,
            "turn_number": turn_number,
            "character_id": character_id
        },
        phase=EventPhase.POST_PROCESS
    )

# Character Events
def create_character_join_event(character_id: str, team_id: str, battle_id: str) -> GameEvent:
    """Create a character join battle event"""
    return GameEvent(
        event_type="character.join",
        data={
            "character_id": character_id,
            "team_id": team_id,
            "battle_id": battle_id
        },
        phase=EventPhase.PROCESS
    )

def create_character_leave_event(character_id: str, battle_id: str, reason: str) -> GameEvent:
    """Create a character leave battle event"""
    return GameEvent(
        event_type="character.leave",
        data={
            "character_id": character_id,
            "battle_id": battle_id,
            "reason": reason
        },
        phase=EventPhase.PROCESS
    )

def create_character_death_event(character_id: str, killer_id: Optional[str] = None) -> GameEvent:
    """Create a character death event"""
    return GameEvent(
        event_type="character.death",
        data={
            "character_id": character_id,
            "killer_id": killer_id
        },
        phase=EventPhase.PROCESS
    )

# Action Events
def create_skill_use_event(
    caster_id: str, 
    skill_id: str, 
    targets: list, 
    battle_id: str
) -> GameEvent:
    """Create a skill use event"""
    return GameEvent(
        event_type="skill.use",
        source=caster_id,
        target=targets[0] if targets else None,
        data={
            "caster_id": caster_id,
            "skill_id": skill_id,
            "targets": targets,
            "battle_id": battle_id
        },
        phase=EventPhase.PROCESS
    )

def create_damage_event(
    source_id: str,
    target_id: str,
    damage_amount: float,
    damage_type: str,
    battle_id: str
) -> GameEvent:
    """Create a damage event"""
    return GameEvent(
        event_type="damage.dealt",
        source=source_id,
        target=target_id,
        data={
            "source_id": source_id,
            "target_id": target_id,
            "damage_amount": damage_amount,
            "damage_type": damage_type,
            "battle_id": battle_id
        },
        phase=EventPhase.PROCESS
    )

def create_healing_event(
    source_id: str,
    target_id: str,
    heal_amount: float,
    battle_id: str
) -> GameEvent:
    """Create a healing event"""
    return GameEvent(
        event_type="healing.dealt",
        source=source_id,
        target=target_id,
        data={
            "source_id": source_id,
            "target_id": target_id,
            "heal_amount": heal_amount,
            "battle_id": battle_id
        },
        phase=EventPhase.PROCESS
    )

# Status Effect Events
def create_status_applied_event(
    target_id: str,
    effect_id: str,
    effect_data: Dict[str, Any],
    source_id: Optional[str] = None
) -> GameEvent:
    """Create a status effect applied event"""
    return GameEvent(
        event_type="status.applied",
        source=source_id,
        target=target_id,
        data={
            "target_id": target_id,
            "effect_id": effect_id,
            "effect_data": effect_data,
            "source_id": source_id
        },
        phase=EventPhase.PROCESS
    )

def create_status_removed_event(
    target_id: str,
    effect_id: str,
    reason: str = "expired"
) -> GameEvent:
    """Create a status effect removed event"""
    return GameEvent(
        event_type="status.removed",
        target=target_id,
        data={
            "target_id": target_id,
            "effect_id": effect_id,
            "reason": reason
        },
        phase=EventPhase.PROCESS
    )

# Stat Events
def create_stat_changed_event(
    character_id: str,
    stat_name: str,
    old_value: float,
    new_value: float,
    change_source: str
) -> GameEvent:
    """Create a stat changed event"""
    return GameEvent(
        event_type="stat.changed",
        target=character_id,
        data={
            "character_id": character_id,
            "stat_name": stat_name,
            "old_value": old_value,
            "new_value": new_value,
            "change_source": change_source
        },
        phase=EventPhase.PROCESS
    )

# System Events
def create_system_error_event(error_type: str, error_message: str, context: Dict[str, Any]) -> GameEvent:
    """Create a system error event"""
    return GameEvent(
        event_type="system.error",
        data={
            "error_type": error_type,
            "error_message": error_message,
            "context": context
        },
        phase=EventPhase.PROCESS,
        cancellable=False
    )

def create_debug_event(debug_type: str, debug_data: Dict[str, Any]) -> GameEvent:
    """Create a debug event"""
    return GameEvent(
        event_type="system.debug",
        data={
            "debug_type": debug_type,
            "debug_data": debug_data
        },
        phase=EventPhase.PROCESS,
        cancellable=False
    )
