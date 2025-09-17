"""State component for managing character dynamic state."""

class StateComponent:
    """Manages dynamic character state like HP, action gauge, and cooldowns."""
    
    def __init__(self, current_hp, max_hp, action_gauge=0, is_alive=True):
        """Initialize character state.
        
        Args:
            current_hp: Current hit points
            max_hp: Maximum hit points
            action_gauge: Current action gauge value
            is_alive: Whether the character is alive
        """
        self.current_hp = current_hp
        self.max_hp = max_hp
        self.action_gauge = action_gauge
        self.is_alive = is_alive
        
        # Skill system additions
        self.skill_cooldowns = {}  # skill_id -> remaining cooldown turns
        self.primed_skill = None   # For signature abilities (Phase 3)
        
        # Additional state tracking
        self.last_action = None    # Last action taken
        self.turn_count = 0        # Number of turns taken
    
    def set_skill_cooldown(self, skill_id, cooldown_turns):
        """Set cooldown for a skill.
        
        Args:
            skill_id: ID of the skill
            cooldown_turns: Number of turns until skill is available
        """
        if cooldown_turns > 0:
            self.skill_cooldowns[skill_id] = cooldown_turns
        elif skill_id in self.skill_cooldowns:
            del self.skill_cooldowns[skill_id]
    
    def get_skill_cooldown(self, skill_id):
        """Get remaining cooldown for a skill.
        
        Args:
            skill_id: ID of the skill
            
        Returns:
            Remaining cooldown turns (0 if skill is ready)
        """
        return self.skill_cooldowns.get(skill_id, 0)
    
    def is_skill_ready(self, skill_id):
        """Check if a skill is ready to use.
        
        Args:
            skill_id: ID of the skill
            
        Returns:
            True if skill is ready, False if on cooldown
        """
        return self.get_skill_cooldown(skill_id) == 0
    
    def tick_cooldowns(self):
        """Reduce all skill cooldowns by 1 turn."""
        expired_skills = []
        
        for skill_id, cooldown in self.skill_cooldowns.items():
            new_cooldown = cooldown - 1
            if new_cooldown <= 0:
                expired_skills.append(skill_id)
            else:
                self.skill_cooldowns[skill_id] = new_cooldown
        
        # Remove expired cooldowns
        for skill_id in expired_skills:
            del self.skill_cooldowns[skill_id]
    
    def get_all_cooldowns(self):
        """Get all active skill cooldowns."""
        return self.skill_cooldowns.copy()
