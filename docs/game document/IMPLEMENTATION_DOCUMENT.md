## **Project Implementation Guide: Anime Character Auto-Battler**

### **Guiding Principles for Development**

*   **Data First:** For each feature, define the JSON data structure first, then write the code that uses it.
*   **Test As You Go:** After implementing a new system (e.g., the `TurnSystem`), write a simple integration test to ensure it works before moving on.
*   **Decouple Everything:** No system should ever call another system's methods directly. All communication *must* go through the `EventBus`.

---

### **Phase 1: Core Framework (Weeks 1-3)**

**Goal:** To create the foundational "scaffolding" of the battle system. By the end of this phase, we will be able to programmatically create a battle, populate it with characters built from data, and have the systems for communication and state management in place. No actual "gameplay" will exist yet.

#### **Week 1: Data Structures & The Core Context**
*   **Objective:** Define the fundamental data containers.
*   **Tasks:**
    1.  **Create the `core/` directory.**
        *   `battle_context.py`: Define a `BattleContext` class. For now, it only needs to hold `team_one: list`, `team_two: list`, and `round_number: int`.
    2.  **Create the `components/` directory.**
        *   `base_component.py`: Define an abstract `Component` base class.
        *   `state_component.py`: Define `StateComponent`. It should hold `current_hp: int`, `max_hp: int`, `action_gauge: int`, and `is_alive: bool`.
        *   `stats_component.py`: Define `StatsComponent`. It should hold dictionaries for `base_stats` and `modified_stats`. Add a method `get_stat(stat_name)` that, for now, just returns the base stat.
    3.  **Define the `Character` Entity.**
        *   Create a simple `Character` class. It should have a `character_id` and a dictionary of `components`.
    4.  **Define Initial Data Schemas (`data/`).**
        *   Create a `character_data.json` file. Define a schema for a single character: `id`, `name`, and `base_stats` (`hp`, `atk`, `mag`, etc.).
        *   Create a simple `ContentLoader` that can read this one JSON file and store its contents in a dictionary.

#### **Week 2: The Event Bus & Basic Communication**
*   **Objective:** Implement the central nervous system.
*   **Tasks:**
    1.  **Implement `event_system.py`:**
        *   Create an `EventBus` class.
        *   Implement `subscribe(event_name, handler_function)`. A simple dictionary where keys are event names and values are lists of handler functions is sufficient.
        *   Implement `publish(event_name, data_payload)`. This method should loop through all subscribed handlers for the given event and call them with the `data_payload`.
    2.  **Create a Test Harness:**
        *   Write a script that creates a `BattleContext` and its own `EventBus`.
        *   Create a dummy handler function `on_test_event(data): print(f"Event received: {data}")`.
        *   Subscribe this handler to a `"TEST_EVENT"`.
        *   Publish a `"TEST_EVENT"` with some sample data to confirm the handler is called. This validates that the core communication loop works.

#### **Week 3: Registries & Character Assembly**
*   **Objective:** Connect the static data to live, in-game objects.
*   **Tasks:**
    1.  **Expand the `core/` Registries:**
        *   Flesh out the `ContentLoader` to read all JSON types (skills, effects, synergies).
        *   Create registries (simple dictionary-based singletons) to hold this loaded data: `SkillRegistry`, `EffectRegistry`, `CharacterDataRegistry`, etc.
    2.  **Create a `CharacterFactory`:**
        *   This factory will have one primary method: `create_character(character_id, team, position)`.
        *   This method will:
            1.  Look up the character's base data from the `CharacterDataRegistry`.
            2.  Instantiate a new `Character` entity.
            3.  Create and attach all necessary components (`StatsComponent`, `StateComponent`, etc.), populating them with the base data.
    3.  **Refine Battle Setup:**
        *   Create a `BattleSetup` class that takes two lists of character IDs.
        *   It should use the `CharacterFactory` to create all 12 character objects and add them to a new `BattleContext`.

