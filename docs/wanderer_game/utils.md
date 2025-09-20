# Utility & Calculation Logic

This document covers the helper classes and calculation logic used throughout the Wanderer Game expedition system.

## AffinityCalculator
- Static methods for affinity-related calculations.
- `calculate_multiplier(favored_matches, disfavored_matches)`: Computes the multiplicative affinity buff/nerf (1.2^favored, 0.6^disfavored, clamped).
- `count_team_matches(team, affinities)`: Counts how many team members match any of the given affinities.

## StatCalculator
- Static methods for stat calculations.
- `apply_star_bonus(base_stat, star_level)`: Applies star bonus to a stat (10% per star above 1).
- `calculate_team_total(team, stat_name)`: Sums a stat across all team members (with star bonuses).

## ChanceCalculator
- Static methods for probability and outcome calculations.
- `calculate_success_threshold(team_score, encounter_difficulty)`: Computes the success threshold for an encounter.
- `get_outcome_probability(success_threshold, outcome)`: Returns the probability of a specific outcome (great_success, success, failure, mishap).

## Usage
- These utilities are used by core systems (ExpeditionResolver, etc) to keep logic modular and testable.
- Extend or override for custom balancing or new mechanics.

---

See also: `systems.md` for core logic, `models.md` for data structures.
