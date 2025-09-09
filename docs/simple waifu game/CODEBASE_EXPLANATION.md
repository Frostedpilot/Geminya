# Complete Codebase Architecture Explanation

## 🏗️ **HIGH-LEVEL ARCHITECTURE**

Think of this codebase like a **modular game engine** for an anime character auto-battler game. Here's the big picture:

```
┌─────────────────────────────────────────────────────────┐
│                   GAME ARCHITECTURE                     │
├─────────────────────────────────────────────────────────┤
│  📊 DATA LAYER     │  🎮 GAME LOGIC   │  🧪 TESTING    │
│  - CSV/JSON files  │  - Characters    │  - Unit Tests   │
│  - Data Manager    │  - Skills        │  - Integration  │
│  - Character Stats │  - Battle System │  - Performance  │
└─────────────────────────────────────────────────────────┘
```

## 📁 **DIRECTORY STRUCTURE EXPLAINED**

```
Geminya/
│
├── 📊 data/                    # All game data (like a database)
│   ├── character_final.csv     # 2354 anime characters with stats
│   ├── general_skills.json     # 50 professional skills we created
│   ├── battlefield_conditions.json
│   └── status_effects.json
│
├── 🎮 src/                     # Core game engine code
│   ├── game/
│   │   ├── components/         # Character building blocks
│   │   ├── core/              # Game systems (battle, effects)
│   │   └── data/              # Data loading and management
│   │
├── 🧪 tests/                   # All test files
├── 📖 docs/                    # Documentation
└── ⚙️ config files             # Settings and configuration
```

## 🎯 **CORE CONCEPT: COMPONENT-BASED ARCHITECTURE**

### What is a Component?
Think of a **component** like a "module" or "part" of a character:

- **Stats Component**: Handles HP, ATK, MAG, DEF, etc.
- **Abilities Component**: Manages skills and abilities
- **Effects Component**: Tracks status effects (poison, buffs, etc.)
- **State Component**: Knows if character is alive, ready to act, etc.

### Why Components?
Instead of having one giant "Character" class with everything, we split functionality into smaller, focused pieces:

```python
# Instead of this messy approach:
class Character:
    def __init__(self):
        self.hp = 100
        self.skills = []
        self.status_effects = []
        self.ready_to_act = False
        # ... 50 more properties

# We use this clean approach:
class Character:
    def __init__(self):
        self.stats = StatsComponent()      # Handles HP, ATK, etc.
        self.abilities = AbilitiesComponent()  # Handles skills
        self.effects = EffectsComponent()      # Handles status effects
        self.state = StateComponent()          # Handles ready/alive status
```

## 📊 **DATA MANAGEMENT SYSTEM**

### The Data Manager (`src/game/data/data_manager.py`)
This is like the "librarian" of our game. It:

1. **Loads data from files** (CSV for characters, JSON for skills)
2. **Organizes and indexes** the data for fast lookup
3. **Provides search functions** (find characters by series, skills by category)

```python
# Example: How to get character data
data_manager = get_data_manager()

# Get a specific character
megumin = data_manager.get_character_stats("117225")
# Returns: {"name": "Megumin", "series": "KonoSuba", "archetype": "Sorcerer", ...}

# Get all skills of a certain type
mage_skills = data_manager.get_skills_by_category("mage_potency")
# Returns: {"fireball": {...}, "chain_lightning": {...}, ...}
```

### Character Factory (`src/game/data/character_factory.py`)
This is like a "character builder" that:

1. **Takes raw data** (from CSV/JSON)
2. **Creates full character objects** with all components
3. **Assigns appropriate skills** based on character archetype

```python
# How a character gets created:
factory = get_character_factory()
character = factory.create_character("117225")  # Megumin's ID

# What happens inside:
# 1. Load stats from CSV
# 2. Determine archetype (Sorcerer)
# 3. Assign skills from mage_potency category
# 4. Create Character object with all components
# 5. Return fully functional character
```

## ⚔️ **SKILLS SYSTEM ARCHITECTURE**

This is the heart of the combat system. Here's how it works:

