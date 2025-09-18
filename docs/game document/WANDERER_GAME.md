Understood. You're asking for a definitive, exhaustive, and meticulously detailed "bible" for this game mode. This document will serve as the absolute source of truth for the entire team, leaving no stone unturned. It will be dense, explicit, and provide enough detail for a programmer to implement systems directly and for a designer to understand the precise levers they can use for balancing.

---

# **Master Design & Implementation Document: Expedition Protocol (V10 - Final Blueprint)**

### **Document Version: 1.0**
### **Last Updated: 2025-09-17**

### **Table of Contents**
**Part A: Game Design & Mechanics (The "What" and "Why")**
1.  **High-Level Vision & Core Pillars**
    *   1.1 Game Mode Concept
    *   1.2 Core Design Philosophy: "Calculated Risks, Not Guaranteed Outcomes"
    *   1.3 Player Experience Goals & Target Audience
2.  **Core Gameplay Loop & User Experience**
    *   2.1 The Four Phases of an Expedition
    *   2.2 Detailed User Interface & User Experience Flow
3.  **The Expedition Engine: Detailed Mechanics**
    *   3.1 Expedition Generation & Dynamic Affinities
    *   3.2 The Encounter System: Types & Resolution
    *   3.3 The Chance Table: Detailed Probabilities
    *   3.4 Final Reward Resolution: The Loot Multiplier Roll
4.  **Content & Balancing Guide**
    *   4.1 Designing Encounters: A Guide for Creatives
    *   4.2 Designing Expeditions: A Guide for System Designers
    *   4.3 Balancing Philosophy & Key Levers

**Part B: Technical Implementation Guide (The "How")**
5.  **System Architecture & Data Flow**
    *   5.1 System Responsibilities & Class Definitions
    *   5.2 Data Structures & Schemas (JSON)
6.  **Step-by-Step Implementation Roadmap (4 Weeks)**
    *   6.1 Week 1: Core Foundation, Data Schemas, and Manager Logic
    *   6.2 Week 2: Encounter Resolution Engine & Loot Generation
    *   6.3 Week 3: Final Resolution Logic & Full UI Implementation
    *   6.4 Week 4: Content Population, Simulation Tools, and Balancing
7.  **Detailed Logic Clarifications**
    *   7.1 Star Bonus Calculation and Application
    *   7.2 Affinity Conflict Resolution Protocol
    *   7.3 Loot Generation Logic & Table Structure
    *   7.4 Encounter Modifier Stacking Rules

---

## **Part A: Game Design & Mechanics (The "What" and "Why")**

### **1.0 High-Level Vision**

#### **1.1 Game Mode Concept**
The Expedition Protocol is a strategic, asynchronous, "fire-and-forget" idle game mode. Players dispatch teams of 1-4 characters on timed expeditions (ranging from 4 to 20 hours). The expedition's success and the value of its rewards are determined by a simulated journey through a series of **random, dynamic encounters**. These encounters can be standard skill checks, conditional gates, or events that alter the expedition's parameters mid-journey. Success is a function of strategic team-building to master an expedition's unique **Affinities** and a significant element of luck.

#### **1.2 Core Design Philosophy**
Our core philosophy is **"Calculated Risks, Not Guaranteed Outcomes."** This mode is designed to feel like a genuine expedition into the unknown.
*   **Player Agency:** The player's primary interaction is strategic team selection. A well-chosen team that counters the expedition's Affinities should feel powerful and intelligent.
*   **Embracing Randomness:** The system is built on multiple layers of RNG. This ensures high replayability and creates memorable "stories" where an underdog team might achieve a massive jackpot, or a powerful team might be undone by a series of unfortunate mishaps.
*   **Informative Failure:** Failure should not feel purely punitive. The post-expedition log is a key feature, designed to show the player *why* they failed (e.g., "Failed multiple INT checks," "Hit by a Mishap on a LCK check"), guiding them to better team compositions for future attempts.

