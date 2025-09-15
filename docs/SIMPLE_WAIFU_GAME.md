# **Project: Anime Character Auto-Battler**
### **Game Design Document - Final Version**

## **1.0 High Concept**

An automated, turn-based PvP battler where players form teams of six characters from a diverse roster of anime personalities. The core of the game lies in a multi-layered strategic system combining team composition, battlefield positioning, a robust status effect system, and powerful pre-battle bonuses. Each character's identity is fully realized through their unique stats, AI-driven "potencies," and game-changing Signature Skills and Passives. The strategic landscape is kept constantly fresh through rotating **Battlefield Conditions** that alter the fundamental rules of combat on a weekly basis.

## **2.0 Core Gameplay Loop**

1.  **Pre-Battle Phase (Team Formation):** Players check the active **Battlefield Condition**. They then select a team of up to six characters, assign a **Leader**, and arrange them in a front/back row formation. Team composition may activate **Synergy** bonuses.
2.  **Battle Phase (Auto-Battle):** The battle commences. All active bonuses are applied as characters' **Action Gauges** fill based on their `spd`. When a character's gauge is full, they take their turn, after which it resets.
3.  **Post-Battle Phase (Victory/Defeat):** The battle concludes when one team is eliminated or the round limit is reached.

## **3.0 Pre-Battle Strategic Systems**

#### **3.1 Team Composition & Positioning**
*   **Structure:** A 3-slot Front Row and a 3-slot Back Row.
*   **Targeting Rule:** The Back Row cannot be targeted by most skills until the Front Row is empty. Skills that specifically mention hitting the back row are the exception.

#### **3.2 Leader System**
*   **Designation:** Before a battle, the player must designate **one character** on their team as the Leader.
*   **Leader Buff:** The designated Leader receives a **+10% bonus to all of their base stats** (`hp`, `atk`, `mag`, `vit`, `spr`, `int`, `spd`, `lck`) for the duration of the battle.

#### **3.3 Team Synergy Bonuses**

*   **Activation:** If a team includes multiple characters from the same `series`, they gain a tiered, passive bonus.

| Series Example | Tier 1 | Tier 2 | Tier 3 |
| :--- | :--- | :--- | :--- |
| **K-On!** | +10% `spd` for all allies. (2 characters) | +10% `mag` for all allies. (4 characters) | All allies gain a small "Regen" effect for the first 2 rounds. (6 characters) |
| **Re:Zero** | +15% `spr` for all allies. (2 characters) | The first time an ally would be defeated, their HP is set to 1 instead (once per battle). (4 characters) | +10% `lck` for all allies. (6 characters) |
| **Konosuba** | +20% `lck` for all allies. (2 characters) | All skills have a 5% chance to not go on cooldown. (4 characters) | At the start of the battle, apply one random buff to all allies and one random debuff to all enemies. (6 characters) |

#### **3.5 Battlefield Conditions**
*   **Function:** A single, game-wide environmental effect that is active for all PvP battles for a set period (e.g., one week).

| Condition Name | Effect |
| :--- | :--- |
| **Scorching Sun** | All Fire-elemental characters gain +20% ATK/MAG. All Water-elemental characters suffer -10% VIT/SPR. |
| **Mystic Fog** | All characters' `lck` stat is reduced by 50%. Critical hits are less likely. |
| **Gravity Well** | All characters' `spd` is reduced by 30%. |
| **Magic Overflow** | All characters gain +25% `mag`. |
| **Warrior's Proving Ground**| All characters gain +25% `atk`. |
| **Volatile Field** | All critical hits deal 2.0x damage instead of 1.5x. |

## **4.0 Battle System & Character Abilities**

#### **4.1 Dynamic Turn Gauge System**
*   **Action Gauge:** Every character has an Action Gauge (0 to 1000).
*   **First Turn Normalization:** At the start of the battle, each character's Action Gauge is set to a random value between **400 and 600**.
*   **Turn Order:** The gauge fills each "tick" by an amount equal to the character's `spd`. The first character to reach 1000 acts, then their gauge resets to its overflow value (e.g., 1015 becomes 15). In case of a tie, the character with the higher overflow value acts first.

