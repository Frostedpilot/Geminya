# Phase 3 TODO List and Implementation Guide

## 🎯 Overview
Phase 1 and 2 are complete and functional. This document tracks what needs to be implemented for Phase 3: Advanced Systems & Features.

---

## 📋 Phase 3 Implementation Checklist

### Week 7: Full Combat & Status Effects

#### ✅ Combat System Enhancements
- [ ] **Universal Scaling Formula Implementation**
  - File: `src/game/systems/combat_system.py`
  - Replace simple damage calculation (line 30-35) with GDD formulas 6.1-6.3
  - Add: Floor, Ceiling, SC1, SC2, PostCapRate parameters
  - Add: Elemental damage modifiers
  - Add: Critical hit system

- [ ] **Status Effects System**
  - Create: `src/game/effects/` directory
  - Implement: `base_effect.py` abstract class
  - Implement: `stat_modifier.py` for buffs/debuffs
  - Implement: `damage_over_time.py` for DoTs/HoTs
  - Update: `effects_component.py` with full effect processing

- [ ] **Skill System Foundation**
  - Create: Skill loading from `data/skill_definitions.json`
  - Implement: Skill execution framework in CombatSystem
  - Add: Cooldown tracking in character components
  - Update: AI to use real skills instead of "basic_attack"

#### 📄 Content Creation
- [ ] **Effect Library Population**
  - File: `data/effect_library.json`
  - Add: Common effects (Bleed, Burn, Poison, Regen, etc.)
  - Add: Buff/debuff effects (ATK+, DEF-, SPD+, etc.)
  - Add: Control effects (Stun, Silence, Sleep, etc.)

- [ ] **Basic Skill Definitions**
  - File: `data/skill_definitions.json`
  - Add: Attacker skills (Power Strike, Flurry, Cleave, etc.)
  - Add: Mage skills (Mana Bolt, Chain Lightning, Fireball, etc.)
  - Add: Healer skills (Lesser Heal, Regen, Mass Heal, etc.)

### Week 8: Advanced AI & Signature Abilities

#### 🤖 AI System Overhaul
- [ ] **Three-Phase AI Implementation**
  - File: `src/game/systems/ai_system.py`
  - Phase 1: Role Selection (Attacker, Mage, Healer, etc.)
  - Phase 2: Skill Selection within chosen role
  - Phase 3: Target Priority Score (TPS) calculation

- [ ] **Dynamic Weight Modifiers**
  - Add: Repetition Penalty (x0.5 for repeated roles)
  - Add: Finishing Blow (x2.0 for low HP enemies)
  - Add: Triage Priority (x3.0 for healing low HP allies)
  - Add: Synergy modifiers (buff exploitation, etc.)

- [ ] **Target Priority Score System**
  - Offensive targeting: Kill Priority × Elemental Weakness × Debuff multipliers
  - Healing targeting: Missing Health × High-Value Ally × Debuff bonuses
  - Buffing targeting: Role Synergy × Turn Order × Leader bonuses

#### 🌟 Signature Abilities Framework
- [ ] **Signature Skill System**
  - Add: `primed_skill` field to StateComponent
  - Add: Signature trigger conditions (HP thresholds, events, etc.)
  - Add: Trigger detection in EffectsComponent
  - Add: AI override for primed skills

- [ ] **Signature Passive System**
  - Add: Passive effect registration
  - Add: Always-on passive processing
  - Add: Character-specific passive loading

- [ ] **Character-Specific Abilities**
  - Add: Megumin's Explosion (HP < 50% trigger)
  - Add: Yor's Thorn Princess (dodge counter)
  - Add: Aqua's God's Blessing (ally defeat trigger)
  - Add: More signature abilities from character data

### Week 9: Global Rules & Synergies

#### 🌍 Global Systems
- [ ] **Rule Engine Implementation**
  - Create: `src/game/core/rule_engine.py`
  - Add: Dynamic rule modification system
  - Add: Global rule queries (critical multiplier, etc.)
  - Replace: Hardcoded values with rule engine calls