#### **1.3 Player Experience Goals**
*   **Strategic Depth:** To create a "puzzle" for players to solve with their character roster before each expedition.
*   **Roster Diversity:** To make every character in a player's collection, regardless of their combat viability, potentially "best-in-slot" for a specific expedition, driving collection and broad investment.
*   **Meaningful Idle Content:** To provide a rewarding, low-effort activity that respects the player's time and provides valuable resources for the core game loop.
*   **Excitement & Unpredictability:** To make the results screen a moment of genuine anticipation.

### **2.0 Core Gameplay Loop & User Experience**

#### **2.1 The Four Phases**
1.  **Selection:** The player views a list of 3-5 available Expeditions from the main menu.
2.  **Dispatch:** The player selects an expedition and assembles a team.
3.  **Wandering (Idle):** The expedition timer runs down in the background. The expedition can be cancelled, but all resources and time are lost.
4.  **Reward:** The player claims their rewards and reviews the automatically generated expedition log.

#### **2.2 User Interface Mockup & Flow**
1.  **Expedition List Screen (`UI_ExpeditionList`)**
    *   A vertically scrolling list of available expeditions.
    *   Each list item will display:
        *   **Header:** Expedition Name (e.g., "The Sunken Temple")
        *   **Sub-header:** Duration (e.g., "12 Hours") and Difficulty (e.g., "Difficulty: 650")
        *   **Favored Affinities:** A row of icons with a green, glowing border (e.g., a Water Drop icon, a Sage Hat icon).
        *   **Disfavored Affinities:** A row of icons with a red, crossed-out border (e.g., a Konosuba series logo with a red X over it).
        *   **Potential Rewards:** Icons of 3-4 possible high-tier rewards to entice the player.
2.  **Team Selection Screen (`UI_TeamSelection`)**
    *   **Top Section:** A static display of the selected expedition's details and Affinities.
    *   **Middle Section:** Four empty character slots. Tapping a slot opens the character roster.
    *   **Bottom Section (Roster):** The player's character collection.
        *   **Dynamic Highlighting:** Characters matching a Favored Affinity will have a green border; those matching a Disfavored Affinity will have a red one.
        *   **Team Effectiveness Meter:** A prominent bar or gauge (0-100%) that fills as characters are added. This meter is a quick, visual representation of `(Total Favored Matches - Total Disfavored Matches) / Total Possible Matches`. It gives at-a-glance feedback without revealing the underlying complexity.
3.  **Results Screen (`UI_ExpeditionLog`)**
    *   **Header:** A large banner declaring the final outcome: "Jackpot!", "Standard Success", "Setback", or "Catastrophe!".
    *   **Log Window:** A scrollable text box. Each entry is a new line:
        *   `Encounter 1: A Rickety Bridge - SUCCESS! (+10 Loot Value)`
        *   `Event: A Sudden Downpour! Fire characters are now Disfavored.`
        *   `Encounter 2: A Mysterious Fog - MISHAP! (-5 Loot Value)`
    *   **Final Tally Section:**
        *   `Base Loot Value: 55`
        *   `Final Multiplier Roll: Setback (-25%)`
        *   `Final Loot Value: 41`
    *   **Item Display:** A grid showing the icons of all items generated by the `LootGenerator` from the final value.

### **3.0 The Expedition Engine: Detailed Mechanics**

#### **3.1 Expedition Generation & Dynamic Affinities**
*   **Expedition Templates:** The master list of all possible expeditions, defined in `expedition_templates.json`.
*   **Duration:** 4, 8, 12, 16, or 20 hours.
*   **Difficulty:** A numerical value from 0-1000. This directly impacts encounter difficulty and loot quality.
*   **Encounter Count:** Calculated upon dispatch. Formula: `Encounters = floor(DurationInHours * (1.5 + (random_float_0_to_1 * 0.5)))`. A 4-hour expedition will have 6-8 encounters.
*   **Dynamic Affinities:** At the start of each 24-hour cycle, the `ExpeditionManager` generates the player's list of expeditions. For each one, it randomly selects `num_favored_affinities` and `num_disfavored_affinities` from the `affinity_pools` in the template.
*   **Dynamic Encounter Tag Pool:** The `encounter_pool_tags` for a resolution instance are created dynamically. The system starts with the base tags from the template (e.g., `["ruins", "magic"]`) and then **appends the unique `series_id` of every character dispatched by the player**. This is a critical mechanic for series-specific content.