#### **4.2 Universal Skill Library & Scaling Parameters**
*   **Skill Parameters:** `Power Weight`, `Floor`, `Ceiling`, `Softcap 1 (SC1)`, `Softcap 2 (SC2)`, `Post-Cap Rate`.

**Attacker Potency (Physical - `atk`)**
| Skill Name | Power Weight | Floor | SC1 | SC2 | Post-Cap Rate | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Power Strike** | 50 | 20 | 50 | 200 | 0.5 | 100% ATK damage to one front-row enemy. |
| **Flurry of Blows** | 30 | 15 | 40 | 150 | 0.4 | Hits one front-row enemy twice for 60% ATK damage each. |
| **Armor Break** | 20 | 25 | 60 | 220 | 0.4 | 80% ATK damage, ignoring 50% of `vit`. |
| **Heavy Slam** | 15 | 40 | 80 | 300 | 0.6 | 150% ATK damage. User's `spd` is halved next round. |
| **Cleave** | 25 | 15 | 70 | 250 | 0.3 | 70% ATK damage to all enemies in the front row. |
| **Execute** | 15 | 30 | 60 | 240 | 0.5 | 100% ATK damage. Damage is doubled if target is below 30% HP. |
| **Rampage** | 10 | 10 | 80 | 300 | 0.3 | 60% ATK damage to three random enemies, regardless of row. |
| **Bleeding Strike** | 20 | 20 | 50 | 200 | 0.4 | 75% ATK damage and applies "Bleed" for 2 turns. |

**Mage Potency (Magical - `mag`)**
| Skill Name | Power Weight | Floor | SC1 | SC2 | Post-Cap Rate | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Mana Bolt** | 50 | 20 | 50 | 200 | 0.5 | 100% MAG damage to one front-row enemy. |
| **Chain Lightning** | 25 | 15 | 60 | 220 | 0.4 | 80% MAG damage to one target, jumps for 40% to another. |
| **Ignite** | 20 | 15 | 50 | 180 | 0.3 | 70% MAG damage and applies "Burn" to one target. |
| **Arcane Overload** | 15 | 45 | 90 | 320 | 0.6 | 160% MAG damage. User suffers 10% recoil damage. |
| **Fireball** | 25 | 20 | 70 | 250 | 0.4 | 90% MAG damage to the target and 40% to adjacent targets. |
| **Frost Nova** | 20 | 10 | 60 | 200 | 0.3 | 60% MAG damage to all front-row enemies; 25% chance to "Slow". |
| **Arcane Missile** | 10 | 10 | 80 | 300 | 0.3 | Fires 3 missiles for 50% MAG damage to random enemies. |
| **Silence** | 15 | 10 | 40 | 150 | 0.2 | 50% MAG damage and prevents target from using Mage skills. |

**Healer Potency (Support - `int`, `spr`)**
| Skill Name | Power Weight | Floor | SC1 | SC2 | Post-Cap Rate | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Lesser Heal** | 50 | 50 | 50 | 200 | 0.5 | Restores a moderate amount of HP to one ally. |
| **Regen** | 25 | 20 | 40 | 150 | 0.4 | Applies a "Heal Over Time" effect to one ally. |
| **Greater Heal** | 20 | 120 | 100 | 300 | 0.6 | Restores a large amount of HP. 1-turn cooldown. |
| **Cleanse** | 15 | N/A | N/A | N/A | N/A | Removes all debuffs from one ally. |
| **Row Heal** | 30 | 30 | 60 | 220 | 0.3 | Restores a small amount of HP to all allies in a row. |
| **Mass Heal** | 10 | 25 | 80 | 280 | 0.2 | Restores a small amount of HP to the entire team. 2-turn cooldown. |
| **Barrier** | 20 | 40 | 50 | 200 | 0.4 | Grants one ally a temporary HP shield. |
| **Resurrection** | 5 | N/A | N/A | N/A | N/A | Revives a defeated ally with 25% HP. Once per battle. |

