"""Enhanced Effects component for managing character status effects and signature abilities."""

class EffectsComponent:
    """Manages active effects on a character and signature ability triggers."""
    
    def __init__(self, event_bus=None):
        """Initialize the effects component.
        
        Args:
            event_bus: EventBus instance for subscribing to events
        """
        self.active_effects = []
        self.event_bus = event_bus
        self.character = None  # Will be set when attached to character
        
        # Signature ability tracking
        self.signature_trigger_conditions = {}  # trigger_name -> condition_func
        self.last_damage_taken = 0
        self.last_ally_died = False
        self.consecutive_turns_below_threshold = 0
        
        # Subscribe to events if event_bus is provided
        if self.event_bus:
            self.event_bus.subscribe("OnTurnStart", self._on_turn_start)
            self.event_bus.subscribe("OnTurnEnded", self._on_turn_ended)
            self.event_bus.subscribe("OnDamageTaken", self._on_damage_taken)
            self.event_bus.subscribe("OnCharacterDefeated", self._on_character_defeated)
            self.event_bus.subscribe("OnHealReceived", self._on_heal_received)
    
    def set_character(self, character):
        """Set the character this component belongs to."""
        self.character = character
        self._initialize_signature_triggers()
    
    def _initialize_signature_triggers(self):
        """Initialize signature ability trigger conditions for this character."""
        if not self.character:
            return
        
        # Register common signature triggers
        self.signature_trigger_conditions = {
            "low_health": self._check_low_health_trigger,
            "ally_in_danger": self._check_ally_in_danger_trigger,
            "enemy_low_health": self._check_enemy_low_health_trigger,
            "consecutive_damage": self._check_consecutive_damage_trigger,
            "ally_defeated": self._check_ally_defeated_trigger,
            "outnumbered": self._check_outnumbered_trigger,
            "high_action_gauge": self._check_high_action_gauge_trigger,
            "multiple_debuffs": self._check_multiple_debuffs_trigger,
            "last_ally_standing": self._check_last_ally_standing_trigger
        }
    
    def check_signature_triggers(self):
        """Check all signature ability trigger conditions.
        
        Returns:
            str or None: Name of triggered condition, or None if no triggers
        """
        if not self.character:
            return None
        
        for trigger_name, condition_func in self.signature_trigger_conditions.items():
            if condition_func():
                return trigger_name
        
        return None
    
    def _check_low_health_trigger(self):
        """Check if character's health is below 25%."""
        state = self.character.components.get('state')
        if not state:
            return False
        
        health_ratio = state.current_hp / state.max_hp
        if health_ratio <= 0.25:
            self.consecutive_turns_below_threshold += 1
            return self.consecutive_turns_below_threshold >= 1  # Trigger immediately
        else:
            self.consecutive_turns_below_threshold = 0
            return False
    
    def _check_ally_in_danger_trigger(self):
        """Check if any ally is critically wounded (<30% HP)."""
        # Get allies from battle context
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return False
        
        # Determine ally team
        ally_team = None
        if self.character in battle_context.team_one:
            ally_team = battle_context.team_one
        elif self.character in battle_context.team_two:
            ally_team = battle_context.team_two
        
        if not ally_team:
            return False
        
        for ally in ally_team:
            if ally == self.character:
                continue
            
            state = ally.components.get('state')
            if state and state.is_alive:
                health_ratio = state.current_hp / state.max_hp
                if health_ratio <= 0.3:
                    return True
        
        return False
    
    def _check_enemy_low_health_trigger(self):
        """Check if any enemy has low health (<40% HP)."""
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return False
        
        # Determine enemy team
        enemy_team = None
        if self.character in battle_context.team_one:
            enemy_team = battle_context.team_two
        elif self.character in battle_context.team_two:
            enemy_team = battle_context.team_one
        
        if not enemy_team:
            return False
        
        for enemy in enemy_team:
            state = enemy.components.get('state')
            if state and state.is_alive:
                health_ratio = state.current_hp / state.max_hp
                if health_ratio <= 0.4:
                    return True
        
        return False
    
    def _check_consecutive_damage_trigger(self):
        """Check if character took significant damage recently."""
        return self.last_damage_taken > 50  # Threshold for "significant" damage
    
    def _check_ally_defeated_trigger(self):
        """Check if an ally was recently defeated."""
        return self.last_ally_died
    
    def _check_outnumbered_trigger(self):
        """Check if allies are outnumbered by enemies."""
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return False
        
        # Count alive allies and enemies
        ally_count = 0
        enemy_count = 0
        
        if self.character in battle_context.team_one:
            ally_team = battle_context.team_one
            enemy_team = battle_context.team_two
        elif self.character in battle_context.team_two:
            ally_team = battle_context.team_two
            enemy_team = battle_context.team_one
        else:
            return False
        
        for ally in ally_team:
            state = ally.components.get('state')
            if state and state.is_alive:
                ally_count += 1
        
        for enemy in enemy_team:
            state = enemy.components.get('state')
            if state and state.is_alive:
                enemy_count += 1
        
        return enemy_count > ally_count
    
    def _check_high_action_gauge_trigger(self):
        """Check if character has high action gauge (>= 80)."""
        state = self.character.components.get('state')
        if not state:
            return False
        
        return state.action_gauge >= 80
    
    def _check_multiple_debuffs_trigger(self):
        """Check if character has multiple debuffs (>= 3)."""
        debuff_count = len([effect for effect in self.active_effects 
                           if hasattr(effect, 'effect_type') and effect.effect_type == 'debuff' and effect.is_active])
        return debuff_count >= 3
    
    def _check_last_ally_standing_trigger(self):
        """Check if character is the last ally standing."""
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return False
        
        # Determine ally team
        ally_team = None
        if self.character in battle_context.team_one:
            ally_team = battle_context.team_one
        elif self.character in battle_context.team_two:
            ally_team = battle_context.team_two
        
        if not ally_team:
            return False
        
        alive_allies = 0
        for ally in ally_team:
            state = ally.components.get('state')
            if state and state.is_alive:
                alive_allies += 1
        
        return alive_allies == 1  # Only this character is alive
    
    def prime_signature_ability(self, signature_skill_name, trigger_condition):
        """Prime a signature ability for automatic activation.
        
        Args:
            signature_skill_name: Name of the signature skill to prime
            trigger_condition: Condition that triggered the priming
        """
        state = self.character.components.get('state')
        if state:
            state.primed_skill = {
                'skill_name': signature_skill_name,
                'trigger': trigger_condition,
                'primed_turn': state.turn_count
            }
    
    def clear_primed_signature(self):
        """Clear any primed signature ability."""
        state = self.character.components.get('state')
        if state:
            state.primed_skill = None
    
    def get_primed_signature(self):
        """Get the currently primed signature ability.
        
        Returns:
            dict or None: Primed skill data or None if no skill is primed
        """
        state = self.character.components.get('state')
        if state:
            return state.primed_skill
        return None
    
    def add_effect(self, effect):
        """Add an active effect to the character.
        
        Args:
            effect: BaseEffect instance to add
        """
        effect.target_character = self.character
        effect.apply_effect(self.event_bus)
        self.active_effects.append(effect)
        
        # Publish effect added event
        if self.event_bus:
            self.event_bus.publish("EffectAdded", {
                "character": self.character,
                "effect": effect
            })
    
    def remove_effect(self, effect):
        """Remove an active effect from the character.
        
        Args:
            effect: BaseEffect instance to remove
        """
        if effect in self.active_effects:
            self.active_effects.remove(effect)
            effect.remove_effect(self.event_bus)
    
    def get_effects_by_type(self, effect_type):
        """Get all effects of a specific type.
        
        Args:
            effect_type: Type of effect to search for (class name)
            
        Returns:
            List of effects matching the type
        """
        return [effect for effect in self.active_effects 
                if effect.__class__.__name__ == effect_type and effect.is_active]
    
    def has_effect_type(self, effect_type):
        """Check if character has any effects of the given type.
        
        Args:
            effect_type: Type of effect to check for
            
        Returns:
            True if character has the effect type, False otherwise
        """
        return len(self.get_effects_by_type(effect_type)) > 0
    
    def get_active_effects(self):
        """Get all currently active effects."""
        return [effect for effect in self.active_effects if effect.is_active]
    
    def clear_effects_by_type(self, effect_type):
        """Remove all effects of a specific type.
        
        Args:
            effect_type: Type of effects to remove
        """
        effects_to_remove = self.get_effects_by_type(effect_type)
        for effect in effects_to_remove:
            self.remove_effect(effect)
    
    def _on_turn_start(self, event_data):
        """Handle turn start events for effect processing."""
        if not event_data or event_data.get('character') != self.character:
            return
        
        # Check for signature ability triggers at turn start
        triggered_condition = self.check_signature_triggers()
        if triggered_condition:
            # Check if character has a signature ability that matches this trigger
            skills_component = self.character.components.get('skills')
            if skills_component:
                signature_skills = skills_component.get_signature_skills()
                for skill_name, skill_data in signature_skills.items():
                    trigger_conditions = skill_data.get('trigger_conditions', [])
                    if triggered_condition in trigger_conditions:
                        self.prime_signature_ability(skill_name, triggered_condition)
                        break
        
        # Reset per-turn tracking variables
        self.last_damage_taken = 0
        self.last_ally_died = False
        
        # Process all active effects on turn start
        effects_to_remove = []
        
        for effect in self.active_effects[:]:  # Copy list to avoid modification during iteration
            if not effect.is_active:
                effects_to_remove.append(effect)
                continue
            
            # Call the effect's turn start method (e.g., DoT damage)
            effect.on_turn_start(self.event_bus)
            
            # Check if effect expired after processing
            if not effect.is_active or effect.duration <= 0:
                effects_to_remove.append(effect)
        
        # Remove expired effects
        for effect in effects_to_remove:
            if effect in self.active_effects:
                self.active_effects.remove(effect)
    
    def _on_turn_ended(self, event_data):
        """Handle turn end events for effect cleanup."""
        if not event_data or event_data.get('character') != self.character:
            return
        
        # Process effects on turn end (duration countdown)
        effects_to_remove = []
        
        for effect in self.active_effects[:]:
            if not effect.is_active:
                effects_to_remove.append(effect)
                continue
            
            # Call the effect's turn end method (duration countdown)
            effect.on_turn_end(self.event_bus)
            
            # Check if effect expired
            if not effect.is_active or effect.duration <= 0:
                effects_to_remove.append(effect)
        
        # Remove expired effects
        for effect in effects_to_remove:
            if effect in self.active_effects:
                self.active_effects.remove(effect)
    
    def _on_damage_taken(self, event_data):
        """Handle damage taken events for signature triggers."""
        if not event_data or event_data.get('target') != self.character:
            return
        
        damage_amount = event_data.get('damage', 0)
        self.last_damage_taken = damage_amount
    
    def _on_character_defeated(self, event_data):
        """Handle character defeated events for signature triggers."""
        if not event_data:
            return
        
        defeated_character = event_data.get('character')
        if not defeated_character:
            return
        
        # Check if the defeated character was an ally
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return
        
        # Determine if defeated character was an ally
        is_ally = False
        if self.character in battle_context.team_one and defeated_character in battle_context.team_one:
            is_ally = True
        elif self.character in battle_context.team_two and defeated_character in battle_context.team_two:
            is_ally = True
        
        if is_ally:
            self.last_ally_died = True
    
    def _on_heal_received(self, event_data):
        """Handle heal received events."""
        if not event_data or event_data.get('target') != self.character:
            return
        
        # Reset consecutive damage turns when healed
        heal_amount = event_data.get('heal', 0)
        if heal_amount > 0:
            self.consecutive_turns_below_threshold = 0