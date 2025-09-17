"""Registries for storing loaded game content."""

class Registry:
    """Base registry class for storing content by ID."""
    
    def __init__(self):
        self.data = {}
    
    def register(self, item_id, item_data):
        """Register an item with the given ID."""
        self.data[item_id] = item_data
    
    def get(self, item_id):
        """Get an item by ID."""
        return self.data.get(item_id)
    
    def get_all(self):
        """Get all registered items."""
        return self.data
    
    def load_from_list(self, items_list):
        """Load items from a list where each item has an 'id' field."""
        for item in items_list:
            if 'id' in item:
                self.register(item['id'], item)

class CharacterDataRegistry(Registry):
    """Registry for character base data."""
    pass

class ArchetypeDataRegistry(Registry):
    """Registry for character archetype data."""
    pass

class SkillRegistry(Registry):
    """Registry for skill definitions."""
    pass

class EffectRegistry(Registry):
    """Registry for effect templates."""
    pass

class SynergyRegistry(Registry):
    """Registry for team synergy definitions."""
    pass