# 📋 JSON DATA FORMATS GUIDE
## Complete reference for all game data JSON files

## 🗡️ **SKILLS (`general_skills.json`)**

### **Structure:**
```json
{
  "skills": {
    "category_name": {
      "skill_id": {
        "name": "Display Name",
        "category": "physical|magical|support|special",
        "description": "What the skill does",
        "cost": 10,                    // MP/Energy cost
        "cooldown": 2,                 // Turns before reuse (0 = no cooldown)
        "target_type": "single_enemy|all_enemies|single_ally|all_allies|self",
        "scaling": {
          "primary_stat": "atk|mag|spd|int",  // Which stat determines power
          "potency": 120                      // Base damage multiplier
        },
        "effects": [
          {
            "type": "damage|heal|status_effect|stat_modifier",
            "value": 120,                     // Base effect value
            "damage_type": "fire|water|earth|wind|nature|neutral|void|light|dark"
          }
        ]
      }
    }
  }
}
```

### **Example - New Lightning Skill:**
```json
{
  "skills": {
    "lightning_attacks": {
      "thunder_bolt": {
        "name": "Thunder Bolt",
        "category": "magical", 
        "description": "Strikes enemy with lightning, chance to stun",
        "cost": 18,
        "cooldown": 1,
        "target_type": "single_enemy",
        "scaling": {
          "primary_stat": "mag",
          "potency": 160
        },
        "effects": [
          {
            "type": "damage",
            "value": 160,
            "damage_type": "lightning"
          },
          {
            "type": "status_effect",
            "effect": "stunned",
            "duration": 1,
            "chance": 25
          }
        ]
      }
    }
  }
}
```

---

## ✨ **STATUS EFFECTS (`status_effects.json`)**

### **Structure:**
```json
{
  "status_effects": {
    "category": {
      "effect_id": {
        "name": "Display Name",
        "type": "buff|debuff|special",
        "description": "Effect description",
        "duration": 3,                    // Turns effect lasts
        "stacking_rule": "no_stack|stack_duration|stack_intensity",
        "max_stacks": 1,
        "priority": "low|normal|high",    // Application priority
        "stat_modifier": {                // Optional: stat changes
          "stat_type": "hp|atk|mag|vit|spr|int|spd|lck",
          "modifier_value": 0.30,         // +30% or +30 flat
          "modifier_type": "percentage|flat"
        }
      }
    }
  }
}
```

### **Example - New Poison Effect:**
```json
{
  "status_effects": {
    "debuffs": {
      "poison": {
        "name": "Poisoned",
        "type": "debuff",
        "description": "Takes damage each turn",
        "duration": 4,
        "stacking_rule": "stack_intensity",
        "max_stacks": 3,
        "priority": "normal",
        "damage_per_turn": {
          "base_damage": 15,
          "scaling": "mag",
          "scaling_multiplier": 0.2
        }
      }
    }
  }
}
```

---

## 🌍 **BATTLEFIELD CONDITIONS (`battlefield_conditions.json`)**

### **Structure:**
```json
{
  "battlefield_conditions": {
    "condition_id": {
      "name": "Display Name",
      "type": "weather|magical|terrain|special",
      "description": "What this condition does",
      "duration_days": 7,               // How long it lasts
      "rarity": "common|uncommon|rare|legendary",
      "effects": [
        {
          "effect_type": "stat_modifier|damage_modifier|skill_modifier",
          "target_criteria": "all|fire_elemental|water_elemental|mage_archetype",
          "stat_affected": "atk|mag|vit|spr|int|spd|lck",
          "modifier_value": 0.20,        // +20% or +20 flat
          "modifier_type": "percentage|flat",
          "description": "Human readable effect"
        }
      ]
    }
  }
}
```