### 1. **Skill Data Structure** (`data/general_skills.json`)
Each skill is defined like this:

```json
{
  "fireball": {
    "name": "Fireball",
    "description": "Launch a fiery projectile",
    "potency_category": "mage_potency",
    "target_type": "single_enemy",
    "cooldown": 2,
    "effects": [
      {
        "type": "damage",
        "damage_type": "fire"
      }
    ],
    "scaling": {
      "floor": 30,
      "sc1": 70
    }
  }
}
```

### 2. **Skill Effect System** (`src/game/components/skill_effects.py`)
This handles what happens when skills are used:

```python
class SkillEffectHandler:
    def _handle_damage(self, effect, caster, targets, battle_context):
        # Calculate damage based on caster's MAG stat
        # Apply damage to targets
        # Handle critical hits, resistances, etc.
    
    def _handle_heal(self, effect, caster, targets, battle_context):
        # Calculate healing based on caster's MAG stat
        # Restore HP to targets
        # Handle overhealing, etc.
    
    # ... 14 different effect handlers
```

### 3. **Skill Execution Pipeline**
When a character uses a skill:

```
1. Check if skill is available (not on cooldown, enough resources)
2. Validate targets (is target alive? in range?)
3. Calculate effects (damage, healing, status effects)
4. Apply effects to targets
5. Handle secondary effects (chain damage, splash, etc.)
6. Update cooldowns and costs
7. Trigger battle events (character defeated, etc.)
```

## 👥 **CHARACTER SYSTEM**

### Character Class (`src/game/components/character.py`)
The main character class is like a "container" that holds all components:

```python
class Character:
    def __init__(self, character_id, character_data):
        self.character_id = character_id
        self.character_data = character_data
        
        # Initialize all components
        self.stats = StatsComponent(character_id)
        self.abilities = AbilitiesComponent(character_id)
        self.effects = EffectsComponent(character_id)
        self.state = StateComponent(character_id)
        
        # Load data into components
        self.initialize_from_data(character_data)
```

### Stats Component (`src/game/components/stats_component.py`)
Handles all numerical stats:

```python
class StatsComponent:
    def __init__(self):
        self.base_stats = {
            "hp": 100, "atk": 50, "mag": 30, "def": 40,
            "spr": 35, "spd": 25, "vit": 45, "lck": 20
        }
        self.current_hp = 100
        self.stat_modifiers = []  # Temporary buffs/debuffs
    
    def get_effective_stat(self, stat_type):
        # Calculate final stat after all modifiers
        base = self.base_stats[stat_type]
        for modifier in self.stat_modifiers:
            base = modifier.apply(base)
        return base
```

### Abilities Component (`src/game/components/abilities_component.py`)
Manages all skills and abilities:

```python
class AbilitiesComponent:
    def __init__(self):
        self.active_skills = {}     # Skills character can use in battle
        self.passive_abilities = {} # Always-on effects
        self.skill_cooldowns = {}   # Track when skills can be used again
    
    def get_available_skills(self):
        # Return skills that are ready to use (not on cooldown)
        available = {}
        for skill_id, skill in self.active_skills.items():
            if self.skill_cooldowns.get(skill_id, 0) <= 0:
                available[skill_id] = skill
        return available
```

## ⚔️ **BATTLE SYSTEM INTEGRATION**

### How Combat Works:
1. **Turn Order**: Characters act based on speed stats
2. **Action Selection**: AI picks best available skill for each character
3. **Skill Execution**: Use the skill effect pipeline
4. **Status Effects**: Apply DoT, buffs, debuffs each turn
5. **Victory Check**: See if any team is defeated

### Battle Flow Example:
```python
# Simplified battle turn:
def process_turn(character):
    1. # Get available skills
       available_skills = character.abilities.get_available_skills()
    
    2. # AI picks best skill
       chosen_skill = battle_ai.choose_skill(character, available_skills, enemies)
    
    3. # Execute skill
       skill_effects.execute_skill(chosen_skill, character, targets)
    
    4. # Update cooldowns
       character.abilities.update_cooldowns()
    
    5. # Process status effects
       character.effects.process_turn_effects()
```

