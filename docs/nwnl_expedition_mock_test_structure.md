---

## 10. Step-by-Step Implementation Breakdown

This section provides a granular, implementation-oriented breakdown for each major component, with explicit substeps and helper function suggestions to make the process as smooth as possible.

### 1. Command Handler

**Steps:**
1. Register the `/nwnl_expedition_mock_test` command with the `character_source` parameter.
2. On invocation, fetch all expeditions (including unavailable ones) from the data manager/service.
3. Instantiate and send the `MockExpeditionSelectView` with the full expedition list.
4. Pass along the `character_source` and user ID for later steps.

**Helpers:**
- `get_all_expeditions()` — returns all expedition templates.

### 2. Expedition Selection View (`MockExpeditionSelectView`)

**Steps:**
1. Display a paginated select menu of all expeditions (no filtering).
2. On selection, fetch the character pool:
  - If `character_source == 'user'`: fetch user's characters (as in real start flow).
  - If `character_source == 'database_maxed'`: fetch all maxed-level database characters (helper needed).
3. Fetch all user equipment (regardless of assignment).
4. Instantiate and send the `MockCharacterSelectView` with the selected expedition, character pool, and equipment.

**Helpers:**
- `get_user_characters_for_expedition(discord_id)`
- `get_maxed_database_characters()` — returns all 5★ characters at max level/stats.
- `get_all_user_equipment(discord_id)`

### 3. Team/Equipment Selection View (`MockCharacterSelectView`)

**Steps:**
1. Display a paginated, searchable, and sortable list of characters (from the chosen pool).
2. Allow selection of up to 3 characters.
3. Display all user equipment, allow selection of any (even if equipped elsewhere).
4. On confirmation, call the simulation logic with the selected expedition, team, and equipment.

**Helpers:**
- UI logic can be reused from `CharacterSelectView`.
- Add a clear "Simulate" button (instead of "Start Expedition").

### 4. Simulation Logic (`run_mock_expedition_simulation`)

**Steps:**
1. Build the expedition instance (using the selected template and team, as in `_generate_expedition_at_completion`).
2. Build the team (instantiate `Character`/`Team` objects, set star level to max if needed).
3. Build the equipment object (if any selected).
4. Call the resolver (as in `complete_expedition`), but do not write to the DB or award loot.
5. Return a result dict in the same format as the real completion flow.

**Helpers:**
- `build_expedition_instance(template, team_series_ids)`
- `build_team_from_selection(selection, maxed=False)`
- `build_equipment_object(equipment_id)`
- `resolve_expedition(expedition, team, equipment)`

### 5. Results View (`MockExpeditionResultsView`)

**Steps:**
1. Display the results using the same multi-page embed UI as `ExpeditionResultsView`.
2. Clearly mark all embeds as "Simulation Only – No Rewards Granted".
3. Allow navigation between summary, encounters, and rewards pages.
4. Optionally, add a "Try Again" or "Change Team" button for rapid iteration.

**Helpers:**
- Subclass `ExpeditionResultsView` and override embed creation to add simulation banners/notes.

---
---
Title: NWNL Expedition Mock Test Command Structure
Date: 2025-09-26
---

# NWNL Expedition Mock Test Command Structure

## Purpose

The `nwnl_expedition_mock_test` command allows users to simulate any expedition with any team and equipment, mimicking the full UI/UX of both the expedition start and completion flows, but without any database writes or rewards. This document outlines the structure and flow for implementing this feature in the Discord bot.

---


## 1. Command Registration

**Goal:** Register a new Discord app command in the `ExpeditionsCog` for the mock test.


**Details:**
- Name: `nwnl_expedition_mock_test`
- Description: "🧪 Simulate any expedition with any team/equipment (no rewards, no database changes)"
- Should be accessible to all users.
- **Parameter:** `character_source` (enum: `"user"` or `"database_maxed"`)
  - If `user`: Use the user's own characters (with their current levels/stats).
  - If `database_maxed`: Use all database characters at max level/stats (e.g., all 5★ at max level).

**Code Scaffold:**
```python
@app_commands.command(
  name="nwnl_expedition_mock_test",
  description="🧪 Simulate any expedition with any team/equipment (no rewards, no database changes)"
)
@app_commands.describe(
  character_source="Choose between your own characters or all maxed-level database characters ('user' or 'database_maxed')"
)
async def nwnl_expedition_mock_test(self, interaction: discord.Interaction, character_source: str = "user"):
  # Step 1: Show all expeditions for selection
  # Use character_source to determine which pool to present in team selection
  ...
```