### **Example - New Desert Condition:**
```json
{
  "battlefield_conditions": {
    "burning_desert": {
      "name": "Burning Desert",
      "type": "terrain",
      "description": "Intense heat drains water users but empowers fire users",
      "duration_days": 5,
      "rarity": "uncommon",
      "effects": [
        {
          "effect_type": "stat_modifier",
          "target_criteria": "fire_elemental", 
          "stat_affected": "atk",
          "modifier_value": 0.25,
          "modifier_type": "percentage",
          "description": "Fire characters gain +25% ATK"
        },
        {
          "effect_type": "damage_per_turn",
          "target_criteria": "water_elemental",
          "damage_value": 10,
          "description": "Water characters take 10 damage per turn"
        }
      ]
    }
  }
}
```

---

## 👥 **TEAM SYNERGIES (`team_synergies.json`)**

### **Structure:**
```json
{
  "team_synergies": {
    "synergy_id": {
      "series_name": "Anime Series Name",
      "tier_requirements": {
        "tier_1": 2,                    // Need 2 characters for tier 1
        "tier_2": 4,                    // Need 4 characters for tier 2  
        "tier_3": 6                     // Need 6 characters for tier 3
      },
      "bonuses": {
        "tier_1": {
          "bonus_type": "stat_modifier|status_effect|special_ability",
          "target_stat": "atk|mag|spd|etc",
          "value": 0.10,
          "description": "Human readable bonus"
        }
      }
    }
  }
}
```

### **Example - New Series Synergy:**
```json
{
  "team_synergies": {
    "attack_on_titan": {
      "series_name": "Shingeki no Kyojin",
      "tier_requirements": {
        "tier_1": 2,
        "tier_2": 4,
        "tier_3": 6
      },
      "bonuses": {
        "tier_1": {
          "bonus_type": "stat_modifier",
          "target_stat": "spd",
          "value": 0.15,
          "description": "+15% SPD for all allies (Survey Corps mobility)"
        },
        "tier_2": {
          "bonus_type": "special_ability",
          "effect_name": "titan_slayer",
          "description": "+50% damage vs large enemies"
        },
        "tier_3": {
          "bonus_type": "status_effect",
          "effect_name": "coordinate_power",
          "duration": 3,
          "description": "All allies gain Coordinate Power for 3 turns"
        }
      }
    }
  }
}
```

---

## ⚡ **CHARACTER ABILITIES (`character_abilities.json`)**

### **Structure:**
```json
{
  "character_id": {
    "signature_abilities": [
      {
        "ability_id": "unique_id",
        "name": "Ability Name",
        "type": "triggered_skill|passive|ultimate",
        "description": "What it does",
        "trigger_condition": "hp_threshold|enemy_dodge|turn_start|battle_start",
        "trigger_value": 0.50,          // 50% HP, or number of dodges, etc
        "cooldown": -1,                 // -1 = once per battle, 0 = no cooldown
        "rarity": "common|rare|epic|legendary",
        "effects": [
          {
            "effect_type": "damage|heal|status_effect|stat_modifier",
            "target_type": "self|single_enemy|all_enemies|all_allies",
            "details": "specific effect parameters"
          }
        ]
      }
    ],
    "signature_passives": [],           // Passive abilities always active
    "skills": []                        // Regular skills character can use
  }
}
```

### **Example - New Character Ability:**
```json
{
  "999999": {
    "signature_abilities": [
      {
        "ability_id": "dragon_flame",
        "name": "Dragon's Flame",
        "type": "ultimate",
        "description": "Unleashes devastating fire attack when health is low",
        "trigger_condition": "hp_threshold",
        "trigger_value": 0.25,
        "cooldown": -1,
        "rarity": "legendary",
        "effects": [
          {
            "effect_type": "damage",
            "target_type": "all_enemies",
            "damage_type": "fire",
            "base_damage": 250,
            "scaling": "mag",
            "scaling_multiplier": 3.0,
            "additional_effects": {
              "burn_duration": 3,
              "burn_damage": 20
            }
          }
        ]
      }
    ],
    "signature_passives": [
      {
        "passive_id": "fire_immunity",
        "name": "Fire Immunity", 
        "description": "Immune to fire damage",
        "effect_type": "damage_immunity",
        "immunity_type": "fire"
      }
    ]
  }
}