## 🧪 **TESTING FRAMEWORK**

I created several types of tests to ensure everything works:

### 1. **Unit Tests** (`test_skills_compatibility.py`)
- Tests individual components in isolation
- Validates skill loading, target types, effect types
- Quick to run, focuses on specific functionality

### 2. **Integration Tests** (`test_ultimate_battle_with_skills.py`)
- Tests how multiple systems work together
- Simulates real battles with skill usage
- Ensures combat mechanics work end-to-end

### 3. **Comprehensive Tests** (`test_comprehensive_game_system_fixed.py`)
- Tests the entire system under stress
- Creates hundreds of characters
- Validates performance and memory usage

## 🔧 **HOW EVERYTHING WORKS TOGETHER**

Let me trace through a complete example:

### Example: Creating and Using Megumin

```python
# 1. DATA LOADING (happens at startup)
data_manager = DataManager()
data_manager.load_all_data()  # Loads 2354 characters, 50 skills, etc.

# 2. CHARACTER CREATION
factory = CharacterFactory()
megumin = factory.create_character("117225")

# What happens inside:
# - Load Megumin's stats from CSV
# - See she's a "Sorcerer" archetype
# - Assign 3 random skills from "mage_potency" category
# - Create Character object with all components initialized

# 3. BATTLE SETUP
battle = Battle()
battle.add_character(megumin, team=1)
battle.add_character(enemy, team=2)

# 4. SKILL USAGE IN BATTLE
available_skills = megumin.abilities.get_available_skills()
# Returns: {"fireball": FireballSkill, "chain_lightning": ChainLightningSkill}

chosen_skill = "fireball"
targets = [enemy]

# 5. SKILL EXECUTION
skill_handler = SkillEffectHandler()
skill_handler.execute_skill(available_skills[chosen_skill], megumin, targets)

# What happens inside:
# - Calculate damage: base_damage + (megumin.stats.get_stat("mag") * scaling)
# - Apply damage to enemy
# - Check if enemy is defeated
# - Apply any secondary effects (burn, etc.)
# - Update skill cooldown
```

## 🎨 **KEY DESIGN PRINCIPLES**

### 1. **Separation of Concerns**
- Data loading is separate from game logic
- Skills are separate from characters
- Effects are separate from calculations

### 2. **Component-Based Design**
- Characters are composed of smaller, focused components
- Easy to modify one aspect without affecting others
- Components can be reused and tested independently

### 3. **Data-Driven Approach**
- Game content (skills, characters) defined in external files
- No need to modify code to add new skills or characters
- Easy for non-programmers to add content

### 4. **Extensibility**
- Easy to add new skill effect types
- Easy to add new character components
- Easy to add new game mechanics

## 🚀 **WHY THIS ARCHITECTURE?**

### Benefits:
1. **Maintainable**: Each file has a single, clear purpose
2. **Testable**: Components can be tested in isolation
3. **Extensible**: Easy to add new features without breaking existing code
4. **Data-Driven**: Game designers can modify content without touching code
5. **Performance**: Only load what you need, when you need it

### Real-World Analogy:
Think of it like a **restaurant kitchen**:

- **Data Manager**: The pantry that stores all ingredients (character data, skills)
- **Character Factory**: The prep station that assembles ingredients into dishes (characters)
- **Components**: Different cooking stations (grill for stats, fryer for abilities)
- **Skills System**: The recipes that tell you how to combine ingredients
- **Battle System**: The service that delivers the final dish to customers
- **Tests**: Quality control that ensures everything tastes good

## 🎯 **WHAT YOU CAN DO NOW**

With this architecture, you can easily:

1. **Add new characters**: Just add a row to the CSV file
2. **Create new skills**: Add an entry to the JSON file
3. **Modify game balance**: Change numbers in the data files
4. **Add new mechanics**: Create new components or effect types
5. **Test changes**: Run the test suite to ensure nothing breaks

The beauty is that most changes don't require programming knowledge - just editing data files!
