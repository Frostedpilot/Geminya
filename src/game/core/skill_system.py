"""Skill system for loading and managing character skills."""

class Skill:
    """Represents a character skill with its properties."""
    
    def __init__(self, skill_id, skill_data):
        """Initialize a skill from data.
        
        Args:
            skill_id: Unique identifier for the skill
            skill_data: Dictionary containing skill properties
        """
        self.skill_id = skill_id
        self.name = skill_data.get("name", skill_id)
        self.description = skill_data.get("description", "")
        self.skill_type = skill_data.get("type", "damage")  # damage, heal, buff, utility
        self.element = skill_data.get("element", "physical")
        self.target_type = skill_data.get("target_type", "single")  # single, all, row, self
        self.cooldown = skill_data.get("cooldown", 0)
        self.multiplier = skill_data.get("multiplier", 1.0)
        self.scaling_params = skill_data.get("scaling_params", {})
        self.effects = skill_data.get("effects", [])  # Status effects to apply
        self.range = skill_data.get("range", "front")  # front, back, any
        
        # Ensure scaling_params has defaults
        self._set_default_scaling_params()
    
    def _set_default_scaling_params(self):
        """Set default scaling parameters if not provided."""
        defaults = {
            "floor": 20,
            "ceiling": 200,
            "sc1": 50,
            "sc2": 200,
            "post_cap_rate": 0.5
        }
        
        for key, value in defaults.items():
            if key not in self.scaling_params:
                self.scaling_params[key] = value
    
    def to_skill_data(self):
        """Convert skill to skill_data format for combat system."""
        return {
            "type": self.skill_type,
            "element": self.element,
            "multiplier": self.multiplier,
            "scaling_params": self.scaling_params,
            "effects": self.effects,
            "target_type": self.target_type,
            "range": self.range
        }


class SkillRegistry:
    """Registry for managing all game skills."""
    
    def __init__(self):
        """Initialize empty skill registry."""
        self.skills = {}
    
    def load_from_file(self, file_path):
        """Load skills from JSON file.
        
        Args:
            file_path: Path to the skills JSON file
        """
        import json
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                skills_data = json.load(file)
                self.load_from_dict(skills_data)
        except FileNotFoundError:
            print(f"Warning: Skills file {file_path} not found. Using empty skill registry.")
        except json.JSONDecodeError as e:
            print(f"Error parsing skills file {file_path}: {e}")
    
    def load_from_dict(self, skills_data):
        """Load skills from dictionary data.
        
        Args:
            skills_data: Dictionary or list of skill definitions
        """
        if isinstance(skills_data, list):
            # Handle list format
            for skill_data in skills_data:
                skill_id = skill_data.get("id")
                if skill_id:
                    self.skills[skill_id] = Skill(skill_id, skill_data)
        elif isinstance(skills_data, dict):
            # Handle object format
            for skill_id, skill_data in skills_data.items():
                self.skills[skill_id] = Skill(skill_id, skill_data)
    
    def get(self, skill_id):
        """Get a skill by ID.
        
        Args:
            skill_id: ID of the skill to retrieve
            
        Returns:
            Skill object or None if not found
        """
        return self.skills.get(skill_id)
    
    def get_all(self):
        """Get all registered skills."""
        return self.skills.copy()
    
    def register_skill(self, skill):
        """Register a single skill.
        
        Args:
            skill: Skill object to register
        """
        self.skills[skill.skill_id] = skill
    
    def get_skills_by_type(self, skill_type):
        """Get all skills of a specific type.
        
        Args:
            skill_type: Type of skills to retrieve
            
        Returns:
            List of skills matching the type
        """
        return [skill for skill in self.skills.values() if skill.skill_type == skill_type]