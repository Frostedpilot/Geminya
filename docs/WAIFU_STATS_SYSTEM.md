
### Example Archetypes (JSON Format)

Archetype assignment is now handled by an LLM (large language model) that analyzes character and anime data, rather than by tag mapping. Archetypes are defined in JSON, with numeric stat ranges and letter grades for role potency. The full list is in `data/archetypes.json`.

```json
{
  "archetypes": [
    {
      "name": "Mage",
      "description": "Focuses on magic attack and intelligence.",
      "stat_focus": {
        "mag": {"min": 120, "max": 140},
        "int": {"min": 120, "max": 140},
        "spr": {"min": 90, "max": 110},
        "atk": {"min": 60, "max": 80},
        "vit": {"min": 60, "max": 80},
        "spd": {"min": 90, "max": 110},
        "lck": {"min": 60, "max": 80},
        "hp": {"min": 60, "max": 80}
      },
      "role_potency": {
        "Mage": "S",
        "Attacker": "D",
        "Healer": "C",
        "Buffer": "C",
        "Debuffer": "D",
        "Defender": "D",
        "Specialist": "C"
      }
    },
    {
      "name": "Physical Attacker",
      "description": "Excels at physical damage and speed.",
      "stat_focus": {
        "atk": {"min": 120, "max": 140},
        "spd": {"min": 120, "max": 140},
        "vit": {"min": 90, "max": 110},
        "mag": {"min": 60, "max": 80},
        "spr": {"min": 60, "max": 80},
        "int": {"min": 60, "max": 80},
        "lck": {"min": 90, "max": 110},
        "hp": {"min": 90, "max": 110}
      },
      "role_potency": {
        "Attacker": "C",
        "Mage": "F",
        "Healer": "D",
        "Buffer": "D",
        "Debuffer": "D",
        "Defender": "D",
        "Specialist": "D"
      }
    }
    // ...see data/archetypes.json for the full list...
  ]
}
```

Each archetype includes:
- `name`: The archetype's name.
- `description`: What the archetype represents.
- `stat_focus`: Numeric min/max for each stat.
- `role_potency`: Letter grade (F–S) for each role.
## 12. Character Data Generation & Archetype System

To efficiently generate and assign data for 2000+ characters, archetype assignment is now handled by a large language model (LLM). The LLM analyzes all available character and anime data (such as names, descriptions, roles, and other metadata) to determine the most appropriate archetype for each character.

**Key changes:**
- Tag-based mapping and rule-based assignment are no longer used.
- Instead, the LLM uses natural language understanding to match each character to the best-fitting archetype.
- This approach allows for more flexible, context-aware, and scalable character generation.

### Process Overview

1. **Data Aggregation:**
   - Gather all available data for each anime and character (names, descriptions, roles, etc.).
2. **LLM Archetype Assignment:**
   - Use an LLM to analyze the aggregated data and assign the most appropriate archetype to each character.
3. **Archetype Application:**
   - Once assigned, the archetype determines the character's stat focus and role potencies.

### Example Data Structure

```yaml
animes:
  - anime_id: 1
    title: "Magical School Girls"
    # ...other fields...
characters:
  - waifu_id: 101
    name: Sakura
    anime_id: 1
    # ...other fields...
    archetype: Mage
archetypes:
  - name: Mage
    # ...
```

This system allows for scalable, flexible, and lore-friendly character data generation, while supporting both automation and manual refinement.
# Waifu Game Design System Overview & Stats System

## Core Gameplay Loop

- **Roguelike Adventure:** Players start a new run, progressing through a series of random battles, events, and choices. They recruit, upgrade, and manage waifus to build a team. Each run is unique, and only the final team at the end of the run is saved as the player's "champion team."
- **Team-Building:** Strategic choices in recruitment, upgrades, and resource management are key to assembling the strongest possible team during each run.
- **PvE Battles:** Players use their champion team to challenge AI bosses, dungeons, or special events for rewards and progression.
- **PvP Battles:** Players can challenge other users' champion teams in asynchronous or live turn-based battles, competing for ranking and seasonal rewards.
- **Replayability:** Players are encouraged to repeat runs to improve their champion team, discover new waifus, and climb leaderboards.

## How the Stats & Role System Fits In

- Each waifu's unique combination of stats, role potencies, element, and resistances determines their effectiveness in battles and events.
- Power progression is achieved by increasing stats, improving role potencies, using items, and learning new skills during runs and through rewards.
- The system is designed for flexibility, allowing for deep strategy, diverse team compositions, and a wide variety of playstyles.

---


## 1. Roles & Potency System

- **Roles:** Attacker, Mage, Defender, Healer, Buffer, Debuffer, Specialist
- **Potency:** Each waifu has a grade (F, D, C, B, A, S) for each role, not just one. Potency is a multiplier for that role's effectiveness.

**Potency Multipliers:**

  - F: 0.5
  - D: 0.7
  - C: 1.0
  - B: 1.2
  - A: 1.5
  - S: 2.0

---

## 2. Base Stats (8 Total)

- **atk:** Physical attack power
- **mag:** Magic attack power
- **vit:** Vitality, defense against damage
- **spr:** Spirit, healing potency
- **int:** Intelligence, buffer potency
- **lck:** Luck, debuffer potency
- **spd:** Speed, determines action order
- **hp:** Health points


## 3. Element & Resistance System

