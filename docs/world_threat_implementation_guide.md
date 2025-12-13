# World Threat: Comprehensive Implementation Guide

# ---
# Implementation Notes (2025-11-16)
#
# - All boss and player status fields that are lists or dicts are now stored as JSON strings in the database (not plain text or JSONB).
#   - Example: dominant_stats, buffs, curses, cursed_stat, claimed_personal_checkpoints, claimed_server_checkpoints
#   - This simplifies parsing and updating, and matches Python's native data structures.
# - The admin script `initialize_world_threat.py` now uses a Python dictionary and `json.dumps` for boss initialization.
# - All service methods in `WorldThreatService` use `json.loads`/`json.dumps` for serialization/deserialization of these fields.
# - The database schema (if using TEXT) should expect JSON-encoded strings for these columns.
# - The implementation is now more maintainable and easier to update for future changes.
#
# Completed Backend Steps:
# 1. Database schema and migration for World Threat tables
# 2. Pydantic models for boss and player status
# 3. WorldThreatService with full game logic and JSON field handling
# 4. Service registration in ServiceContainer
# 5. Admin script for boss initialization/reset
#
# Next Steps:
# - Frontend Discord Cog and UI integration
# - Testing and validation
# - Further documentation and user guide updates
# ---

## 1. Introduction

This document provides a detailed technical guide for implementing the **World Threat** game mode. It covers backend architecture, database design, frontend (Discord UI) implementation, and integration with the existing codebase.

The core principle is to **adapt and reuse** the robust systems already built for the Expedition game mode, as the fundamental concepts (team selection, power calculation, rewards) are similar. This guide will frequently reference files like `services/expedition_service.py`, `cogs/commands/expeditions.py`, and `services/database.py` as blueprints.

---

## 2. Backend Implementation

The backend is the heart of the World Threat system, responsible for managing the boss's state, processing player actions, and calculating results.

### 2.1. Database Schema Design

We need new tables to store the persistent state of the World Threat. These should be added to the database initialization scripts.

**Reference**: Look at how tables like `user_expeditions` and `user_equipment` are created and managed in `services/database.py`.

#### Table 1: `world_threat_boss`

This is a **single-row table** that holds the state of the current boss.

```sql
CREATE TABLE IF NOT EXISTS world_threat_boss (
    id INT PRIMARY KEY DEFAULT 1, -- Ensures only one row
    boss_name TEXT NOT NULL,
    dominant_stats TEXT NOT NULL,      -- e.g., ["strength", "speed"]
    cursed_stat TEXT NOT NULL,          -- e.g., "intelligence"
    buffs TEXT NOT NULL,               -- e.g., {"elemental": ["Fire"], "archetype": ["Tank"]}
    curses TEXT NOT NULL,              -- e.g., {"genre": ["Shounen"]}
    buff_cap INT NOT NULL DEFAULT 3,
    curse_cap INT NOT NULL DEFAULT 3,
    server_total_points BIGINT NOT NULL DEFAULT 0,
    total_research_actions INT NOT NULL DEFAULT 0,
    adaptation_level INT NOT NULL DEFAULT 0 -- 0: None, 1: First stage, 2: Second stage
);
```

#### Table 2: `world_threat_player_status`

This table tracks the progress and status of each individual player.

```sql
CREATE TABLE IF NOT EXISTS world_threat_player_status (
    discord_id TEXT PRIMARY KEY,
    cumulative_points BIGINT NOT NULL DEFAULT 0,
    last_action_timestamp TIMESTAMPTZ,
    research_stacks INT NOT NULL DEFAULT 0,
    claimed_personal_checkpoints TEXT DEFAULT '[]'::text, -- e.g., [10000, 25000]
    claimed_server_checkpoints TEXT DEFAULT '[]'::text
);
```

### 2.2. Data Models

Create Pydantic models to represent the data structures for type-safe operations within the service layer.

**Location**: `src/wanderer_game/models/world_threat.py` (new file)
**Reference**: `src/wanderer_game/models/character.py`

```python
# src/wanderer_game/models/world_threat.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime
import json

class WorldThreatBoss(BaseModel):
    boss_name: str
    dominant_stats: List[str]
    cursed_stat: str
    buffs: Dict[str, List[str]]
    curses: Dict[str, List[str]]
    buff_cap: int
    curse_cap: int
    server_total_points: int = 0
    total_research_actions: int = 0
    adaptation_level: int = 0

    class Config:
        json_encoders = {
            set: lambda v: list(v),
            frozenset: lambda v: list(v),
        }

class WorldThreatPlayerStatus(BaseModel):
    discord_id: str
    cumulative_points: int = 0
    last_action_timestamp: datetime | None = None
    research_stacks: int = 0
    claimed_personal_checkpoints: List[int] = Field(default_factory=list)
    claimed_server_checkpoints: List[int] = Field(default_factory=list)

    class Config:
        json_encoders = {
            set: lambda v: list(v),
            frozenset: lambda v: list(v),
        }
```

