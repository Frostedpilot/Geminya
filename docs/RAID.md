# **Master Design Document: World-Threat Expeditions (V5 - Final Blueprint)**
### **Project: Anime Character Auto-Battler - Expansion 2**

### **Table of Contents**
1.  **High-Level Vision**
    *   1.1 Game Mode Concept
    *   1.2 Core Design Philosophy: "A Collaborative War of Attrition"
    *   1.3 Player Experience Goals
2.  **Core Gameplay Loop: The Siege**
    *   2.1 Phase 1: The Threat Emerges
    *   2.2 Phase 2: The Strike (Player Action)
    *   2.3 Phase 3: Resolution & Reaction
    *   2.4 Phase 4: The Aftermath
3.  **The Raid Engine: Detailed Mechanics**
    *   3.1 The World-Threat Entity (The Boss)
    *   3.2 The Player's Arsenal: Character Roster Management
    *   3.3 Player Actions: Fight vs. Analyze
    *   3.4 The Retaliation System: Evolving Curses
    *   3.5 The Analysis System: Unlocking Weaknesses
    *   3.6 Reward Structure
4.  **User Experience & Interface Flow**

---

## **1.0 High-Level Vision**

#### **1.1 Game Mode Concept**
World-Threat Expeditions are limited-time, server-wide raid events where the player base collaborates to defeat a single, powerful "Raid Boss." Players use their entire character roster to launch **instant Strikes**, as each character can only be used **once** per event.

Players face a crucial choice with each strike: **Fight** the boss to deal direct damage, or **Analyze** it to contribute to a single, global research effort. Filling the global **Analysis Bar** to one of its ten thresholds unlocks a new, randomly determined Weakness for the boss, creating a deep strategic layer that requires server-wide coordination.

#### **1.2 Core Design Philosophy: "Collaborative Strategy & Roster Mastery"**
*   **Every Character Matters:** With a one-use-per-character rule, players are forced to utilize their entire collection, making every character a valuable resource.
*   **Strategic Community Choice:** The "Fight vs. Analyze" choice is a community-level decision. Do we focus on burning down the boss now, or do we invest in Analysis to make future attacks stronger?
*   **Dynamic Battlefield:** The boss's reactive **Curses** and the community's randomly unlocked **Weaknesses** ensure the optimal team composition is constantly in flux.

#### **1.3 Player Experience Goals**
*   To create a deep, strategic challenge that rewards long-term collection and roster planning.
*   To foster a strong sense of community and shared purpose.
*   To make every player's choice feel impactful.

## **2.0 Core Gameplay Loop: The Siege**

1.  **The Threat Emerges:** A World-Threat appears for 7 days with its initial Affinities and **Dominant Stats** revealed.
2.  **The Strike (Player Action):** On a one-hour personal cooldown, a player chooses to **Fight** or **Analyze**. They assemble a team of 1-6 **unused** characters.
3.  **Resolution & Reaction:**
    *   The strike is resolved instantly. The team's score is calculated based only on the boss's **Dominant Stats**.
    *   **Fight:** Score is converted to Damage, reducing the boss's global HP.
    *   **Analyze:** Score is converted to Analysis Points and added to the single, global Analysis Bar.
    *   The boss **Retaliates** with new **Curses** at set intervals.
    *   The community achieves **Breakthroughs**, unlocking a random new **Weakness** when the Analysis Bar reaches a threshold.
4.  **The Aftermath:** The event ends. Rewards are distributed.

## **3.0 The Raid Engine: Detailed Mechanics**

#### **3.1 The World-Threat Entity (The Boss)**
*   **`total_hp`:** A colossal number (e.g., 1 Billion).
*   **`dominant_stats`:** An array of 1-8 stats (e.g., `["atk", "spd", "lck"]`) that are the **only stats used** to calculate the Expedition Score for this boss.
*   **`weaknesses` (Initial Favored):** 1-2 starting affinities.
*   **`resistances` (Permanent Disfavored):** 1-2 starting affinities.
*   **`curse_pool`:** A large list of potential **Disfavored Affinities** the boss can apply.
*   **`curse_limits`:** Max active Curses per type (e.g., `{ "elemental": 2, "genre": 1 }`).
*   **`analysis_thresholds`:** An array of 10 point values for the global Analysis Bar (e.g., `[50M, 120M, 250M, ... ]`).
*   **`analysis_reward_pool`:** A weighted pool defining what *types* of Weaknesses can be unlocked.

