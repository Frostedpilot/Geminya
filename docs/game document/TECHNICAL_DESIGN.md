# **Technical Design Document: Anime Character Auto-Battler**
**Version: Final**

## **1.0 Core Architecture Philosophy: The Three Pillars**

This architecture is built on three foundational pillars that ensure maximum extensibility, maintainability, and the ability to handle complex ability interactions. Every other system serves or utilizes these core components.

#### **1.1 The `BattleContext`: The Single Source of Truth**
The `BattleContext` is the central state container for a single, active battle. It holds the "game board" and knows the current state of everything: which characters are on which team, their positions, the current round number, and the active Battlefield Condition. It is the definitive source of information that other systems query to make decisions. It contains no game logic itself, only state.

#### **1.2 The `EventBus`: The Central Nervous System**
The `EventBus` is the game's communication backbone. Systems do not talk directly to one another; instead, they publish events (e.g., `OnTurnStart`, `OnHPChanged`) to the bus. Other systems, character passives, and status effects subscribe to these events to trigger their logic. This decoupling is the key to our architecture, allowing us to add complex, reactive abilities (like Signature Skills) without ever modifying the original system that fired the event. The "Hooks" described in this document are the specific, named events the bus can broadcast.

#### **1.3 The Component-Based Character: The Dynamic Actor**
A "Character" is not a monolithic object. It is a simple container entity for various modular **Components**. This is crucial for runtime flexibility. A character *is* a collection of a `StatsComponent`, `EffectsComponent`, an `AbilitiesComponent`, and a `StateComponent`. All buffs, debuffs, and status effects work by adding or altering data within these components, which the core game systems then read from.

---

## **2.0 The Anatomy of an Action: A Turn's Lifecycle**

To understand how the systems interact, we can follow the logical flow of a single character's turn from its beginning to its end. This sequence demonstrates the handoff of control from one system to the next.

1.  **TICK (`TurnSystem`)**: The main `Battle` loop calls the `TurnSystem.tick()` method. The `TurnSystem` gets each character's current `spd` from their `StatsComponent` and adds it to the Action Gauge in their `StateComponent`.

2.  **TURN SELECTION (`TurnSystem`)**: The `Battle` loop asks the `TurnSystem.get_active_character()` for the next character to act. The `TurnSystem` identifies the character with an Action Gauge >= 1000 and returns them.

3.  **TURN START (`EventBus`)**: The `TurnSystem` publishes an `OnTurnStart` event. The Active Character's `EffectsComponent` catches this and applies turn-based effects like Bleed, Regen, and counts down all status effect durations.

4.  **AI DECISION (`AI_System`)**: The `Battle` loop passes control to the `AI_System`, calling `choose_action()`. The AI queries the `BattleContext` for a complete snapshot of the battlefield, runs its Three-Phase logic (Role -> Skill -> Target), and returns a complete `ActionCommand` object.

5.  **ACTION EXECUTION (`CombatSystem`)**: The `Battle` loop sends the `ActionCommand` to the `CombatSystem`. The `CombatSystem` resolves the action, running through its internal pipeline of hooks (Pre-Process, Post-Process) to allow effects to modify the outcome. It applies the final damage/healing and publishes result events like `HPChanged` and `EffectApplied`.

6.  **RESOLUTION (`VictorySystem`)**: The `VictorySystem`, which is subscribed to the `CharacterDefeated` event, receives the signal from the `EventBus` if a character was defeated. It then checks the `BattleContext` to see if a team has been wiped out, ending the battle if necessary.

7.  **TURN END (`EventBus`)**: If the battle continues, the `TurnSystem` publishes a `TurnEnded` event. This is caught by the Active Character's `EffectsComponent` to clean up any temporary effects. The `Battle` loop is now ready for the next tick.

---

## **3.0 Module & System Architecture**

The project is structured into distinct modules, each with a clear responsibility.