**Buffer/Debuffer Potency (Support - `int`)**
| Skill Name | Power Weight | Floor % | Ceiling % | SC1 | SC2 | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Rally/Weaken** | 40 | 10% | 35% | 80 | 250 | +/- 20% ATK & MAG for one target. |
| **Fortify/Break** | 40 | 10% | 35% | 80 | 250 | +/- 20% VIT & SPR for one target. |
| **Haste/Slow** | 25 | 15% | 50% | 100 | 300 | +/- 30% SPD for one target. |
| **Focus/Curse** | 20 | 20% | 60% | 120 | 320 | +/- 40% LCK for one target. |
| **Aura of Power/Mass Slow**| 10 | 5% | 20% | 150 | 400 | +/- 10-20% ATK/MAG or SPD for a row/team. |

**Defender Potency (Defensive - `vit`, `spr`)**
| Skill Name | Power Weight | Description |
| :--- | :--- | :--- |
| **Guard Stance** | 50 | User doubles their `vit` and `spr` until their next turn. |
| **Provoke** | 30 | Forces a single enemy to target the user on their next attack. |
| **Aegis** | 15 | User takes all damage intended for one specific ally until their next turn. |
| **Riposte Stance** | 20 | User retaliates against the next physical attack for 50% ATK damage. |
| **Shield Wall** | 20 | Increases the `vit` of the entire front row by 25% for 2 turns. |
| **Last Stand** | 5 | For one turn, the user's HP cannot drop below 1. Once per battle. |
| **Reflect** | 15 | Reflects 30% of the next magical damage instance back at the attacker. |
| **Intimidate** | 25 | Lowers the `atk` of all front-row enemies by 15%. |

**Tactician Potency (Utility - `spd`, `lck`)**
| Skill Name | Power Weight | Description |
| :--- | :--- | :--- |
| **Swift Strike** | 30 | A high-priority 70% ATK damage attack. |
| **Mirage** | 15 | Grants user a "Guaranteed Dodge" buff against the next single-target attack. |
| **Study Foe** | 25 | Applies "Vulnerable" to one enemy (next attack is a guaranteed crit). |
| **Accelerate** | 10 | Target ally's Action Gauge is set to 999. |
| **Snipe** | 20 | Deals 90% ATK damage to a single enemy in the **back row**. |
| **Disrupting Shot** | 25 | Deals 50% ATK damage and has a 50% chance to remove one buff from the target. |
| **Smoke Bomb** | 15 | Increases the dodge chance of all allies in the user's row by 20% for 1 turn. |
| **Set Trap** | 10 | Sets a trap on an enemy; they take damage the next time they use a skill. |

#### **4.3 Signature Abilities**
*   **Signature Skills:** When a Signature Skill's conditions are met, the character gains a hidden **"Primed"** status. On their next turn, the AI will use this skill instead of a normal action, and the status is removed. Only usable once per game.
*   **Signature Passives:** Always-on traits that modify a character's stats or abilities.

**A. Signature Skills (Examples)**
| Character | Skill Name | Trigger | Effect |
| :--- | :--- | :--- | :--- |
| **Megumin** | Explosion | Activates once when HP drops below 50%. | Deals massive, unavoidable Fire damage to all enemies. User is Stunned for 2 rounds. |
| **Yor Forger** | Thorn Princess | Activates if an enemy dodges one of Yor's attacks. | Yor immediately gains a +50% ATK and +50% SPD buff for her next turn. |
| **Aqua** | God's Blessing | Activates the first time an ally is defeated. | Fully heals all living allies. 50% chance to revive the fallen ally with 30% HP. |
| **Homura Akemi** | Time Loop | Activates once if an ally is defeated by a critical hit. | Resets the current Round. All characters' HP and status effects revert to what they were at the start of the round. |

