"""
Victory System - Handles battle end conditions and outcome determination.

This system manages:
- Victory/defeat condition evaluation
- Battle outcome determination (win/loss/draw)
- Battle result calculation and statistics
- Experience and reward distribution
- Battle end event processing
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import time

from ..core.event_system import GameEvent, event_bus, EventPhase
from ..core.battle_context import BattleContext
from ..components.character import Character

logger = logging.getLogger(__name__)

class BattleOutcome(Enum):
    """Possible battle outcomes"""
    VICTORY = "victory"
    DEFEAT = "defeat"
    DRAW = "draw"
    SURRENDER = "surrender"
    TIMEOUT = "timeout"

class VictoryConditionType(Enum):
    """Types of victory conditions"""
    ELIMINATION = "elimination"      # All enemies defeated
    SURVIVAL = "survival"           # Survive for X turns/time
    OBJECTIVE = "objective"         # Complete specific objectives
    TIME_LIMIT = "time_limit"       # Battle duration limit
    CUSTOM = "custom"               # Custom condition function

@dataclass
class VictoryCondition:
    """Defines a specific victory condition"""
    condition_id: str
    name: str
    description: str
    condition_type: VictoryConditionType
    team_id: Optional[str] = None  # Which team this applies to (None = all teams)
    
    # Condition parameters
    target_count: int = 0           # For elimination/survival conditions
    time_limit: float = 0.0         # For time-based conditions (seconds)
    turn_limit: int = 0             # For turn-based conditions
    objectives: List[str] = field(default_factory=list)  # For objective conditions
    
    # Custom condition function
    check_function: Optional[Callable[[BattleContext], bool]] = None
    
    # Metadata
    priority: int = 100             # Higher priority conditions checked first
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BattleResult:
    """Contains the complete result of a battle"""
    battle_id: str
    outcome: BattleOutcome
    winning_teams: List[str]
    losing_teams: List[str]
    
    # Battle statistics
    duration_seconds: float
    total_turns: int
    total_actions: int
    
    # Condition information
    victory_condition: Optional[VictoryCondition] = None
    conditions_met: List[str] = field(default_factory=list)
    
    # Character statistics
    character_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Rewards and experience
    experience_gained: Dict[str, int] = field(default_factory=dict)
    rewards: Dict[str, List[str]] = field(default_factory=dict)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

class VictorySystem:
    """Main victory system for battle outcome determination"""
    
    def __init__(self, battle_context: BattleContext):
        self.battle_context = battle_context
        self.victory_conditions: List[VictoryCondition] = []
        self.battle_start_time: float = time.time()
        self.battle_result: Optional[BattleResult] = None
        self.is_battle_ended: bool = False
        
        # Battle tracking
        self.turn_count: int = 0
        self.action_count: int = 0
        self.character_action_counts: Dict[str, int] = {}
        self.character_damage_dealt: Dict[str, float] = {}
        self.character_damage_taken: Dict[str, float] = {}
        self.character_healing_done: Dict[str, float] = {}
        
        # Setup default victory conditions
        self._setup_default_conditions()
        
        logger.info("Initialized victory system for battle %s", battle_context.battle_id)
    
    def _setup_default_conditions(self):
        """Setup standard elimination victory conditions"""
        # Get all teams in the battle
        teams = set()
        for character in self.battle_context.characters.values():
            team_id = self.battle_context.character_teams.get(character.character_id)
            if team_id:
                teams.add(team_id)
        
        # Create elimination conditions for each team
        for team_id in teams:
            condition = VictoryCondition(
                condition_id=f"eliminate_enemies_{team_id}",
                name=f"Victory for {team_id}",
                description=f"All enemies of {team_id} are defeated",
                condition_type=VictoryConditionType.ELIMINATION,
                team_id=team_id,
                priority=100
            )
            self.add_victory_condition(condition)
        
        logger.debug("Added %d default elimination conditions", len(teams))
    
    def add_victory_condition(self, condition: VictoryCondition):
        """Add a victory condition to the battle"""
        self.victory_conditions.append(condition)
        # Sort by priority (higher priority first)
        self.victory_conditions.sort(key=lambda c: c.priority, reverse=True)
        
        logger.debug("Added victory condition: %s (priority: %d)", 
                    condition.name, condition.priority)
    
    def remove_victory_condition(self, condition_id: str) -> bool:
        """Remove a victory condition by ID"""
        original_count = len(self.victory_conditions)
        self.victory_conditions = [c for c in self.victory_conditions if c.condition_id != condition_id]
        
        removed = len(self.victory_conditions) < original_count
        if removed:
            logger.debug("Removed victory condition: %s", condition_id)
        
        return removed
    
    def check_victory_conditions(self) -> Optional[BattleResult]:
        """Check all victory conditions and return result if battle should end"""
        if self.is_battle_ended:
            return self.battle_result
        
        # Check each condition in priority order
        for condition in self.victory_conditions:
            if not condition.is_active:
                continue
            
            result = self._evaluate_condition(condition)
            if result:
                logger.info("Victory condition met: %s", condition.name)
                self.battle_result = result
                self.is_battle_ended = True
                
                # Publish battle end event
                self._publish_battle_end_event(result)
                
                return result
        
        return None
    
    def _evaluate_condition(self, condition: VictoryCondition) -> Optional[BattleResult]:
        """Evaluate a specific victory condition"""
        
        if condition.condition_type == VictoryConditionType.ELIMINATION:
            return self._check_elimination_condition(condition)
        elif condition.condition_type == VictoryConditionType.SURVIVAL:
            return self._check_survival_condition(condition)
        elif condition.condition_type == VictoryConditionType.TIME_LIMIT:
            return self._check_time_limit_condition(condition)
        elif condition.condition_type == VictoryConditionType.OBJECTIVE:
            return self._check_objective_condition(condition)
        elif condition.condition_type == VictoryConditionType.CUSTOM:
            return self._check_custom_condition(condition)
        
        return None
    
    def _check_elimination_condition(self, condition: VictoryCondition) -> Optional[BattleResult]:
        """Check if elimination victory condition is met"""
        if not condition.team_id:
            return None
        
        # Get all characters from other teams
        enemy_teams = set()
        for character in self.battle_context.characters.values():
            team_id = self.battle_context.character_teams.get(character.character_id)
            if team_id and team_id != condition.team_id:
                enemy_teams.add(team_id)
        
        # Check if all enemies are defeated
        all_enemies_defeated = True
        for team_id in enemy_teams:
            team_alive = False
            for character in self.battle_context.characters.values():
                if (self.battle_context.character_teams.get(character.character_id) == team_id and 
                    not character.is_defeated()):
                    team_alive = True
                    break
            
            if team_alive:
                all_enemies_defeated = False
                break
        
        if all_enemies_defeated:
            return self._create_battle_result(
                outcome=BattleOutcome.VICTORY,
                winning_teams=[condition.team_id],
                losing_teams=list(enemy_teams),
                victory_condition=condition
            )
        
        return None
    
    def _check_survival_condition(self, condition: VictoryCondition) -> Optional[BattleResult]:
        """Check if survival victory condition is met"""
        # Check turn-based survival
        if condition.turn_limit > 0 and self.turn_count >= condition.turn_limit:
            if condition.team_id:
                # Check if the team has survivors
                team_has_survivors = any(
                    not char.is_defeated() 
                    for char in self.battle_context.characters.values()
                    if self.battle_context.character_teams.get(char.character_id) == condition.team_id
                )
                
                if team_has_survivors:
                    return self._create_battle_result(
                        outcome=BattleOutcome.VICTORY,
                        winning_teams=[condition.team_id],
                        losing_teams=[],
                        victory_condition=condition
                    )
        
        return None
    
    def _check_time_limit_condition(self, condition: VictoryCondition) -> Optional[BattleResult]:
        """Check if time limit victory condition is met"""
        elapsed_time = time.time() - self.battle_start_time
        
        if condition.time_limit > 0 and elapsed_time >= condition.time_limit:
            # Time limit reached - determine outcome based on remaining forces
            teams_alive = {}
            for character in self.battle_context.characters.values():
                team_id = self.battle_context.character_teams.get(character.character_id)
                if team_id and not character.is_defeated():
                    teams_alive[team_id] = teams_alive.get(team_id, 0) + 1
            
            if len(teams_alive) == 0:
                # Everyone is defeated - draw
                return self._create_battle_result(
                    outcome=BattleOutcome.DRAW,
                    winning_teams=[],
                    losing_teams=[],
                    victory_condition=condition
                )
            elif len(teams_alive) == 1:
                # One team remains - victory
                winning_team = list(teams_alive.keys())[0]
                losing_teams = [t for t in self.battle_context.teams.keys() if t != winning_team]
                return self._create_battle_result(
                    outcome=BattleOutcome.VICTORY,
                    winning_teams=[winning_team],
                    losing_teams=losing_teams,
                    victory_condition=condition
                )
            else:
                # Multiple teams remain - draw
                return self._create_battle_result(
                    outcome=BattleOutcome.DRAW,
                    winning_teams=list(teams_alive.keys()),
                    losing_teams=[],
                    victory_condition=condition
                )
        
        return None
    
    def _check_objective_condition(self, condition: VictoryCondition) -> Optional[BattleResult]:
        """Check if objective victory condition is met"""
        # Objective conditions would be implemented based on specific battle objectives
        # For now, return None (not implemented)
        return None
    
    def _check_custom_condition(self, condition: VictoryCondition) -> Optional[BattleResult]:
        """Check if custom victory condition is met"""
        if condition.check_function:
            try:
                if condition.check_function(self.battle_context):
                    return self._create_battle_result(
                        outcome=BattleOutcome.VICTORY,
                        winning_teams=[condition.team_id] if condition.team_id else [],
                        losing_teams=[],
                        victory_condition=condition
                    )
            except Exception as e:
                logger.error("Error evaluating custom condition %s: %s", condition.condition_id, str(e))
        
        return None
    
    def _create_battle_result(self, outcome: BattleOutcome, winning_teams: List[str], 
                             losing_teams: List[str], victory_condition: Optional[VictoryCondition] = None) -> BattleResult:
        """Create a complete battle result"""
        
        # Calculate battle duration
        duration = time.time() - self.battle_start_time
        
        # Compile character statistics
        character_stats = {}
        for character in self.battle_context.characters.values():
            char_id = character.character_id
            character_stats[char_id] = {
                "final_hp": character.current_hp,
                "max_hp": character.get_stat("hp"),
                "is_defeated": character.is_defeated(),
                "actions_taken": self.character_action_counts.get(char_id, 0),
                "damage_dealt": self.character_damage_dealt.get(char_id, 0.0),
                "damage_taken": self.character_damage_taken.get(char_id, 0.0),
                "healing_done": self.character_healing_done.get(char_id, 0.0),
                "team": self.battle_context.character_teams.get(char_id)
            }
        
        # Calculate experience and rewards (basic implementation)
        experience_gained = {}
        rewards = {}
        
        for team_id in winning_teams:
            for character in self.battle_context.characters.values():
                if self.battle_context.character_teams.get(character.character_id) == team_id:
                    char_id = character.character_id
                    # Base experience for victory
                    base_exp = 100
                    # Bonus for participation
                    action_bonus = self.character_action_counts.get(char_id, 0) * 5
                    # Bonus for survival
                    survival_bonus = 50 if not character.is_defeated() else 0
                    
                    experience_gained[char_id] = base_exp + action_bonus + survival_bonus
                    rewards[char_id] = ["victory_reward"]
        
        result = BattleResult(
            battle_id=self.battle_context.battle_id,
            outcome=outcome,
            winning_teams=winning_teams,
            losing_teams=losing_teams,
            duration_seconds=duration,
            total_turns=self.turn_count,
            total_actions=self.action_count,
            victory_condition=victory_condition,
            conditions_met=[victory_condition.condition_id] if victory_condition else [],
            character_stats=character_stats,
            experience_gained=experience_gained,
            rewards=rewards
        )
        
        logger.info("Battle ended: %s (duration: %.1fs, turns: %d)", 
                   outcome.value, duration, self.turn_count)
        
        return result
    
    def force_end_battle(self, outcome: BattleOutcome, reason: str = "forced") -> BattleResult:
        """Force the battle to end with a specific outcome"""
        logger.info("Force ending battle with outcome: %s (reason: %s)", outcome.value, reason)
        
        if outcome == BattleOutcome.SURRENDER:
            # For surrender, determine who surrendered (implementation dependent)
            winning_teams = []
            losing_teams = list(self.battle_context.teams.keys())
        else:
            # For other forced outcomes, treat as draw
            winning_teams = []
            losing_teams = []
        
        result = self._create_battle_result(outcome, winning_teams, losing_teams)
        result.metadata["forced_end"] = True
        result.metadata["reason"] = reason
        
        self.battle_result = result
        self.is_battle_ended = True
        
        self._publish_battle_end_event(result)
        
        return result
    
    def update_statistics(self, event_type: str, data: Dict[str, Any]):
        """Update battle statistics based on events"""
        
        if event_type == "turn.completed":
            self.turn_count += 1
        
        elif event_type == "action.executed":
            self.action_count += 1
            actor_id = data.get("actor_id")
            if actor_id:
                self.character_action_counts[actor_id] = self.character_action_counts.get(actor_id, 0) + 1
        
        elif event_type == "damage.dealt":
            attacker_id = data.get("attacker_id")
            target_id = data.get("target_id") 
            damage_amount = data.get("damage_amount", 0.0)
            
            if attacker_id:
                self.character_damage_dealt[attacker_id] = self.character_damage_dealt.get(attacker_id, 0.0) + damage_amount
            if target_id:
                self.character_damage_taken[target_id] = self.character_damage_taken.get(target_id, 0.0) + damage_amount
        
        elif event_type == "healing.done":
            healer_id = data.get("healer_id")
            healing_amount = data.get("healing_amount", 0.0)
            
            if healer_id:
                self.character_healing_done[healer_id] = self.character_healing_done.get(healer_id, 0.0) + healing_amount
    
    def _publish_battle_end_event(self, result: BattleResult):
        """Publish battle end event"""
        event = GameEvent(
            event_type="battle.ended",
            source=self.battle_context.battle_id,
            data={
                "battle_result": result,
                "battle_id": self.battle_context.battle_id,
                "outcome": result.outcome.value,
                "winning_teams": result.winning_teams,
                "losing_teams": result.losing_teams
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.info("Published battle end event for %s", self.battle_context.battle_id)
    
    def get_battle_progress(self) -> Dict[str, Any]:
        """Get current battle progress and statistics"""
        elapsed_time = time.time() - self.battle_start_time
        
        # Count living characters per team
        team_counts = {}
        for character in self.battle_context.characters.values():
            team_id = self.battle_context.character_teams.get(character.character_id)
            if team_id:
                if team_id not in team_counts:
                    team_counts[team_id] = {"alive": 0, "total": 0}
                
                team_counts[team_id]["total"] += 1
                if not character.is_defeated():
                    team_counts[team_id]["alive"] += 1
        
        return {
            "battle_id": self.battle_context.battle_id,
            "is_ended": self.is_battle_ended,
            "elapsed_time": elapsed_time,
            "turn_count": self.turn_count,
            "action_count": self.action_count,
            "team_status": team_counts,
            "active_conditions": [c.condition_id for c in self.victory_conditions if c.is_active]
        }
