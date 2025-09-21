# Equipment System Design and Implementation Guide

## Overview
This document describes the design and implementation plan for the Equipment System in the Wanderer Game. The system is designed to be simple, extensible, and user-friendly, providing meaningful progression and customization for players.

## System Summary
- **Each player can equip only 1 item at a time.**
- **Each equipment has 6 slots:**
  - 1 Main Slot (always present)
  - 5 Sub Slots (locked by default, can be unlocked)
- **Main Slot Effect:**
  - Determined randomly when the item is retrieved (one equipment per expedition completion).
- **Sub Slots:**
  - All sub slots are empty by default.
  - Each sub slot can be unlocked by sacrificing (using as cost) another equipment item.
  - Sub slots can be filled with effects (future expansion: gems, runes, etc.).
  - All sub slots can be removed at once (reset), but not individually.

## Player Flow
1. **Obtain Equipment:**
   - After each expedition, the player receives one equipment item with a random main effect.
2. **Equip Equipment:**
   - The player can equip one equipment at a time.
3. **Unlock Sub Slots:**
   - The player can unlock sub slots by sacrificing other equipment items.
   - Each unlock consumes one equipment and opens the next available sub slot.
4. **Remove Sub Slots:**
   - The player can reset (remove) all sub slots on an equipment at once. This action clears all sub slot effects and locks them again.

## Data Model
### Equipment
- `equipment_id`: Unique identifier
- `owner_id`: Player/user ID
- `main_effect`: Effect object (randomized on creation)
- `sub_slots`: List of 5 sub slot objects (each can be empty or filled)
- `unlocked_sub_slots`: Integer (0-5)
- `is_equipped`: Boolean
- `created_at`, `updated_at`: Timestamps

### SubSlot
- `slot_index`: 1-5
- `effect`: Effect object or None
- `is_unlocked`: Boolean

### Player
- `equipped_equipment_id`: Reference to currently equipped equipment
- `inventory`: List of owned equipment

## Implementation Plan
1. **Data Structures:**
   - Define Equipment and SubSlot classes/models.
   - Update Player/User model to reference equipped equipment.
2. **Database:**
   - Add tables/collections for equipment and sub slots.
   - Add fields to player/user table for equipped equipment.
3. **Backend Logic:**
   - Equipment creation (random main effect on expedition completion)
   - Equip/unequip logic (one at a time)
   - Unlock sub slot logic (consume equipment, open next slot)
   - Remove/reset all sub slots logic
4. **Commands/UI:**
   - View equipment inventory
   - Equip/unequip equipment
   - Unlock sub slot (choose equipment to sacrifice)
   - Remove all sub slots
   - Show equipment effects and slot status
5. **Testing:**
   - Unit and integration tests for all logic
   - Edge cases: max sub slots, removing sub slots, equipping/unequipping

## Future Expansion

- **Effect System Reuse:**
   - The encounter system already defines a flexible, extensible effect model using `ModifierType` and `EncounterModifier`.
   - Equipment effects (main and sub slots) can directly reuse this structure, storing a list of `EncounterModifier` objects as their effects.
   - The same effect application logic (e.g., `_apply_modifier`) can be used for both encounters and equipment, with minor adaptation for the target (player, team, or expedition).
   - Some effect types (e.g., loot pool changes) may not be relevant for equipment and should be filtered or ignored.
   - This approach ensures consistency, reduces code duplication, and makes balancing and future expansion easier.

---

*Next: Brainstorm and define the possible effects for equipment main and sub slots, using the shared effect model as a base.*

## Equipment Effect Types

Only the following effects are allowed for equipment:

- **stat_check_bonus** (Sub Slot):
   - Grants a bonus to one or more stats during stat checks.
   - Can affect a single stat or all stats.
   - Only available in sub slots.

- **final_stat_check_bonus** (Sub Slot):
   - Grants a bonus to one or more stats during stat checks, applied **after all multipliers** (affinity, series, etc.).
   - Can affect a single stat or all stats.
   - Only available in sub slots.

- **loot_pool_bonus** (Main Slot):
   - Increases the quality or quantity of loot gained from expeditions.
   - Only available in the main slot.

- **prevent_mishap_loot_loss** (Main Slot):
   - Prevents loss of loot when a mishap occurs during an expedition.
   - Only available in the main slot.

- **final_roll_bonus** (Main Slot):
   - Provides a bonus to the final outcome roll of an expedition.
   - Only available in the main slot.

- **encounter_count_add** (Main Slot):
   - Adds extra encounters to the expedition, increasing potential rewards and risk.
   - Only available in the main slot.

- **affinity_add** (Main Slot):
   - Adds a favored affinity for the duration of the expedition.
   - Only available in the main slot.

---

*Next: Brainstorm and define the possible effects for equipment main and sub slots.*