**B. Signature Passives (Examples)**
| Character | Passive Name | Effect |
| :--- | :--- | :--- |
| **Kaguya Shinomiya**| Ice Queen's Gaze | At the start of her turn, has a 20% chance to apply "Slow" to a random enemy that does not already have a debuff. |
| **Hitori Gotou** | Bocchi the Rock! | Gains +15% `mag` but suffers -10% `vit`. If she is the last surviving member of her team, all of her stats are increased by 25%. |
| **Mashiro Shiina** | Savant Syndrome | Immune to "Silence" and "Blind." However, has a 10% chance to target a random enemy instead of the optimal one. |
| **Chika Fujiwara**| Subject F | At the end of each round, a random ally and a random enemy each get a random, weak (5%) buff or debuff for 1 turn. |

#### **4.4 Expanded Status Effect System**
*   **Duration:** Counted in **"character turns."**
*   **Stacking Rules:** Pre-battle bonuses are additive; in-battle are multiplicative. A character is limited to **3 active buffs** and **3 active debuffs**.

## **5.0 Combat AI: Three-Phase Skill Selection**

#### **Phase 1: Role Selection**
1.  **Filter Viable Roles:** Determines which skill categories are useful.
2.  **Get Base Weights:** Converts `potency` ratings to numerical weights (S=10, etc.).
3.  **Apply Dynamic Weight Modifiers:** Modifies the weights based on the battlefield context.

| Modifier Name | Trigger Condition | Role(s) Affected | Weight Multiplier |
| :--- | :--- | :--- | :--- |
| Repetition Penalty | Used this role last turn. | The repeated role | **x0.5** |
| Finishing Blow | An enemy is below 25% HP. | Attacker, Mage, Tactician | **x2.0** |
| Triage Priority | An ally is below 30% HP. | Healer | **x3.0** |
| Synergy - Exploit | Ally just landed a debuff. | Attacker, Mage | **x1.5** |
| Synergy - Empower | Self has ATK/MAG buff. | Attacker, Mage | **x1.75** |
| Synergy - Protect | Self has VIT/SPR buff. | Defender | **x2.0** |
| Synergy - Swiftness | Self has SPD buff. | Tactician, Attacker | **x1.5** |
| Counter-Heal | Enemy healed last round. | Debuffer, Attacker | **x1.5** |
| Defensive Stance | Self is below 40% HP. | Defender, Healer | **x1.5** |

4.  **Final Roll:** A weighted random roll selects one role for the turn.

#### **Phase 2: Specific Skill Selection**
A second weighted roll based on the `Power Weight` of skills within the chosen role's library.

#### **Phase 3: Target Selection using Priority Score**
After a skill is chosen, the AI calculates a **Target Priority Score (TPS)** for every valid target. The target with the highest TPS is selected. If there's a tie, a random choice is made between the tied targets.

**A. Offensive Single-Target Skills (Damage)**
`TPS = Base Score * Kill Priority Multiplier * Elemental Weakness Multiplier * Debuff Multiplier`

*   **Base Score:** 100
*   **Kill Priority Multiplier:** `(1 / (Current HP / Max HP))` (e.g., a target at 25% HP has a 4x multiplier).
*   **Elemental Weakness Multiplier:** `1.5` if the target is weak to the attack's element.
*   **Debuff Multiplier:** `1.4` if the target has a "Break" or "Vulnerable" debuff.

**B. Healing Single-Target Skills**
`TPS = Base Score * Missing Health Multiplier + High-Value Ally Bonus + Debuff Bonus + Leader Bonus`

*   **Base Score:** 100
*   **Missing Health Multiplier:** `(1 / (Current HP / Max HP))`
*   **High-Value Ally Bonus:** `(Target's ATK + MAG) / 10`
*   **Debuff Bonus:** `+150` if the ally has Stun or Heal Block; `+75` if they have a strong DoT.
*   **Leader Bonus:** `+50` if the target is the team's Leader.

**C. Buffing Single-Target Skills**
`TPS = Base Score + Role Synergy Bonus + Turn Order Bonus + Leader Bonus`

