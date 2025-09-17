"""Stats component for managing character statistics."""

class StatsComponent:
    """Manages base and modified character statistics."""
    
    # Role potency multipliers for stat calculations
    ROLE_POTENCY_MULTIPLIERS = {
        'S': 1.10,  # +10% Master bonus
        'A': 1.05,  # +5% Expert bonus  
        'B': 1.00,  # Baseline competent
        'C': 0.95,  # -5% Average penalty
        'D': 0.85,  # -15% Poor penalty
        'F': 0.70   # -30% Terrible penalty
    }
    
    def __init__(self, base_stats):
        """Initialize with base stats.
        
        Args:
            base_stats: Dictionary of base stat values
        """
        self.base_stats = base_stats.copy()
        self.active_modifiers = {}  # stat_name -> list of modifier effects
        self.character = None  # Will be set by character factory
        self._cached_potency_multiplier = None  # Cache for performance
    
    def set_character(self, character):
        """Set the character reference for accessing archetype data.
        
        Args:
            character: The character entity this component belongs to
        """
        self.character = character
        self._cached_potency_multiplier = None  # Reset cache
    
    def _get_role_potency_multiplier(self):
        """Get the role potency multiplier based on character's highest potency rating.
        
        Returns:
            float: Multiplier value (0.70 to 1.10)
        """
        # Use cached value if available
        if self._cached_potency_multiplier is not None:
            return self._cached_potency_multiplier
        
        # Default to baseline if no character or archetype data
        if not self.character:
            self._cached_potency_multiplier = 1.0
            return self._cached_potency_multiplier
        
        archetype_component = self.character.components.get('archetype')
        if not archetype_component:
            self._cached_potency_multiplier = 1.0
            return self._cached_potency_multiplier
        
        # Get role potencies from archetype data
        archetype_data = archetype_component.archetype_data
        role_potencies = archetype_data.get('role_potency', {})
        
        if not role_potencies:
            self._cached_potency_multiplier = 1.0
            return self._cached_potency_multiplier
        
        # Find the highest potency rating
        highest_potency = 'C'  # Default to average
        highest_multiplier = 0.0
        
        for role, potency_letter in role_potencies.items():
            multiplier = self.ROLE_POTENCY_MULTIPLIERS.get(potency_letter, 1.0)
            if multiplier > highest_multiplier:
                highest_multiplier = multiplier
                highest_potency = potency_letter
        
        self._cached_potency_multiplier = highest_multiplier
        return self._cached_potency_multiplier
    
    def get_stat(self, stat_name):
        """Get the final modified value of a stat.
        
        Args:
            stat_name: Name of the stat to get
            
        Returns:
            Final calculated stat value including role potency and all modifiers
        """
        base_value = self.base_stats.get(stat_name, 0)
        
        # Step 1: Apply role potency multiplier to base stats
        potency_multiplier = self._get_role_potency_multiplier()
        potency_enhanced_base = base_value * potency_multiplier
        
        # Step 2: Apply flat and percentage modifiers
        if stat_name not in self.active_modifiers:
            return max(1, int(potency_enhanced_base))
        
        # Calculate modified value starting from potency-enhanced base
        flat_modifiers = 0
        percentage_modifiers = 0
        
        for modifier_effect in self.active_modifiers[stat_name]:
            if not modifier_effect.is_active:
                continue
            
            if modifier_effect.modifier_type == "flat":
                flat_modifiers += modifier_effect.modifier_value
            elif modifier_effect.modifier_type == "percentage":
                percentage_modifiers += modifier_effect.modifier_value
        
        # Apply modifiers: (base * potency) + flat + (base * potency * percentage/100)
        final_value = potency_enhanced_base + flat_modifiers
        if percentage_modifiers != 0:
            final_value += potency_enhanced_base * (percentage_modifiers / 100)
        
        # Ensure minimum value of 1 for most stats
        return max(1, int(final_value))
    
    def get_base_stat(self, stat_name):
        """Get the unmodified base value of a stat.
        
        Args:
            stat_name: Name of the stat to get
            
        Returns:
            Base stat value without modifiers or potency
        """
        return self.base_stats.get(stat_name, 0)
    
    def get_potency_enhanced_base_stat(self, stat_name):
        """Get the base stat enhanced by role potency multiplier.
        
        Args:
            stat_name: Name of the stat to get
            
        Returns:
            Base stat value enhanced by role potency (before other modifiers)
        """
        base_value = self.base_stats.get(stat_name, 0)
        potency_multiplier = self._get_role_potency_multiplier()
        return base_value * potency_multiplier
    
    def get_role_potency_info(self):
        """Get information about the character's role potency.
        
        Returns:
            dict: Contains multiplier value and highest potency rating
        """
        if not self.character:
            return {'multiplier': 1.0, 'highest_rating': 'C', 'source_role': None}
        
        archetype_component = self.character.components.get('archetype')
        if not archetype_component:
            return {'multiplier': 1.0, 'highest_rating': 'C', 'source_role': None}
        
        archetype_data = archetype_component.archetype_data
        role_potencies = archetype_data.get('role_potency', {})
        
        if not role_potencies:
            return {'multiplier': 1.0, 'highest_rating': 'C', 'source_role': None}
        
        # Find the highest potency rating and its source role
        highest_potency = 'C'
        highest_multiplier = 0.0
        source_role = None
        
        for role, potency_letter in role_potencies.items():
            multiplier = self.ROLE_POTENCY_MULTIPLIERS.get(potency_letter, 1.0)
            if multiplier > highest_multiplier:
                highest_multiplier = multiplier
                highest_potency = potency_letter
                source_role = role
        
        return {
            'multiplier': highest_multiplier,
            'highest_rating': highest_potency,
            'source_role': source_role
        }
    
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
    
    def invalidate_potency_cache(self):
        """Invalidate the cached potency multiplier (call when archetype changes)."""
        self._cached_potency_multiplier = None
