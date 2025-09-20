"""
Calculation utilities for the Wanderer Game

Helper functions for affinity matching, stat calculations, and probability.
"""

from typing import List
from ..models import Team, Affinity


class AffinityCalculator:
    """Utility class for affinity-related calculations"""
    
    @staticmethod
    def calculate_multiplier(favored_matches: int, disfavored_matches: int) -> float:
        multiplier = 1.25**(favored_matches) * (0.6**(disfavored_matches))
        return max(0.1, min(5.0, multiplier))
    
    @staticmethod
    def count_team_matches(team: Team, affinities: List[Affinity]) -> int:
        """Count how many team members match any of the given affinities"""
        matches = 0
        for character in team.characters:
            for affinity in affinities:
                if character.matches_affinity(affinity):
                    matches += 1
        return matches


class StatCalculator:
    """Utility class for stat-related calculations"""
    
    @staticmethod
    def apply_star_bonus(base_stat: int, star_level: int) -> int:
        """
        Apply star bonus to a stat
        Formula: Stat * (1 + (Star Level - 1) * 0.10)
        """
        multiplier = 1 + (star_level - 1) * 0.10
        return int(base_stat * multiplier)
    
    @staticmethod
    def calculate_team_total(team: Team, stat_name: str) -> int:
        """Calculate total of a stat across all team members (with star bonuses)"""
        total = 0
        for character in team.characters:
            expedition_stats = character.get_expedition_stats()
            total += expedition_stats.get_stat(stat_name)
        return total


class ChanceCalculator:
    """Utility class for probability calculations"""
    
    @staticmethod
    def calculate_success_threshold(team_score: float, encounter_difficulty: int) -> float:
        """Calculate success threshold for encounter resolution"""
        if encounter_difficulty <= 0:
            return float('inf')
        return team_score / encounter_difficulty
    
    @staticmethod
    def get_outcome_probability(success_threshold: float, outcome: str) -> float:
        """Get probability for a specific outcome given success threshold"""
        # This would use the chance table logic
        # Simplified version for now
        if success_threshold < 0.5:
            probabilities = {"great_success": 0.0, "success": 0.05, "failure": 0.80, "mishap": 0.15}
        elif success_threshold < 1.0:
            probabilities = {"great_success": 0.05, "success": 0.35, "failure": 0.55, "mishap": 0.05}
        elif success_threshold < 1.5:
            probabilities = {"great_success": 0.15, "success": 0.70, "failure": 0.13, "mishap": 0.02}
        elif success_threshold < 2.0:
            probabilities = {"great_success": 0.35, "success": 0.60, "failure": 0.05, "mishap": 0.0}
        else:
            probabilities = {"great_success": 0.60, "success": 0.40, "failure": 0.0, "mishap": 0.0}
        
        return probabilities.get(outcome, 0.0)