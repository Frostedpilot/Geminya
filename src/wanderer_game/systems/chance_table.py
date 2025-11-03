"""
Chance Table system for determining encounter outcomes

Implements the probability tables from the design document for
converting success thresholds into encounter outcomes.
"""

from typing import Dict, Tuple
import random
from ..models import EncounterOutcome


class ChanceTable:
    """
    Handles probability calculations for encounter outcomes
    
    Based on the success threshold, determines the probability ranges
    for each possible outcome (Great Success, Success, Failure, Mishap)
    """
    
    # Chance table mapping success threshold ranges to outcome probabilities
    # Format: (threshold_min, threshold_max): {outcome: (min_roll, max_roll)}
    CHANCE_TABLE = {
        (0.0, 0.25): {
            EncounterOutcome.GREAT_SUCCESS: (1, 0),    
            EncounterOutcome.SUCCESS: (1, 5),          
            EncounterOutcome.FAILURE: (6, 70),        
            EncounterOutcome.MISHAP: (71, 100)         
        },
        (0.25, 0.5): {
            EncounterOutcome.GREAT_SUCCESS: (1, 0),    
            EncounterOutcome.SUCCESS: (1, 15),          
            EncounterOutcome.FAILURE: (16, 85),         
            EncounterOutcome.MISHAP: (86, 100)         
        },
        (0.5, 0.75): {
            EncounterOutcome.GREAT_SUCCESS: (1, 0),   
            EncounterOutcome.SUCCESS: (1, 25),      
            EncounterOutcome.FAILURE: (26, 90),       
            EncounterOutcome.MISHAP: (91, 100)        
        },
        (0.75, 1.0): {
            EncounterOutcome.GREAT_SUCCESS: (1, 3),    
            EncounterOutcome.SUCCESS: (4, 40),         
            EncounterOutcome.FAILURE: (41, 90),       
            EncounterOutcome.MISHAP: (91, 100)         
        },
        (1.0, 1.25): {
            EncounterOutcome.GREAT_SUCCESS: (1, 5),    
            EncounterOutcome.SUCCESS: (6, 65),         
            EncounterOutcome.FAILURE: (66, 95),        
            EncounterOutcome.MISHAP: (96, 100)         
        },
        (1.25, 1.5): {
            EncounterOutcome.GREAT_SUCCESS: (1, 10),    
            EncounterOutcome.SUCCESS: (11, 77),         
            EncounterOutcome.FAILURE: (78, 96),        
            EncounterOutcome.MISHAP: (97, 100)         
        },
        (1.5, 1.75): {
            EncounterOutcome.GREAT_SUCCESS: (1, 15),   
            EncounterOutcome.SUCCESS: (16, 87),        
            EncounterOutcome.FAILURE: (88, 98),        
            EncounterOutcome.MISHAP: (99, 100)         
        },
        (1.75, 2.0): {
            EncounterOutcome.GREAT_SUCCESS: (1, 25),   
            EncounterOutcome.SUCCESS: (26, 97),       
            EncounterOutcome.FAILURE: (98, 100),       
            EncounterOutcome.MISHAP: (101, 100)        
        },
        (2.0, float('inf')): {
            EncounterOutcome.GREAT_SUCCESS: (1, 35),  
            EncounterOutcome.SUCCESS: (36, 100),      
            EncounterOutcome.FAILURE: (101, 100),      
            EncounterOutcome.MISHAP: (101, 100)        
        }
    }
    
    @classmethod
    def get_outcome_probabilities(cls, success_threshold: float) -> Dict[EncounterOutcome, float]:
        """
        Get the probability percentages for each outcome given a success threshold
        
        Args:
            success_threshold: The calculated success threshold (team_score / encounter_difficulty)
            
        Returns:
            Dictionary mapping outcomes to their probability (0.0 to 1.0)
        """
        # Find the appropriate threshold range
        threshold_range = None
        for (min_thresh, max_thresh), probabilities in cls.CHANCE_TABLE.items():
            if min_thresh <= success_threshold < max_thresh:
                threshold_range = probabilities
                break
        
        if threshold_range is None:
            # Fallback for edge cases
            threshold_range = cls.CHANCE_TABLE[(0.0, 0.5)]
        
        # Convert roll ranges to probabilities
        outcome_probabilities = {}
        for outcome, (min_roll, max_roll) in threshold_range.items():
            if max_roll >= min_roll:
                probability = (max_roll - min_roll + 1) / 100.0
            else:
                probability = 0.0  # Impossible outcome
            outcome_probabilities[outcome] = probability
        
        return outcome_probabilities
    
    @classmethod
    def roll_outcome(cls, success_threshold: float) -> EncounterOutcome:
        """
        Roll for an encounter outcome based on success threshold
        
        Args:
            success_threshold: The calculated success threshold
            
        Returns:
            The randomly determined encounter outcome
        """
        # Find the appropriate threshold range
        threshold_range = None
        for (min_thresh, max_thresh), probabilities in cls.CHANCE_TABLE.items():
            if min_thresh <= success_threshold < max_thresh:
                threshold_range = probabilities
                break
        
        if threshold_range is None:
            # Fallback for edge cases - use lowest threshold
            threshold_range = cls.CHANCE_TABLE[(0.0, 0.5)]
        
        # Roll d100 (1-100)
        roll = random.randint(1, 100)
        
        # Determine outcome based on roll
        for outcome, (min_roll, max_roll) in threshold_range.items():
            if max_roll >= min_roll and min_roll <= roll <= max_roll:
                return outcome
        
        # Fallback - should not happen with properly defined tables
        return EncounterOutcome.FAILURE
    
    @classmethod
    def calculate_success_threshold(cls, team_score: float, encounter_difficulty: int) -> float:
        """
        Calculate the success threshold for a team against an encounter
        
        Args:
            team_score: The team's final score (stat sum * affinity multiplier)
            encounter_difficulty: The encounter's difficulty rating
            
        Returns:
            Success threshold (team_score / encounter_difficulty)
        """
        if encounter_difficulty <= 0:
            return float('inf')  # Automatic success
        
        return team_score / encounter_difficulty
    
    @classmethod
    def get_outcome_description(cls, outcome: EncounterOutcome, success_threshold: float) -> str:
        """
        Get a descriptive text for an encounter outcome
        
        Args:
            outcome: The encounter outcome
            success_threshold: The success threshold that led to this outcome
            
        Returns:
            Human-readable description of the outcome
        """
        descriptions = {
            EncounterOutcome.GREAT_SUCCESS: f"Exceptional performance! (Threshold: {success_threshold:.2f})",
            EncounterOutcome.SUCCESS: f"Successfully overcome! (Threshold: {success_threshold:.2f})",
            EncounterOutcome.FAILURE: f"The team struggled... (Threshold: {success_threshold:.2f})",
            EncounterOutcome.MISHAP: f"Things went horribly wrong! (Threshold: {success_threshold:.2f})"
        }
        
        return descriptions.get(outcome, f"Unknown outcome (Threshold: {success_threshold:.2f})")