---


## 2. Expedition Selection UI

**Goal:** Let the user select any expedition (including unavailable ones) to simulate.

**Details:**
- Show a paginated list of all expeditions.
- Use a view similar to `ExpeditionListView` or `ExpeditionSelectView`, but do not filter by availability.
- On selection, proceed to team/equipment selection.

**Code Scaffold:**
```python
class MockExpeditionSelectView(discord.ui.View):
  def __init__(self, expeditions, user_id):
    super().__init__(timeout=300)
    self.expeditions = expeditions  # All expeditions
    self.user_id = user_id
    self.selected_expedition = None
    # Setup pagination and select menu as in ExpeditionSelectView
    ...

  async def expedition_selected(self, interaction: discord.Interaction):
    # Set self.selected_expedition and proceed to team selection
    ...
```

---


## 3. Team/Equipment Selection UI

**Goal:** Let the user select a team and equipment for the simulation.

**Details:**
- Present a UI similar to `CharacterSelectView`.
+- Use the `character_source` parameter to determine the pool:
  - If `user`: Show user's own characters
  - If `database_maxed`: Show all maxed-level database characters
- Show all user equipment, even if currently equipped.
- Allow selection of up to 3 characters and any equipment.
- On confirmation, proceed to simulation.

**Code Scaffold:**
```python
class MockCharacterSelectView(discord.ui.View):
    def __init__(self, character_pool, equipment_list, user_id, expedition):
        super().__init__(timeout=300)
        self.character_pool = character_pool  # User or 5★ DB characters
        self.equipment_list = equipment_list
        self.user_id = user_id
        self.expedition = expedition
        self.selected_characters = []
        self.selected_equipment = []
        # Add toggle for character pool, selection menus, etc.
        ...

    async def confirm_selection(self, interaction: discord.Interaction):
        # Proceed to simulation with selected team/equipment
        ...
```

---


## 4. Simulation Logic

**Goal:** Simulate the expedition instantly using the selected team and equipment.

**Details:**
- Assemble the team and equipment as in `nwnl_expeditions_start`.
- Call the expedition resolution logic (as in `nwnl_expeditions_complete`).
- Ensure all operations are read-only:
  - No database writes
  - No rewards granted
- Mark the result as a simulation in the output.

**Code Scaffold:**
```python
async def run_mock_expedition_simulation(expedition, team, equipment, services):
    # Prepare all data as for a real expedition
    # Call the expedition resolution logic (refactor if needed to allow dry-run)
    # Return a result dict as would be returned by completion logic
    ...
    return simulation_result
```

---


## 5. Results UI

**Goal:** Present the simulation results in a familiar, multi-page embed view.

**Details:**
- Use an `ExpeditionResultsView` or similar to show:
  - Summary (outcome, stats, multipliers)
  - Encounters (detailed log)
  - Simulated rewards (clearly marked as "simulation only")
- Allow navigation between result pages.
- Clearly indicate that this is a simulation and no rewards are granted.

**Code Scaffold:**
```python
class MockExpeditionResultsView(ExpeditionResultsView):
    def __init__(self, simulation_result, user_id):
        super().__init__([simulation_result], user_id)
        # Add a "Simulation Only" banner or note to embeds
        ...
```

---


## 6. No Side Effects

**Goal:** Guarantee that the mock test does not affect any persistent data or grant rewards.

**Details:**
- All data fetching is read-only.
- No expedition, character, or equipment state is changed.
- No rewards are granted.
- All logic should be contained within the command/session.

---


## 7. Example Flow

1. User runs `/nwnl_expedition_mock_test`.
2. Bot presents a paginated list of all expeditions for selection (MockExpeditionSelectView).
3. User selects an expedition.
4. Bot presents a team/equipment selection UI (MockCharacterSelectView), with a toggle for character pool.
5. User selects team and equipment.
6. Bot simulates the expedition instantly (run_mock_expedition_simulation) and presents the results in a multi-page embed view (MockExpeditionResultsView).
7. User can repeat as desired; nothing is saved or rewarded.

