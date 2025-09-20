# Wanderer Game Expedition System: Overview & Architecture

## Introduction
The Wanderer Game expedition system is a modular, extensible backend for simulating multi-encounter expeditions, team-based skill checks, affinity bonuses, and dynamic loot generation. It is designed for Discord bot integration but is architected for general use.

## High-Level Architecture
- **Models**: Data classes for expeditions, encounters, characters, loot, and results.
- **Systems**: Core logic for expedition management, encounter resolution, and loot generation.
- **Registries**: Content/data loaders and managers for characters, expeditions, and encounters.
- **Utils**: Calculation helpers for affinity, stats, and probability.

## Data Flow
1. **Content Loading**: Expedition templates and encounters are loaded from JSON; characters from CSV.
2. **Expedition Generation**: Daily expeditions are generated from templates, with randomized affinities and encounter pools.
3. **Team Dispatch**: Users select a team; the system validates and dispatches the expedition.
4. **Encounter Resolution**: Each encounter is processed in sequence, applying stat checks, affinity multipliers, and modifiers.
5. **Loot Generation**: Rewards are generated based on outcomes, difficulty, and final luck multipliers.
6. **Result Logging**: A detailed log and summary are produced for UI and analytics.

## Key Concepts
- **Affinities**: Expeditions have favored/disfavored affinities; matching team members grant multiplicative buffs/nerfs.
- **Encounters**: Each expedition consists of a sequence of encounters (standard, gated, boon, hazard).
- **Loot**: Rewards are generated using a two-stage system (type selection, then amount/item selection).
- **Persistence**: Expedition state is managed via slots, supporting active, completed, and cancelled states.

## Extensibility
- New encounter types, modifiers, and loot can be added via data files and model extensions.
- The system is designed for easy integration with Discord UI and other frontends.

---

**Next:** See `systems.md` for deep dives into core logic, or `models.md` for data model reference.
