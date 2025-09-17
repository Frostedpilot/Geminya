"""Advanced Effect Interaction Engine for managing complex effect relationships."""

from typing import Dict, List, Set, Optional, Tuple, Any
from enum import Enum
import logging

class EffectInteractionType(Enum):
    """Types of effect interactions."""
    STACK = "stack"              # Effects can stack (damage, healing)
    OVERRIDE = "override"        # Newer effect replaces older
    MERGE = "merge"              # Effects combine into stronger version
    IMMUNITY = "immunity"        # Effect grants immunity to other effects
    DISPEL = "dispel"            # Effect removes other effects
    SYNERGY = "synergy"          # Effects boost each other
    CONFLICT = "conflict"        # Effects cancel each other out
    AMPLIFY = "amplify"          # One effect amplifies another
    SUPPRESS = "suppress"        # One effect reduces another

class EffectCategory(Enum):
    """Categories for effect classification."""
    DAMAGE_OVER_TIME = "dot"
    HEAL_OVER_TIME = "hot"
    STAT_MODIFIER = "stat"
    CROWD_CONTROL = "cc"
    DEFENSIVE = "defensive"
    OFFENSIVE = "offensive"
    UTILITY = "utility"
    SIGNATURE = "signature"
    BATTLEFIELD = "battlefield"

class EffectInteractionRule:
    """Defines how two effects interact with each other."""
    
    def __init__(self, effect_a: str, effect_b: str, interaction_type: EffectInteractionType,
                 condition_func=None, result_modifier=None, priority=0):
        """Initialize an interaction rule.
        
        Args:
            effect_a: First effect name/category
            effect_b: Second effect name/category
            interaction_type: Type of interaction
            condition_func: Optional function to check if interaction applies
            result_modifier: Function to modify the interaction result
            priority: Priority level (higher = more important)
        """
        self.effect_a = effect_a
        self.effect_b = effect_b
        self.interaction_type = interaction_type
        self.condition_func = condition_func
        self.result_modifier = result_modifier
        self.priority = priority