#### **3.2 The Encounter System & Chance Table**
**Encounter Types:**
*   **Standard (Skill Check):** A challenge against a random stat (`atk`, `int`, `lck`, etc.). The outcome is probabilistic.
*   **Gated (Conditional Check):** A binary pass/fail check for a specific trait (e.g., `series_id`, `archetype`).
*   **Boon (Dynamic Modifier):** An automatic success that adds a new temporary **Favored** Affinity for the rest of the journey.
*   **Hazard (Dynamic Modifier):** An automatic event that adds a new temporary **Disfavored** Affinity for the rest of the journey.

**Encounter Resolution & Loot Generation:**
1.  **Calculate Team Skill Score:**
    *   `Affinity Multiplier = 1.0 + (Total Favored Matches * 0.25) - (Total Disfavored Matches * 0.25)`. Clamped between `0.1` and `3.0`.
    *   `Stat Sum = Sum of the relevant stat from all team members (after Star Bonus is applied)`.
    *   `Final Score = Stat Sum * Affinity Multiplier`.
2.  **Calculate Success Threshold:** `Threshold = (Final Score / Encounter Difficulty)`.
3.  **Roll on the Chance Table:** A d100 (1-100) roll determines the outcome.

| Success Threshold | Great Success (d100) | Success (d100) | Failure (d100) | Mishap (d100) |
| :--- | :--- | :--- | :--- | :--- |
| **< 0.5** | 1-0 (0%) | 1-5 (5%) | 6-85 (80%) | 86-100 (15%) |
| **0.5 - 0.99**| 1-5 (5%) | 6-40 (35%) | 41-95 (55%) | 96-100 (5%) |
| **1.0 - 1.49** | 1-15 (15%) | 16-85 (70%) | 86-98 (13%) | 99-100 (2%) |
| **1.5 - 1.99** | 1-35 (35%) | 36-95 (60%) | 96-100 (5%) | 0% |
| **2.0+** | 1-60 (60%) | 61-100 (40%) | 0% | 0% |

4.  **Generate Loot Per Encounter:**
    *   **`Success`:** Call `LootGenerator(ExpeditionDifficulty, "common")`. Add result to Loot Pool.
    *   **`Great Success`:** Call `LootGenerator(ExpeditionDifficulty, "great")`. Add result to Loot Pool.
    *   **`Mishap`:** If Loot Pool is not empty, remove one random item.

#### **3.3 Final Reward Resolution: The Loot Multiplier**
1.  **Calculate Final Luck Score:** `Luck Score = (Team's Total LCK) + (Num Great Successes * 20) - (Num Mishaps * 40)`.
2.  **Roll on the Final Multiplier Table:** A d100 roll is made.

| Final Luck Score | **Catastrophe!** (-75% Loot) | **Setback** (-25% Loot) | **Standard** (No Change) | **Jackpot!** (+50% Loot) |
| :--- | :--- | :--- | :--- | :--- |
| **< 100 (Unlucky)** | 1-10 (10%) | 11-50 (40%) | 51-100 (50%) | 0% |
| **100 - 299 (Average)** | 1-5 (5%) | 6-25 (20%) | 26-90 (65%) | 91-100 (10%) |
| **300 - 499 (Lucky)** | 1 (1%) | 2-11 (10%) | 12-75 (64%) | 76-100 (25%) |
| **500+ (Extremely Lucky)**| 0% | 1-5 (5%) | 6-55 (50%) | 56-100 (45%) |

*   The modifier is applied to the **total number of items** in the final Loot Pool. `0.75 * 7 items = 5.25`, rounded down to 5 items.

---

