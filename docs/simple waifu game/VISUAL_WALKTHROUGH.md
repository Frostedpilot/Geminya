# 🎮 VISUAL WALKTHROUGH: How Everything Works Together

## 📊 **STEP 1: DATA LOADING (Game Startup)**

```
🗂️  Data Files                    🏭 Data Manager
┌─────────────────────┐          ┌─────────────────────┐
│ character_final.csv │   ────▶  │ Loads & organizes   │
│ (2354 characters)   │          │ all game data       │
├─────────────────────┤          ├─────────────────────┤
│ general_skills.json │   ────▶  │ • Characters        │
│ (50 skills)         │          │ • Skills            │
├─────────────────────┤          │ • Status Effects    │
│ status_effects.json │   ────▶  │ • Battlefield       │
│ battlefield_*.json  │          │   Conditions        │
└─────────────────────┘          └─────────────────────┘
```

## 🏭 **STEP 2: CHARACTER CREATION**

When you want to create a character (like Megumin):

```
1️⃣  Request Character
    factory.create_character("117225")  # Megumin's ID
    
2️⃣  Character Factory Workflow:
    ┌─────────────────────────────────────────────────────────┐
    │ CharacterFactory.create_character("117225")             │
    │                                                         │
    │ 1. data_manager.get_character_stats("117225")          │
    │    ▶ Returns: {"name": "Megumin", "archetype":         │
    │                "Sorcerer", "stats": {...}}             │
    │                                                         │
    │ 2. _assign_skills_by_archetype()                       │
    │    ▶ Sorcerer → mage_potency skills                     │
    │    ▶ Randomly picks 3 skills: ["fireball",             │
    │      "chain_lightning", "arcane_missile"]               │
    │                                                         │
    │ 3. Character(id="117225", data={...})                  │
    │    ▶ Creates character with all components              │
    └─────────────────────────────────────────────────────────┘

3️⃣  Character Object Created:
    ┌─────────────────┐
    │    Megumin      │
    │   (Character)   │
    ├─────────────────┤
    │ StatsComponent  │  ▶ HP: 100, ATK: 45, MAG: 85, etc.
    │ AbilitiesComp   │  ▶ Skills: [Fireball, Chain Lightning, Arcane Missile]
    │ EffectsComp     │  ▶ Status Effects: [] (none initially)
    │ StateComponent  │  ▶ Alive: True, Ready: True
    └─────────────────┘
```

## ⚔️ **STEP 3: BATTLE SIMULATION**

Here's what happens when Megumin uses a skill in battle:

```
🎯 BATTLE TURN: Megumin's Turn
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│ 1️⃣  GET AVAILABLE SKILLS                                        │
│    megumin.abilities.get_available_skills()                    │
│    ▶ Returns: {"fireball": FireballSkill,                      │
│                "chain_lightning": ChainLightningSkill,         │
│                "arcane_missile": ArcaneMissileSkill}           │
│                                                                 │
│ 2️⃣  AI CHOOSES SKILL                                            │
│    battle_ai.choose_best_skill(megumin, enemies)              │
│    ▶ Analyzes: enemy HP, resistances, skill damage            │
│    ▶ Chooses: "fireball" (highest single-target damage)       │
│                                                                 │
│ 3️⃣  EXECUTE SKILL                                               │
│    skill_effects.execute_skill(fireball, megumin, [enemy])    │
│                                                                 │
│    ┌─────────────────────────────────────────────────────────┐ │
│    │ SKILL EXECUTION PIPELINE                                │ │
│    │                                                         │ │
│    │ A. Validate Skill Usage                                 │ │
│    │    ✓ Not on cooldown                                    │ │
│    │    ✓ Megumin has enough MP                              │ │
│    │    ✓ Target is alive and in range                       │ │
│    │                                                         │ │
│    │ B. Calculate Damage                                     │ │
│    │    base_damage = 30 (skill floor)                       │ │
│    │    scaling = megumin.stats.get_stat("mag") * 0.7        │ │
│    │    final_damage = 30 + (85 * 0.7) = 89.5               │ │
│    │                                                         │ │
│    │ C. Apply Effects                                        │ │
│    │    SkillEffectHandler._handle_damage()                  │ │
│    │    ▶ enemy.stats.current_hp -= 89.5                     │ │
│    │    ▶ Check if enemy defeated                            │ │
│    │    ▶ Apply secondary effects (burn, etc.)              │ │
│    │                                                         │ │
│    │ D. Update State                                         │ │
│    │    ▶ fireball.current_cooldown = 2                      │ │
│    │    ▶ Log battle event                                   │ │
│    │    ▶ Check victory conditions                           │ │
│    └─────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🧩 **COMPONENT INTERACTION EXAMPLE**

Let's see how components work together when Megumin gets poisoned:

```
🟢 BEFORE POISON:
┌─────────────────┐
│    Megumin      │
├─────────────────┤
│ Stats: HP 100   │ ◀┐
│ Effects: []     │  │  Clean state
│ State: Alive    │ ◀┘
└─────────────────┘

