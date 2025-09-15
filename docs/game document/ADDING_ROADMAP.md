### **Roadmap: Adding a New Ability**

This process is broken into four phases: Conception, Implementation, Integration, and Validation. The key is to determine early on if the new ability can be built using existing tools (a "Data-Only" task) or if it requires new code (a "Developer Task").

### **Phase 0: Conception & Design (Designer)**

*Before writing any code or data, the ability must be fully defined on paper.*

1.  **Define the Core Concept:**
    *   **Name & Flavor:** What is the ability called? What is its theme? (e.g., "Chains of Stasis").
    *   **Player-Facing Description:** What does the player read? (e.g., "Deals a small amount of Void damage and has a 50% chance to apply 'Stun' for 1 turn.")

2.  **Define the Mechanics:** Break the ability down into its fundamental parts.
    *   **Damage/Heal:** Does it deal damage? How much? What type? How does it scale?
    *   **Status Effects:** Does it apply any buffs or debuffs? What are their names, durations, and effects?
    *   **Triggers & Conditions (for Passives/Signatures):** When does this happen? (e.g., "At the start of the turn," "When an ally is healed," "If the character's HP is below 30%").

3.  **The Critical Question: Does a template for this mechanic already exist?**
    *   Review the `effect_library/` and existing skills.
    *   Does it just modify stats? -> Use a `StatModifierEffect` template.
    *   Does it deal damage over time? -> Use a `DamageOverTimeEffect` template.
    *   Does it prevent an action? -> Use a `RestrictionEffect` template with a "Silence" tag.
    *   Does it trigger on a common hook (`OnTurnStart`, `OnHPChanged`, etc.)?

    If the answer to these questions is "yes," proceed to **Phase 1: Scenario A**.
    If the ability requires a fundamentally new mechanic (e.g., "Reflects the next debuff applied back to its caster") or a new trigger condition (e.g., "When an ally's Action Gauge reaches 1000"), a developer is needed. Proceed to **Phase 1: Scenario B**.

---

### **Phase 1: Implementation (Designer or Developer)**

#### **Scenario A: Data-Only Implementation (Designer's Workflow)**

*This is the most common path, used when the ability is a new combination of existing mechanics.*

1.  **Create/Define Effect Templates (if needed) in `effect_library.json`:**
    *   Even if the core effect *type* exists, you may need a new template for a unique version. For "Chains of Stasis," you would check if a "Stun" effect template exists. If not, you'd add one:
        ```json
        {
          "template_id": "stun_effect_1t",
          "name": "Stun",
          "type": "RESTRICTION",
          "hook": "PreProcess_Action",
          "parameters": {
            "restriction": "cannot_act"
          },
          "tags": ["debuff", "control"]
        }
        ```

2.  **Create the Skill Definition in `skill_definitions.json`:**
    *   This is the main step. You assemble the skill by referencing the effect templates.
        ```json
        {
          "skill_id": "chains_of_stasis",
          "name": "Chains of Stasis",
          "potency_type": "Mage",
          "parameters": {
            "target": "single_enemy",
            "damage_multiplier": 0.40,
            "damage_type": "void"
            // ... scaling parameters from GDD ...
          },
          "effects": [
            {
              "template_id": "stun_effect_1t",
              "duration": 1,
              "apply_chance": 50 // The skill handles the application chance
            }
          ]
        }
        ```
    *   **For a Passive:** A passive is just an effect that is applied at `BattleStarted`. You would create an effect template and add its ID to the character's data file.

#### **Scenario B: New Code Implementation (Developer's Workflow)**

*This path is taken when a truly novel mechanic is required.*

1.  **Identify the Missing Piece:** Determine if you need a new **Hook**, a new **Effect Class**, or both. Let's imagine a new skill: "Mana Burn - Drains 10% of the target's max mana." *Our game doesn't have a mana system yet.*

2.  **Step 1: Create the Hook (If Needed):**
    *   Our existing hooks don't cover mana. We need a new component (`ManaComponent`) and a new hook.
    *   In the `CombatSystem`, after damage is applied, you would add: `self.event_bus.publish('OnManaChanged', { target: target, amount: -mana_drained })`. This creates the new hook that other effects can now listen for.

3.  **Step 2: Create the New Effect Class in `src/game/effects/`:**
    *   Create `mana_drain_effect.py`.
    *   Define a `ManaDrainEffect(BaseEffect)` class.
    *   Its `apply()` method will contain the core logic:
        *   Access the target's `ManaComponent`.
        *   Calculate the 10% mana drain.
        *   Reduce the target's current mana.
        *   Publish the `OnManaChanged` event.

4.  **Step 3: Create the JSON Template for the Designer:**
    *   In `effect_library.json`, create the template the designer will use.
        ```json
        {
          "template_id": "mana_burn_10_percent",
          "name": "Mana Burn",
          "type": "MANA_DRAIN", // The new type the factory will recognize
          "hook": "OnDamageDealt", // Triggers after damage is done
          "parameters": {
            "drain_percent": 0.10
          },
          "tags": ["debuff"]
        }
        ```
    *   The developer must now update the `EffectFactory` to recognize `"type": "MANA_DRAIN"` and instantiate the new `ManaDrainEffect` class.

---

### **Phase 2: Integration (Designer)**

*Once the skill and its effects are defined (either by data or new code), it needs to be attached to a character.*

1.  **For a General Skill:**
    *   Open the `characters_with_stats_for_llm.csv` (or the character database).
    *   Add the `skill_id` (e.g., "chains_of_stasis") to the library of skills available to the appropriate character archetypes (e.g., Debuffers).

2.  **For a Signature Skill or Passive:**
    *   Open the character database.
    *   Add the skill/effect `template_id` to the character's specific `signature_skill` or `signature_passive` field.
    *   The `CharacterFactory` will be programmed to automatically apply signature passives at `BattleStarted` and to check for signature skill triggers.

---

### **Phase 3: Validation & Balancing (Designer & QA)**

*No ability is complete until it's tested and balanced.*

1.  **Unit Test (Developer Task, for Scenario B only):**
    *   If a new `Effect` class was created, a unit test must be written for it to confirm its logic works in isolation.

2.  **Integration Test (Designer/QA Task):**
    *   Use a debug battle tool to create a controlled scenario.
    *   **Setup:** Create a battle with the character who has the new ability against a stationary test dummy.
    *   **Execution:** Force the character to use the new skill.
    *   **Verification:** Check the battle log to confirm:
        *   Did the damage calculate correctly?
        *   Was the "Stun" effect applied to the target's `EffectsComponent`?
        *   On the target's next turn, did the `OnTurnStart` hook correctly prevent them from acting?
        *   Did the "Stun" effect's duration correctly decrease to 0 and get removed on their next turn?

3.  **Balance Test (Designer Task):**
    *   Add the new skill to the AI's possible choices.
    *   Run large-scale Monte Carlo simulations (e.g., 10,000 automated battles) of common team compositions with and without the new ability.
    *   Analyze the data. Did the win rate of the character with the new skill skyrocket? Is the skill being used too often or too rarely by the AI?
    *   Adjust the skill's power, cooldown, or the AI's `Power Weight` in the JSON files based on the results. Repeat until the ability feels powerful but fair.