### 2.3. Service Layer: `WorldThreatService`

This will be the central logic hub. Create a new service file.

**Location**: `services/world_threat_service.py` (new file)
**Reference**: `services/expedition_service.py`

```python
# services/world_threat_service.py
import random
from datetime import datetime, timedelta, timezone
from .database import Database
from .container import ServiceContainer # To access other services
from src.wanderer_game.models.world_threat import WorldThreatBoss, WorldThreatPlayerStatus
import json

class WorldThreatService:
    def __init__(self, container: ServiceContainer):
        self.db: Database = container.database
        self.data_manager = container.data_manager
        # Define constants for game balance
        self.RESEARCH_ADAPTATION_THRESHOLD_1 = 5
        self.RESEARCH_ADAPTATION_THRESHOLD_2 = 10
        self.ADAPTATION_DAMAGE_MULTIPLIER = 0.8
        self.SERIES_MULTIPLIER = 1.5
        self.DAPHINE_REWARD_MULTIPLIER = 1.2

    # --- Data Access Methods ---
    async def get_boss(self) -> WorldThreatBoss:
        # Fetches the single row from world_threat_boss and returns a Pydantic model
        result = await self.db.fetch("SELECT * FROM world_threat_boss WHERE id = 1")
        if result:
            boss_data = result[0]
            # Deserialize JSON fields
            boss_data['dominant_stats'] = json.loads(boss_data['dominant_stats'])
            boss_data['cursed_stat'] = json.loads(boss_data['cursed_stat'])
            boss_data['buffs'] = json.loads(boss_data['buffs'])
            boss_data['curses'] = json.loads(boss_data['curses'])
            return WorldThreatBoss(**boss_data)
        else:
            # Handle missing boss row (shouldn't happen in normal operation)
            raise Exception("Boss not found")

    async def get_player_status(self, discord_id: str) -> WorldThreatPlayerStatus:
        # Fetches a player's status, creating a default one if it doesn't exist
        result = await self.db.fetch("SELECT * FROM world_threat_player_status WHERE discord_id = %s", discord_id)
        if result:
            player_data = result[0]
            # Deserialize JSON fields
            player_data['claimed_personal_checkpoints'] = json.loads(player_data['claimed_personal_checkpoints'])
            player_data['claimed_server_checkpoints'] = json.loads(player_data['claimed_server_checkpoints'])
            return WorldThreatPlayerStatus(**player_data)
        else:
            # Create a new player status row
            new_player_status = WorldThreatPlayerStatus(discord_id=discord_id)
            await self.db.execute(
                "INSERT INTO world_threat_player_status (discord_id) VALUES (%s)",
                discord_id
            )
            return new_player_status

    async def _update_boss(self, boss: WorldThreatBoss):
        # Writes the updated boss model back to the database
        await self.db.execute(
            "UPDATE world_threat_boss SET "
            "boss_name = %s, "
            "dominant_stats = %s, "
            "cursed_stat = %s, "
            "buffs = %s, "
            "curses = %s, "
            "buff_cap = %s, "
            "curse_cap = %s, "
            "server_total_points = %s, "
            "total_research_actions = %s, "
            "adaptation_level = %s "
            "WHERE id = 1",
            boss.boss_name,
            json.dumps(boss.dominant_stats),
            json.dumps(boss.cursed_stat),
            json.dumps(boss.buffs),
            json.dumps(boss.curses),
            boss.buff_cap,
            boss.curse_cap,
            boss.server_total_points,
            boss.total_research_actions,
            boss.adaptation_level
        )

    async def _update_player_status(self, player_status: WorldThreatPlayerStatus):
        # Writes the updated player status back to the database
        await self.db.execute(
            "UPDATE world_threat_player_status SET "
            "cumulative_points = %s, "
            "last_action_timestamp = %s, "
            "research_stacks = %s, "
            "claimed_personal_checkpoints = %s, "
            "claimed_server_checkpoints = %s "
            "WHERE discord_id = %s",
            player_status.cumulative_points,
            player_status.last_action_timestamp,
            player_status.research_stacks,
            json.dumps(player_status.claimed_personal_checkpoints),
            json.dumps(player_status.claimed_server_checkpoints),
            player_status.discord_id
        )

    # --- Core Game Logic ---
    async def perform_research(self, discord_id: str) -> dict:
        """Handles the Research action."""
        player_status = await self.get_player_status(discord_id)

        # 1. Check if player can perform action (daily reset at midnight UTC+7)
        action_check = await self.can_perform_action(discord_id)
        if not action_check["can_act"]:
            return {"success": False, "error": "Action is on cooldown until midnight UTC+7."}

        # 2. Update research stacks (cap at 2 for a x4 multiplier)
        player_status.research_stacks = min(2, player_status.research_stacks + 1)
        player_status.last_action_timestamp = datetime.now(timezone.utc)
        await self._update_player_status(player_status)

        # 3. Evolve the boss
        await self._evolve_boss(is_research_action=True)

        return {"success": True, "new_stacks": player_status.research_stacks}

    async def perform_fight(self, discord_id: str, team: List[dict]) -> dict:
        """Handles the Fight action: calculates points, rewards, and evolves the boss."""
        player_status = await self.get_player_status(discord_id)
        boss = await self.get_boss()

        # 1. Check if player can perform action (daily reset at midnight UTC+7)
        action_check = await self.can_perform_action(discord_id)
        if not action_check["can_act"]:
            return {"success": False, "error": "Action is on cooldown until midnight UTC+7."}

        # 2. Validate team against curses
        # ...

        # 3. Calculate points
        base_power = 0
        affinity_matches = 0
        is_daphine_present = False
        series_ids = set()

        for character_data in team:
            character = self.data_manager.get_character_registry().get_character(character_data['waifu_id'])
            series_ids.add(character.series_id)
            # Calculate Base Power
            dominant_total = sum(character.base_stats.to_dict().get(stat, 0) for stat in boss.dominant_stats)
            cursed_total = character.base_stats.to_dict().get(boss.cursed_stat, 0)
            base_power += (dominant_total - cursed_total) * (1 + (character_data['star_level'] - 1) * 0.1)

            # Check for affinity matches and Daphine
            # ...

        # Apply multipliers
        affinity_multiplier = 1.2 ** affinity_matches
        series_multiplier = self.SERIES_MULTIPLIER if len(series_ids) == 1 and len(team) == 6 else 1.0
        research_multiplier = (2 * player_status.research_stacks) if player_status.research_stacks > 0 else 1.0
        adaptation_multiplier = self.ADAPTATION_DAMAGE_MULTIPLIER if boss.adaptation_level > 0 else 1.0

        final_points = (base_power * affinity_multiplier * series_multiplier * research_multiplier) * adaptation_multiplier

        # 4. Generate immediate rewards
        # ... (base on final_points, apply daphine bonus) ...

        # 5. Update player and server progress
        player_status.cumulative_points += final_points
        boss.server_total_points += final_points
        player_status.research_stacks = 0 # Reset stacks
        player_status.last_action_timestamp = datetime.now(timezone.utc)

        # 6. Automatically grant checkpoint rewards
        personal_rewards_granted = self._grant_checkpoint_rewards(player_status, boss)
        # ...

        await self._update_player_status(player_status)

        # 7. Evolve the boss
        await self._evolve_boss()

        return {"success": True, "points_scored": final_points, "rewards": ..., "checkpoint_rewards": personal_rewards_granted}

    async def _grant_checkpoint_rewards(self, player_status: WorldThreatPlayerStatus, boss: WorldThreatBoss) -> dict:
        """
        Checks for and automatically grants personal and server checkpoint rewards.
        Returns a dictionary of rewards granted.
        """
        # This logic would be defined in a config file
        PERSONAL_CHECKPOINTS = [10000, 25000, 50000, 100000]
        SERVER_CHECKPOINTS = [1000000, 5000000, 10000000]
        
        granted_rewards = {"personal": [], "server": []}

        # Check personal checkpoints
        for checkpoint in PERSONAL_CHECKPOINTS:
            if player_status.cumulative_points >= checkpoint and checkpoint not in player_status.claimed_personal_checkpoints:
                # Grant reward (e.g., add items/currency to user's inventory)
                # ...
                player_status.claimed_personal_checkpoints.append(checkpoint)
                granted_rewards["personal"].append(checkpoint)

        # Check server checkpoints
        for checkpoint in SERVER_CHECKPOINTS:
            if boss.server_total_points >= checkpoint and checkpoint not in player_status.claimed_server_checkpoints:
                # Grant reward
                # ...
                player_status.claimed_server_checkpoints.append(checkpoint)
                granted_rewards["server"].append(checkpoint)
        
        return granted_rewards

    async def _evolve_boss(self, is_research_action: bool = False):
        """Updates the boss's stats and affinities."""
        boss = await self.get_boss()

        # 1. Re-roll stats
        all_stats = ["strength", "intelligence", "speed", "stamina", "luck"]
        random.shuffle(all_stats)
        boss.dominant_stats = all_stats[:2]
        boss.cursed_stat = all_stats[2]

        # 2. Add a new buff/curse
        # ... (logic to pick a random affinity type and value) ...
        # ... (logic to replace a random one if cap is reached) ...

        # 3. Handle research-based evolution
        if is_research_action:
            boss.total_research_actions += 1
            if boss.adaptation_level == 0 and boss.total_research_actions >= self.RESEARCH_ADAPTATION_THRESHOLD_1:
                boss.adaptation_level = 1
                boss.buff_cap += 1
            elif boss.adaptation_level == 1 and boss.total_research_actions >= self.RESEARCH_ADAPTATION_THRESHOLD_2:
                boss.adaptation_level = 2
                boss.buff_cap += 1

        await self._update_boss(boss)

### 2.4. Admin and Lifecycle Management

Create a script or admin command to initialize or reset the World Threat.

**Location**: `initialize_world_threat.py` (new file)
**Reference**: `initialize_expeditions.py`

This script will:
1.  Connect to the database.
2.  Clear the `world_threat_boss` and `world_threat_player_status` tables.
3.  Insert a new boss with a starting configuration into `world_threat_boss`.

---

## 3. Frontend (Discord Cog) Implementation

The frontend will consist of a new cog with slash commands and interactive views.

**Location**: `cogs/commands/world_threat.py` (new file)
**Reference**: `cogs/commands/expeditions.py`

### 3.1. `WorldThreatCog`

This class will contain the slash commands and will be initialized with the `WorldThreatService`.

```python
# cogs/commands/world_threat.py
from discord.ext import commands
from discord import app_commands
from services.container import ServiceContainer
from .views.world_threat_views import StatusView # To be created

class WorldThreatCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.world_threat_service = services.world_threat_service

    @app_commands.command(name="wt_status", description="View the current World Threat status.")
    async def status(self, interaction: discord.Interaction):
        boss = await self.world_threat_service.get_boss()
        player = await self.world_threat_service.get_player_status(str(interaction.user.id))
        view = StatusView(boss, player)
        embed = await view.create_embed()
        await interaction.response.send_message(embed=embed, view=view)

    # ... other commands like /wt_fight and /wt_research
```

### 3.2. UI Views

Create a new file for the UI views.

**Location**: `cogs/commands/views/world_threat_views.py` (new file)
**Reference**: The various View classes in `cogs/commands/expeditions.py`.

#### `StatusView`

* **Purpose**: The main hub for the game mode.
* **Components**:
  * An embed showing the boss's name, current stats (Dominant/Cursed), and affinities (Buffs/Curses).
  * The embed should also show server-wide points and the next server checkpoint.
  * A personal status section in the footer or a field: "Your Points: X | Research Stacks: Y | Action: Ready/Cooldown".
  * Buttons: `Fight` and `Research`. These buttons should be disabled if the player's action is on cooldown.

#### `TeamSelectView`

* **Purpose**: Allow the user to select a team of 6 characters for a fight.
* **Implementation**: This can be a near-direct copy of `CharacterSelectView` from `expeditions.py`, with modifications:
  * Allow selection of **6 characters** instead of 3.
  * **Filter out cursed characters**: Before displaying the character list, filter out any character whose affinities match the boss's active `curses`.
  * **Update Point Calculation Preview**: The live preview of "Team Power" should be updated to use the new formula: `(Sum of Dominant Stats - Cursed Stat)`.
  * **Series Bonus Indicator**: Add a visual indicator that turns on when all 6 selected characters are from the same series.

---

## 4. Integration and Development Workflow

1. **Backend First**:
   * **Step 1**: Implement the database schema changes and run the migration.
   * **Step 2**: Create the Pydantic models in `src/wanderer_game/models/world_threat.py`.
   * **Step 3**: Build the `WorldThreatService`, starting with the data access methods (`get_boss`, `get_player_status`) and then implementing the core logic (`perform_fight`, `perform_research`, `_evolve_boss`).
   * **Step 4**: Add `world_threat_service` to the `ServiceContainer` in `services/container.py`.

2. **Frontend Second**:
   * **Step 5**: Create the `WorldThreatCog` and the basic `/wt_status` command.
   * **Step 6**: Implement the `StatusView` to display the boss and player data fetched from the service.
   * **Step 7**: Adapt the `CharacterSelectView` from expeditions to create the `TeamSelectView` for World Threat, ensuring the new rules (6 characters, curse filtering) are applied.
   * **Step 8**: Implement the `Fight` and `Research` button callbacks to trigger the corresponding service methods.

3. **Finalization**:
   * **Step 9**: Create the admin script (`initialize_world_threat.py`) to manage the game mode's lifecycle.
   * **Step 10**: Thoroughly test the entire flow, from action cooldowns to boss evolution and reward calculation.

By following this guide and heavily referencing the existing expedition system, you can implement this complex feature in a structured and efficient manner. The key is to isolate the new logic in the `WorldThreatService` and reuse the UI patterns already proven to work.