#### **3.2 The Player's Arsenal: Character Roster Management**
*   **One Use Per Character:** Once a character is used in a Strike Mission (Fight or Analyze), they are "exhausted" and cannot be used again for the duration of this World-Threat event.
*   **Team Size:** 1 to 6 characters per strike.

#### **3.3 Player Actions: Fight or Analyze**

**1. Calculate Expedition Score:**
*   **Formula:** `Score = (Sum of the boss's Dominant Stats for all team members) * Affinity Multiplier`.
*   *Example:* If `dominant_stats` is `["atk", "vit"]`, the score is `(Total Team ATK + Total Team VIT) * Multiplier`.

**2. Resolve Action:**
*   **If FIGHT:**
    *   `Damage = floor(Score / 10)`.
    *   This damage is subtracted from the boss's global HP.
*   **If ANALYZE:**
    *   `Analysis Points = floor(Score / 10)`.
    *   These points are added to the single, global Analysis Bar.
    *   Players can contribute to the Analyze action an infinite number of times.

#### **3.4 The Retaliation System: Evolving Curses**
*   **Trigger:** Occurs after a fixed number of total server-wide strikes.
*   **Process:**
    1.  A random Affinity is selected from the boss's `curse_pool`.
    2.  If the `curse_limit` for that affinity's type has been reached, a random existing Curse of the **same type** is replaced. Otherwise, the new Curse is added.

#### **3.5 The Analysis System: Unlocking Weaknesses**
This system is the core community progression mechanic.
*   **Global Analysis Bar:** There is one shared progress bar for the entire server, with **10 thresholds**.
*   **Breakthrough (Threshold Reached):**
    1.  The system performs a weighted roll on the boss's `analysis_reward_pool` to determine the **type** of Weakness to be unlocked (e.g., 40% chance for Elemental, 30% for Archetype, 20% for Genre, 10% for Series).
    2.  The system then performs a second, unweighted roll from within the chosen affinity type to select the **specific** Weakness (e.g., if "Elemental" was chosen, it randomly picks one from `fire`, `water`, `wind`, etc.).
    3.  This new **Weakness (Favored Affinity)** is permanently added to the boss for all players.
    4.  The next threshold on the Analysis Bar becomes the new target.
    5.  Once all 10 thresholds are met, the Analysis phase is complete for the event.

#### **3.6 Reward Structure**
*   **Strike Rewards:** Small, immediate rewards for completing a Fight or Analyze action.
*   **Milestone Rewards:** Based on a player's **total personal damage contribution**.
*   **Analysis Rewards:** When a community-wide Analysis threshold is met, **all players who have contributed at least 1 point** to the Analysis Bar receive a bonus cache of items.
*   **Victory Cache:** The ultimate prize, given to all participants if the boss is defeated.

## **4.0 User Experience & Interface Flow**

#### **4.1 The Raid Hub Screen**
*   **Boss Panel:** Displays HP, Art, and a list of **Dominant Stats**.
*   **Affinities Panel:** Shows current Weaknesses and the evolving list of Curses.
*   **Analysis Panel:**
    *   A single, large progress bar showing `Current Analysis Points / Next Threshold`.
    *   A counter showing `Thresholds Unlocked: X/10`.
*   **Action Panel:** "Fight" and "Analyze" buttons, with a shared one-hour cooldown timer.

#### **4.2 Team Selection Screen**
*   The character roster clearly displays "Available" and "Used" characters.
*   The UI highlights which stats on each character card are contributing, based on the boss's `dominant_stats`.

#### **4.3 The After-Action Report**
*   **If Fight:** Shows "Damage Dealt: X".
*   **If Analyze:** Shows "Analysis Points Contributed: Y".
*   Will display a server-wide announcement if the player's strike was the one to trigger a Retaliation or a Breakthrough. The Breakthrough announcement will dramatically reveal the new Weakness: **"Breakthrough! The team has discovered a weakness to the [Elemental/Archetype/etc.] affinity: [AFFINITY NAME]!"**