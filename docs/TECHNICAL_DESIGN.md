# Technical Design Document: Anime Character Auto-Battler

## System Architecture for Extensible Auto-Battler

## 1. Core Design Philosophy

### 1.1 Extensibility Principles

- **Event-Driven Architecture**: All game actions trigger events that effects can intercept
- **Component-Based Design**: Characters are compositions of modular, replaceable components
- **Strategy Pattern**: Skills and effects use pluggable implementations
- **Observer Pattern**: Global systems observe and react to state changes
- **Command Pattern**: All actions are commands that can be modified, queued, or cancelled

### 1.2 Expandability Goals

The system must support complex skills/passives that can:

- Modify multiple game systems simultaneously
- Change fundamental battle rules (turn order, damage calculation, etc.)
- Create persistent effects that outlast their source
- Interact with and modify other skills/effects
- Scale to hundreds of unique abilities without performance degradation

## 2. Module Structure

```
src/game/
├── core/                     # Core battle systems
│   ├── battle_context.py     # Central state manager
│   ├── event_system.py       # Event bus and handlers
│   ├── effect_registry.py    # Global effect management
│   └── rule_engine.py        # Dynamic game rule management
├── components/               # Character component system
│   ├── stats_component.py    # Dynamic stat calculations
│   ├── effects_component.py  # Active effects management
│   ├── abilities_component.py # Skill availability & cooldowns
│   └── state_component.py    # Character state tracking
├── systems/                  # Core game logic systems
│   ├── turn_system.py        # Action gauge & turn processing
│   ├── combat_system.py      # Damage/healing resolution
│   ├── ai_system.py          # Decision making engine
│   └── victory_system.py     # Win condition evaluation
├── effects/                  # Effect implementation framework
│   ├── base_effect.py        # Abstract effect interface
│   ├── modifiers/            # Stat/calculation modifiers
│   ├── triggers/             # Event-based triggers
│   ├── rules/                # Game rule modifications
│   └── complex/              # Multi-system effects
├── data/                     # Data-driven content
│   ├── skill_definitions/    # JSON skill configurations
│   ├── effect_library/       # Reusable effect templates
│   └── expansion_hooks/      # Plugin registration points
└── plugins/                  # Hot-loadable extensions
  ├── rule_mods/            # Game rule modifications
  └── ai_behaviors/         # Custom AI strategies
```

## 3. Event-Driven Battle System

### 3.1 Central Event Bus

**Core Architecture:**

- All game actions publish events to a central bus
- Effects register handlers for specific event types
- Events carry immutable context data
- Handlers can modify event outcomes through return values

**Event Categories:**

**Battle Flow Events:**

- `BattleInitiated`, `BattleCompleted`
- `RoundStarted`, `RoundEnded`
- `TurnStarted`, `TurnEnded`

**Action Events:**

- `ActionQueued`, `ActionExecuting`, `ActionResolved`
- `SkillActivated`, `SkillResolved`
- `EffectApplied`, `EffectExpired`

**State Change Events:**

- `StatModified`, `HPChanged`
- `StatusApplied`, `StatusRemoved`
- `PositionChanged`, `CharacterDefeated`

**Combat Events:**

- `DamageCalculated`, `DamageDealt`
- `HealingCalculated`, `HealingApplied`
- `CriticalHit`, `AttackDodged`

### 3.2 Effect Hook System

**Hook Registration:**
Effects register for specific events with priority levels and execution conditions.

**Hook Types:**

- `PreProcess`: Modify inputs before calculations
- `PostProcess`: Modify outputs after calculations
- `OnEvent`: React to specific events
- `Continuous`: Persistent effects during battle
- `Conditional`: Context-dependent activation

**Priority and Execution:**

- Priority levels: 0-1000 (higher = earlier execution)
- Same priority = registration order
- Some effects can force specific execution timing
- Circular dependency detection prevents infinite loops

## 4. Component-Based Character System

### 4.1 Character Composition

Characters are assembled from independent components that can be dynamically modified:

**StatsComponent:**

- Base stats from character definition
- Dynamic modifiers from active effects
- Layered calculation system (base → equipment → passives → temporary → caps)
- Percentage vs flat modifications with proper stacking

**EffectsComponent:**

- Registry of active status effects
- Effect interaction rules (stacking, replacement, immunity)
- Duration tracking and expiration handling
- Effect priority and application order

**AbilitiesComponent:**

- Available skills with usage tracking
- Cooldown management per skill
- Dynamic skill modification (cost changes, effect changes)
- Skill replacement and addition from effects

**StateComponent:**

- Battle position and movement capabilities
- Action gauge and turn tracking
- Signature ability states
- Combat history for AI decisions