- Each waifu has a single element: Fire, Water, Earth, Air, Light, Dark
- Each waifu has unique resistances/weaknesses for each element (e.g., Fire: Weak, Water: Resist, etc.)


## 4. Role-Stat Interaction

- The effectiveness of a stat in a given action is:
  - **Effective Value = Raw Stat × Corresponding Role Potency Multiplier**
- Each role's effectiveness is determined by its corresponding stat and the waifu's potency grade for that role.
- Example mappings:
  - Attacker: atk × Attacker Potency
  - Mage: mag × Mage Potency
  - Defender: vit × Defender Potency
  - Healer: spr × Healer Potency
  - Buffer: int × Buffer Potency
  - Debuffer: lck × Debuffer Potency
  - Specialist: spd × Specialist Potency


## 5. Stat Versatility

- Stats are not exclusive to one role; they can influence multiple mechanics.
  - `spd` affects turn order, evasion, and crit rate.
  - `vit` reduces both physical and magical damage.
  - `int` and `lck` affect skill success rates, status effect chances, and event outcomes.
  - `atk` and `mag` may both contribute to hybrid skills.


## 6. Power Progression

- **Increase stats directly** (e.g., +10 atk)
- **Increase potency directly** (e.g., Attacker Potency C → B)
- **Use items** (temporary or permanent boosts)
- **Learn skills** (new abilities, passive or active)


---


### Passives

- Passive abilities learned by waifus.
- Activate automatically when specific conditions are met (e.g., HP below 50%, after attacking, when buffed).
- Once learned, always available to that waifu.


### Equipment

- Equipable passives that can be granted to any waifu.
- Provide passive effects while equipped.
- Can be unequipped, but will break and be lost upon removal.
- Allow for flexible, strategic customization with a risk/reward tradeoff.


### Items

- Single-use consumables.
- Grant an immediate, one-time effect (e.g., heal, stat boost, revive, instant buff/debuff).
- Used during battles or events for tactical advantage.


### Skills

- Usable skills that a waifu can activate during battle.
- Require player input or AI decision to trigger.
- May have cooldowns, resource costs, or specific activation conditions.
- Provide tactical options such as attacks, buffs, debuffs, healing, or unique effects.

---


## 8. Example Waifu Data Structure

```yaml
waifu_id: 101
name: Sakura
element: Fire
element_resistances:
  Fire: Weak
  Water: Resist
  Earth: Neutral
  Air: Neutral
  Light: Neutral
  Dark: Neutral
potency:
  Attacker: B
  Mage: S
  Defender: D
  Healer: F
  Buffer: C
  Debuffer: A
  Specialist: B
stats:
  atk: 120
  mag: 180
  vit: 90
  spr: 60
  int: 100
  lck: 110
  spd: 130
  hp: 900
```


## 9. Example Action Formulas

- **Attack:** Damage = atk × Attacker Potency × (other modifiers)
- **Magic:** Damage = mag × Mage Potency × (other modifiers)
- **Heal:** Heal = spr × Healer Potency × (other modifiers)
- **Buff:** Buff Strength = int × Buffer Potency × (other modifiers)
- **Debuff:** Debuff Strength = lck × Debuffer Potency × (other modifiers)
- **Specialist:** Effectiveness = spd × Specialist Potency × (other modifiers)


## 10. Battle System

- **Turn-Based Queue:**  
  All waifus (allies and enemies) are placed in a queue based on their speed (or other initiative stat).

- **Turn Order:**  
  The waifu at the top of the queue acts. After acting, they are placed back in the queue according to their speed.

- **Action Usage:**  
  - Each action (skill, attack, etc.) has its own cooldown.
  - Some actions have specific conditions (e.g., healing only triggers if an ally is low HP).
  - On their turn, a waifu will automatically use all available actions that are off cooldown and meet their conditions.

- **Automation:**  
  The entire battle is automatic—no player input during combat. All decisions are made by the AI based on action availability and conditions.



## 11. Roguelike Adventure Gameplay Loop

- **Deck Selection:**  
  Before starting a run, each player selects a deck of 9 waifus.

- **Initial Team:**  
  The run begins with the player choosing 1 waifu from their deck as their starting team member.

- **Team Expansion:**  
  Players can expand their team through special events. When expansion is allowed, they choose an additional waifu from their deck to join the team.

- **Core Actions Each Turn:**  
  - **Rest:** Recover HP for the team.
  - **Training:** Increase stats; may trigger special events.
  - **Move:** Choose to move in up to 3 directions. Each movement leads to uncertainty—players may encounter events, enemies, items, etc.


- **Boss Encounters:**  
  - **Mandatory Bosses:** These bosses are required to progress—such as floor guardians, story bosses, or map bosses that block the way forward. Players must find and defeat them to continue or complete objectives.
  - **Punishing Bosses:** These are special, extremely strong bosses that appear only if the player exceeds the turn limit or fails certain objectives. Their purpose is to punish stalling or failure, and they initiate a battle immediately as a penalty.

### Map & Progression

- The map consists of multiple floors, each represented as a 2D grid.
- There are special locations on each floor that allow the team to go up to the next floor.
- Once the team goes up a floor, they cannot return to lower floors.
- The main objective is to reach a specific floor, defeat a mandatory boss, or achieve another set goal.
- If the player does not reach the goal within a set number of turns, a punishing boss will appear and force a battle as a penalty (see Punishing Bosses above).
---


---

*This document defines the core of the waifu stats and role system for Geminya. All future gameplay, balance, and feature additions should reference this design.*
