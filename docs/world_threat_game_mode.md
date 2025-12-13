# Game Mode Design: World Threat

## 1. Concept Overview

**World Threat** is a server-wide cooperative game mode where all players work together to fight a powerful boss. Unlike expeditions, which are individual journeys, the World Threat is a persistent, shared enemy that evolves over time. Players contribute by fighting the boss to score points and earn rewards, both individually and collectively. The mode emphasizes strategic team building to counter the boss's ever-changing affinities.

## 2. The World Threat Boss

The World Threat is a singular, server-wide entity with unique attributes and mechanics.

### 2.1. Core Attributes

* **Name**: The name of the boss (e.g., "The Crimson Tyrant", "Void Leviathan").
* **HP**: The boss does not have a traditional HP pool. Instead, its "health" is represented by a server-wide point total that players contribute to.
* **Affinities & Stats**: The boss has several dynamic attributes that evolve:
  * **Affinities**: Two types, **Buffs** and **Curses**.
  * **Stats**: Two types, **Dominant Stats** (2 total) and a **Cursed Stat** (1 total).
* **Evolution**: After every player action (Fight or Research), the boss's affinities and stats will be updated.
  * A new buff/curse is added, replacing a random existing one if the cap is reached.
  * The 2 Dominant Stats and 1 Cursed Stat are re-rolled.
* **Caps**: There is a configurable maximum number of buffs and curses (e.g., 3 of each).
* **Adaptation**: The boss adapts based on server-wide actions. After the first 5 total `Research` actions on the server, the boss gains a permanent extra buff slot. After the second 5 `Research` actions, it gains another. However, after adapting each time, it will take 20% less damage (0.8x multiplier) from all subsequent `Fight` actions.

### 2.2. Affinity & Stat System

* **Buffs**: These work exactly like `favored` affinities in the expedition system. Characters possessing a buffed affinity (e.g., a specific element, archetype, or series) will contribute to a higher team power.
* **Curses**: This is a hard restriction. If an affinity is cursed (e.g., the "Shounen" genre is cursed), **any character with that affinity cannot be selected** for the fight.
* **Dominant Stats**: These 2 stats are the most effective against the boss. A character's score in these stats will contribute positively to the team's Base Power.
* **Cursed Stat**: This stat is ineffective against the boss. A character's score in this stat will be deducted from the team's Base Power, discouraging the use of "jack-of-all-trades" characters who are high in every stat.


## 3. Player Interaction

### 3.1. Daily Actions

* Each player can perform **one action per day**. The cooldown resets at **midnight UTC+7** (Vietnam/Bangkok timezone).
* Players can choose between two actions: `Fight` or `Research`.

### 3.2. Action Types

* **Fight**: The player assembles a team of characters to attack the boss. This action scores points and grants immediate rewards.
* **Research**: The player forgoes a fight to prepare for the next one. This action grants a **Research Stack**.
  * Each Research Stack multiplies the points earned from the player's **next fight** by **x2**.
  * This can be stacked up to a maximum of **x4** (requiring two consecutive `Research` actions).
  * After a `Fight` action, all Research Stacks are consumed.

## 4. Combat System (The `Fight` Action)

### 4.1. Team Composition

* A team consists of **6 characters**.
* Characters matching any of the boss's active **Curses** cannot be included in the team.

### 4.2. Point Calculation

The points earned from a fight will be calculated based on a formula similar to the expedition system's "Team Power," but adapted for this mode:

`Points = (Base_Power * Affinity_Multiplier * Series_Multiplier) * Research_Multiplier`

* **Base Power**: Calculated from the team's stats. For each character, this is the `sum of their Dominant Stats` minus `their Cursed Stat`.
* **Affinity Multiplier**: Increased by characters matching the boss's **Buffs**.
* **Series Multiplier**: A significant bonus (e.g., x1.5) is applied if **all 6 characters** in the squad are from the same series.
* **Research Multiplier**: x2 or x4 if the player has active Research Stacks.

### 4.3. Daphine Bonus

* If Daphine is included in the team, a **x1.2 multiplier** is applied to the **immediate rewards** (currency, items) gained from that fight. This bonus does not affect the points scored.

## 5. Reward System

### 5.1. Immediate Fight Rewards

* After each `Fight` action, the player receives a base amount of currency and potentially items.
* The quantity and quality of these rewards are based on the points scored in that fight.
* The Daphine bonus applies to these rewards.

### 5.2. Cumulative Rewards

The World Threat features two tracks for cumulative rewards: one for individual player progress and one for the entire server's collective effort.

#### Individual Rewards

* Each player has a personal, cumulative score for the current World Threat.
* The system will have a series of **personal checkpoints** (e.g., at 10,000, 25,000, and 50,000 total points).
* When a player's cumulative score reaches a checkpoint, they will automatically receive a significant, one-time reward.

#### Server-Wide Rewards

* All points scored by all players contribute to a server-wide total.
* This total unlocks **global checkpoints** for everyone on the server.
* When a server checkpoint is reached, **all players** who have participated in the event (i.e., have scored at least 1 point) can claim a special reward.

## 6. Game Flow and Lifecycle

1. **Start**: An administrator runs a script to activate a new World Threat boss, resetting all server-wide and individual progress from the previous one.
2. **Daily Cycle**: Players perform their daily `Fight` or `Research` action. With each action, the boss may evolve its buffs and curses.
3. **Progression**: Players accumulate points, hit personal reward checkpoints, and contribute to the server-wide effort.
4. **End**: The event continues indefinitely until an administrator decides to end it by running the reset script, which archives the final results and starts a new World Threat.
