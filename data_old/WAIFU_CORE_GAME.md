## Game Design Document: Waifu Stats & Gameplay Systems

### **Introduction: Core Gameplay Loop**

The game is a session-based, roguelike auto-battler focused on strategic team-building and character progression. The core loop is divided into two main phases:

1.  **The Roguelike Adventure:** Players select a starting "deck" of 9 characters and embark on a run. During the run, they navigate a multi-floor map, making strategic choices in battles, events, and resource management to recruit and upgrade a small team of waifus. Each run is a unique, self-contained adventure.
2.  **Persistent Progression & Competition:** At the end of a successful run, the player's final team is saved as their "Champion Team." This persistent team can be used in challenging PvE content and asynchronous PvP battles to compete for leaderboard rankings and seasonal rewards.

This design emphasizes **pre-combat preparation as the core skill**. The gameplay is not *in* the battle; it is in building the perfect machine that wins the battle on its own.

---

### **Part I: The Anatomy of a Character**

Every character is defined by a unique combination of stats, roles, and elemental properties that dictate their performance in combat.

#### **1. Base Stats (The 8 Core Attributes)**
*   **hp:** Health Points
*   **atk:** Physical attack power
*   **mag:** Magic attack power
*   **vit:** Vitality - Reduces incoming damage
*   **spr:** Spirit - Increases healing effectiveness
*   **int:** Intelligence - Governs buff effectiveness
*   **lck:** Luck - Governs debuff effectiveness
*   **spd:** Speed - Determines turn order

#### **2. Roles & Potency**
Instead of a single class, each character has a proficiency grade for all **7 combat roles**. This grade, called Potency, acts as a multiplier for role-based actions and is the **key factor in the AI's decision-making**.

*   **The 7 Roles:** Attacker, Mage, Defender, Healer, Buffer, Debuffer, Specialist
*   **Potency Grades & Multipliers:**
    *   **S:** 2.0x, **A:** 1.5x, **B:** 1.2x, **C:** 1.0x, **D:** 0.7x, **F:** 0.5x

#### **3. Element & Resistance System**
*   Each character has a primary element and a unique profile of resistances and weaknesses.

#### **4. The Archetype System**
An LLM (Large Language Model) analyzes each character's source material to assign them a fitting **Archetype**. This determines their general stat focus, base Role Potencies, and their **default AI targeting behavior** in combat (e.g., a Healer AI targets the most wounded ally).

---

### **Part II: Character Progression & Customization**

Player progression is divided into permanent, account-level growth and temporary, in-run adaptation.

#### **1. The Awakening System (Permanent Progression)**
The sole method of permanent character growth is "Awakening," which increases a character's star rarity up to 5 stars. Awakening is achieved by consuming duplicates or special fragments and unlocks new, pre-defined skills and passives.

#### **2. The Abilities System: Skills & Passives**
A character's abilities are divided into **Skills (Active)** and **Passives (Automatic)**.

**Skill Types (Active Abilities):**
*   **Basic Attack:** A universal, no-cooldown skill every character possesses.
*   **Normal Skills:** A wide pool of common skills (e.g., "Fireball," "Slash").
*   **Signature Skills:** Unique skills inherent to a character.
*   **Ultimate Skills:** Exceptionally powerful skills for base 3-star characters, requiring specific in-battle **conditions** to be met before activation.
*   **Series Skills:** Thematic skills shared by characters from the same anime, which are **temporary** and acquired for the duration of a run via special events.

**Passive Types (Automatic Abilities):**
*   **Generic Passives:** Common, straightforward abilities (e.g., "+10% HP").
*   **Signature Passives:** Unique abilities tied to a character's lore.
*   **Series Passives:** Thematic passives shared by characters from the same anime, which are **temporary** and acquired during a run.

#### **3. Awakening Progression Path**
The skills and passives a character learns are pre-defined and unlocked based on their **base rarity** as they are Awakened.