- [ ] **Battlefield Conditions**
  - File: `data/battlefield_conditions.json`
  - Add: Scorching Sun (Fire +20% ATK/MAG, Water -10% VIT/SPR)
  - Add: Mystic Fog (LCK -50%, reduced crits)
  - Add: Gravity Well (SPD -30%)
  - Add: Magic Overflow (MAG +25%)
  - Add: Weekly rotation system

- [ ] **Team Synergy System**
  - File: `data/synergy_definitions.json`
  - Add: K-On! synergies (SPD+10%, MAG+10%, Regen)
  - Add: Re:Zero synergies (SPR+15%, Death Save, LCK+10%)
  - Add: Konosuba synergies (LCK+20%, No Cooldown chance, Random effects)
  - Add: Series detection and bonus application

#### 👑 Leader System
- [ ] **Leader Mechanics**
  - Add: Leader designation in BattleSetup
  - Add: +10% stat bonus application
  - Add: Leader-specific targeting bonuses
  - Update: AI to consider leader value

---

## 🏗️ Current Template Code Locations

### Combat System Templates
```
File: src/game/systems/combat_system.py
Lines: 30-35 (basic damage calculation)
Lines: 45-50 (simple defense formula)
TODO: Replace with Universal Scaling Formula
```

### AI System Templates
```
File: src/game/systems/ai_system.py
Lines: 18-25 (random target selection)
Lines: 27-35 (basic attack only)
TODO: Implement Three-Phase AI decision making
```

### Stats Component Templates
```
File: src/game/components/stats_component.py
Lines: 6-7 (get_stat method)
TODO: Add dynamic stat calculation with modifiers
```

### Empty Content Files
```
data/skill_definitions.json (empty array)
data/effect_library.json (empty array)
data/synergy_definitions.json (empty array)
game_data/characters/ (empty directory)
game_data/skills/ (empty directory)
game_data/effects/ (empty directory)
```

---

## 🧪 Testing Strategy for Phase 3

### Integration Tests to Create
- [ ] **test_universal_scaling.py** - Combat formula validation
- [ ] **test_status_effects.py** - DoT/HoT and buff/debuff testing
- [ ] **test_ai_intelligence.py** - Three-phase AI decision validation
- [ ] **test_signature_abilities.py** - Character-specific ability testing
- [ ] **test_team_synergies.py** - Series bonus application testing
- [ ] **test_battlefield_conditions.py** - Global rule modification testing

### Test Battle Scenarios
- [ ] 3v3 battle with mixed archetypes
- [ ] Team synergy activation testing
- [ ] Signature ability trigger testing
- [ ] Complex status effect interactions
- [ ] Battlefield condition impact validation

---

## 📊 Phase 3 Success Criteria

### Week 7 Goals
- [ ] Universal Scaling Formula producing balanced damage
- [ ] Status effects applying and ticking correctly
- [ ] Basic skill library functional
- [ ] DoT/HoT effects working in battle

### Week 8 Goals
- [ ] AI making intelligent role-based decisions
- [ ] Target priority working logically
- [ ] Signature abilities triggering correctly
- [ ] Character uniqueness through abilities

### Week 9 Goals
- [ ] Team synergies providing meaningful bonuses
- [ ] Battlefield conditions changing strategy
- [ ] Leader system functional
- [ ] Global rules modifiable dynamically

### Final Integration Test
- [ ] 6v6 battle with full feature set
- [ ] Multiple synergies active
- [ ] Signature abilities firing
- [ ] Battlefield condition impact
- [ ] Complex AI decisions
- [ ] Victory through strategy, not just stats

---

## 📝 Notes

### Architecture Compatibility
All Phase 3 features are designed to work with the existing event-driven, component-based architecture. No breaking changes to Phase 1/2 code should be needed.

### Performance Considerations
- Effect processing should be optimized for many active effects
- AI calculations may need caching for complex battles
- Rule engine should cache frequently-accessed rules

### Content Pipeline
The JSON-based content system is ready for Phase 3 data. Content creators can add skills, effects, and synergies without code changes.

### Extension Points
The modular design allows for easy addition of:
- New character archetypes
- Additional status effect types
- More complex signature abilities
- Extra battlefield conditions
- Advanced team synergies

**Phase 3 will transform the functional battle system into a strategic, character-driven experience!** 🚀