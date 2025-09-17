"""Stat modifier effects for buffs and debuffs."""

from src.game.effects.base_effect import BaseEffect

class StatModifierEffect(BaseEffect):
    """Effect that modifies character stats (buffs/debuffs)."""
    
    def __init__(self, source_character, target_character, duration, stat_name, modifier_value, modifier_type="percentage"):
        """Initialize stat modifier effect.
        
        Args:
            source_character: Character who applied this effect
            target_character: Character affected by this effect
            duration: Number of turns this effect lasts
            stat_name: Name of stat to modify ('atk', 'vit', 'mag', 'spr', 'spd', 'lck', 'int')
            modifier_value: Value to modify stat by
            modifier_type: 'percentage' or 'flat' modification
        """
        effect_data = {
            "stat_name": stat_name,
            "modifier_value": modifier_value,
            "modifier_type": modifier_type
        }
        super().__init__(source_character, target_character, duration, effect_data)
        self.stat_name = stat_name
        self.modifier_value = modifier_value
        self.modifier_type = modifier_type
        self.applied = False
    
    def apply_effect(self, event_bus):
        """Apply the stat modification."""
        if self.applied:
            return
        
        target_stats = self.target_character.components.get('stats')
        if not target_stats:
            return
        
        # Add this effect as an active modifier
        if not hasattr(target_stats, 'active_modifiers'):
            target_stats.active_modifiers = {}
        
        if self.stat_name not in target_stats.active_modifiers:
            target_stats.active_modifiers[self.stat_name] = []
        
        target_stats.active_modifiers[self.stat_name].append(self)
        self.applied = True
        
        # Publish effect application event
        event_bus.publish("EffectApplied", {
            "effect": self,
            "character": self.target_character,
            "stat_name": self.stat_name,
            "modifier_value": self.modifier_value
        })
    
    def on_turn_start(self, event_bus):
        """Called when the affected character's turn starts."""
        # Stat modifiers are passive, no turn start effects
        return
    
    def remove_effect(self, event_bus):
        """Remove the stat modification."""
        target_stats = self.target_character.components.get('stats')
        if target_stats and hasattr(target_stats, 'active_modifiers'):
            if self.stat_name in target_stats.active_modifiers:
                try:
                    target_stats.active_modifiers[self.stat_name].remove(self)
                    if not target_stats.active_modifiers[self.stat_name]:
                        del target_stats.active_modifiers[self.stat_name]
                except ValueError:
                    pass  # Effect already removed
        
        super().remove_effect(event_bus)
    
    def get_description(self):
        """Get a human-readable description of this effect."""
        sign = "+" if self.modifier_value > 0 else ""
        if self.modifier_type == "percentage":
            return f"{self.stat_name.upper()}{sign}{self.modifier_value}% ({self.duration} turns)"
        else:
            return f"{self.stat_name.upper()}{sign}{self.modifier_value} ({self.duration} turns)"