## **Part B: Technical Implementation Guide (The "How")**

### **5.0 System Architecture & Data Flow**

#### **5.1 System Responsibilities**
1.  **`ExpeditionManager` (Stateful, Persistent System):**
    *   `available_expeditions`: A list of `Expedition` instances.
    *   `active_expeditions`: A dictionary mapping `slot_id` to `{ expedition_data, team_data, end_timestamp }`.
    *   `generate_available_expeditions()`: Called daily. Loops through templates, creates instances, and calls `randomize_affinities()` for each.
    *   `dispatch_expedition(expedition_id, team)`: Moves an expedition from available to active and sets a timer.
    *   `claim_reward(slot_id)`: Checks if the timer is done. If so, calls `ExpeditionResolver`, stores the result, and clears the slot.
2.  **`ExpeditionResolver` (Stateless Service/Function):**
    *   `resolve(expedition_data, team_data)`:
        1.  Create an empty `ExpeditionResult` object (to store log and loot).
        2.  Build the dynamic `encounter_pool_tags` list.
        3.  Loop `N` times for each encounter:
            *   Select a valid `Encounter` from the JSON data.
            *   Execute encounter logic based on its `type`.
            *   Update the `ExpeditionResult` log and Loot Pool.
        4.  Perform the Final Multiplier Roll.
        5.  Apply the final modifier to the Loot Pool.
        6.  Return the `ExpeditionResult`.
3.  **`LootGenerator` (Utility/Service):**
    *   `generate_loot(difficulty, success_level)`:
        *   Contains predefined `LootTable` objects.
        *   Selects the correct table based on difficulty (e.g., `loot_tables["tier_4_great"]`).
        *   Rolls on the table to generate and return a list of `Item` objects.

#### **5.2 Data Structures & Schemas (JSON)**

*   **/data/expeditions/expedition_templates.json**:
    ```json
    {
      "expedition_id": "ruins_of_the_wise_long",
      "name": "Deep Exploration of the Wise Ruins",
      "duration_hours": 12,
      "difficulty": 750,
      "num_favored_affinities": 3,
      "num_disfavored_affinities": 2,
      "affinity_pools": {
        "favored": { "archetype": ["Sage"], "genre": ["Mystery"] },
        "disfavored": { "series_id": [117223] }
      },
      "encounter_pool_tags": ["ruins", "magic", "rare", "boss"]
    }
    ```
*   **/data/expeditions/encounters.json**:
    ```json
    {
      "encounter_id": "enc_series_konosuba_001",
      "name": "A Horde of Giant Toads Appears!",
      "type": "STANDARD",
      "tags": ["68"],
      "description_success": "...",
      "check_stat": "lck",
      "difficulty": 300
    },
    {
      "encounter_id": "enc_gated_seal",
      "name": "An Ancient Magical Seal",
      "type": "GATED",
      "tags": ["ruins", "rare"],
      "condition": { "type": "elemental", "value": "void" }
    }
    ```

### **6.0 Step-by-Step Implementation Roadmap (4 Weeks)**

#### **6.1 Week 1: Core Foundation & Data**
*   **Tasks:**
    1.  Finalize and implement all JSON schemas in code as data classes/structs.
    2.  Implement the `ContentLoader` to parse these new JSON files.
    3.  Implement `ExpeditionManager`: class structure, properties, and the `generate_available_expeditions` logic including random affinity selection.
    4.  Implement `ExpeditionResolver`: class structure and the initial dynamic `encounter_pool_tags` generation.
    5.  Implement `calculate_team_skill_score` logic, including fetching character data and applying Star Bonuses.
    6.  **Unit Tests:** Verify `generate_available_expeditions` produces valid, randomized results. Verify `calculate_team_skill_score` is correct with multiple affinities.

