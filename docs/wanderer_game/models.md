# Data Models Reference

This document describes the core data models used in the Wanderer Game expedition system.

## Expedition & ExpeditionTemplate

- **ExpeditionTemplate**: Blueprint for generating expeditions. Contains duration, difficulty, affinity pools, and encounter tags. Used for daily rotation.
- **Expedition**: A specific expedition instance with resolved affinities, encounter pool, and dynamic state (modifiers, bonuses, etc).
- **Fields:**
  - `expedition_id`, `name`, `duration_hours`, `difficulty`, `favored_affinities`, `disfavored_affinities`, `encounter_pool_tags`, `encounter_count`, plus dynamic state fields.

## Encounter & Encounter Types

- **Encounter**: Represents a single event in an expedition. Types:
  - `STANDARD`: Stat check
  - `GATED`: Conditional check (elemental, archetype, series, genre, team size)
  - `BOON`: Beneficial modifier
  - `HAZARD`: Detrimental modifier
- **Fields:**
  - `encounter_id`, `name`, `type`, `tags`, `description`, `check_stat`, `difficulty`, `loot_values`, `condition`, `modifier`

## Character & Team

- **Character**: Represents a playable character. Fields:
  - `waifu_id`, `name`, `series`, `series_id`, `genres`, `image_url`, `base_stats`, `elemental_types`, `archetype`, `potency`, `elemental_resistances`, `star_level`
- **Team**: A group of 1-4 characters dispatched on an expedition.

## Affinity

- **Affinity**: (Type, Value) pair. Types: `elemental`, `archetype`, `series_id`, `genre`.
- Used for matching team members to expedition bonuses/nerfs.

## Loot & LootPool

- **LootItem**: Represents a reward (gems, quartzs, item, etc). Fields:
  - `item_type`, `item_id`, `quantity`, `rarity`, `value`
- **LootPool**: Collection of loot items accumulated during an expedition.

## Result Models

- **ExpeditionResult**: Aggregates all encounter results, loot, and summary stats for an expedition.
- **EncounterResult**: Outcome of a single encounter (success, failure, loot, modifiers, etc).

---

See also: `systems.md` for logic, `registries.md` for data/content loading.
