# Core Systems: ExpeditionResolver, ExpeditionManager, LootGenerator

## ExpeditionResolver

**Purpose:**
- Resolves the full sequence of encounters for an expedition.
- Applies affinity multipliers, stat checks, encounter modifiers, and generates loot.

**Key Methods:**
- `resolve(active_expedition, team)`: Simulates all encounters, returns an `ExpeditionResult`.
- `_resolve_encounter(encounter, expedition, team)`: Handles logic for each encounter type (standard, gated, boon, hazard).
- `_calculate_affinity_multiplier(expedition, team)`: Computes the multiplicative buff/nerf for team affinity matches.
- `_apply_encounter_effects(...)`: Applies loot, modifiers, and mishap effects.
- `_apply_final_multiplier(...)`: Applies the final luck-based multiplier to currency loot.

**Data Flow:**
1. Selects encounters by type distribution (6 standard, 2 gated, 1 boon, 1 hazard).
2. For each encounter:
   - Resolves outcome (stat check, condition, or modifier).
   - Applies affinity and stat bonuses.
   - Generates loot and applies modifiers.
3. Applies final multiplier to currency rewards.

---

## ExpeditionManager

**Purpose:**
- Manages the lifecycle of expeditions: generation, dispatch, tracking, completion, and claiming.

**Key Methods:**
- `generate_available_expeditions(current_time)`: Rotates daily expeditions from templates.
- `dispatch_expedition(expedition_id, team, current_time)`: Assigns a team to an expedition slot.
- `get_active_expeditions()`, `get_available_slots()`: State queries.
- `complete_expedition(slot_id)`: Marks an expedition as completed and clears the slot.

**Features:**
- Supports up to 10 concurrent expedition slots.
- Tracks expedition status: available, active, completed, cancelled.
- Integrates with templates for dynamic affinity/encounter generation.

---

## LootGenerator

**Purpose:**
- Generates loot rewards using a two-stage system: type selection (gems, quartzs, items), then amount/item selection.

**Key Methods:**
- `generate_loot(loot_value, num_rolls)`: Main entry for loot generation.
- `_select_loot_type(difficulty)`: Weighted random selection of loot type.
- `_generate_gems_amount`, `_generate_quartzs_amount`: Amount generation using normal distribution.
- `_select_item(difficulty)`: Weighted item selection based on target value.

**Features:**
- Probability and amount scale with encounter difficulty and outcome.
- Supports simulation and info queries for balancing and analytics.

---

**See also:**
- `models.md` for data structures
- `registries.md` for content/data loading