#### **6.2 Week 2: Encounter Resolution & Loot**
*   **Tasks:**
    1.  Implement the Chance Table logic as a static method or dictionary lookup in `ExpeditionResolver`.
    2.  Build the main encounter loop within `ExpeditionResolver.resolve()`.
    3.  Implement the resolution logic for all four encounter types (`STANDARD`, `GATED`, `BOON`, `HAZARD`). This will be the most complex part of the week.
    4.  Implement a robust `LootGenerator` service with a clear structure for defining loot tables by tier and rarity.
    5.  Integrate `LootGenerator` calls into the encounter loop.
    6.  **Unit Tests:** Create tests for each encounter type. Test `GATED` with both passing and failing teams. Test that `BOON`/`HAZARD` correctly modify the affinity list for subsequent loops.

#### **6.3 Week 3: Final Resolution & UI**
*   **Tasks:**
    1.  Implement the `Final Luck Score` calculation and the `Final Multiplier Table` logic.
    2.  Implement the logic for applying the final multiplier to the Loot Pool.
    3.  Build the `UI_ExpeditionList` and `UI_TeamSelection` screens, including the real-time "Team Effectiveness" meter.
    4.  Build the `UI_ExpeditionLog` screen, ensuring it can parse and display the detailed log from the `ExpeditionResult`.
    5.  Connect the UI to the `ExpeditionManager` with API calls for dispatching and claiming.

#### **6.4 Week 4: Content Population & Balancing Tools**
*   **Tasks:**
    1.  **Content Entry:** This is a designer-heavy task. Populate the JSON files with a large and diverse set of expeditions and encounters, including many series-specific ones.
    2.  **Build Simulation Tool:** Create a command-line Python/Node.js script that:
        *   Takes an `expedition_id` and a list of `character_id`s as arguments.
        *   Runs the `ExpeditionResolver` 10,000 times with this input.
        *   Outputs aggregated results: average loot value, percentage of each encounter outcome, percentage of each final multiplier, etc.
    3.  **Balancing:** Use the tool to find and fix outliers. Is one expedition too rewarding? Is an encounter too punishing? Adjust `Difficulty` values until the system feels fair and rewarding.

### **7.0 Clarifications on Ambiguous Mechanics**

#### **7.1 Star Bonus Calculation and Application**
*   **Formula:** `Stat for Expedition = Base Stat * (1 + (Star Level - 1) * 0.10)`.
*   This calculation is the **very first step** before any other logic. The `ExpeditionResolver` should receive character stats that have already been pre-calculated with this bonus.

#### **7.2 Affinity Conflict Resolution Protocol**
*   Dynamic modifiers from **Boon/Hazard** encounters are absolute and temporary for that expedition only. If an expedition starts with "Favored: `fire`" and a Hazard adds "Disfavored: `fire`," the `Disfavored` status will be used for all subsequent checks in that journey. The `Affinity Multiplier` should be recalculated after each Boon/Hazard.

#### **7.3 Loot Generation Logic**
*   The `LootGenerator` must be a separate, stateless utility. This allows it to be used by other future game modes.
*   It should contain a dictionary of `LootTable` objects. Each table is a list of `(item_id, weight)`.
*   `generate_loot(difficulty, success_level)`:
    1.  `tier = floor(difficulty / 200) + 1` (e.g., Difficulty 0-199 is Tier 1, 200-399 is Tier 2).
    2.  `table_name = f"{success_level}_tier_{tier}"` (e.g., "great_tier_4").
    3.  Perform a weighted random roll on the selected table.
    4.  `Great Success` can be configured to grant multiple rolls (e.g., 3 rolls) while `Success` grants one.

#### **7.4 Encounter Modifier Stacking Rules**
*   `stat_bonus` / `stat_check_penalty` (from Boons/Hazards) are additive. If a team gets `+100 SPD` from one Boon and `-50 SPD` from a Hazard, the net effect is a `+50` bonus to all future SPD checks.
*   `difficulty_increase_percent`: These are multiplicative and stack. Two `+20%` difficulty hazards would result in `Difficulty * 1.2 * 1.2`.
*   `prevent_next_mishap`: This is a consumable flag. The first time a Mishap is rolled, the effect is nullified, and the boon is removed.