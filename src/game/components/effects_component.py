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
        
        # Initialize Effect Interaction Engine (lazy import to avoid circular dependencies)
        self.interaction_engine = None
        
        # Signature ability tracking
        self.signature_trigger_conditions = {}  # trigger_name -> condition_func
        self.last_damage_taken = 0
        self.last_ally_died = False
        self.consecutive_turns_below_threshold = 0
        
        # Enhanced trigger tracking for complex conditions
        self.skill_chain_count = 0
        self.damage_turn_count = 0
        self.pattern_tracking = {}
        self.last_enemy_actions = []
        
        # Combat event tracking
        self._successful_dodge_this_turn = False
        self._successful_block_this_turn = False
        self._would_be_fatal = False
        self._round_ending = False
        
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
    
    def _safe_get_character_state(self, character):
        """Safely get state component from any character.
        
        Args:
            character: Character to get state from
            
        Returns:
            State component or None if not available
        """
        if not character or not hasattr(character, 'components'):
            return None
        return character.components.get('state')
    
    def _safe_get_component(self, component_name):
        """Safely get a component from the character.
        
        Args:
            component_name: Name of the component to get
            
        Returns:
            Component instance or None if not available
        """
        if not self.character or not hasattr(self.character, 'components'):
            return None
        return self.character.components.get(component_name)
    
    def _initialize_signature_triggers(self):
        """Initialize signature ability trigger conditions for this character."""
        if not self.character:
            return
        
        # Register comprehensive signature triggers
        self.signature_trigger_conditions = {
            # Health-based triggers
            "low_health": self._check_low_health_trigger,
            "ally_in_danger": self._check_ally_in_danger_trigger,
            "enemy_low_health": self._check_enemy_low_health_trigger,
            "ally_critical_health": self._check_ally_critical_health_trigger,
            "ally_about_to_die": self._check_ally_about_to_die_trigger,
            
            # Combat event triggers
            "consecutive_damage": self._check_consecutive_damage_trigger,
            "ally_defeated": self._check_ally_defeated_trigger,
            "successful_dodge": self._check_successful_dodge_trigger,
            "successful_block": self._check_successful_block_trigger,
            "fatal_damage_received": self._check_fatal_damage_received_trigger,
            
            # Formation and battlefield triggers
            "outnumbered": self._check_outnumbered_trigger,
            "last_ally_standing": self._check_last_ally_standing_trigger,
            "team_advantage": self._check_team_advantage_trigger,
            "enemy_formation_advantage": self._check_enemy_formation_advantage_trigger,
            "multiple_mages_alive": self._check_multiple_mages_alive_trigger,
            
            # Action and skill triggers
            "high_action_gauge": self._check_high_action_gauge_trigger,
            "ally_skill_chain": self._check_ally_skill_chain_trigger,
            "enemy_pattern_detected": self._check_enemy_pattern_detected_trigger,
            "enemy_high_defense": self._check_enemy_high_defense_trigger,
            
            # Status and effect triggers
            "multiple_debuffs": self._check_multiple_debuffs_trigger,
            "damaged_multiple_turns": self._check_damaged_multiple_turns_trigger,
            "battlefield_condition_active": self._check_battlefield_condition_active_trigger,
            
            # Time-based triggers
            "turn_start_chance": self._check_turn_start_chance_trigger,
            "round_end": self._check_round_end_trigger,
            
            # Passive triggers
            "passive": self._check_passive_trigger
        }
        
        # Initialize tracking variables for complex triggers
        # (These are now initialized in __init__)
    
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
        state = self._safe_get_component('state')
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
        state = self._safe_get_component('state')
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
        state = self._safe_get_component('state')
        if state:
            state.primed_skill = {
                'skill_name': signature_skill_name,
                'trigger': trigger_condition,
                'primed_turn': getattr(state, 'turn_count', 0)
            }
    
    def clear_primed_signature(self):
        """Clear any primed signature ability."""
        state = self._safe_get_component('state')
        if state:
            state.primed_skill = None
    
    def get_primed_signature(self):
        """Get the currently primed signature ability.
        
        Returns:
            dict or None: Primed skill data or None if no skill is primed
        """
        state = self._safe_get_component('state')
        if state:
            return getattr(state, 'primed_skill', None)
        return None
    
    def add_effect(self, effect):
        """Add an active effect to the character with interaction processing.
        
        Args:
            effect: BaseEffect instance to add
        """
        # Initialize interaction engine if needed (lazy loading)
        if not self.interaction_engine:
            try:
                from src.game.systems.effect_interaction_engine import EffectInteractionEngine
                self.interaction_engine = EffectInteractionEngine(self.event_bus)
            except ImportError:
                # Fallback to simple effect addition if interaction engine not available
                effect.target_character = self.character
                effect.apply_effect(self.event_bus)
                self.active_effects.append(effect)
                
                if self.event_bus:
                    self.event_bus.publish("EffectAdded", {
                        "character": self.character,
                        "effect": effect
                    })
                return
        
        # Process effect interactions
        final_effects, interaction_results = self.interaction_engine.process_effect_application(
            effect, self.active_effects, self.character
        )
        
        # Update active effects list
        self.active_effects = final_effects
        
        # Apply the effect if it wasn't blocked
        effect_blocked = any(result.get("action") == "block_new" for result in interaction_results)
        if not effect_blocked:
            effect.target_character = self.character
            effect.apply_effect(self.event_bus)
        
        # Publish interaction events
        if self.event_bus:
            for result in interaction_results:
                self.event_bus.publish("EffectInteraction", {
                    "character": self.character,
                    "interaction_result": result
                })
            
            if not effect_blocked:
                self.event_bus.publish("EffectAdded", {
                    "character": self.character,
                    "effect": effect,
                    "interactions": interaction_results
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
    
    def get_effect_interactions_summary(self):
        """Get a summary of all active effect interactions.
        
        Returns:
            Dictionary summarizing effect interactions
        """
        if not self.interaction_engine:
            return {
                "total_effects": len(self.active_effects),
                "interaction_engine": "not_available"
            }
        
        return self.interaction_engine.get_effect_interactions_summary(self.active_effects)
    
    def process_turn_effects(self):
        """Process all effects at turn start/end with interaction handling.
        
        Returns:
            List of effect processing results
        """
        if not self.interaction_engine:
            # Fallback to simple processing
            results = []
            for effect in self.active_effects:
                if hasattr(effect, 'on_turn_start'):
                    effect.on_turn_start(self.event_bus)
                results.append({
                    "effect": effect.__class__.__name__,
                    "message": "Effect processed (simple mode)"
                })
            return results
        
        return self.interaction_engine.process_turn_effects(self.character, self.active_effects)
    
    def has_immunity_to(self, effect_name):
        """Check if character has immunity to a specific effect.
        
        Args:
            effect_name: Name of effect to check immunity for
            
        Returns:
            bool: True if character is immune to the effect
        """
        if not self.interaction_engine:
            return False
        
        return self.interaction_engine._check_immunity(effect_name, self.active_effects)
    
    def get_effect_stacks(self, effect_name):
        """Get the number of stacks of a specific effect.
        
        Args:
            effect_name: Name of effect to count
            
        Returns:
            int: Number of stacks of the effect
        """
        count = 0
        for effect in self.active_effects:
            if (getattr(effect, 'name', effect.__class__.__name__.lower()) == effect_name and
                effect.is_active):
                count += 1
        return count
    
    def can_apply_effect(self, effect_name):
        """Check if an effect can be applied (not blocked by immunity or stack limits).
        
        Args:
            effect_name: Name of effect to check
            
        Returns:
            bool: True if effect can be applied
        """
        # Check immunity
        if self.has_immunity_to(effect_name):
            return False
        
        # Check stack limits
        if not self.interaction_engine:
            return True
        
        return self.interaction_engine._check_stacking_limit(effect_name, self.active_effects)
    
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
            skills_component = self._safe_get_component('skills')
            if skills_component and hasattr(skills_component, 'get_signature_skills'):
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

    # ========== EXPANDED SIGNATURE TRIGGER METHODS ==========
    
    def _check_ally_critical_health_trigger(self):
        """Check if any ally is at critical health (<15% HP)."""
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return False
        
        ally_team = self._get_ally_team(battle_context)
        if not ally_team:
            return False
        
        for ally in ally_team:
            if ally == self.character:
                continue
            state = ally.components.get('state')
            if state and state.is_alive:
                health_ratio = state.current_hp / state.max_hp
                if health_ratio <= 0.15:
                    return True
        return False
    
    def _check_ally_about_to_die_trigger(self):
        """Check if any ally would die from next hit."""
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return False
        
        ally_team = self._get_ally_team(battle_context)
        if not ally_team:
            return False
        
        for ally in ally_team:
            if ally == self.character:
                continue
            state = ally.components.get('state')
            if state and state.is_alive and state.current_hp <= 25:  # Estimated fatal damage threshold
                return True
        return False
    
    def _check_successful_dodge_trigger(self):
        """Check if character successfully dodged an attack."""
        return hasattr(self, '_successful_dodge_this_turn') and self._successful_dodge_this_turn
    
    def _check_successful_block_trigger(self):
        """Check if character successfully blocked an attack."""
        return hasattr(self, '_successful_block_this_turn') and self._successful_block_this_turn
    
    def _check_fatal_damage_received_trigger(self):
        """Check if character would receive fatal damage."""
        state = self._safe_get_component('state')
        if not state:
            return False
        return self._would_be_fatal
    
    def _check_team_advantage_trigger(self):
        """Check if team has numerical advantage."""
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return False
        
        team_one_alive = sum(1 for char in battle_context.team_one if char.components.get('state', {}).get('is_alive', False))
        team_two_alive = sum(1 for char in battle_context.team_two if char.components.get('state', {}).get('is_alive', False))
        
        if self.character in battle_context.team_one:
            return team_one_alive > team_two_alive
        else:
            return team_two_alive > team_one_alive
    
    def _check_enemy_formation_advantage_trigger(self):
        """Check if enemies have formation advantage."""
        return not self._check_team_advantage_trigger()  # Inverse of team advantage
    
    def _check_multiple_mages_alive_trigger(self):
        """Check if multiple mage-type allies are alive."""
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return False
        
        ally_team = self._get_ally_team(battle_context)
        if not ally_team:
            return False
        
        mage_count = 0
        for ally in ally_team:
            if ally.components.get('state', {}).get('is_alive', False):
                # Check if ally has high MAG stat (indicating mage archetype)
                stats = ally.components.get('stats')
                if stats and stats.get_stat('mag') > stats.get_stat('atk'):
                    mage_count += 1
        
        return mage_count >= 2
    
    def _check_ally_skill_chain_trigger(self):
        """Check if allies used skills in sequence."""
        return getattr(self, 'skill_chain_count', 0) >= 2
    
    def _check_enemy_pattern_detected_trigger(self):
        """Check if enemy patterns have been detected."""
        return len(getattr(self, 'last_enemy_actions', [])) >= 3
    
    def _check_enemy_high_defense_trigger(self):
        """Check if facing an enemy with high defense."""
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return False
        
        enemy_team = self._get_enemy_team(battle_context)
        if not enemy_team:
            return False
        
        for enemy in enemy_team:
            if enemy.components.get('state', {}).get('is_alive', False):
                stats = enemy.components.get('stats')
                if stats and (stats.get_stat('vit') > 150 or stats.get_stat('spr') > 150):
                    return True
        return False
    
    def _check_damaged_multiple_turns_trigger(self):
        """Check if character has been damaged for multiple consecutive turns."""
        return getattr(self, 'damage_turn_count', 0) >= 3
    
    def _check_battlefield_condition_active_trigger(self):
        """Check if any battlefield condition is active."""
        # This would check global battlefield conditions
        rule_engine = getattr(self.event_bus, 'rule_engine', None)
        if rule_engine:
            return rule_engine.get_rule('battlefield.condition_active', False)
        return False
    
    def _check_turn_start_chance_trigger(self):
        """Check random chance trigger at turn start."""
        import random
        return random.randint(1, 100) <= 20  # 20% chance
    
    def _check_round_end_trigger(self):
        """Check if it's the end of a round."""
        battle_context = getattr(self.event_bus, 'battle_context', None)
        if not battle_context:
            return False
        return hasattr(self, '_round_ending') and self._round_ending
    
    def _check_passive_trigger(self):
        """Check for passive abilities (always active)."""
        return True
    
    def _get_ally_team(self, battle_context):
        """Get the ally team for this character."""
        if self.character in battle_context.team_one:
            return battle_context.team_one
        elif self.character in battle_context.team_two:
            return battle_context.team_two
        return None
    
    def _get_enemy_team(self, battle_context):
        """Get the enemy team for this character."""
        if self.character in battle_context.team_one:
            return battle_context.team_two
        elif self.character in battle_context.team_two:
            return battle_context.team_one
        return None