### 4.2 Dynamic Stat Calculation

**Layered Calculation System:**

1. **Base Layer**: Character's fundamental stats
2. **Equipment Layer**: Gear modifications (future expansion)
3. **Passive Layer**: Permanent character abilities
4. **Temporary Layer**: Status effects and buffs
5. **Battlefield Layer**: Environmental conditions
6. **Rule Layer**: Effect-driven rule modifications
7. **Final Layer**: Caps, floors, and validation

**Calculation Engine:**

- On-demand calculation with intelligent caching
- Dependency tracking for cache invalidation
- Support for conditional modifiers
- Mathematical operation types: flat, percentage, multiplicative

## 5. Expandable Effect Framework

### 5.1 Effect Classification System

**Simple Effects:**

- Single-target stat modifications
- Direct damage/healing values
- Basic status conditions
- Duration-based temporary changes

**Complex Effects:**

- Multi-target interactions
- Conditional logic trees
- Cross-system modifications
- State-dependent behaviors

**Meta Effects:**

- Effects that modify other effects
- Battle rule alterations
- AI behavior changes
- Persistent cross-battle effects

**System Effects:**

- Turn order manipulation
- Victory condition modifications
- Resource system changes
- Battle flow alterations

### 5.2 Effect Implementation Strategy

**Base Effect Interface:**
All effects implement a standard interface with:

- Unique identification and versioning
- Target scope and selection rules
- Trigger conditions and event bindings
- Application and removal logic
- Interaction rules with other effects

**Effect Categories:**

**Modifier Effects:**

- Change existing calculations without replacing them
- Stack with other modifiers using defined rules
- Can be temporary or permanent
- Examples: +20% ATK, damage reduction, accuracy bonuses

**Replacement Effects:**