---


## 8. Implementation Notes

- Reuse as much UI and logic as possible from the existing start/complete commands.
- Refactor shared logic into helpers if needed.
- Clearly label all embeds and results as “Simulation Only – No Rewards Granted”.
- Consider adding a "Try Again" or "Change Team" button for rapid iteration.

---


---

## 9. Detailed Code Structure & Scaffold Plan

### Overview
The mock test command will closely mirror the real expedition start/complete flow, using the same UI classes and logic wherever possible. The main differences are:
- All expeditions are available for selection.
- Team selection can use either the user's characters or all maxed-level database characters.
- No database writes or rewards; all simulation is in-memory.

### Main Components

1. **Command Handler**
  - Registers `/nwnl_expedition_mock_test` with a `character_source` parameter.
  - Entry point for the flow.

2. **Expedition Selection View**
  - Subclass or reuse `ExpeditionSelectView` as `MockExpeditionSelectView`.
  - Shows all expeditions (no filtering by availability).
  - On selection, transitions to team/equipment selection.

3. **Team/Equipment Selection View**
  - Subclass or reuse `CharacterSelectView` as `MockCharacterSelectView`.
  - Uses the `character_source` parameter to determine the pool.
  - Allows selection of up to 3 characters and any equipment.
  - On confirmation, triggers the simulation.

4. **Simulation Logic**
  - Function (e.g., `run_mock_expedition_simulation`) that:
    - Builds the expedition instance (using the selected template and team).
    - Calls the resolver as in the real completion flow.
    - Returns a result dict (no DB writes, no rewards).

5. **Results View**
  - Subclass or reuse `ExpeditionResultsView` as `MockExpeditionResultsView`.
  - Presents the simulation results in the same multi-page format.
  - Clearly marks the results as a simulation.

### Scaffold Example

```python
# 1. Command Handler
@app_commands.command(
  name="nwnl_expedition_mock_test",
  description="🧪 Simulate any expedition with any team/equipment (no rewards, no database changes)"
)
@app_commands.describe(
  character_source="Choose between your own characters or all maxed-level database characters ('user' or 'database_maxed')"
)
async def nwnl_expedition_mock_test(self, interaction: discord.Interaction, character_source: str = "user"):
  # Step 1: Fetch all expeditions
  expeditions = await self.expedition_service.get_all_expeditions()  # or similar
  view = MockExpeditionSelectView(expeditions, interaction.user.id)
  await interaction.response.send_message(embed=await view._create_expedition_list_embed(), view=view)

# 2. Expedition Selection View
class MockExpeditionSelectView(ExpeditionSelectView):
  def __init__(self, expeditions, user_id):
    # Show all expeditions, not just available
    super().__init__(expeditions, user_id, expedition_service=None)
    # ...
  async def expedition_selected(self, interaction: discord.Interaction):
    # On selection, fetch character/equipment pool and show team selection
    ...

# 3. Team/Equipment Selection View
class MockCharacterSelectView(CharacterSelectView):
  def __init__(self, character_pool, user_id, expedition, equipment_list):
    # Use character_pool based on character_source
    super().__init__(character_pool, user_id, expedition_service=None, expedition=expedition, equipment_list=equipment_list)
    # ...
  async def start_expedition(self, interaction: discord.Interaction):
    # Instead of DB write, call simulation logic
    simulation_result = await run_mock_expedition_simulation(...)
    results_view = MockExpeditionResultsView(simulation_result, user_id)
    await interaction.followup.send(embed=results_view.get_current_embed(), view=results_view)

# 4. Simulation Logic
async def run_mock_expedition_simulation(expedition, team, equipment, services):
  # Build expedition instance (as in _generate_expedition_at_completion)
  # Build team (Character/Team objects, maxed if needed)
  # Call resolver (as in complete_expedition), but do not write to DB
  # Return result dict for display
  ...

# 5. Results View
class MockExpeditionResultsView(ExpeditionResultsView):
  def __init__(self, simulation_result, user_id):
    super().__init__([simulation_result], user_id)
    # Add "Simulation Only" note to embeds
    ...
```

### Notes
- All UI/UX should be visually and functionally identical to the real start/complete flow.
- Only the data sources and side effects differ (all read-only, no rewards).
- Refactor shared logic as needed to avoid code duplication.

---
