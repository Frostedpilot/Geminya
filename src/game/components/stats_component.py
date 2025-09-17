"""Stats component for managing character statistics."""

class StatsComponent:
    """Manages base and modified character statistics."""
    
    def __init__(self, base_stats):
        """Initialize with base stats.
        
        Args:
            base_stats: Dictionary of base stat values
        """
        self.base_stats = base_stats.copy()
        self.active_modifiers = {}  # stat_name -> list of modifier effects
    
    def get_stat(self, stat_name):
        """Get the final modified value of a stat.
        
        Args:
            stat_name: Name of the stat to get
            
        Returns:
            Final calculated stat value including all modifiers
        """
        base_value = self.base_stats.get(stat_name, 0)
        
        # If no modifiers, return base value
        if stat_name not in self.active_modifiers:
            return base_value
        
        # Calculate modified value
        final_value = base_value
        flat_modifiers = 0
        percentage_modifiers = 0
        
        for modifier_effect in self.active_modifiers[stat_name]:
            if not modifier_effect.is_active:
                continue
            
            if modifier_effect.modifier_type == "flat":
                flat_modifiers += modifier_effect.modifier_value
            elif modifier_effect.modifier_type == "percentage":
                percentage_modifiers += modifier_effect.modifier_value
        
        # Apply modifiers: base + flat + (base * percentage/100)
        final_value = base_value + flat_modifiers
        if percentage_modifiers != 0:
            final_value += int(base_value * (percentage_modifiers / 100))
        
        # Ensure minimum value of 1 for most stats
        return max(1, final_value)
    
    def get_base_stat(self, stat_name):
        """Get the unmodified base value of a stat.
        
        Args:
            stat_name: Name of the stat to get
            
        Returns:
            Base stat value without modifiers
        """
        return self.base_stats.get(stat_name, 0)
    
    def get_all_stats(self):
        """Get all final stat values as a dictionary."""
        stats = {}
        for stat_name in self.base_stats.keys():
            stats[stat_name] = self.get_stat(stat_name)
        return stats
    
    def get_all_base_stats(self):
        """Get all base stat values as a dictionary."""
        return self.base_stats.copy()
    
    def cleanup_inactive_modifiers(self):
        """Remove inactive modifiers from the active modifiers list."""
        for stat_name in list(self.active_modifiers.keys()):
            active_mods = [mod for mod in self.active_modifiers[stat_name] if mod.is_active]
            if active_mods:
                self.active_modifiers[stat_name] = active_mods
            else:
                del self.active_modifiers[stat_name]