---

### **Phase 2: Battle Systems (Weeks 4-6)**

**Goal:** To implement a minimal, functioning battle loop. Characters will take turns, use basic attacks, and affect each other's HP. The game will be "playable" by the engine, if not yet strategic.

#### **Week 4: The Turn System & Game Clock**
*   **Objective:** Make time pass and turns happen in the correct order.
*   **Tasks:**
    1.  **Implement `turn_system.py`:**
        *   Create a `TurnSystem` class that takes a `BattleContext` and `EventBus` on initialization.
        *   Implement a `tick()` method. This method will:
            *   Loop through every living character in the `BattleContext`.
            *   Get their `spd` from their `StatsComponent`.
            *   Add this value to the `action_gauge` in their `StateComponent`.
        *   Implement a `check_for_next_turn()` method that finds the character with the highest Action Gauge >= 1000.
    2.  **Integrate with the Battle Loop:**
        *   Create a main `Battle` class that contains the primary `while (is_battle_active)` loop.
        *   Inside the loop, it calls `TurnSystem.tick()` and `TurnSystem.check_for_next_turn()`.
        *   When a turn is ready, publish the `OnTurnStart` event. After the (currently empty) action phase, publish `OnTurnEnded`.

#### **Week 5: Basic Combat & AI**
*   **Objective:** Implement the ability for one character to affect another.
*   **Tasks:**
    1.  **Implement `combat_system.py`:**
        *   Create a `CombatSystem` class.
        *   Implement a `resolve_action(action)` method.
        *   For now, make it simple: look up the skill's base power, subtract it from the target's `current_hp`, and publish the `HPChanged` event.
    2.  **Implement a Placeholder `ai_system.py`:**
        *   Create an `AI_System` class.
        *   Implement a `choose_action(character)` method.
        *   Logic:
            1.  Get a list of all enemies from the `BattleContext`.
            2.  Pick a random enemy as the target.
            3.  Pick the character's first available skill.
            4.  Return an `ActionCommand` object.
    3.  **Connect the Loop:** In the main `Battle` loop, after `OnTurnStart`, call the `AI_System` to get an action, then pass that action to the `CombatSystem` to be resolved.

#### **Week 6: Effects & Components V2**
*   **Objective:** Introduce the first real status effect and make stats dynamic.
*   **Tasks:**
    1.  **Create the `effects/` directory and `base_effect.py`.**
    2.  **Implement the first effect:**
        *   `stat_modifier.py`: Create a `StatModifierEffect` class. It should store a `stat_to_modify`, a `value`, a `duration`, and whether it's a `flat` or `percentage` modifier.
    3.  **Upgrade `effects_component.py`:**
        *   Implement `add_effect(effect)` and `remove_effect(effect)` methods.
        *   Add a method that is subscribed to the `OnTurnStart` event to tick down the duration of its active effects.
    4.  **Upgrade `stats_component.py`:**
        *   Modify the `get_stat(stat_name)` method. It should now:
            1.  Start with the `base_stat`.
            2.  Get all active stat-modifying effects from its character's `EffectsComponent`.
            3.  Apply all additive bonuses, then all multiplicative bonuses.
            4.  Return the final, modified value. This makes buffs and debuffs functional.

---

### **Phase 3: Advanced Systems & Features (Weeks 7-9)**

**Goal:** To implement the complex, game-defining mechanics from the GDD. By the end of this phase, the game will be feature-complete.

