"""Combat system for resolving actions and damage."""

from .base_system import BaseSystem

class CombatSystem(BaseSystem):
    """Handles combat resolution and damage calculation."""
    
    def __init__(self, battle_context, event_bus, skill_registry=None):
        """Initialize combat system with skill registry.
        
        Args:
            battle_context: BattleContext instance
            event_bus: EventBus instance
            skill_registry: SkillRegistry for looking up skill data
        """
        super().__init__(battle_context, event_bus)
        self.skill_registry = skill_registry
    
    def resolve_action(self, action_command):
        """Resolve an action command and apply its effects.
        
        Args:
            action_command: ActionCommand object containing action details
        """
        if not action_command or not action_command.targets:
            return
        
        # Publish PreProcess_Action hook for action cancellation (e.g., Stun)
        cancel_event = self.event_bus.publish("PreProcess_Action", {
            "action_command": action_command,
            "caster": action_command.caster
        })
        
        if cancel_event and cancel_event.get("cancelled"):
            return
        
        # Look up skill data from registry if available
        skill_data = self._get_skill_data(action_command.skill_name, action_command.skill_data)
        
        # Apply skill cooldown
        self._apply_skill_cooldown(action_command.caster, action_command.skill_name, skill_data)
        
        # Resolve different skill types
        skill_type = skill_data.get("type", "damage")
        
        if skill_type == "damage":
            self._resolve_damage_skill(action_command, skill_data)
        elif skill_type == "heal":
            self._resolve_heal_skill(action_command, skill_data)
        elif skill_type == "buff":
            self._resolve_buff_skill(action_command, skill_data)
        else:
            # Default to basic attack for unknown skills
            self._resolve_basic_attack(action_command)
    
    def _get_skill_data(self, skill_name, fallback_data):
        """Get skill data from registry or use fallback.
        
        Args:
            skill_name: Name of the skill
            fallback_data: Fallback skill data if not in registry
            
        Returns:
            Dictionary containing skill data
        """
        if self.skill_registry:
            skill = self.skill_registry.get(skill_name)
            if skill:
                return skill.to_skill_data()
        
        # Use fallback data if skill not found in registry
        return fallback_data or {}
    
    def _apply_skill_cooldown(self, caster, skill_name, skill_data):
        """Apply cooldown to the skill after use.
        
        Args:
            caster: Character using the skill
            skill_name: Name of the skill
            skill_data: Skill data containing cooldown info
        """
        cooldown = skill_data.get("cooldown", 0)
        if cooldown > 0:
            state_component = caster.components.get('state')
            if state_component:
                state_component.set_skill_cooldown(skill_name, cooldown)
    
    def _resolve_basic_attack(self, action_command):
        """Resolve a basic attack action using the new damage system."""
        # Convert basic attack to damage skill format
        skill_data = {
            "type": "damage",
            "element": "physical",
            "multiplier": 1.0,
            "scaling_params": {
                "floor": 20,
                "ceiling": 200,
                "sc1": 50,
                "sc2": 200,
                "post_cap_rate": 0.5
            }
        }
        
        # Update action command with proper skill data
        action_command.skill_data = skill_data
        
        # Use the new damage resolution system
        self._resolve_damage_skill(action_command)
    
    def _resolve_damage_skill(self, action_command, skill_data=None):
        """Resolve a damage-dealing skill using Universal Scaling Formula."""
        caster = action_command.caster
        skill_data = skill_data or action_command.skill_data or {}
        
        # Get caster's stats
        caster_stats = caster.components.get('stats')
        if not caster_stats:
            return
        
        # Determine damage type and scaling stat
        element = skill_data.get("element", "physical")
        if element == "physical":
            scaling_stat = caster_stats.get_stat('atk')
        else:
            scaling_stat = caster_stats.get_stat('mag')
        
        # Get skill parameters (with defaults for basic_attack)
        skill_multiplier = skill_data.get("multiplier", 1.0)
        scaling_params = skill_data.get("scaling_params", {
            "floor": 20,
            "ceiling": 200,
            "sc1": 50,
            "sc2": 200,
            "post_cap_rate": 0.5
        })
        
        for target in action_command.targets:
            if not self._is_valid_target(target):
                continue
            
            # Publish PreProcess_DamageCalculation hook
            pre_calc_event = self.event_bus.publish("PreProcess_DamageCalculation", {
                "caster": caster,
                "target": target,
                "scaling_stat": scaling_stat,
                "skill_data": skill_data
            })
            
            # Apply any stat modifications from pre-calculation hooks
            modified_scaling_stat = pre_calc_event.get("modified_scaling_stat", scaling_stat) if pre_calc_event else scaling_stat
            
            # Calculate Potency Value using GDD 6.2 formulas
            potency_value = self._calculate_potency_value(
                modified_scaling_stat, skill_multiplier, target, element
            )
            
            # Apply Universal Scaling Formula (GDD 6.1)
            scaled_damage = self._apply_universal_scaling(potency_value, scaling_params)
            
            # Publish PostProcess_DamageCalculation hook
            post_calc_event = self.event_bus.publish("PostProcess_DamageCalculation", {
                "caster": caster,
                "target": target,
                "base_damage": scaled_damage,
                "skill_data": skill_data
            })
            
            # Apply any final modifications (crits, elemental bonuses, etc.)
            final_damage = post_calc_event.get("modified_damage", scaled_damage) if post_calc_event else scaled_damage
            final_damage = max(1, int(final_damage))  # Minimum 1 damage
            
            # Apply damage to target
            self._apply_damage(target, final_damage, caster, skill_data)
    
    def _resolve_heal_skill(self, action_command, skill_data=None):
        """Resolve a healing skill using Universal Scaling Formula."""
        caster = action_command.caster
        skill_data = skill_data or action_command.skill_data or {}
        
        # Get caster's stats
        caster_stats = caster.components.get('stats')
        if not caster_stats:
            return
        
        # Calculate heal potency: (INT * 0.5) + (SPR * 1.25)
        int_stat = caster_stats.get_stat('int')
        spr_stat = caster_stats.get_stat('spr')
        base_heal = (int_stat * 0.5) + (spr_stat * 1.25)
        
        # Get skill parameters
        skill_multiplier = skill_data.get("multiplier", 1.0)
        scaling_params = skill_data.get("scaling_params", {
            "floor": 15,
            "ceiling": 300,
            "sc1": 40,
            "sc2": 150,
            "post_cap_rate": 0.4
        })
        
        potency_value = base_heal * skill_multiplier
        scaled_heal = self._apply_universal_scaling(potency_value, scaling_params)
        
        for target in action_command.targets:
            target_state = target.components.get('state')
            if not target_state:
                continue
            
            # Apply healing
            old_hp = target_state.current_hp
            max_hp = target_state.max_hp
            target_state.current_hp = min(max_hp, target_state.current_hp + int(scaled_heal))
            
            # Publish HP changed event
            self.event_bus.publish("HPChanged", {
                "character": target,
                "old_hp": old_hp,
                "new_hp": target_state.current_hp,
                "heal": int(scaled_heal),
                "source": caster
            })
    
    def _resolve_buff_skill(self, action_command, skill_data=None):
        """Resolve a buff/debuff skill."""
        # Placeholder for Phase 3 effects system
        skill_data = skill_data or action_command.skill_data or {}
        print(f"Buff skill {action_command.skill_name} not yet implemented")
    
    def _calculate_potency_value(self, scaling_stat, skill_multiplier, target, element):
        """Calculate base potency value using GDD 6.2 formulas."""
        target_stats = target.components.get('stats')
        if not target_stats:
            return 0
        
        base_damage = scaling_stat * skill_multiplier
        
        if element == "physical":
            # Physical damage: (ATK * Multiplier) * (1 - VIT/(150 + VIT))
            target_vit = target_stats.get_stat('vit')
            damage_reduction = target_vit / (150 + target_vit)
            potency_value = base_damage * (1 - damage_reduction)
        else:
            # Magical damage: (MAG * Multiplier) * (1 - (VIT*0.6 + SPR*0.4)/(150 + VIT*0.6 + SPR*0.4))
            target_vit = target_stats.get_stat('vit')
            target_spr = target_stats.get_stat('spr')
            combined_defense = (target_vit * 0.6) + (target_spr * 0.4)
            damage_reduction = combined_defense / (150 + combined_defense)
            potency_value = base_damage * (1 - damage_reduction)
        
        return max(1, potency_value)
    
    def _apply_universal_scaling(self, potency_value, scaling_params):
        """Apply Universal Scaling Formula (GDD 6.1)."""
        floor = scaling_params.get("floor", 20)
        ceiling = scaling_params.get("ceiling", 200)
        sc1 = scaling_params.get("sc1", 50)
        sc2 = scaling_params.get("sc2", 200)
        post_cap_rate = scaling_params.get("post_cap_rate", 0.5)
        
        if potency_value <= sc1:
            # Below first softcap
            final_value = floor
        elif potency_value <= sc2:
            # Between softcaps
            final_value = floor + (potency_value - sc1)
        else:
            # Above second softcap
            final_value = (floor + (sc2 - sc1)) + ((potency_value - sc2) * post_cap_rate)
        
        # For buffs/debuffs, cap by ceiling (damage skills don't have this limit)
        if ceiling and "buff" in scaling_params.get("type", ""):
            final_value = min(final_value, ceiling)
        
        return final_value
    
    def _apply_damage(self, target, damage, caster, skill_data):
        """Apply final damage to target and publish events."""
        target_state = target.components.get('state')
        if not target_state:
            return
        
        # Apply damage
        old_hp = target_state.current_hp
        target_state.current_hp = max(0, target_state.current_hp - damage)
        
        # Publish HP changed event
        self.event_bus.publish("HPChanged", {
            "character": target,
            "old_hp": old_hp,
            "new_hp": target_state.current_hp,
            "damage": damage,
            "source": caster,
            "skill_data": skill_data
        })
        
        # Check if character was defeated
        if target_state.current_hp <= 0 and target_state.is_alive:
            target_state.is_alive = False
            self.event_bus.publish("CharacterDefeated", {
                "character": target,
                "killer": caster
            })
    
    def _is_valid_target(self, target):
        """Check if target is valid for combat."""
        if not target:
            return False
        
        target_state = target.components.get('state')
        return target_state and target_state.is_alive