class EffectInteractionEngine:
    """Manages complex interactions between status effects."""
    
    def __init__(self, event_bus=None):
        """Initialize the effect interaction engine.
        
        Args:
            event_bus: EventBus for publishing interaction events
        """
        self.event_bus = event_bus
        self.interaction_rules: List[EffectInteractionRule] = []
        self.effect_categories: Dict[str, EffectCategory] = {}
        self.immunity_chains: Dict[str, Set[str]] = {}
        self.synergy_bonuses: Dict[Tuple[str, str], Dict[str, float]] = {}
        
        # Effect stacking limits
        self.max_stacks: Dict[str, int] = {}
        self.stack_decay_rates: Dict[str, float] = {}
        
        # Initialize standard interaction rules
        self._initialize_interaction_rules()
        self._initialize_effect_categories()
        self._initialize_immunity_chains()
        self._initialize_synergy_bonuses()
    
    def _initialize_interaction_rules(self):
        """Initialize standard effect interaction rules."""
        # Damage over Time stacking rules
        self.add_interaction_rule("poison", "poison", EffectInteractionType.STACK)
        self.add_interaction_rule("bleed", "bleed", EffectInteractionType.STACK)
        self.add_interaction_rule("burn", "burn", EffectInteractionType.STACK)
        
        # Stat modifier override rules
        self.add_interaction_rule("atk_up", "atk_up", EffectInteractionType.OVERRIDE)
        self.add_interaction_rule("atk_down", "atk_down", EffectInteractionType.OVERRIDE)
        self.add_interaction_rule("def_up", "def_up", EffectInteractionType.OVERRIDE)
        self.add_interaction_rule("def_down", "def_down", EffectInteractionType.OVERRIDE)
        
        # Conflicting effects
        self.add_interaction_rule("atk_up", "atk_down", EffectInteractionType.CONFLICT)
        self.add_interaction_rule("def_up", "def_down", EffectInteractionType.CONFLICT)
        self.add_interaction_rule("spd_up", "spd_down", EffectInteractionType.CONFLICT)
        self.add_interaction_rule("mag_up", "mag_down", EffectInteractionType.CONFLICT)
        
        # Immunity interactions
        self.add_interaction_rule("holy_barrier", "poison", EffectInteractionType.IMMUNITY)
        self.add_interaction_rule("holy_barrier", "burn", EffectInteractionType.IMMUNITY)
        self.add_interaction_rule("holy_barrier", "bleed", EffectInteractionType.IMMUNITY)
        self.add_interaction_rule("magic_immunity", "freeze", EffectInteractionType.IMMUNITY)
        self.add_interaction_rule("magic_immunity", "charm", EffectInteractionType.IMMUNITY)
        
        # Dispelling interactions
        self.add_interaction_rule("purify", "poison", EffectInteractionType.DISPEL)
        self.add_interaction_rule("purify", "burn", EffectInteractionType.DISPEL)
        self.add_interaction_rule("purify", "bleed", EffectInteractionType.DISPEL)
        self.add_interaction_rule("cleanse", "freeze", EffectInteractionType.DISPEL)
        self.add_interaction_rule("cleanse", "stun", EffectInteractionType.DISPEL)
        
        # Synergy interactions
        self.add_interaction_rule("burn", "explosion", EffectInteractionType.SYNERGY)
        self.add_interaction_rule("freeze", "shatter", EffectInteractionType.SYNERGY)
        self.add_interaction_rule("poison", "acid", EffectInteractionType.SYNERGY)
        self.add_interaction_rule("atk_up", "crit_up", EffectInteractionType.AMPLIFY)
        self.add_interaction_rule("spd_up", "dodge_up", EffectInteractionType.AMPLIFY)
        
        # Signature ability interactions
        self.add_interaction_rule("megumin_explosion", "burn", EffectInteractionType.AMPLIFY)
        self.add_interaction_rule("aqua_purification", "holy_barrier", EffectInteractionType.SYNERGY)
        self.add_interaction_rule("yor_assassination", "poison", EffectInteractionType.SYNERGY)
        self.add_interaction_rule("rimuru_predator", "devour", EffectInteractionType.MERGE)
    
    def _initialize_effect_categories(self):
        """Initialize effect category mappings."""
        # Damage over Time effects
        dot_effects = ["poison", "burn", "bleed", "acid", "curse", "darkness"]
        for effect in dot_effects:
            self.effect_categories[effect] = EffectCategory.DAMAGE_OVER_TIME
        
        # Heal over Time effects
        hot_effects = ["regeneration", "healing_light", "sacred_recovery", "nature_blessing"]
        for effect in hot_effects:
            self.effect_categories[effect] = EffectCategory.HEAL_OVER_TIME
        
        # Stat modifiers
        stat_effects = ["atk_up", "atk_down", "def_up", "def_down", "spd_up", "spd_down", 
                       "mag_up", "mag_down", "vit_up", "vit_down", "spr_up", "spr_down"]
        for effect in stat_effects:
            self.effect_categories[effect] = EffectCategory.STAT_MODIFIER
        
        # Crowd Control effects
        cc_effects = ["stun", "freeze", "sleep", "charm", "confusion", "silence", "bind"]
        for effect in cc_effects:
            self.effect_categories[effect] = EffectCategory.CROWD_CONTROL
        
        # Defensive effects
        defensive_effects = ["barrier", "shield", "holy_barrier", "magic_immunity", 
                           "physical_immunity", "dodge_up", "block_up"]
        for effect in defensive_effects:
            self.effect_categories[effect] = EffectCategory.DEFENSIVE
        
        # Signature effects
        signature_effects = ["megumin_explosion", "aqua_purification", "yor_assassination",
                           "rimuru_predator", "ainz_death", "accelerator_reflection"]
        for effect in signature_effects:
            self.effect_categories[effect] = EffectCategory.SIGNATURE
    
    def _initialize_immunity_chains(self):
        """Initialize immunity chain relationships."""
        # Holy immunity chain
        self.immunity_chains["holy_barrier"] = {
            "poison", "burn", "bleed", "curse", "darkness", "charm"
        }
        
        # Magic immunity chain
        self.immunity_chains["magic_immunity"] = {
            "freeze", "stun", "sleep", "charm", "confusion", "silence"
        }
        
        # Physical immunity chain
        self.immunity_chains["physical_immunity"] = {
            "bleed", "bind", "knockdown", "fatigue"
        }
        
        # Death immunity chain
        self.immunity_chains["undead"] = {
            "poison", "death", "instant_kill", "drain_life"
        }
        
        # Element immunity chains
        self.immunity_chains["fire_immunity"] = {"burn", "ignite", "melt"}
        self.immunity_chains["ice_immunity"] = {"freeze", "slow", "brittle"}
        self.immunity_chains["poison_immunity"] = {"poison", "acid", "venom"}
    
    def _initialize_synergy_bonuses(self):
        """Initialize synergy bonus calculations."""
        # Elemental synergies
        self.synergy_bonuses[("burn", "explosion")] = {
            "damage_multiplier": 1.5,
            "area_bonus": 1.2
        }
        
        self.synergy_bonuses[("freeze", "shatter")] = {
            "damage_multiplier": 2.0,
            "crit_chance_bonus": 0.3
        }
        
        self.synergy_bonuses[("poison", "acid")] = {
            "duration_multiplier": 1.3,
            "damage_multiplier": 1.2
        }
        
        # Stat synergies
        self.synergy_bonuses[("atk_up", "crit_up")] = {
            "effectiveness_bonus": 1.4
        }
        
        self.synergy_bonuses[("spd_up", "dodge_up")] = {
            "dodge_chance_bonus": 0.25
        }
        
        # Signature synergies
        self.synergy_bonuses[("aqua_purification", "holy_barrier")] = {
            "heal_bonus": 1.6,
            "immunity_duration": 1.5
        }
        
        self.synergy_bonuses[("yor_assassination", "poison")] = {
            "instant_kill_chance": 0.15,
            "damage_multiplier": 1.3
        }
    
    def add_interaction_rule(self, effect_a: str, effect_b: str, 
                           interaction_type: EffectInteractionType,
                           condition_func=None, result_modifier=None, priority=0):
        """Add a new interaction rule.
        
        Args:
            effect_a: First effect name
            effect_b: Second effect name
            interaction_type: Type of interaction
            condition_func: Optional condition function
            result_modifier: Optional result modifier function
            priority: Rule priority
        """
        rule = EffectInteractionRule(effect_a, effect_b, interaction_type,
                                   condition_func, result_modifier, priority)
        self.interaction_rules.append(rule)
    
    def process_effect_application(self, new_effect, existing_effects: List, 
                                 character) -> Tuple[List, List]:
        """Process the application of a new effect considering existing effects.
        
        Args:
            new_effect: The new effect being applied
            existing_effects: List of currently active effects
            character: Character receiving the effect
            
        Returns:
            Tuple of (final_effects_list, interaction_results)
        """
        interaction_results = []
        final_effects = existing_effects.copy()
        effect_applied = False
        
        new_effect_name = getattr(new_effect, 'name', new_effect.__class__.__name__.lower())
        
        # Check for immunity
        if self._check_immunity(new_effect_name, existing_effects):
            interaction_results.append({
                "type": "immunity",
                "message": f"{character.name if hasattr(character, 'name') else 'Character'} is immune to {new_effect_name}",
                "effect_blocked": new_effect_name
            })
            return final_effects, interaction_results
        
        # Process interactions with existing effects
        effects_to_remove = []
        effects_to_modify = []
        
        for existing_effect in existing_effects:
            existing_effect_name = getattr(existing_effect, 'name', 
                                         existing_effect.__class__.__name__.lower())
            
            interaction = self._find_interaction(new_effect_name, existing_effect_name)
            if interaction:
                result = self._apply_interaction(interaction, new_effect, existing_effect,
                                               character)
                interaction_results.append(result)
                
                if result["action"] == "remove_existing":
                    effects_to_remove.append(existing_effect)
                elif result["action"] == "modify_existing":
                    effects_to_modify.append((existing_effect, result["modifications"]))
                elif result["action"] == "block_new":
                    effect_applied = True  # Prevent new effect from being added
                elif result["action"] == "modify_new":
                    # Apply modifications to new effect
                    self._apply_effect_modifications(new_effect, result["modifications"])
        
        # Remove effects marked for removal
        for effect in effects_to_remove:
            final_effects.remove(effect)
        
        # Apply modifications to existing effects
        for effect, modifications in effects_to_modify:
            self._apply_effect_modifications(effect, modifications)
        
        # Add new effect if not blocked
        if not effect_applied:
            # Check for stacking limits
            if self._check_stacking_limit(new_effect_name, final_effects):
                final_effects.append(new_effect)
            else:
                interaction_results.append({
                    "type": "stack_limit",
                    "message": f"Maximum stacks of {new_effect_name} reached",
                    "effect_blocked": new_effect_name
                })
        
        return final_effects, interaction_results
    
    def _check_immunity(self, effect_name: str, existing_effects: List) -> bool:
        """Check if character is immune to the effect.
        
        Args:
            effect_name: Name of effect to check
            existing_effects: Currently active effects
            
        Returns:
            bool: True if immune to the effect
        """
        for existing_effect in existing_effects:
            existing_name = getattr(existing_effect, 'name', 
                                  existing_effect.__class__.__name__.lower())
            
            if existing_name in self.immunity_chains:
                immune_effects = self.immunity_chains[existing_name]
                if effect_name in immune_effects:
                    return True
        
        return False
    
    def _find_interaction(self, effect_a: str, effect_b: str) -> Optional[EffectInteractionRule]:
        """Find the highest priority interaction rule for two effects.
        
        Args:
            effect_a: First effect name
            effect_b: Second effect name
            
        Returns:
            EffectInteractionRule or None if no interaction found
        """
        matching_rules = []
        
        for rule in self.interaction_rules:
            if ((rule.effect_a == effect_a and rule.effect_b == effect_b) or
                (rule.effect_a == effect_b and rule.effect_b == effect_a)):
                if not rule.condition_func or rule.condition_func():
                    matching_rules.append(rule)
        
        if matching_rules:
            # Return highest priority rule
            return max(matching_rules, key=lambda r: r.priority)
        
        return None
    
    def _apply_interaction(self, rule: EffectInteractionRule, new_effect, 
                         existing_effect, character) -> Dict[str, Any]:
        """Apply an interaction rule between two effects.
        
        Args:
            rule: The interaction rule to apply
            new_effect: The new effect being applied
            existing_effect: The existing effect
            character: Character receiving the effects
            
        Returns:
            Dict describing the interaction result
        """
        result = {
            "type": rule.interaction_type.value,
            "effect_a": getattr(new_effect, 'name', new_effect.__class__.__name__.lower()),
            "effect_b": getattr(existing_effect, 'name', existing_effect.__class__.__name__.lower()),
            "action": "none",
            "message": "",
            "modifications": {}
        }
        
        if rule.interaction_type == EffectInteractionType.STACK:
            result["action"] = "stack"
            result["message"] = f"Effects stack: +1 stack of {result['effect_a']}"
            
        elif rule.interaction_type == EffectInteractionType.OVERRIDE:
            result["action"] = "remove_existing"
            result["message"] = f"{result['effect_a']} overrides {result['effect_b']}"
            
        elif rule.interaction_type == EffectInteractionType.CONFLICT:
            # Stronger effect wins, or they cancel out
            new_power = getattr(new_effect, 'power', 1.0)
            existing_power = getattr(existing_effect, 'power', 1.0)
            
            if new_power > existing_power:
                result["action"] = "remove_existing"
                result["message"] = f"{result['effect_a']} overcomes {result['effect_b']}"
            elif existing_power > new_power:
                result["action"] = "block_new"
                result["message"] = f"{result['effect_b']} resists {result['effect_a']}"
            else:
                result["action"] = "remove_existing"
                result["message"] = f"{result['effect_a']} and {result['effect_b']} cancel out"
                
        elif rule.interaction_type == EffectInteractionType.DISPEL:
            result["action"] = "remove_existing"
            result["message"] = f"{result['effect_a']} dispels {result['effect_b']}"
            
        elif rule.interaction_type == EffectInteractionType.SYNERGY:
            bonus_key = (result['effect_a'], result['effect_b'])
            if bonus_key not in self.synergy_bonuses:
                bonus_key = (result['effect_b'], result['effect_a'])
            
            if bonus_key in self.synergy_bonuses:
                bonus = self.synergy_bonuses[bonus_key]
                result["action"] = "modify_both"
                result["modifications"] = bonus
                result["message"] = f"Synergy bonus: {result['effect_a']} + {result['effect_b']}"
            
        elif rule.interaction_type == EffectInteractionType.AMPLIFY:
            result["action"] = "modify_existing"
            result["modifications"] = {"power_multiplier": 1.3, "duration_bonus": 1}
            result["message"] = f"{result['effect_a']} amplifies {result['effect_b']}"
            
        elif rule.interaction_type == EffectInteractionType.SUPPRESS:
            result["action"] = "modify_existing"
            result["modifications"] = {"power_multiplier": 0.7, "duration_reduction": 1}
            result["message"] = f"{result['effect_a']} suppresses {result['effect_b']}"
        
        # Apply custom result modifier if present
        if rule.result_modifier:
            result = rule.result_modifier(result, new_effect, existing_effect, character)
        
        return result
    
    def _apply_effect_modifications(self, effect, modifications: Dict[str, Any]):
        """Apply modifications to an effect.
        
        Args:
            effect: Effect to modify
            modifications: Dictionary of modifications to apply
        """
        for mod_name, mod_value in modifications.items():
            if mod_name == "power_multiplier":
                current_power = getattr(effect, 'power', 1.0)
                setattr(effect, 'power', current_power * mod_value)
            elif mod_name == "duration_bonus":
                current_duration = getattr(effect, 'duration', 0)
                setattr(effect, 'duration', current_duration + mod_value)
            elif mod_name == "duration_reduction":
                current_duration = getattr(effect, 'duration', 0)
                setattr(effect, 'duration', max(0, current_duration - mod_value))
            elif mod_name == "duration_multiplier":
                current_duration = getattr(effect, 'duration', 0)
                setattr(effect, 'duration', int(current_duration * mod_value))
            elif hasattr(effect, mod_name):
                setattr(effect, mod_name, mod_value)
    
    def _check_stacking_limit(self, effect_name: str, existing_effects: List) -> bool:
        """Check if effect can be stacked based on limits.
        
        Args:
            effect_name: Name of effect to check
            existing_effects: Currently active effects
            
        Returns:
            bool: True if effect can be stacked
        """
        if effect_name not in self.max_stacks:
            return True  # No limit set
        
        max_stacks = self.max_stacks[effect_name]
        current_stacks = sum(1 for effect in existing_effects 
                           if getattr(effect, 'name', effect.__class__.__name__.lower()) == effect_name)
        
        return current_stacks < max_stacks
    
    def process_turn_effects(self, character, effects: List) -> List[Dict[str, Any]]:
        """Process all effects at turn start/end, handling interactions.
        
        Args:
            character: Character whose effects to process
            effects: List of active effects
            
        Returns:
            List of effect results
        """
        results = []
        
        # Group effects by category for interaction processing
        effect_groups = self._group_effects_by_category(effects)
        
        # Process each group with potential interactions
        for category, category_effects in effect_groups.items():
            category_results = self._process_effect_group(category, category_effects, character)
            results.extend(category_results)
        
        return results
    
    def _group_effects_by_category(self, effects: List) -> Dict[EffectCategory, List]:
        """Group effects by their categories.
        
        Args:
            effects: List of effects to group
            
        Returns:
            Dictionary of category -> effects list
        """
        groups = {}
        
        for effect in effects:
            effect_name = getattr(effect, 'name', effect.__class__.__name__.lower())
            category = self.effect_categories.get(effect_name, EffectCategory.UTILITY)
            
            if category not in groups:
                groups[category] = []
            groups[category].append(effect)
        
        return groups
    
    def _process_effect_group(self, category: EffectCategory, effects: List, 
                            character) -> List[Dict[str, Any]]:
        """Process a group of effects of the same category.
        
        Args:
            category: Effect category
            effects: Effects in this category
            character: Character with these effects
            
        Returns:
            List of effect processing results
        """
        results = []
        
        if category == EffectCategory.DAMAGE_OVER_TIME:
            # DoT effects can have cumulative interactions
            total_damage = 0
            for effect in effects:
                damage = getattr(effect, 'damage_per_turn', 0)
                total_damage += damage
            
            # Apply synergy bonuses for multiple DoT effects
            if len(effects) > 1:
                synergy_multiplier = 1.0 + (len(effects) - 1) * 0.1  # 10% per additional DoT
                total_damage = int(total_damage * synergy_multiplier)
                
                results.append({
                    "type": "dot_synergy",
                    "message": f"Multiple DoT effects synergize for {total_damage} total damage",
                    "total_damage": total_damage,
                    "effect_count": len(effects)
                })
        
        elif category == EffectCategory.HEAL_OVER_TIME:
            # HoT effects stack additively but can be amplified
            total_healing = sum(getattr(effect, 'healing_per_turn', 0) for effect in effects)
            
            results.append({
                "type": "hot_stack",
                "message": f"Healing over time effects provide {total_healing} total healing",
                "total_healing": total_healing
            })
        
        elif category == EffectCategory.STAT_MODIFIER:
            # Stat modifiers need careful stacking rules
            stat_results = self._process_stat_modifiers(effects, character)
            results.extend(stat_results)
        
        return results
    
    def _process_stat_modifiers(self, effects: List, character) -> List[Dict[str, Any]]:
        """Process stat modifier effects with proper stacking rules.
        
        Args:
            effects: List of stat modifier effects
            character: Character with these effects
            
        Returns:
            List of stat modification results
        """
        results = []
        stat_changes = {}
        
        for effect in effects:
            effect_name = getattr(effect, 'name', effect.__class__.__name__.lower())
            
            # Extract stat and value from effect
            if 'atk' in effect_name:
                stat = 'atk'
            elif 'def' in effect_name:
                stat = 'def'
            elif 'spd' in effect_name:
                stat = 'spd'
            elif 'mag' in effect_name:
                stat = 'mag'
            else:
                continue
            
            value = getattr(effect, 'modifier_value', 0)
            if 'down' in effect_name:
                value = -abs(value)
            else:
                value = abs(value)
            
            if stat not in stat_changes:
                stat_changes[stat] = 0
            stat_changes[stat] += value
        
        # Apply stat changes with diminishing returns for high values
        for stat, total_change in stat_changes.items():
            if abs(total_change) > 50:  # Apply diminishing returns
                sign = 1 if total_change > 0 else -1
                diminished_change = sign * (50 + (abs(total_change) - 50) * 0.5)
                
                results.append({
                    "type": "stat_diminishing_returns",
                    "message": f"{stat.upper()} modifier reduced due to diminishing returns",
                    "original_change": total_change,
                    "final_change": diminished_change,
                    "stat": stat
                })
                
                stat_changes[stat] = diminished_change
        
        return results
    
    def get_effect_interactions_summary(self, effects: List) -> Dict[str, Any]:
        """Get a summary of all active effect interactions.
        
        Args:
            effects: List of active effects
            
        Returns:
            Dictionary summarizing effect interactions
        """
        summary = {
            "total_effects": len(effects),
            "categories": {},
            "active_synergies": [],
            "immunity_effects": [],
            "stacked_effects": {}
        }
        
        # Count effects by category
        for effect in effects:
            effect_name = getattr(effect, 'name', effect.__class__.__name__.lower())
            category = self.effect_categories.get(effect_name, EffectCategory.UTILITY)
            
            category_name = category.value
            if category_name not in summary["categories"]:
                summary["categories"][category_name] = 0
            summary["categories"][category_name] += 1
            
            # Check for immunity effects
            if effect_name in self.immunity_chains:
                summary["immunity_effects"].append({
                    "effect": effect_name,
                    "grants_immunity_to": list(self.immunity_chains[effect_name])
                })
        
        # Find active synergies
        effect_names = [getattr(e, 'name', e.__class__.__name__.lower()) for e in effects]
        for (effect_a, effect_b), bonus in self.synergy_bonuses.items():
            if effect_a in effect_names and effect_b in effect_names:
                summary["active_synergies"].append({
                    "effects": [effect_a, effect_b],
                    "bonus": bonus
                })
        
        # Count stacked effects
        effect_counts = {}
        for effect in effects:
            effect_name = getattr(effect, 'name', effect.__class__.__name__.lower())
            effect_counts[effect_name] = effect_counts.get(effect_name, 0) + 1
        
        summary["stacked_effects"] = {name: count for name, count in effect_counts.items() if count > 1}
        
        return summary