#### **Week 7: Full Combat & Status Effects**
*   **Objective:** Implement the final combat formulas and common status effects (DoTs/HoTs).
*   **Tasks:**
    1.  **Refactor `CombatSystem`:**
        *   Replace the simple damage logic with the full Universal Scaling Formula (GDD 6.1-6.3).
        *   Integrate the `PreProcess_DamageCalculation` and `PostProcess_DamageCalculation` hooks at the correct points in the formula.
    2.  **Implement `damage_over_time.py`:**
        *   Create the `DamageOverTimeEffect` class. Its core logic will be a handler that subscribes to the `OnTurnStart` event and applies damage when triggered.
    3.  **Data Implementation:**
        *   Create the JSON definitions for skills like "Bleeding Strike" and "Ignite" and effects like "Bleed" and "Burn."
        *   Test that using the skill correctly applies the effect, which then correctly deals damage on the target's next turn.

#### **Week 8: Advanced AI & Signature Abilities**
*   **Objective:** Make the AI intelligent and implement the most exciting character abilities.
*   **Tasks:**
    1.  **Implement Full `AI_System` Logic:**
        *   Build out the Role Selection and Target Priority Score (TPS) systems. This involves significant querying of the `BattleContext`.
    2.  **Signature Ability Framework:**
        *   Add a `primed_skill` field to the `StateComponent`.
        *   In the `AI_System`, the first step will be to check if `primed_skill` is set. If it is, that skill is used immediately, overriding all other logic.
        *   Create effect templates for the Signature triggers (e.g., an effect that listens for `HPChanged` for Megumin, or `AttackDodged` for Yor). When triggered, these effects set the `primed_skill` on the character.

#### **Week 9: Global Rules & Synergies**
*   **Objective:** Implement battle-wide modifiers.
*   **Tasks:**
    1.  **Implement `rule_engine.py`:**
        *   The `RuleEngine` will be a global system that other systems query.
        *   For example, the `CombatSystem` will ask `RuleEngine.get_critical_multiplier()` instead of using a hardcoded `1.5`.
    2.  **Implement Battlefield Conditions:**
        *   Create a `RuleModificationEffect`. When a battle starts, the active condition creates these effects and registers them with the `RuleEngine`, changing the base rules of the fight.
    3.  **Implement Team Synergies:**
        *   At `BattleStarted`, a `SynergySystem` checks team composition and applies the appropriate permanent effects to the characters (e.g., adding a permanent `StatModifierEffect` for the K-On! speed bonus).

---

### **Phase 4 & 5: Content, Polish & Tools (Weeks 10-13)**

**Goal:** To transform the feature-complete engine into a full-fledged, balanced, and debuggable game.

#### **Weeks 10-11: Full Content Implementation**
*   **Objective:** Populate the game with all characters, skills, and passives from the design documents.
*   **Tasks:**
    1.  **Data Entry:** This is a major, non-coding task. Go through the GDD and `characters.csv` and create the JSON definition for every single character, skill, signature passive, and synergy.
    2.  **Initial Validation:** As data is entered, run simple battle simulations with new characters to ensure their skills and stats are being loaded and executed correctly. Look for obvious errors or crashes.

#### **Week 12: Testing, Validation & Balancing**
*   **Objective:** Hunt for bugs and begin the balancing process.
*   **Tasks:**
    1.  **Write Integration Tests:** Create test scripts for specific, complex interactions. For example, a test where Homura's Time Loop is triggered by an attack that also applies a DoT, and verify that the DoT is correctly removed after the state rollback.
    2.  **Statistical Analysis:** Create a script that can run a specific matchup 10,000 times and log the results (win rates, average damage per character, etc.). Use this data to provide balance feedback to the design team.

#### **Week 13: Developer Tools & Final Polish**
*   **Objective:** Build tools to make future development and debugging easier.
*   **Tasks:**
    1.  **Create a Battle Logger:** Enhance the `EventBus` to log every event published and its payload to a text file. This is the single most valuable debugging tool you can build.
    2.  **Create a State Inspector:** Build a simple tool that can pause a battle simulation at any point and print the complete state of the `BattleContext`, including every character's stats, active effects, and action gauge.
    3.  **Code Cleanup:** Refactor any placeholder code, add comments, and ensure the codebase is clean and well-documented for future expansion.