## 9. Database Service Layer Integration

The World-Threat Raid system should interact with the database through a dedicated service layer, following the patterns established in the Wanderer/expedition system's `DatabaseService` (see `services/database.py`).

### 9.1. Key Patterns and Methods

- **Connection Pooling:** All database access is performed via an async connection pool, ensuring efficient and safe concurrent access.
- **Atomic Operations & Transactions:** For multi-step updates (e.g., updating boss state and player state after a strike), use `async with conn.transaction()` blocks to ensure atomicity and rollback on error.
- **CRUD Methods:** Implement async methods for creating, reading, updating, and deleting raid-related records (boss state, player state, logs, rewards, etc.), mirroring the structure of methods like `add_equipment`, `get_equipment_by_id`, `update_equipment`, etc.
- **Batch and Upsert Operations:** Use batch inserts/updates and upsert logic where appropriate (see `add_waifus_to_user_batch`, `get_or_create_user`).
- **Query Patterns:** Use parameterized SQL queries to prevent injection and ensure clarity (see all `await conn.fetchrow(...)`, `await conn.fetch(...)` patterns).

### 9.2. Example Interactions for Raid System

- **BossRaidState:**
  - Store and update the global boss raid state in a dedicated table (e.g., `boss_raids`).
  - Use methods like `get_boss_raid_by_id`, `update_boss_raid_state`, and `create_boss_raid`.
  - Reference: `get_equipment_by_id`, `update_equipment` for single-record CRUD.

- **PlayerRaidState:**
  - Store per-user, per-raid state in a table (e.g., `player_raid_states`).
  - Use methods like `get_player_raid_state`, `update_player_raid_state`, `create_player_raid_state`.
  - Reference: `get_user_equipment`, `update_equipment`, `get_user_collection` for per-user queries and updates.

- **StrikeLog:**
  - Store each strike as an append-only log (e.g., `raid_strike_logs`).
  - Use methods like `add_raid_strike_log`, `get_raid_strike_logs_by_raid`.
  - Reference: `add_expedition_log`, `get_expedition_logs` for logging patterns.

- **Reward Claims:**
  - Track claimed rewards in a table (e.g., `raid_reward_claims`).
  - Use upsert or unique constraints to prevent double-claiming (see `claim_user_mission_reward`).

### 9.3. Best Practices

- Always check for connection pool initialization before DB access.
- Use transactions for multi-step or related updates.
- Return clear status or result objects from service methods (e.g., success/failure, affected rows, new IDs).
- Parse and format data as needed for the game layer (see `_parse_waifu_json_fields`).
- Use async/await for all DB operations to avoid blocking the event loop.

### 9.4. Reference Table: DatabaseService Methods

| Raid System Need         | DatabaseService Example Method(s)         |
|-------------------------|-------------------------------------------|
| Create/Update Boss      | add_equipment, update_equipment           |
| Get Boss State          | get_equipment_by_id                       |
| Create/Update Player    | add_waifu_to_user, update_equipment       |
| Get Player State        | get_user_collection, get_user_equipment   |
| Log Strike              | add_expedition_log                        |
| Get Strike Logs         | get_expedition_logs                       |
| Reward Claim/Upsert     | claim_user_mission_reward                 |
| Batch/Upsert            | add_waifus_to_user_batch, get_or_create_user |

---
# World-Threat Raid System: Implementation Blueprint

## 1. Architecture Overview

- **Brand new, modular system** for World-Threat Raids, with clear separation of concerns.
- **Reference the Wanderer (expedition) system** for proven patterns in stat calculation, team management, UI flows, and reward logic.
- **No direct code reuse** unless a component is truly generic; instead, adapt and improve upon Wanderer’s best ideas.

---

## 2. Data Models & Persistence

### 2.1. BossRaidState (Global)
- Fields: boss_id, total_hp, current_hp, dominant_stats, weaknesses, resistances, curse_pool, active_curses, curse_limits, analysis_thresholds, analysis_points, analysis_breakthroughs, analysis_reward_pool, event_start, event_end, strike_count
- **Reference:** Wanderer’s expedition state models (e.g., `ExpeditionInstance`, `ExpeditionBoss` in `expeditions.py` or `models/expedition.py`) for structuring boss and event state.

### 2.2. PlayerRaidState (Per-User, Per-Raid)
- Fields: user_id, boss_raid_id, last_strike_time, exhausted_characters, personal_damage, personal_analysis, rewards_claimed
- **Note:** This state is tracked separately for each user and each boss raid event. All cooldowns, exhausted characters, and progress are isolated to a specific raid.
- **Reference:** Wanderer’s per-user expedition progress and cooldown tracking (e.g., `UserExpeditionState`, cooldown logic in `expeditions.py`), but ensure scoping is per raid event.

### 2.3. StrikeLog (History)
- Fields: timestamp, user_id, action, team, score, damage, analysis_points, breakthrough_triggered, retaliation_triggered
- **Reference:** Wanderer’s expedition log or battle history (if present) for audit and analytics structure.

### 2.4. Persistence
- Use a database (SQL/NoSQL) for all state. In-memory cache for active event state, with regular DB sync.
- **Reference:** Wanderer’s persistence layer for saving/loading expedition and user state.