🟡 POISON APPLIED:
┌─────────────────┐
│    Megumin      │
├─────────────────┤
│ Stats: HP 100   │
│ Effects: [      │ ◀── EffectsComponent gets new status effect
│   Poison {      │
│     duration: 3,│
│     damage: 10  │
│   }             │
│ ]               │
│ State: Alive    │
└─────────────────┘

🔴 EACH TURN (Turn Processing):
┌─────────────────────────────────────┐
│ effects.process_turn_effects()      │
│                                     │
│ For each effect in active_effects:  │
│   if effect.type == "poison":       │
│     1. Calculate damage (10)        │
│     2. stats.current_hp -= 10       │  ◀── Components communicate
│     3. Check if hp <= 0             │
│     4. If hp <= 0:                  │
│        state.set_defeated()         │  ◀── State component updated
│     5. effect.duration -= 1         │
│     6. If duration <= 0:            │
│        Remove effect                │
└─────────────────────────────────────┘

📉 AFTER 3 TURNS:
┌─────────────────┐
│    Megumin      │
├─────────────────┤
│ Stats: HP 70    │ ◀── HP reduced by poison
│ Effects: []     │ ◀── Poison expired and removed
│ State: Alive    │ ◀── Still alive (HP > 0)
└─────────────────┘
```

## 📁 **FILE RESPONSIBILITY BREAKDOWN**

### 🎯 **Core Game Logic** (`src/game/`)

```
src/game/
├── components/                    # Character building blocks
│   ├── character.py              # Main character container
│   ├── stats_component.py        # HP, ATK, MAG, DEF, etc.
│   ├── abilities_component.py    # Skills and abilities management
│   ├── effects_component.py      # Status effects (poison, buffs)
│   ├── state_component.py        # Alive/dead, ready/acting
│   └── skill_effects.py          # Skill execution logic
│
├── core/                         # Game systems
│   ├── event_system.py           # Game event handling
│   ├── team_synergy.py           # Team bonuses
│   └── battlefield_conditions.py # Environmental effects
│
└── data/                         # Data management
    ├── data_manager.py           # Loads and organizes all data
    └── character_factory.py      # Creates characters from data
```

### 📊 **Data Files** (`data/`)

```
data/
├── character_final.csv           # 2354 anime characters with stats
├── general_skills.json           # 50 professional skills we created
├── status_effects.json           # Poison, buffs, debuffs
├── battlefield_conditions.json   # Environmental effects
└── team_synergies.json          # Series-based team bonuses
```

### 🧪 **Testing** (Root directory)

```
test_skills_compatibility.py      # Unit tests for skills system
test_ultimate_battle_with_skills.py # Integration test (full battle)
test_comprehensive_game_system_fixed.py # Stress test (everything)
```

## 🔧 **HOW TO MODIFY THE GAME**

### Want to add a new skill? ✨

1. **Edit** `data/general_skills.json`
2. **Add** your skill definition:
   ```json
   "ice_spear": {
     "name": "Ice Spear",
     "description": "Piercing ice attack",
     "potency_category": "mage_potency",
     "target_type": "single_enemy",
     "effects": [{"type": "damage", "damage_type": "ice"}],
     "scaling": {"floor": 25, "sc1": 60}
   }
   ```
3. **Done!** The skill will automatically be available to mage characters

### Want to add a new character? 👤

1. **Edit** `data/character_final.csv`
2. **Add** a new row with the character's stats
3. **Done!** The character factory will automatically create them

### Want to change game balance? ⚖️

1. **Edit** the numbers in data files
2. **Run** tests to make sure nothing breaks
3. **Done!** No code changes needed

## 🎯 **WHY THIS APPROACH IS POWERFUL**

### ✅ **Separation of Concerns**
- **Data** (JSON/CSV) is separate from **Logic** (Python)
- **Components** handle one specific aspect each
- **Systems** coordinate components without tight coupling

### ✅ **Extensibility**
- Add new skill effects by adding handler methods
- Add new components by implementing the BaseComponent interface
- Add new data by extending existing JSON structures

### ✅ **Testability**
- Each component can be tested in isolation
- Integration tests verify system interactions
- Performance tests ensure scalability

### ✅ **Maintainability**
- Clear file organization
- Consistent naming conventions
- Comprehensive documentation

This architecture follows industry best practices used in professional game development, making it both powerful and maintainable! 🚀
