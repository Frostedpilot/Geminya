"""Action command objects for system communication."""

class ActionCommand:
    """Represents an action to be executed in combat."""
    
    def __init__(self, caster, skill_name, targets, skill_data=None):
        """Initialize an action command.
        
        Args:
            caster: The character performing the action
            skill_name: Name of the skill being used
            targets: List of target characters
            skill_data: Optional skill data for damage/effect calculations
        """
        self.caster = caster
        self.skill_name = skill_name
        self.targets = targets if isinstance(targets, list) else [targets]
        self.skill_data = skill_data or {}
        
    def __repr__(self):
        return f"ActionCommand(caster={self.caster.name}, skill={self.skill_name}, targets={len(self.targets)})"