*   **Base Score:** 100
*   **Role Synergy Bonus:** `+ (Target's Relevant Stat)` (e.g., `+ATK` for a Rally buff).
*   **Turn Order Bonus:** `+ (Target's Action Gauge / 10)`
*   **Leader Bonus:** `+30` if the target is the team's Leader.

**D. Debuffing Single-Target Skills**
`TPS = Base Score + Threat Bonus + Turn Order Bonus * Un-debuffed Multiplier`

*   **Base Score:** 100
*   **Threat Bonus:** `+ (Target's relevant stat)` (e.g., `+(ATK+MAG)/2` for Weaken, `+SPD` for Slow).
*   **Turn Order Bonus:** `+ (Target's Action Gauge / 5)`
*   **Un-debuffed Multiplier:** `1.2` if the target has no other active debuffs.


## **6.0 Combat Resolution Formulas**

#### **6.1 Universal Scaling Formula**
*   `PotencyValue` is the raw, pre-scaling number from 6.2.
*   `Floor`, `Ceiling`, `SC1`, `SC2`, `PostCapRate` are unique to each skill.

1.  **If `PotencyValue` ≤ `SC1`:** `FinalValue = Floor`
2.  **If `SC1` < `PotencyValue` ≤ `SC2`:** `FinalValue = Floor + (PotencyValue - SC1)`
3.  **If `PotencyValue` > `SC2`:** `FinalValue = (Floor + (SC2 - SC1)) + ((PotencyValue - SC2) * PostCapRate)`
    *   *For Buffs/Debuffs, `FinalValue` is capped by `Ceiling`.*

#### **6.2 Potency Value Formulas**
*   **Initial Physical Damage:** `(Attacker's ATK * SkillMultiplier) * (1 - (Target's VIT)/(150 + Target's VIT)`
*   **Initial Magical Damage:** `(Attacker's MAG * SkillMultiplier) * (1 - (Target's VIT * 0.6 + Target's SPR * 0.4)/(150 + Target's VIT * 0.6 + Target's SPR * 0.4)`
*   **Heal Potency:** `(Caster's INT * 0.5) + (Caster's SPR * 1.25)`
*   **Effect Potency (for Buffs/Debuffs):** `Caster's INT`

#### **6.3 Final Combat Calculations**
1.  Calculate **Initial Damage** (Potency Value) using 6.2. Minimum of 1.
2.  Apply the **Universal Scaling Formula** (6.1) to get the `Scaled Damage`.
3.  Apply modifiers: `Final Damage = Scaled Damage * Elemental Modifier * Critical Modifier`

#### **6.4 Other Formulas**
*   **Dodge %:** `5 + ((Target SPD + Target LCK) - (Attacker SPD + Attacker LCK)) / 20` (Capped 5%-40%)
*   **Crit %:** `5 + (Attacker LCK - Target LCK) / 10` (Capped 5%-50%)
*   **Status Application %:** `Base Chance % + ((Attacker's LCK - Target's LCK) / 10)` (Capped 10%-90%)

## **7.0 Victory & End-of-Game Conditions**

*   **Victory:** A team wins when all opposing characters are defeated.
*   **Battle Limit:** The battle ends after a **30-round equivalent**. A "Round" is defined as occurring every time the total Action Gauge points gained across all characters equals `(Number of living characters * 1000)`.
*   **Draw Resolution:** If no winner is declared by the time limit, the team with the higher total remaining HP percentage wins.

#### **7.1 Endgame Accelerator: "Sudden Death"**
*   **Trigger:** Activates after the **20th round-equivalent** has passed.
*   **Effect:** At the start of each subsequent "round-equivalent," all living characters' stats are modified based on their **base** values. For Round-Equivalent `N` (where `N` ≥ 21):
    *   `Current ATK = Base ATK * (1.1 ^ (N - 20))`
    *   `Current MAG = Base MAG * (1.1 ^ (N - 20))`
    *   `Current SPR = Base SPR * (0.9 ^ (N - 20))`
*   **Purpose:** To ensure battles escalate in lethality and reach a decisive conclusion.