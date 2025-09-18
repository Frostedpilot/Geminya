"""
Helper utilities for the Wanderer Game

General purpose utility functions.
"""

import time
import random
from typing import List, Any, Optional


class TimeHelper:
    """Utility class for time-related operations"""
    
    @staticmethod
    def get_current_timestamp() -> float:
        """Get current timestamp in seconds"""
        return time.time()
    
    @staticmethod
    def hours_to_seconds(hours: int) -> float:
        """Convert hours to seconds"""
        return hours * 60 * 60
    
    @staticmethod
    def seconds_to_hours(seconds: float) -> float:
        """Convert seconds to hours"""
        return seconds / (60 * 60)
    
    @staticmethod
    def format_time_remaining(seconds: float) -> str:
        """Format time remaining in human-readable format"""
        if seconds <= 0:
            return "Complete"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"


class RandomHelper:
    """Utility class for random operations"""
    
    @staticmethod
    def roll_d100() -> int:
        """Roll a d100 (1-100)"""
        return random.randint(1, 100)
    
    @staticmethod
    def roll_dice(sides: int, count: int = 1) -> List[int]:
        """Roll multiple dice"""
        return [random.randint(1, sides) for _ in range(count)]
    
    @staticmethod
    def weighted_choice(items: List[tuple], weights: Optional[List[int]] = None) -> Any:
        """Make a weighted random choice from list of items"""
        if weights is None:
            weights = [1] * len(items)
        
        if len(items) != len(weights):
            raise ValueError("Items and weights must have same length")
        
        total_weight = sum(weights)
        roll = random.randint(1, total_weight)
        current_weight = 0
        
        for item, weight in zip(items, weights):
            current_weight += weight
            if roll <= current_weight:
                return item
        
        # Fallback
        return items[0] if items else None


class LogHelper:
    """Utility class for logging and formatting"""
    
    @staticmethod
    def format_expedition_log(encounter_results: List) -> str:
        """Format expedition results into a readable log"""
        log_lines = []
        
        for i, result in enumerate(encounter_results, 1):
            outcome = result.outcome.value.replace("_", " ").title()
            log_lines.append(f"Encounter {i}: {result.encounter.name} - {outcome}")
            if result.description:
                log_lines.append(f"  {result.description}")
            if result.loot_value_change != 0:
                sign = "+" if result.loot_value_change > 0 else ""
                log_lines.append(f"  {sign}{result.loot_value_change} loot value")
        
        return "\n".join(log_lines)
    
    @staticmethod
    def format_team_summary(team) -> str:
        """Format team composition summary"""
        lines = [f"Team ({len(team.characters)} members):"]
        for char in team.characters:
            lines.append(f"  - {char.name} ({char.archetype}, {char.series})")
        return "\n".join(lines)
    
    @staticmethod
    def format_loot_summary(loot_pool) -> str:
        """Format loot pool summary"""
        if not loot_pool.items:
            return "No loot obtained"
        
        lines = [f"Loot obtained ({len(loot_pool.items)} items):"]
        for item in loot_pool.items:
            lines.append(f"  - {item}")
        return "\n".join(lines)