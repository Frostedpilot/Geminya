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

### 8.1 Declarative Content Definitions

**Skill Templates:**

```json
{
  "skill_id": "fireball",
  "base_template": "damage_skill",
  "parameters": {
    "damage_type": "magical",
    "scaling": "mag",
    "target_type": "single_enemy",
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
      },
      {
        "type": "status_immunity",
        "status_types": ["fear", "charm"]
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
      "max_stacks": 5,
      "stack_effect": "damage_multiplier"
    },
    "visual_effects": {
      "icon": "fire_dot",
      "particle": "flame_aura"
    }
  }
}
```

**Battlefield Condition Templates:**

```json
{
  "condition_id": "arcane_storm",
  "base_template": "global_modifier",
  "parameters": {
    "effects": [
      {
        "type": "skill_cost_modifier",
        "skill_types": ["magical"],
        "cost_multiplier": 0.8
      },
      {
        "type": "elemental_amplification",
        "elements": ["arcane", "lightning"],
        "damage_multiplier": 1.3
      },
      {
        "type": "periodic_event",
        "event": "mana_surge",
        "frequency": "every_3_turns",
        "effect": {
          "type": "restore_resource",
          "resource": "mp",
          "amount": 50
        }
      }
    ],
    "duration": "battle",
    "visual_theme": "purple_lightning"
  }
}
```

**Character Archetype Templates:**

```json
{
  "archetype_id": "battle_mage",
  "base_template": "hybrid_archetype",
  "parameters": {
    "primary_roles": ["mage", "attacker"],
    "stat_affinities": {
      "mag": 1.2,
      "atk": 0.8,
      "int": 1.1,
      "spd": 0.9
    },
    "passive_abilities": [
      {
        "id": "spellsword_mastery",
        "effect": "physical_skills_scale_with_mag"
      },
      {
        "id": "arcane_weapon",
        "effect": "basic_attacks_deal_magical_damage"
      }
    ],
    "skill_affinities": {
      "magical_damage": 1.0,
      "physical_damage": 0.7,
      "buff": 0.6
    }
  }
}
```

**Series Synergy Templates:**

```json
{
  "synergy_id": "fate_servants",
  "base_template": "series_synergy",
  "parameters": {
    "series_name": "Fate",
    "thresholds": [
      {
        "character_count": 2,
        "effects": [
          {
            "type": "stat_bonus",
            "stats": ["atk", "mag"],
            "bonus": 0.1
          }
        ]
      },
      {
        "character_count": 4,
        "effects": [
          {
            "type": "skill_enhancement",
            "skill_types": ["signature"],
            "cooldown_reduction": 1
          },
          {
            "type": "passive_ability",
            "ability": "noble_phantasm_charge"
          }
        ]
      },
      {
        "character_count": 6,
        "effects": [
          {
            "type": "team_ability",
            "ability": "reality_marble",
            "trigger": "team_hp_below_30_percent"
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
  "equipment_id": "excalibur",
  "base_template": "legendary_weapon",
  "parameters": {
    "equipment_type": "sword",
    "stat_bonuses": {
      "atk": 150,
      "mag": 50,
      "lck": 20
    },
    "passive_effects": [
      {
        "id": "holy_blade",
        "effect": "extra_damage_vs_dark_enemies",
        "multiplier": 1.5
      }
    ],
    "active_ability": {
      "skill_id": "excalibur_blast",
      "cooldown": 5,
      "description": "Unleash a devastating light beam"
    },
    "restrictions": {
      "archetype_requirements": ["knight", "paladin"],
      "character_requirements": ["artoria_pendragon"]
    }
  }
}
```

**Event Templates:**

```json
{
  "event_id": "summer_festival",
  "base_template": "seasonal_event",
  "parameters": {
    "duration": "2_weeks",
    "battle_modifiers": [
      {
        "type": "exp_bonus",
        "multiplier": 1.5
      },
      {
        "type": "special_battlefield",
        "condition": "beach_party"
      }
    ],
    "special_rewards": [
      {
        "type": "limited_character",
        "character_id": "summer_jeanne"
      },
      {
        "type": "cosmetic",
        "item_id": "beach_outfit_set"
      }
    ],
    "unlock_conditions": {
      "player_level": 10,
      "story_progress": "chapter_3_complete"
    }
  }
}
```

**AI Behavior Templates:**

```json
{
  "ai_behavior_id": "berserker_ai",
  "base_template": "aggressive_ai",
  "parameters": {
    "role_preferences": {
      "attacker": 2.0,
      "defender": 0.3,
      "healer": 0.1
    },
    "target_priority": {
      "lowest_hp_enemy": 1.5,
      "highest_threat_enemy": 1.2,
      "weakest_defense": 1.1
    },
    "special_behaviors": [
      {
        "condition": "self_hp_below_25_percent",
        "effect": "ignore_defense_focus_damage"
      },
      {
        "condition": "ally_defeated",
        "effect": "rage_mode_increased_aggression"
      }
    ],
    "skill_usage_patterns": {
      "signature_skill_trigger": "hp_below_50_percent",
      "ultimate_skill_priority": "when_multiple_enemies"
    }
  }
}
```

**Template System Features:**

