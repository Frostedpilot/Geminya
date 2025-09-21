# Equipment System Design and Implementation Guide

## Overview
This document describes the design and implementation plan for the Equipment System in the Wanderer Game. The system is designed to be simple, extensible, and user-friendly, providing meaningful progression and customization for players.

## System Summary
- **Each player can equip only 1 equipment item per expedition.**
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
   - The player can equip one equipment item for each expedition. Equipment selection is made when starting an expedition, and does not affect other ongoing or future expeditions.
## Data Model

### Equipment
- `equipment_id`: Unique identifier
- `owner_id`: Player/user ID
- `main_effect`: Effect object (randomized on creation)
- `sub_slots`: List of 5 sub slot objects (each can be empty or filled)
- `unlocked_sub_slots`: Integer (0-5)
- `is_equipped`: Boolean (deprecated; see Player/Expedition model)
- `created_at`, `updated_at`: Timestamps

### SubSlot
- `slot_index`: 1-5
- `effect`: Effect object or None
- `is_unlocked`: Boolean

### Player
- `inventory`: List of owned equipment

### Expedition
- `equipped_equipment_id`: Reference to the equipment item equipped for this expedition

**Note:** Equipment is equipped per expedition, not globally per player. Each expedition can have a different equipment item equipped, and changing equipment for one expedition does not affect others.

## Database Schema (PostgreSQL)

```sql
-- Equipment table: stores equipment items owned by users
CREATE TABLE IF NOT EXISTS equipment (
   id SERIAL PRIMARY KEY,
   discord_id VARCHAR(100) NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
   main_effect TEXT NOT NULL, -- JSON-encoded EncounterModifier
   unlocked_sub_slots INTEGER DEFAULT 0,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_equipment_discord_id ON equipment(discord_id);

-- Sub slots for each equipment item
CREATE TABLE IF NOT EXISTS equipment_sub_slots (
   id SERIAL PRIMARY KEY,
   equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
   slot_index INTEGER NOT NULL CHECK (slot_index >= 1 AND slot_index <= 5),
   effect TEXT, -- JSON-encoded EncounterModifier or NULL
   is_unlocked BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_equipment_id ON equipment_sub_slots(equipment_id);

-- Expedition table (partial, for equipment linkage)
-- Add a column to link equipped equipment to each expedition
ALTER TABLE expeditions ADD COLUMN IF NOT EXISTS equipped_equipment_id INTEGER REFERENCES equipment(id);
```
3. **Unlock Sub Slots:**
   - The player can unlock sub slots by sacrificing other equipment items.
   - Each unlock consumes one equipment and opens the next available sub slot.
4. **Remove Sub Slots:**
   - The player can reset (remove) all sub slots on an equipment at once. This action clears all sub slot effects and locks them again.



## Implementation Steps

1. **Database Migration:**
   - Create the `equipment` and `equipment_sub_slots` tables using the provided schema.
   - Add the `equipped_equipment_id` column to the `expeditions` table.
   - Ensure all foreign key constraints and indexes are in place.

2. **Backend Models & Services:**
   - Define Equipment and SubSlot models/classes in the backend, matching the schema and data model.
   - Update user inventory logic to support equipment items (add, remove, list, etc.).
   - Implement CRUD operations for equipment and sub slots.
   - Implement logic for equipping equipment per expedition (set and retrieve equipped_equipment_id).

3. **Effect Application Logic:**
   - Integrate equipment effect application into the expedition resolver, using the shared EncounterModifier model.
   - Ensure sub slot and main slot effects are applied at the correct stages (stat checks, loot, etc.).
   - Add support for new effect types as needed.

4. **User Interface & Commands:**
   - Add commands/UI for viewing, equipping, and managing equipment.
   - Add commands/UI for unlocking and resetting sub slots.
   - Display equipment effects and slot status to the user.

5. **Testing & Validation:**
   - Write unit and integration tests for all equipment logic.
   - Test edge cases: max sub slots, equipping/unequipping, effect stacking, etc.

6. **Documentation & Balancing:**
   - Update user and developer documentation as features are implemented.
   - Playtest and balance equipment effects and acquisition rates.


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