class FinalMultiplierTable:
    """
    Handles the final luck-based multiplier calculation for expedition rewards
    """
    
    # Final multiplier table based on luck score
    # Format: (luck_min, luck_max): {multiplier: (min_roll, max_roll)}
    MULTIPLIER_TABLE = {
        (0, 100): {  # Unlucky
            "catastrophe": (1, 10),    # 10% (-75% loot)
            "setback": (11, 50),       # 40% (-25% loot)
            "standard": (51, 100),     # 50% (no change)
            "jackpot": (101, 100)      # 0% (+50% loot) - impossible
        },
        (100, 300): {  # Average
            "catastrophe": (1, 5),     # 5% (-75% loot)
            "setback": (6, 25),        # 20% (-25% loot)
            "standard": (26, 90),      # 65% (no change)
            "jackpot": (91, 100)       # 10% (+50% loot)
        },
        (300, 500): {  # Lucky
            "catastrophe": (1, 1),     # 1% (-75% loot)
            "setback": (2, 11),        # 10% (-25% loot)
            "standard": (12, 75),      # 64% (no change)
            "jackpot": (76, 100)       # 25% (+50% loot)
        },
        (500, float('inf')): {  # Extremely Lucky
            "catastrophe": (101, 100), # 0% - impossible
            "setback": (1, 5),         # 5% (-25% loot)
            "standard": (6, 55),       # 50% (no change)
            "jackpot": (56, 100)       # 45% (+50% loot)
        }
    }
    
    @classmethod
    def calculate_luck_score(cls, team_luck: int, great_successes: int, mishaps: int, expedition_difficulty: int = 0) -> int:
        """
        Calculate final luck score for multiplier determination, factoring in expedition difficulty.
        Harder expeditions require more luck for the best multipliers.
        
        Args:
            team_luck: Total LCK stat of all team members
            great_successes: Number of great successes achieved
            mishaps: Number of mishaps encountered
            expedition_difficulty: The difficulty of the expedition (higher = harder)
        Returns:
            Final luck score
        """
        # Difficulty penalty: for every 10 difficulty, reduce luck score by 5 (tunable)
        difficulty_penalty = expedition_difficulty // 40
        return max(0,team_luck + (great_successes * 20) - (mishaps * 40) - difficulty_penalty)
    
    @classmethod
    def roll_final_multiplier(cls, luck_score: int) -> Tuple[str, float]:
        """
        Roll for final multiplier based on luck score
        
        Args:
            luck_score: The calculated final luck score
            
        Returns:
            Tuple of (multiplier_name, multiplier_value)
        """
        # Find appropriate luck range
        luck_range = None
        for (min_luck, max_luck), multipliers in cls.MULTIPLIER_TABLE.items():
            if min_luck <= luck_score < max_luck:
                luck_range = multipliers
                break
        
        if luck_range is None:
            # Default to unlucky range
            luck_range = cls.MULTIPLIER_TABLE[(0, 100)]
        
        # Roll d100
        roll = random.randint(1, 100)
        
        # Determine multiplier
        multiplier_values = {
            "catastrophe": 0.75,  # -75%
            "setback": 0.9,      # -25%
            "standard": 1.0,      # No change
            "jackpot": 1.1        # +50%
        }
        
        for multiplier_name, (min_roll, max_roll) in luck_range.items():
            if max_roll >= min_roll and min_roll <= roll <= max_roll:
                return multiplier_name, multiplier_values[multiplier_name]
        
        # Fallback
        return "standard", 1.0