- **Inheritance Hierarchy**: Templates can extend other templates
- **Parameter Validation**: Type checking and constraint validation
- **Dynamic Loading**: Hot-reload templates without restart
- **Composition Support**: Combine multiple template effects
- **Version Management**: Track template changes over time
- **Localization Ready**: Text strings separated for translation
- **Automatic Documentation**: Generate docs from template definitions

### 8.2 Template Inheritance and Composition

**Base Template Definitions:**

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
    "removal_conditions",
    "visual_effects"
  ],
  "validation_rules": {
    "duration": {
      "type": "integer",
      "min": 0,
      "special_values": ["permanent", "conditional"]
    },
    "target_scope": {
      "type": "enum",
      "values": ["self", "single", "multiple", "all", "global"]
    }
  }
}
```

**Template Inheritance Example:**

```json
{
  "template_id": "stat_modifier_effect",
  "extends": "base_effect",
  "additional_parameters": [
    "stat_type",
    "modifier_value",
    "modifier_type"
  ],
  "parameter_overrides": {
    "effect_type": {
      "default": "stat_modification",
      "readonly": true
    }
  },
  "validation_rules": {
    "stat_type": {
      "type": "enum",
      "values": ["hp", "atk", "mag", "vit", "spr", "int", "spd", "lck"]
    },
    "modifier_type": {
      "type": "enum",
      "values": ["flat", "percentage", "multiplicative"]
    }
  }
}
```

**Content Validation Framework:**

```json
{
  "validation_config": {
    "balance_checks": {
      "damage_skills": {
        "max_base_damage": 500,
        "max_scaling_multiplier": 2.0,
        "cooldown_vs_power_ratio": "linear"
      },
      "healing_skills": {
        "max_healing_per_turn": 300,
        "healing_vs_cost_efficiency": "bounded"
      }
    },
    "performance_limits": {
      "max_effects_per_skill": 5,
      "max_conditional_checks": 10,
      "max_calculation_depth": 15
    },
    "compatibility_checks": {
      "required_game_version": "1.0.0",
      "deprecated_features": ["old_damage_formula"],
      "conflicting_effects": ["silence_and_skill_boost"]
    }
  }
}
```

### 8.3 Content Management and Expansion System

**Hot-Reloadable Content Pipeline:**

**Development Workflow:**

1. **Content Creation**: Use template-based JSON definitions
2. **Validation**: Automatic validation against schemas and balance rules  
3. **Testing**: Isolated testing environment for new content
4. **Staging**: Deploy to test servers for integration testing
5. **Production**: Hot-reload into live game with rollback capability

**Version Management:**

```json
{
  "content_package": {
    "package_id": "summer_2025_update", 
    "version": "1.2.0",
    "dependencies": ["base_game:1.0.0"],
    "contents": {
      "skills": ["beach_volleyball_spike", "sandcastle_fortress"],
      "characters": ["summer_miku", "beach_volleyball_team"], 
      "battlefield_conditions": ["summer_heat_wave"],
      "events": ["beach_tournament"]
    },
    "compatibility": {
      "min_game_version": "1.0.0",
      "max_game_version": "2.0.0"
    },
    "rollback_data": {
      "previous_version": "1.1.5", 
      "affected_systems": ["battle_engine", "character_stats"]
    }
  }
}
```

**Plugin Architecture:**

```json
{
  "plugin_manifest": {
    "plugin_id": "custom_battle_modes",
    "version": "1.0.0", 
    "author": "CommunityDev",
    "description": "Adds custom battle modes and rules",
    "permissions": [
      "modify_battle_rules",
      "add_victory_conditions", 
      "create_custom_effects"
    ],
    "entry_points": {
      "battle_mode_handlers": ["survival_mode", "king_of_hill"],
      "effect_processors": ["custom_damage_calculator"],
      "ai_behaviors": ["defensive_turtle_ai"]
    },
    "resource_limits": {
      "max_memory_mb": 50,
      "max_cpu_percent": 5,
      "max_execution_time_ms": 100
    }
  }
}
```

**Content Creator API:**

```python
# Simplified API interface for content creation
class ContentCreatorAPI:
    def create_skill(self, template: str, parameters: dict) -> SkillID
    def create_passive(self, template: str, parameters: dict) -> PassiveID
    def create_status_effect(self, template: str, parameters: dict) -> StatusID
    def validate_content(self, content: dict) -> ValidationResult
    def test_balance(self, content: dict, test_scenarios: list) -> BalanceReport
    def submit_for_review(self, content_package: dict) -> SubmissionID
```

**Content Distribution:**

**Skill Libraries**: Collections of thematic abilities
**Battle Modes**: Alternative victory conditions and rules
**Cosmetic Packs**: Visual themes and effects
**Balance Updates**: Numerical adjustments and formula changes

**Note:** All new characters are imported and managed via the database. There is no modular content pack system for character additions; character data is handled through database operations and migrations.

**Performance Monitoring:**

- Resource usage limits per plugin
- Execution time timeouts  
- Memory leak detection
- Performance regression alerts
- Automatic rollback on critical issues

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

- JSON skill definition system
- Template and inheritance support
- Hot-reload capability
- Validation and testing tools

**Plugin Architecture:**

- External content loading
- Sandboxed execution
- Performance monitoring
- Error handling and recovery

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