**Base 1-Star Character Progression:**
*   **1★ (Base):** 1 Normal Skill, 1 Generic Passive
*   **2★:** Unlocks 2nd Normal Skill
*   **3★:** Unlocks 3rd Normal Skill, 2nd Generic Passive
*   **4★:** Unlocks 4th Normal Skill
*   **5★:** Unlocks 5th Normal Skill

**Base 2-Star Character Progression:**
*   **2★ (Base):** 2 Normal Skills, 1 Signature Passive
*   **3★:** Unlocks 1 Signature Skill, 2nd Generic Passive
*   **4★:** Unlocks 3rd Normal Skill
*   **5★:** Unlocks 4th Normal Skill

**Base 3-Star Character Progression:**
*   **3★ (Base):** 1 Signature Skill, 2 Normal Skills, 2 Signature Passives
*   **4★:** Unlocks **Ultimate Skill**
*   **5★:** Unlocks 2nd Signature Skill

#### **4. Equipment (Temporary Customization)**
Equipment pieces grant a powerful **passive ability** for the duration of a single run. They are the primary tool for adapting a team's strategy mid-run. Once equipped, **equipment will break and be lost forever upon removal.**

---

### **Part III: The Roguelike Adventure**

The core gameplay occurs during a run, where players navigate a map and build their team.

#### **1. Deck Selection & Team Traits**
Before a run, the player selects a **deck of 9 characters**. The composition of this deck activates powerful **Team Traits** for the entire run based on Archetype and Series synergy.

#### **2. The Event System: The Heart of the Adventure**
Events are the primary engine of the roguelike experience. An event can have a wide array of powerful and permanent (for the run) consequences, including stat changes, resource gains/losses, team composition changes (including character death), and the unlocking of temporary **Series Skills** and **Series Passives**.

#### **3. Map Progression & Bosses**
*   The map consists of multiple floors on a 2D grid.
*   **Mandatory Bosses:** Powerful enemies that block progress.
*   **Punishing Bosses:** Overwhelmingly strong bosses that appear if a player exceeds a floor's turn limit.

---

### **Part IV: The Combat System - Strategic Automation**

Battles are fully automated. The player's skill is expressed entirely through their pre-combat preparation.

#### **1. The Formation Phase**
Before every battle, the player arranges their active party on a **2x3 grid** (Front Row & Back Row). This positioning is a critical strategic layer for protecting fragile units and managing enemy aggression.

#### **2. The Action Queue**
All combatants are placed in an action queue based on their `spd` stat. The character at the top of the queue takes their turn.

#### **3. Automated Action Priority Logic**
On a character's turn, their AI uses skills based on a strict, predictable hierarchy. The player has no direct control during combat.

**AI Decision-Making Hierarchy:**

1.  **Check by Skill Tier:** The AI first checks for available skills in descending order of power:
    *   **Ultimate > Signature > Normal > Basic Attack**
    *   It will always attempt to use a skill from the highest possible tier that is off cooldown and has its conditions met.

2.  **Potency-Based Tiebreaker:** If multiple skills of the *same tier* are available (e.g., two "Normal Skills"), the AI will choose the skill that corresponds to the character's **highest Role Potency grade**. This ensures a character naturally plays to their strengths.

**Example of Tiebreaker:**
A character has two available Normal Skills:
*   *Skill A:* A healing spell (Healer Role)
*   *Skill B:* An attack spell (Attacker Role)

If the character's **Healer Potency is 'A'** and their **Attacker Potency is 'C'**, the AI will **always prioritize using Skill A** if there is a valid target. It will only use Skill B if Skill A is on cooldown or there are no allies to heal. In the rare case of a potency tie, a pre-defined sub-priority (e.g., Healer > Attacker) is used.

#### **4. Action Formulas**
*   **Formula:** `Effective Value = Raw Stat × Role Potency Multiplier`

---

### **Part V: Items (Strategic Resources)**

Items are single-use consumables. They **cannot be used during battle** and serve as preparatory tools for recovery and pre-battle buffs.