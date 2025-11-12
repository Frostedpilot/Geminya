# Registries & Content Loading

This document explains how game data is loaded, managed, and accessed in the Wanderer Game expedition system.

## ContentLoader
- Loads expedition templates and encounters from JSON files in the `data/expeditions/` directory.
- Methods:
  - `load_expedition_templates(filename)`: Loads and parses templates into `ExpeditionTemplate` objects.
  - `load_encounters(filename)`: Loads and parses encounters into `Encounter` objects.
  - `load_raw_json(filename)`: Loads raw JSON data for custom use.

## CharacterRegistry
- Loads character data from `characters_final.csv` in the `data/final/` directory.
- Provides lookup and search for characters by ID, series, name, archetype, or elemental type.
- Methods:
  - `load_characters(filename)`: Loads and indexes all characters.
  - `get_character(waifu_id)`, `get_characters_by_series(series_id)`, `search_characters(...)`

## DataManager
- Central coordinator for all data loading and access.
- Instantiates and manages `ContentLoader`, `CharacterRegistry`, and `LootGenerator`.
- Methods:
  - `load_all_data()`: Loads all required data files.
  - `get_character_registry()`, `get_expedition_templates()`, `get_encounters()`, `get_loot_generator()`

## Data File Structure
- `data/expeditions/base_expeditions.json`: Expedition templates
- `data/expeditions/encounters.json`: Encounter definitions
- `data/final/characters_final.csv`: Character data

---

See also: `models.md` for data structures, `systems.md` for logic, `utils.md` for calculation helpers.
