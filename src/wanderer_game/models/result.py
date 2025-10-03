"""
Result models for tracking expedition outcomes
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from .encounter import EncounterResult
from .loot import LootPool, FinalMultiplier


@dataclass
class ExpeditionResult:
    """
    Complete result of an expedition including log and final loot
    """
    expedition_id: str
    expedition_name: str
    team_character_ids: List[int]
    encounter_results: List[EncounterResult] = field(default_factory=list)
    loot_pool: LootPool = field(default_factory=LootPool)
    final_multiplier: FinalMultiplier = FinalMultiplier.STANDARD
    final_luck_score: int = 0
    
    # Summary statistics
    great_successes: int = 0
    successes: int = 0
    failures: int = 0
    mishaps: int = 0
    
    # Awakened mechanic fields
    awakened_count: int = 0
    awaken_multiplier: float = 1.0

    def add_encounter_result(self, result: EncounterResult):
        """Add an encounter result and update statistics"""
        self.encounter_results.append(result)
        
        # Update counters
        if result.outcome.value == "great_success":
            self.great_successes += 1
        elif result.outcome.value == "success":
            self.successes += 1
        elif result.outcome.value == "failure":
            self.failures += 1
        elif result.outcome.value == "mishap":
            self.mishaps += 1
    
    def generate_log(self) -> List[str]:
        """Generate a human-readable log of the expedition"""
        log_lines = []
        
        log_lines.append(f"=== Expedition: {self.expedition_name} ===")
        log_lines.append(f"Team dispatched with {len(self.team_character_ids)} characters")
        log_lines.append("")
        
        for i, result in enumerate(self.encounter_results, 1):
            outcome_text = result.outcome.value.replace("_", " ").title()
            log_lines.append(f"Encounter {i}: {result.encounter.name} - {outcome_text}")
            log_lines.append(f"  {result.description}")
            
            if result.loot_value_change > 0:
                log_lines.append(f"  (+{result.loot_value_change} Loot Value)")
            elif result.loot_value_change < 0:
                log_lines.append(f"  ({result.loot_value_change} Loot Value)")
            
            if result.modifier_applied:
                log_lines.append(f"  Applied modifier: {result.modifier_applied.type.value}")
            
            log_lines.append("")
        
        # Summary
        log_lines.append("=== Expedition Summary ===")
        log_lines.append(f"Great Successes: {self.great_successes}")
        log_lines.append(f"Successes: {self.successes}")
        log_lines.append(f"Failures: {self.failures}")
        log_lines.append(f"Mishaps: {self.mishaps}")
        log_lines.append("")
        log_lines.append(f"Final Luck Score: {self.final_luck_score}")
        log_lines.append(f"Final Outcome: {self.final_multiplier.value.title()}")
        log_lines.append(f"Final Loot Items: {len(self.loot_pool)}")
        
        return log_lines
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics as a dictionary"""
        return {
            'expedition_id': self.expedition_id,
            'expedition_name': self.expedition_name,
            'team_size': len(self.team_character_ids),
            'total_encounters': len(self.encounter_results),
            'great_successes': self.great_successes,
            'successes': self.successes,
            'failures': self.failures,
            'mishaps': self.mishaps,
            'final_luck_score': self.final_luck_score,
            'final_multiplier': self.final_multiplier.value,
            'final_loot_count': len(self.loot_pool),
            'total_loot_value': self.loot_pool.get_total_value()
        }