"""Rule Engine for dynamic game rule management and configuration."""

import json
import os
from typing import Any, Dict, List, Optional, Union

class RuleEngine:
    """Dynamic rule engine for managing game configuration and rules.
    
    The Rule Engine provides:
    - Dynamic rule modification without code changes
    - Global rule queries throughout the codebase
    - Rule categories and namespacing
    - Rule validation and type checking
    - Rule inheritance and overrides
    """
    
    def __init__(self, rules_file_path: str = None):
        """Initialize the rule engine.
        
        Args:
            rules_file_path: Path to the rules configuration file
        """
        self._rules = {}
        self._rule_metadata = {}
        self._default_rules_file = rules_file_path or "data/game_rules.json"
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default game rules from configuration file."""
        if os.path.exists(self._default_rules_file):
            try:
                with open(self._default_rules_file, 'r') as f:
                    data = json.load(f)
                    self._rules = data.get('rules', {})
                    self._rule_metadata = data.get('metadata', {})
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Warning: Could not load rules file {self._default_rules_file}: {e}")
                self._initialize_default_rules()
        else:
            self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default hardcoded rules as fallback."""
        self._rules = {
            "combat": {
                "max_action_gauge": 100,
                "action_gauge_increment": 10,
                "critical_hit_multiplier": 1.5,
                "critical_hit_base_chance": 0.05,
                "max_skill_cooldown": 10,
                "death_hp_threshold": 0
            },
            "scaling": {
                "universal_scaling": {
                    "default_floor": 20,
                    "default_ceiling": 200,
                    "default_sc1": 50,
                    "default_sc2": 200,
                    "default_post_cap_rate": 0.5
                },
                "stat_scaling_caps": {
                    "max_stat_value": 999,
                    "max_percentage_buff": 200,
                    "max_percentage_debuff": -80
                }
            },
            "effects": {
                "max_effect_stacks": 5,
                "max_effect_duration": 10,
                "effect_resistance_cap": 0.9,
                "dot_tick_timing": "turn_start",
                "buff_application_timing": "immediate"
            },
            "ai": {
                "role_selection_weights": {
                    "base_weight": 1.0,
                    "max_weight_multiplier": 3.0,
                    "health_threshold_low": 0.4,
                    "health_threshold_critical": 0.25
                },
                "targeting_priorities": {
                    "low_hp_bonus": 30,
                    "high_threat_bonus": 20,
                    "position_front_bonus": 10,
                    "position_back_bonus": 5
                }
            },
            "signature_abilities": {
                "trigger_thresholds": {
                    "low_health": 0.25,
                    "ally_in_danger": 0.3,
                    "enemy_low_health": 0.4,
                    "significant_damage": 50,
                    "high_action_gauge": 80,
                    "multiple_debuffs": 3
                },
                "priming_rules": {
                    "max_primed_duration": 3,
                    "auto_activate": True,
                    "override_normal_skills": True
                }
            },
            "balance": {
                "damage_variance": 0.1,
                "healing_efficiency": 1.0,
                "buff_effectiveness": 1.0,
                "debuff_effectiveness": 1.0,
                "speed_action_gauge_ratio": 1.2
            }
        }
        
        self._rule_metadata = {
            "version": "1.0.0",
            "last_updated": "2024-01-01",
            "categories": list(self._rules.keys()),
            "rule_descriptions": {
                "combat.max_action_gauge": "Maximum action gauge value before character acts",
                "combat.critical_hit_multiplier": "Damage multiplier for critical hits",
                "scaling.universal_scaling.default_floor": "Default floor value for Universal Scaling Formula",
                "effects.max_effect_stacks": "Maximum number of effect stacks allowed",
                "ai.role_selection_weights.base_weight": "Base weight for AI role selection",
                "signature_abilities.trigger_thresholds.low_health": "HP percentage threshold for low health triggers"
            }
        }
    
    def get_rule(self, rule_path: str, default: Any = None) -> Any:
        """Get a rule value by path.
        
        Args:
            rule_path: Dot-separated path to the rule (e.g., "combat.max_action_gauge")
            default: Default value if rule is not found
            
        Returns:
            Rule value or default
        """
        path_parts = rule_path.split('.')
        current = self._rules
        
        try:
            for part in path_parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return default
    
    def set_rule(self, rule_path: str, value: Any, validate: bool = True) -> bool:
        """Set a rule value by path.
        
        Args:
            rule_path: Dot-separated path to the rule
            value: New value for the rule
            validate: Whether to validate the value
            
        Returns:
            True if successful, False otherwise
        """
        if validate and not self._validate_rule_value(rule_path, value):
            return False
        
        path_parts = rule_path.split('.')
        current = self._rules
        
        # Navigate to the parent of the target
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the final value
        current[path_parts[-1]] = value
        return True
    
    def _validate_rule_value(self, rule_path: str, value: Any) -> bool:
        """Validate a rule value before setting it.
        
        Args:
            rule_path: Path to the rule
            value: Value to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic type validation based on rule path
        validation_rules = {
            "combat.max_action_gauge": lambda v: isinstance(v, (int, float)) and v > 0,
            "combat.critical_hit_multiplier": lambda v: isinstance(v, (int, float)) and v >= 1.0,
            "scaling.universal_scaling.default_floor": lambda v: isinstance(v, (int, float)) and v >= 0,
            "effects.max_effect_stacks": lambda v: isinstance(v, int) and v > 0,
            "signature_abilities.trigger_thresholds.low_health": lambda v: isinstance(v, (int, float)) and 0 < v <= 1
        }
        
        validator = validation_rules.get(rule_path)
        if validator:
            return validator(value)
        
        # Default validation - just check that value is not None
        return value is not None
    
    def get_category_rules(self, category: str) -> Dict[str, Any]:
        """Get all rules in a category.
        
        Args:
            category: Category name
            
        Returns:
            Dictionary of rules in the category
        """
        return self._rules.get(category, {}).copy()
    
    def get_all_rules(self) -> Dict[str, Any]:
        """Get all rules.
        
        Returns:
            Complete rules dictionary
        """
        return self._rules.copy()
    
    def reload_rules(self):
        """Reload rules from the configuration file."""
        self._load_default_rules()
    
    def save_rules(self, file_path: str = None):
        """Save current rules to file.
        
        Args:
            file_path: Path to save rules to (default: use default rules file)
        """
        save_path = file_path or self._default_rules_file
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        data = {
            "rules": self._rules,
            "metadata": self._rule_metadata
        }
        
        try:
            with open(save_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving rules to {save_path}: {e}")
            return False
    
    def create_rule_override(self, base_path: str, override_name: str, overrides: Dict[str, Any]) -> str:
        """Create a rule override for specific conditions.
        
        Args:
            base_path: Base rule path to override
            override_name: Name for this override
            overrides: Dictionary of rule overrides
            
        Returns:
            Path to the created override
        """
        override_path = f"{base_path}.overrides.{override_name}"
        
        # Get base rules
        base_rules = self.get_rule(base_path, {})
        if not isinstance(base_rules, dict):
            return None
        
        # Create override
        override_rules = base_rules.copy()
        override_rules.update(overrides)
        
        self.set_rule(override_path, override_rules)
        return override_path
    
    def apply_rule_override(self, base_path: str, override_name: str) -> bool:
        """Apply a previously created rule override.
        
        Args:
            base_path: Base rule path
            override_name: Name of the override to apply
            
        Returns:
            True if successful, False otherwise
        """
        override_path = f"{base_path}.overrides.{override_name}"
        override_rules = self.get_rule(override_path)
        
        if override_rules is None:
            return False
        
        return self.set_rule(base_path, override_rules)
    
    def get_combat_rule(self, rule_name: str, default: Any = None) -> Any:
        """Convenience method for getting combat rules."""
        return self.get_rule(f"combat.{rule_name}", default)
    
    def get_scaling_rule(self, rule_name: str, default: Any = None) -> Any:
        """Convenience method for getting scaling rules."""
        return self.get_rule(f"scaling.{rule_name}", default)
    
    def get_effect_rule(self, rule_name: str, default: Any = None) -> Any:
        """Convenience method for getting effect rules."""
        return self.get_rule(f"effects.{rule_name}", default)
    
    def get_ai_rule(self, rule_name: str, default: Any = None) -> Any:
        """Convenience method for getting AI rules."""
        return self.get_rule(f"ai.{rule_name}", default)
    
    def get_signature_rule(self, rule_name: str, default: Any = None) -> Any:
        """Convenience method for getting signature ability rules."""
        return self.get_rule(f"signature_abilities.{rule_name}", default)
    
    def get_balance_rule(self, rule_name: str, default: Any = None) -> Any:
        """Convenience method for getting balance rules."""
        return self.get_rule(f"balance.{rule_name}", default)


# Global rule engine instance
_global_rule_engine = None

def get_rule_engine() -> RuleEngine:
    """Get the global rule engine instance."""
    global _global_rule_engine
    if _global_rule_engine is None:
        _global_rule_engine = RuleEngine()
    return _global_rule_engine

def initialize_rule_engine(rules_file_path: str = None) -> RuleEngine:
    """Initialize the global rule engine with a specific rules file."""
    global _global_rule_engine
    _global_rule_engine = RuleEngine(rules_file_path)
    return _global_rule_engine

# Convenience functions for quick rule access
def get_rule(rule_path: str, default: Any = None) -> Any:
    """Get a rule from the global rule engine."""
    return get_rule_engine().get_rule(rule_path, default)

def get_combat_rule(rule_name: str, default: Any = None) -> Any:
    """Get a combat rule from the global rule engine."""
    return get_rule_engine().get_combat_rule(rule_name, default)

def get_scaling_rule(rule_name: str, default: Any = None) -> Any:
    """Get a scaling rule from the global rule engine."""
    return get_rule_engine().get_scaling_rule(rule_name, default)

def get_effect_rule(rule_name: str, default: Any = None) -> Any:
    """Get an effect rule from the global rule engine."""
    return get_rule_engine().get_effect_rule(rule_name, default)

def get_ai_rule(rule_name: str, default: Any = None) -> Any:
    """Get an AI rule from the global rule engine."""
    return get_rule_engine().get_ai_rule(rule_name, default)

def get_signature_rule(rule_name: str, default: Any = None) -> Any:
    """Get a signature ability rule from the global rule engine."""
    return get_rule_engine().get_signature_rule(rule_name, default)

def get_balance_rule(rule_name: str, default: Any = None) -> Any:
    """Get a balance rule from the global rule engine."""
    return get_rule_engine().get_balance_rule(rule_name, default)