```
src/game/
├── core/                     # Core architectural pillars
│   ├── battle_context.py     # Central state manager (The Board)
│   ├── event_system.py       # Event bus and handlers (The Nervous System)
│   ├── rule_engine.py        # Dynamic game rule management for global effects
│   └── effect_registry.py    # Global cache for loaded effect templates
├── components/               # Building blocks of a Character
│   ├── stats_component.py    # Manages base and modified stats
│   ├── effects_component.py  # Manages active buffs/debuffs
│   ├── abilities_component.py # Manages skills and cooldowns
│   └── state_component.py    # Tracks position, action gauge, life status
├── systems/                  # Core gameplay logic managers
│   ├── turn_system.py        # Manages the Action Gauge and battle timeline
│   ├── ai_system.py          # Implements GDD decision-making logic
│   ├── combat_system.py      # Resolves all actions (damage, healing, effects)
│   └── victory_system.py     # Checks for win/loss conditions
├── effects/                  # Concrete implementations of effect templates
│   ├── base_effect.py        # Abstract effect interface
│   ├── stat_modifier.py      # Class for effects that change stats
│   ├── damage_over_time.py   # Class for Bleed/Burn effects
│   └── rule_modification.py  # Class for effects that alter core rules
└── data/                     # Data-driven content (editable by designers)
    ├── skill_definitions/    # JSON skill configurations
    ├── effect_library/       # JSON reusable effect templates
    └── synergy_definitions/  # JSON series synergy configurations
```
---

## **4.0 The Event & Hook System**

The `EventBus` forms the core of the game's interactivity. "Hooks" are the specific, named events that systems publish, which effects can subscribe to. The following hooks are critical for implementing the GDD.

| Event Hook Name | Purpose | Example GDD Triggers |
| :--- | :--- | :--- |
| **`BattleStarted`** | Apply all initial, one-time effects at the start of combat. | Leader Buffs, Team Synergies, Battlefield Conditions. |
| **`RoundEnded`** | Trigger logic based on the passing of a full round-equivalent. | "Sudden Death" activation, K-On! Tier 3 Regen. |
| **`TurnStarted`** | Primary trigger for turn-based status effects. | Applying Bleed/Burn damage, counting down Stun duration. |
| **`PreProcess_Action`** | Intercept an action *before* any calculations. | Checking for "Silence" to prevent a skill, "Primed" Signature Skills overriding the AI's choice. |
| **`PostProcess_Damage`**| Modify a calculated damage value *before* it is applied. | Critical Hit multiplier, Barrier absorption, Elemental Modifiers. |
| **`PostProcess_Heal`** | Modify a calculated heal value *before* it is applied. | Buffs that increase "incoming healing." |
| **`HPChanged`** | React to any change in a character's health. | Megumin's "Explosion," Re:Zero's "survive at 1 HP" synergy. |
| **`CharacterDefeated`**| Trigger effects specifically upon a character's death. | Aqua's "God's Blessing," Victory condition checks. |
| **`AttackDodged`** | Trigger effects when a character successfully dodges an attack. | Yor Forger's "Thorn Princess." |
| **`EffectApplied`** | React to a character gaining a new buff or debuff. | A passive that cleanses a debuff whenever the character is buffed. |
| **`TurnEnded`** | Cleanup actions and effects that last until the next turn. | Removing "Guard Stance," applying skill cooldowns. |

---

## **5.0 Data-Driven Content Pipeline**

The game's content (skills, effects, etc.) is entirely decoupled from its code via JSON templates. This empowers designers to balance, create, and modify gameplay without requiring engineering changes.

#### **5.1 Unified Effect Template (`/data/effect_library/`)**
The backbone for all statuses, passives, and rule modifications.

```json
{
  "template_id": "unique_effect_name",
  "name": "Player-Facing Name",
  "type": "EFFECT_TYPE", // STAT_MODIFIER, DAMAGE_OVER_TIME, RULE_MODIFICATION, RESTRICTION
  "hook": "EventBusHookName", // e.g., "OnTurnStart", "OnHPChanged"
  "duration": {
    "type": "turns" | "rounds" | "permanent",
    "value": 2
  },
  "tags": ["buff" | "debuff", "dot", "control"],
  "stacking": { "type": "refresh" | "stack_intensity", "max_stacks": 3 },
  "parameters": {
    // Parameters vary based on the effect "type"
    "stat": "atk", "modifier": "percentage", "value": 0.20
  },
  "conditions": [ // Optional conditions for the effect to trigger
    { "type": "hp_threshold", "target": "self", "operator": "less_than", "value": 0.5 }
  ]
}
```

#### **5.2 Skill Template (`/data/skill_definitions/`)**
Defines a character's usable action.

