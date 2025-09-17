"""Skills component for managing character skills and abilities."""

class SkillsComponent:
    """Manages character skills, cooldowns, and signature abilities."""
    
    def __init__(self, skills=None):
        """Initialize the skills component.
        
        Args:
            skills: List of skill names this character has access to
        """
        self.skills = skills if skills is not None else []
        self.skill_registry = None  # Will be set by factory
        self.character = None  # Will be set when attached to character
    
    def set_character(self, character):
        """Set the character this component belongs to."""
        self.character = character
    
    def set_skill_registry(self, skill_registry):
        """Set the skill registry for looking up skill data."""
        self.skill_registry = skill_registry
    
    def is_skill_available(self, skill_name):
        """Check if a skill is available to use (not on cooldown).
        
        Args:
            skill_name: Name of the skill to check
            
        Returns:
            bool: True if skill is available, False if on cooldown or not known
        """
        if skill_name not in self.skills:
            return False
        
        if not self.character:
            return False
        
        state_component = self.character.components.get('state')
        if not state_component:
            return False
        
        return state_component.is_skill_ready(skill_name)
    
    def get_skill_data(self, skill_name):
        """Get skill data from the registry.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            dict or None: Skill data or None if not found
        """
        if not self.skill_registry:
            return None
        
        return self.skill_registry.get(skill_name)
    
    def get_signature_skills(self):
        """Get all signature skills for this character.
        
        Returns:
            dict: skill_name -> skill_data for all signature skills
        """
        if not self.skill_registry:
            return {}
        
        signature_skills = {}
        for skill_name in self.skills:
            skill_data = self.skill_registry.get(skill_name)
            if skill_data and skill_data.get('is_signature', False):
                signature_skills[skill_name] = skill_data
        
        return signature_skills
    
    def get_available_skills(self):
        """Get all skills that are currently available (not on cooldown).
        
        Returns:
            List of skill names that are available
        """
        available = []
        for skill_name in self.skills:
            if self.is_skill_available(skill_name):
                available.append(skill_name)
        return available
    
    def add_skill(self, skill_name):
        """Add a skill to this character's skill list.
        
        Args:
            skill_name: Name of the skill to add
        """
        if skill_name not in self.skills:
            self.skills.append(skill_name)
    
    def remove_skill(self, skill_name):
        """Remove a skill from this character's skill list.
        
        Args:
            skill_name: Name of the skill to remove
        """
        if skill_name in self.skills:
            self.skills.remove(skill_name)
    
    def use_skill(self, skill_name):
        """Mark a skill as used (apply cooldown).
        
        Args:
            skill_name: Name of the skill that was used
        """
        if not self.character or skill_name not in self.skills:
            return
        
        skill_data = self.get_skill_data(skill_name)
        if not skill_data:
            return
        
        cooldown = skill_data.get('cooldown', 0)
        if cooldown > 0:
            state_component = self.character.components.get('state')
            if state_component:
                state_component.set_skill_cooldown(skill_name, cooldown)