- Completely replace normal game behavior
- Higher priority than modifiers
- Usually exclusive (don't stack)
- Examples: "attacks never miss", "heal instead of damage"

**Additional Effects:**

- Add new behaviors without changing existing ones
- Layer on top of normal actions
- Can stack and combine
- Examples: "attacks also heal allies", "skills trigger twice"

**Restriction Effects:**

- Prevent or limit specific actions
- Override normal permissions
- Can be conditional or absolute
- Examples: "cannot use skills", "maximum 1 action per turn"

### 5.3 Complex Skill Architecture

**Skill Execution Pipeline:**

1. **Validation Phase**: Check all prerequisites and restrictions
2. **Targeting Phase**: Determine valid targets with effect modifications
3. **Calculation Phase**: Compute base effects using current stats
4. **Modification Phase**: Apply all modifying effects in priority order
5. **Resolution Phase**: Apply final results and trigger consequences
6. **Cleanup Phase**: Handle post-action effects and state updates

**Multi-System Skills:**
Skills that affect multiple game systems use a composite effect structure:

- Primary effect (main skill function)
- Secondary effects (additional impacts)
- Trigger effects (reactive components)
- Persistent effects (lasting changes)

## 6. Battle State Management

### 6.1 Central Battle Context

**Immutable State Container:**

- Battle phase and round tracking
- Complete character state snapshots
- Active effects registry with metadata
- Environmental condition tracking
- Action history and undo capability

**State Synchronization:**

- Copy-on-write for performance
- Atomic updates with validation
- Event notification on all changes
- Rollback capability for "what-if" calculations

### 6.2 Rule Engine System

**Dynamic Rule Management:**

- Rules can be added, modified, or removed during battle
- Rule conflicts are resolved by priority and specificity
- Rules can be temporary or permanent
- Rule changes trigger appropriate recalculations

**Rule Categories:**

- **Calculation Rules**: How stats and damage are computed
- **Action Rules**: What actions are allowed when
- **Victory Rules**: How battles are won or lost
- **Timing Rules**: When effects activate or expire

## 7. AI System Architecture

### 7.1 Modular Decision Making

**Layered AI Architecture:**

**Strategic Layer:**

- Overall battle strategy based on team composition
- Long-term goal setting (aggro, control, support)
- Resource management decisions
- Win condition evaluation

**Tactical Layer:**

- Turn-by-turn action selection
- Target prioritization
- Skill usage optimization
- Positional decision making

**Reactive Layer:**

- Response to opponent actions
- Emergency decision making
- Interrupt handling
- Counter-strategy activation

**Adaptive Layer:**

- Learning from battle patterns
- Dynamic weight adjustment
- Player behavior modeling
- Meta-game considerations

### 7.2 Extensible AI Framework

**Plugin System:**

- Custom evaluation functions per character/archetype
- Modular decision tree components
- External AI behavior injection
- Performance-safe sandboxing

**AI Hook Points:**

- Pre-action decision modification
- Custom skill evaluation logic
- Target selection overrides
- Emergency action triggers

## 8. Data-Driven Content System

### 8.1 Core Content Definitions

The system uses JSON templates to define game content declaratively, allowing for easy modification and extension without code changes.

**Skill Templates:**

```json
{
  "skill_id": "fireball",
  "base_template": "damage_skill",
  "parameters": {
    "damage_type": "magical",
    "scaling": "mag",
    "target_type": "single_enemy",
    "base_damage": 100,
    "effects": [
      {
        "type": "burn",
        "duration": 3,
        "probability": 0.3
      }
    ]
  },
  "modifiers": [
    {
      "condition": "target_is_water_type",
      "damage_multiplier": 1.5
    }
  ]
}
```

**Passive Ability Templates:**

```json
{
  "passive_id": "berserker_rage",
  "base_template": "conditional_stat_modifier",
  "parameters": {
    "trigger": {
      "type": "hp_threshold",
      "condition": "below",
      "value": 0.5
    },
    "effects": [
      {
        "type": "stat_modifier",
        "stat": "atk",
        "modifier_type": "percentage",
        "value": 0.5
      }
    ],
    "duration": "while_condition_met"
  }
}
```

**Status Effect Templates:**

```json
{
  "status_id": "burning",
  "base_template": "dot_effect",
  "parameters": {
    "damage_type": "fire",
    "base_damage": 20,
    "scaling": {
      "stat": "mag",
      "multiplier": 0.3
    },
    "duration": 3,
    "stacking": {
      "type": "intensity",
      "max_stacks": 5
    }
  }
}
```

**Battlefield Condition Templates:**

```json
{
  "condition_id": "scorching_sun",
  "base_template": "global_modifier",
  "parameters": {
    "effects": [
      {
        "type": "elemental_amplification",
        "elements": ["fire"],
        "stat_bonus": {"atk": 0.2, "mag": 0.2}
      },
      {
        "type": "elemental_weakness",
        "elements": ["water"],
        "stat_penalty": {"vit": 0.1, "spr": 0.1}
      }
    ],
    "duration": "battle"
  }
}
```

**Series Synergy Templates:**

```json
{
  "synergy_id": "konosuba_team",
  "base_template": "series_synergy",
  "parameters": {
    "series_name": "Konosuba",
    "thresholds": [
      {
        "character_count": 2,
        "effects": [
          {
            "type": "stat_bonus",
            "stats": ["lck"],
            "bonus": 0.2
          }
        ]
      },
      {
        "character_count": 4,
        "effects": [
          {
            "type": "skill_enhancement",
            "effect": "cooldown_chance",
            "probability": 0.05
          }
        ]
      }
    ]
  }
}
```

**Equipment Templates (Future Expansion):**

```json
{
  "equipment_id": "basic_sword",
  "base_template": "weapon",
  "parameters": {
    "equipment_type": "sword",
    "stat_bonuses": {
      "atk": 50,
      "lck": 5
    },
    "restrictions": {
      "archetype_requirements": ["attacker", "knight"]
    }
  }
}
```

**AI Behavior Templates (Future Expansion):**

```json
{
  "ai_behavior_id": "aggressive_attacker",
  "base_template": "role_focused_ai",
  "parameters": {
    "role_preferences": {
      "attacker": 2.0,
      "mage": 1.5,
      "healer": 0.2
    },
    "target_priority": {
      "lowest_hp_enemy": 1.8,
      "highest_threat_enemy": 1.2
    }
  }
}
```

### 8.2 Template System Implementation

**Base Template Structure:**

All content definitions follow a common structure with inheritance support:

```json
{
  "template_id": "base_effect",
  "type": "abstract",
  "required_parameters": [
    "effect_type",
    "target_scope",
    "duration"
  ],
  "optional_parameters": [
    "stacking_rules",
    "removal_conditions"
  ]
}
```

**Template Inheritance:**

```json
{
  "template_id": "stat_modifier_effect",
  "extends": "base_effect",
  "additional_parameters": [
    "stat_type",
    "modifier_value",
    "modifier_type"
  ]
}
```

**Content Loading System:**

- JSON files are loaded from `src/game/data/` directories
- Templates are validated against base schemas
- Content is cached and can be hot-reloaded during development
- Simple dependency resolution for template inheritance

**File Organization:**

```text
src/game/data/
├── skills/              # Skill definitions
├── passives/            # Passive ability definitions  
├── status_effects/      # Status effect definitions
├── battlefield/         # Battlefield condition definitions
├── synergies/           # Series synergy definitions
├── equipment/           # Equipment definitions (future)
└── ai_behaviors/        # AI behavior definitions (future)
```

### 8.3 Integration with Game Systems

**Content Loading Process:**

1. **Initialization**: Load all JSON content files at game startup
2. **Template Resolution**: Resolve inheritance chains and build final definitions
3. **Registration**: Register content with appropriate game systems
4. **Runtime Access**: Game systems query content by ID as needed

**Example Integration:**

```python
# Skill system integration
skill_definition = ContentLoader.get_skill("fireball")
skill_instance = SkillFactory.create(skill_definition, caster_character)

# Effect system integration  
status_definition = ContentLoader.get_status_effect("burning")
status_instance = StatusEffectFactory.create(status_definition, target_character)

# Battle system integration
battlefield_condition = ContentLoader.get_battlefield_condition("scorching_sun")
battle_context.apply_global_condition(battlefield_condition)
```

**Benefits:**

- **Maintainability**: Content changes don't require code modifications
- **Extensibility**: New content types can be added easily
- **Balance Iteration**: Rapid tweaking of parameters during development
- **Modularity**: Content can be organized by features or expansions

**Character Data Note:**

Character definitions remain database-driven rather than file-based, as they require more complex relationships and frequently change during gameplay (levels, equipment, etc.). The data-driven system focuses on static game rules and content definitions.

## 9. Performance and Scalability

### 9.1 Optimization Strategies

**Calculation Optimization:**

- Lazy evaluation with smart caching
- Batch processing of similar operations
- Early termination for impossible outcomes
- Precomputed lookup tables for common values

**Memory Management:**

- Object pooling for temporary battle objects
- Weak references for event handlers
- Garbage collection friendly patterns
- Resource cleanup protocols

**Event System Performance:**

- Event filtering before handler invocation
- Handler priority queues for efficiency
- Event batching for bulk operations
- Async handler execution where safe

### 9.2 Concurrency Design

**Battle Processing:**

- Single-threaded battle execution for determinism
- Async I/O for database operations
- Parallel battle simulations for testing
- Thread-safe state access patterns

**Plugin Safety:**

- Sandboxed execution environments
- Resource usage limits
- Timeout protections
- Error isolation and recovery

## 10. Testing and Validation Framework

### 10.1 Multi-Level Testing

**Unit Testing:**

- Component isolation and mocking
- Effect interaction validation
- AI decision correctness
- Performance benchmarking

**Integration Testing:**

- Full battle simulations
- Complex effect combinations
- Edge case validation
- Cross-system interactions

**Balance Testing:**

- Statistical outcome analysis
- Monte Carlo simulations
- Win rate monitoring
- Power level validation

### 10.2 Development Tools

**Battle Simulation Tools:**

- Step-by-step battle debugging
- Alternative outcome simulation
- Performance profiling
- State inspection utilities

**Content Creation Tools:**

- Skill definition validators
- Effect interaction checkers
- Balance impact analyzers
- Documentation generators

## 11. Implementation Roadmap

### Phase 1: Core Framework (3-4 weeks)

**Event System Foundation:**

- Central event bus implementation
- Basic effect registration and execution
- Simple hook system for modifiers
- Core battle state management

**Component Architecture:**

- Character component system
- Basic stats calculation layers
- Simple effect application
- State synchronization

### Phase 2: Battle Systems (3-4 weeks)

**Core Combat:**

- Turn management with action gauge
- Basic damage/healing calculations
- Simple AI decision making
- Victory condition checking

**Effect Framework:**

- Effect base classes and interfaces
- Basic modifier effects
- Status effect system
- Duration and expiration handling

### Phase 3: Advanced Effects (2-3 weeks)

**Complex Interactions:**

- Multi-system effect coordination
- Rule modification system
- Effect priority resolution
- Meta-effect implementation

**AI Enhancement:**

- Multi-layer decision making
- Effect-aware AI logic
- Custom evaluation functions
- Adaptive behavior systems

### Phase 4: Content Framework (2-3 weeks)

**Data-Driven System:**

- JSON content definition system for skills, passives, status effects
- Basic template inheritance support
- Content loading and caching
- Integration with existing game systems

**Future Expansion Support:**

- Equipment system templates
- AI behavior customization
- Additional battlefield conditions
- Series synergy extensions

### Phase 5: Polish and Tools (2-3 weeks)

**Development Tools:**

- Battle simulation and debugging
- Content creation utilities
- Balance analysis tools
- Performance profilers

**Production Ready:**

- Comprehensive testing suite
- Documentation generation
- Deployment automation
- Monitoring and analytics

This architecture provides a solid foundation for a highly extensible auto-battler system where complex skills and effects can be added without modifying core systems, allowing for rich gameplay mechanics and easy content expansion.