```json
{
  "skill_id": "heavy_slam",
  "name": "Heavy Slam",
  "potency_type": "Attacker",
  "description": "Deals 150% ATK damage. The user's SPD is halved next round.",
  "cooldown": 1,
  "skill_tags": ["physical", "single_target", "self_debuff"],
  "targeting": {
    "scope": "enemy",
    "pattern": "single",
    "valid_rows": ["front"]
  },
  "scaling_params": {
    "primary_stat": "atk",
    "multiplier": 1.5,
    "power_weight": 15,
    "floor": 40, "sc1": 80, "sc2": 300, "post_cap_rate": 0.6
  },
  "effects": [], // Effects applied to targets
  "self_effects": [ // Effects applied to the caster
    { "template_id": "stat_mod_spd_down_50p", "duration": 1 }
  ]
}
```

---

## **6.0 Specialized Systems Deep Dive**

#### **6.1 Combat Resolution Pipeline**
The `CombatSystem` follows a strict, event-driven pipeline to ensure all modifiers are applied in the correct order:
1.  **Publish `PreProcess_Action` Hook**: Check for action cancellations (Stun).
2.  **Publish `PreProcess_DamageCalculation` Hook**: Apply modifiers to input stats (Armor Break).
3.  **Calculate Initial Damage**: Use the GDD's Potency Value formulas.
4.  **Apply Universal Scaling Formula**: Use the skill's unique `scaling_params`.
5.  **Publish `PostProcess_DamageCalculation` Hook**: Apply modifiers to the final number (Critical Hits, Barriers).
6.  **Apply Final Damage/Healing**: Change the target's `current_hp`.
7.  **Publish Result Hooks**: `HPChanged`, `EffectApplied`, etc.

#### **6.2 AI Decision Logic**
The `AI_System` makes intelligent, context-aware decisions by:
1.  **Querying `BattleContext`**: Gathers a complete understanding of the current game state.
2.  **Evaluating Dynamic Weights**: Modifies the base `potency` of its roles based on the situation (e.g., heavily weighting "Healer" when an ally is low on health).
3.  **Calculating Target Priority**: Uses the GDD's TPS formulas to find the optimal target for the chosen skill, focusing on low-health enemies for attacks or high-value allies for buffs.

---

## **7.0 Performance & Scalability**

*   **Lazy Evaluation & Caching**: Character stats are recalculated only when a relevant modifier changes and the result is cached.
*   **Object Pooling**: Temporary objects (event payloads, short-term effects) are recycled to minimize garbage collection.
*   **Efficient Event Handling**: The `EventBus` uses a direct mapping system to notify only relevant subscribers, avoiding unnecessary checks.

---

## **8.0 Testing Framework**

*   **Unit Tests**: Each `Component` and `System` will be tested in isolation.
*   **Integration Tests**: Full, scripted battle simulations will verify complex chains of events and interactions.
*   **Balance Testing**: Monte Carlo simulations will run thousands of battles to gather statistical data on win rates and ability performance to inform game balancing.

---

## **9.0 Implementation Roadmap**

The project will be built in four distinct phases over approximately 12-14 weeks.

*   **Phase 1: Core Framework (3-4 weeks)**
    *   **Goal:** Build the architectural skeleton.
    *   **Deliverables:** `BattleContext`, `EventBus`, `Component` system, `ContentLoader`, and `CharacterFactory`.

*   **Phase 2: Battle Systems (3-4 weeks)**
    *   **Goal:** Create a minimal, functional battle loop.
    *   **Deliverables:** `TurnSystem`, a basic `CombatSystem`, a placeholder `AI_System`, and functional stat-modifying effects.

*   **Phase 3: Advanced Features & AI (2-3 weeks)**
    *   **Goal:** Implement the game-defining mechanics.
    *   **Deliverables:** Full GDD combat formulas, advanced status effects (DoTs, Control), the complete `AI_System`, `RuleEngine` for global conditions, and the Signature Skill framework.

*   **Phase 4: Content, Polish & Tools (2-3 weeks)**
    *   **Goal:** Populate the game and create tools for iteration.
    *   **Deliverables:** All characters, skills, and synergies implemented as data; a comprehensive suite of tests; and essential developer tools like a Battle Logger and State Inspector.