---

## 3. Core Logic & Algorithms

### 3.1. Team Validation
- Ensure all selected characters are owned and not exhausted for this raid.
- Team size: 1-6.
- **Reference:** Wanderer’s team selection and validation logic (e.g., `validate_team`, `get_available_characters` in `expeditions.py`).

### 3.2. Score Calculation
- `Score = (Sum of the boss's Dominant Stats for all team members) * Affinity Multiplier`
- **Reference:** Wanderer’s stat and multiplier calculation (e.g., `calculate_expedition_score`, `get_affinity_multiplier` in `expeditions.py` or `battle.py`).

### 3.3. Fight/Analyze Resolution
- Fight: `damage = floor(score / 10)`; subtract from boss HP.
- Analyze: `analysis_points = floor(score / 10)`; add to global analysis bar.
- **Reference:** Wanderer’s expedition resolution and result logic (e.g., `resolve_expedition`, `apply_damage`, `grant_rewards`).

### 3.4. Breakthroughs & Retaliations
- On analysis threshold: roll for new weakness, add to boss, increment breakthroughs.
- On strike count threshold: roll for new curse, add/replace in active_curses.
- **Reference:** Wanderer’s event/trigger system (e.g., milestone or boss phase logic).

### 3.5. Cooldown & Exhaustion
- Enforce per-user, per-character cooldowns and exhaustion for the event.
- **Reference:** Wanderer’s cooldown and usage tracking (e.g., `can_strike`, `mark_character_used`).

---

## 4. UI/UX Flows

### 4.1. Raid Hub
- Shows boss HP, dominant stats, weaknesses, curses, analysis bar, and action buttons.
- **Reference:** Wanderer’s expedition hub or main menu UI (e.g., `ExpeditionHubView`, `ExpeditionStatusEmbed`).

### 4.2. Team Selection
- Shows available/used characters, highlights contributing stats.
- **Reference:** Wanderer’s team selection UI (e.g., `CharacterSelectView`, `get_team_selection_embed`).

### 4.3. After-Action Report
- Shows damage/analysis, triggers, and announcements.
- **Reference:** Wanderer’s result/summary UI (e.g., `ExpeditionResultView`, `get_result_embed`).

### 4.4. Reward Claim
- UI for claiming milestone, analysis, and victory rewards.
- **Reference:** Wanderer’s reward claim UI (e.g., `RewardClaimView`).

---

## 5. Event & Reward Handling

### 5.1. Strike Rewards
- Immediate rewards for each Fight/Analyze action.
- **Reference:** Wanderer’s per-battle or per-expedition reward logic.

### 5.2. Milestone & Analysis Rewards
- Based on personal damage and analysis contribution.
- **Reference:** Wanderer’s milestone reward system.

### 5.3. Victory Cache
- Distributed to all participants if boss is defeated.
- **Reference:** Wanderer’s expedition completion rewards.

### 5.4. Announcement System
- Broadcast breakthroughs, retaliations, and victory to all players.
- **Reference:** Wanderer’s announcement or notification system (e.g., `send_announcement`, `broadcast_event`).

---

## 6. Testing & Extensibility

- Unit tests for all core services and algorithms.
- Integration tests for full strike-to-reward flow.
- All thresholds, multipliers, and pools are data-driven for easy tuning.
- **Reference:** Wanderer’s test suite and data-driven config patterns.

---

## 7. Example File Structure

```
raid/
  __init__.py
  models.py           # BossRaidState, PlayerRaidState, StrikeLog
  manager.py          # RaidManager, PlayerRaidManager
  resolver.py         # StrikeResolver
  rewards.py          # RewardManager
  announce.py         # AnnouncementService
  ui/
    hub.py
    team_select.py
    after_action.py
    rewards.py
  tests/
    test_manager.py
    test_resolver.py
    test_rewards.py
```

---

## 8. Reference Table: Wanderer Segments to Reference

| Raid System Component         | Wanderer Reference (File/Class/Function)           |
|------------------------------|----------------------------------------------------|
| Boss/Event State             | expeditions.py: ExpeditionInstance, ExpeditionBoss |
| Per-User State/Cooldowns     | expeditions.py: UserExpeditionState, cooldown logic|
| Team Selection/Validation    | expeditions.py: validate_team, get_available_characters |
| Stat/Multiplier Calculation  | expeditions.py/battle.py: calculate_expedition_score, get_affinity_multiplier |
| Resolution/Results           | expeditions.py: resolve_expedition, apply_damage, grant_rewards |
| UI: Hub/Status               | expeditions.py: ExpeditionHubView, ExpeditionStatusEmbed |
| UI: Team Selection           | expeditions.py: CharacterSelectView, get_team_selection_embed |
| UI: Results                  | expeditions.py: ExpeditionResultView, get_result_embed |
| UI: Rewards                  | expeditions.py: RewardClaimView                    |
| Reward/Announcement System   | expeditions.py: send_announcement, broadcast_event |
| Testing/Config Patterns      | tests/, config/                                    |

---

This document provides a step-by-step technical plan for implementing the World-Threat Raid system, with explicit reference points in the Wanderer game system for each major component. Use the Wanderer codebase as a living design document and inspiration for robust, maintainable implementation.
