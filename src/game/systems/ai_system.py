"""AI system for character decision making - Three-Phase Intelligence."""

import random
from .base_system import BaseSystem
from .action_command import ActionCommand

# Import rule engine for dynamic configuration
try:
    from src.game.core.rule_engine import get_ai_rule, get_signature_rule
except ImportError:
    # Fallback if rule engine is not available
    def get_ai_rule(rule_name, default=None):
        return default
    def get_signature_rule(rule_name, default=None):
        return default

class AI_System(BaseSystem):
    """Handles AI decision making for characters using Three-Phase Intelligence:
    Phase 1: Role Selection based on battlefield analysis
    Phase 2: Skill Selection filtered by chosen role
    Phase 3: Target Priority Score (TPS) calculation
    """
    
    # Role potency mappings from archetype data
    ROLE_POTENCY_VALUES = {
        'S': 4.0, 'A': 3.0, 'B': 2.0, 'C': 1.0, 'D': 0.5, 'F': 0.1
    }
    
    def choose_action(self, character):
        """Choose an action for the given character using Three-Phase AI.
        
        Args:
            character: The character making the decision
            
        Returns:
            ActionCommand object representing the chosen action
        """
        if not character:
            return None
        
        # Check for primed signature abilities first (highest priority)
        primed_action = self._check_primed_signature_ability(character)
        if primed_action:
            return primed_action
        
        # Phase 1: Role Selection
        chosen_role = self._phase_1_role_selection(character)
        
        # Phase 2: Skill Selection
        chosen_skill = self._phase_2_skill_selection(character, chosen_role)
        
        # Phase 3: Target Priority Score calculation
        targets = self._phase_3_target_selection(character, chosen_skill)
        
        if not targets:
            # Fallback to basic attack on random enemy
            enemies = self._get_enemies(character)
            if enemies:
                return ActionCommand(
                    caster=character,
                    skill_name="basic_attack",
                    targets=[random.choice(enemies)],
                    skill_data={"type": "damage", "element": "physical"}
                )
            return None
        
        return ActionCommand(
            caster=character,
            skill_name=chosen_skill['name'],
            targets=targets,
            skill_data=chosen_skill
        )
    
    def _check_primed_signature_ability(self, character):
        """Check if character has a primed signature ability ready to use.
        
        Args:
            character: The character to check
            
        Returns:
            ActionCommand or None: Primed signature ability action or None
        """
        effects_component = character.components.get('effects')
        if not effects_component:
            return None
        
        primed_skill = effects_component.get_primed_signature()
        if not primed_skill:
            return None
        
        skill_name = primed_skill['skill_name']
        
        # Check if the signature skill is actually available
        skills_component = character.components.get('skills')
        if not skills_component or not skills_component.is_skill_available(skill_name):
            # Clear invalid primed skill
            effects_component.clear_primed_signature()
            return None
        
        # Get skill data
        skill_data = skills_component.get_skill_data(skill_name)
        if not skill_data:
            effects_component.clear_primed_signature()
            return None
        
        # Get targets for signature ability
        targets = self._phase_3_target_selection(character, skill_data)
        if not targets:
            # Clear primed skill if no valid targets
            effects_component.clear_primed_signature()
            return None
        
        # Clear primed skill since we're using it
        effects_component.clear_primed_signature()
        
        return ActionCommand(
            caster=character,
            skill_name=skill_name,
            targets=targets,
            skill_data=skill_data
        )
    
    def _phase_1_role_selection(self, character):
        """Phase 1: Select optimal role based on battlefield analysis.
        
        Args:
            character: The character making the decision
            
        Returns:
            str: Chosen role (Attacker, Mage, Healer, Buffer, Debuffer, Defender, Specialist)
        """
        # Get character's archetype and role potencies
        archetype_component = character.components.get('archetype')
        if not archetype_component:
            return 'Attacker'  # Fallback
        
        archetype_data = archetype_component.archetype_data
        role_potencies = archetype_data.get('role_potency', {})
        
        # Calculate base weights from role potencies
        role_weights = {}
        for role, potency in role_potencies.items():
            role_weights[role] = self.ROLE_POTENCY_VALUES.get(potency, 1.0)
        
        # Apply dynamic weight modifiers based on battlefield conditions
        self._apply_battlefield_modifiers(character, role_weights)
        
        # Weighted random selection
        return self._weighted_random_choice(role_weights)
    
    def _apply_battlefield_modifiers(self, character, role_weights):
        """Apply dynamic weight modifiers based on battlefield conditions.
        
        Args:
            character: The character making the decision
            role_weights: Dict of role -> weight to modify
        """
        allies = self._get_allies(character)
        enemies = self._get_enemies(character)
        
        # Health Status Analysis
        ally_avg_hp = self._get_average_hp_percentage(allies) if allies else 1.0
        enemy_avg_hp = self._get_average_hp_percentage(enemies) if enemies else 1.0
        
        # Get health thresholds from rule engine
        health_threshold_low = get_ai_rule("role_selection_weights.health_threshold_low", 0.4)
        health_threshold_critical = get_ai_rule("role_selection_weights.health_threshold_critical", 0.25)
        max_weight_multiplier = get_ai_rule("role_selection_weights.max_weight_multiplier", 3.0)
        
        # Low Health - favor healing and defense
        if ally_avg_hp < health_threshold_low:
            role_weights['Healer'] = role_weights.get('Healer', 1.0) * 2.0
            role_weights['Defender'] = role_weights.get('Defender', 1.0) * 1.5
        
        # High enemy health - favor damage
        if enemy_avg_hp > 0.7:
            role_weights['Attacker'] = role_weights.get('Attacker', 1.0) * 1.5
            role_weights['Mage'] = role_weights.get('Mage', 1.0) * 1.5
        
        # Buff/Debuff Analysis
        ally_buffs = self._count_buffs_on_team(allies)
        enemy_debuffs = self._count_debuffs_on_team(enemies)
        
        # Few ally buffs - favor buffing
        if ally_buffs < len(allies):
            role_weights['Buffer'] = role_weights.get('Buffer', 1.0) * 1.5
        
        # Few enemy debuffs - favor debuffing
        if enemy_debuffs < len(enemies):
            role_weights['Debuffer'] = role_weights.get('Debuffer', 1.0) * 1.5
        
        # Self-condition modifiers
        state_component = character.components.get('state')
        if state_component:
            self_hp_pct = state_component.current_hp / state_component.max_hp
            
            # Low self HP - defensive stance
            if self_hp_pct < 0.4:
                role_weights['Defender'] = role_weights.get('Defender', 1.0) * 1.5
                role_weights['Healer'] = role_weights.get('Healer', 1.0) * 1.5
            
            # Check for self buffs
            effects_component = character.components.get('effects')
            if effects_component:
                active_effects = effects_component.get_active_effects()
                has_atk_buff = any('atk_up' in effect.name.lower() for effect in active_effects)
                has_mag_buff = any('mag_up' in effect.name.lower() for effect in active_effects)
                has_def_buff = any('vit_up' in effect.name.lower() or 'spr_up' in effect.name.lower() for effect in active_effects)
                
                # Synergy modifiers
                if has_atk_buff:
                    role_weights['Attacker'] = role_weights.get('Attacker', 1.0) * 1.75
                if has_mag_buff:
                    role_weights['Mage'] = role_weights.get('Mage', 1.0) * 1.75
                if has_def_buff:
                    role_weights['Defender'] = role_weights.get('Defender', 1.0) * 2.0
    
    def _phase_2_skill_selection(self, character, chosen_role):
        """Phase 2: Select skill based on chosen role and availability.
        
        Args:
            character: The character making the decision
            chosen_role: Role selected in Phase 1
            
        Returns:
            dict: Chosen skill data
        """
        skill_component = character.components.get('skills')
        if not skill_component:
            return {"name": "basic_attack", "type": "damage", "element": "physical"}
        
        # Get available skills (not on cooldown)
        available_skills = []
        for skill_name in skill_component.skills:
            if skill_component.is_skill_available(skill_name):
                skill_data = skill_component.get_skill_data(skill_name)
                if skill_data:
                    available_skills.append(skill_data)
        
        if not available_skills:
            return {"name": "basic_attack", "type": "damage", "element": "physical"}
        
        # Filter skills by role preference
        role_filtered_skills = self._filter_skills_by_role(available_skills, chosen_role)
        
        if not role_filtered_skills:
            # No role-specific skills available, use any available skill
            role_filtered_skills = available_skills
        
        # Select skill based on power weight and situational factors
        return self._select_best_skill(character, role_filtered_skills, chosen_role)
    
    def _filter_skills_by_role(self, skills, role):
        """Filter skills that match the chosen role.
        
        Args:
            skills: List of available skill data dicts
            role: Target role to filter for
            
        Returns:
            List of skills matching the role
        """
        role_skill_types = {
            'Attacker': ['damage'],
            'Mage': ['damage'],  # Magic damage
            'Healer': ['heal'],
            'Buffer': ['buff'],
            'Debuffer': ['debuff'],
            'Defender': ['defensive', 'taunt'],
            'Specialist': ['special', 'utility']
        }
        
        target_types = role_skill_types.get(role, ['damage'])
        filtered_skills = []
        
        for skill in skills:
            skill_type = skill.get('type', 'damage')
            # Check if skill type matches role or if it's a multi-type skill
            if skill_type in target_types or any(t in skill_type for t in target_types):
                filtered_skills.append(skill)
            # Special case for Mage role - prefer MAG scaling
            elif role == 'Mage' and skill.get('scaling_stat') == 'mag':
                filtered_skills.append(skill)
        
        return filtered_skills
    
    def _select_best_skill(self, character, skills, role):
        """Select the best skill from filtered options.
        
        Args:
            character: The character making the decision
            skills: List of available skills
            role: Chosen role
            
        Returns:
            dict: Best skill data
        """
        if len(skills) == 1:
            return skills[0]
        
        # Score skills based on power weight and situational factors
        skill_scores = {}
        
        for skill in skills:
            score = skill.get('power_weight', 50)  # Base power weight
            
            # Role synergy bonus
            if self._skill_matches_role_perfectly(skill, role):
                score *= 1.3
            
            # Situational bonuses
            score = self._apply_situational_skill_bonuses(character, skill, score)
            
            skill_scores[skill['name']] = score
        
        # Select skill with highest score
        best_skill_name = max(skill_scores.keys(), key=lambda k: skill_scores[k])
        return next(s for s in skills if s['name'] == best_skill_name)
    
    def _skill_matches_role_perfectly(self, skill, role):
        """Check if skill perfectly matches the chosen role.
        
        Args:
            skill: Skill data dict
            role: Target role
            
        Returns:
            bool: True if perfect match
        """
        perfect_matches = {
            'Attacker': ['damage'] and skill.get('scaling_stat') == 'atk',
            'Mage': ['damage'] and skill.get('scaling_stat') == 'mag',
            'Healer': skill.get('type') == 'heal',
            'Buffer': skill.get('type') == 'buff',
            'Debuffer': skill.get('type') == 'debuff',
            'Defender': skill.get('type') in ['defensive', 'taunt']
        }
        
        return perfect_matches.get(role, False)
    
    def _apply_situational_skill_bonuses(self, character, skill, base_score):
        """Apply situational bonuses to skill scoring.
        
        Args:
            character: The character making the decision
            skill: Skill data dict
            base_score: Base power weight score
            
        Returns:
            float: Modified score
        """
        score = base_score
        
        # Low health bonus for healing skills
        if skill.get('type') == 'heal':
            allies = self._get_allies(character)
            avg_hp = self._get_average_hp_percentage(allies) if allies else 1.0
            if avg_hp < 0.5:
                score *= 1.5
        
        # High enemy health bonus for damage skills
        if skill.get('type') == 'damage':
            enemies = self._get_enemies(character)
            avg_hp = self._get_average_hp_percentage(enemies) if enemies else 1.0
            if avg_hp > 0.7:
                score *= 1.3
        
        # AoE skills bonus when multiple targets available
        if skill.get('target_count', 1) > 1:
            if skill.get('type') == 'damage':
                enemy_count = len(self._get_enemies(character))
                if enemy_count >= 3:
                    score *= 1.4
            elif skill.get('type') in ['heal', 'buff']:
                ally_count = len(self._get_allies(character))
                if ally_count >= 3:
                    score *= 1.4
        
        return score
    
    def _phase_3_target_selection(self, character, skill):
        """Phase 3: Calculate Target Priority Score for optimal targeting.
        
        Args:
            character: The character making the decision
            skill: Chosen skill data
            
        Returns:
            List of target characters
        """
        skill_type = skill.get('type', 'damage')
        target_count = skill.get('target_count', 1)
        
        if skill_type in ['damage', 'debuff']:
            candidates = self._get_enemies(character)
        elif skill_type in ['heal', 'buff']:
            candidates = self._get_allies(character)
        else:
            candidates = self._get_all_valid_targets(character)
        
        if not candidates:
            return []
        
        if target_count >= len(candidates):
            return candidates
        
        # Calculate Target Priority Score (TPS) for each candidate
        target_scores = {}
        for target in candidates:
            tps = self._calculate_target_priority_score(character, target, skill)
            target_scores[target] = tps
        
        # Select top scoring targets
        sorted_targets = sorted(target_scores.keys(), key=lambda t: target_scores[t], reverse=True)
        return sorted_targets[:target_count]
    
    def _calculate_target_priority_score(self, character, target, skill):
        """Calculate Target Priority Score (TPS) for a potential target.
        
        Args:
            character: The character making the decision
            target: Potential target character
            skill: Skill being used
            
        Returns:
            float: Target Priority Score
        """
        skill_type = skill.get('type', 'damage')
        base_score = 50.0
        
        if skill_type in ['damage', 'debuff']:
            return self._calculate_enemy_tps(character, target, skill, base_score)
        elif skill_type in ['heal', 'buff']:
            return self._calculate_ally_tps(character, target, skill, base_score)
        
        return base_score
    
    def _calculate_enemy_tps(self, character, enemy, skill, base_score):
        """Calculate TPS for enemy targets (damage/debuff skills).
        
        Args:
            character: The character making the decision
            enemy: Enemy target
            skill: Skill being used
            base_score: Base TPS value
            
        Returns:
            float: Enemy TPS
        """
        score = base_score
        
        # Get targeting priority bonuses from rule engine
        low_hp_bonus = get_ai_rule("targeting_priorities.low_hp_bonus", 30)
        high_threat_bonus = get_ai_rule("targeting_priorities.high_threat_bonus", 20)
        position_front_bonus = get_ai_rule("targeting_priorities.position_front_bonus", 10)
        position_back_bonus = get_ai_rule("targeting_priorities.position_back_bonus", 5)
        
        # Health Priority - prefer low HP enemies for finishing
        enemy_state = enemy.components.get('state')
        if enemy_state:
            hp_pct = enemy_state.current_hp / enemy_state.max_hp
            if hp_pct < 0.3:
                score += low_hp_bonus  # High priority for low HP enemies
            elif hp_pct < 0.6:
                score += low_hp_bonus // 2
        
        # Threat Assessment - target high damage dealers
        enemy_stats = enemy.components.get('stats')
        if enemy_stats:
            atk = enemy_stats.get_stat('atk')
            mag = enemy_stats.get_stat('mag')
            threat_level = max(atk, mag)
            score += (threat_level * high_threat_bonus) / 1000  # Scale with threat
        
        # Debuff Resistance - avoid heavily debuffed enemies for debuff skills
        if skill.get('type') == 'debuff':
            enemy_effects = enemy.components.get('effects')
            if enemy_effects:
                debuff_count = len([e for e in enemy_effects.get_active_effects() if hasattr(e, 'effect_type') and e.effect_type == 'debuff'])
                score -= debuff_count * 5  # Lower priority if already debuffed
        
        # Position Priority - prefer front row for AoE, back row for single target
        position_component = enemy.components.get('position')
        if position_component:
            if skill.get('target_count', 1) > 1:  # AoE skills
                if position_component.row == 0:  # Front row
                    score += position_front_bonus
            else:  # Single target skills
                if position_component.row == 1:  # Back row (usually squishier)
                    score += position_back_bonus
        
        return score
    
    def _calculate_ally_tps(self, character, ally, skill, base_score):
        """Calculate TPS for ally targets (heal/buff skills).
        
        Args:
            character: The character making the decision
            ally: Ally target
            skill: Skill being used
            base_score: Base TPS value
            
        Returns:
            float: Ally TPS
        """
        score = base_score
        
        # Health Priority - prefer low HP allies for healing
        if skill.get('type') == 'heal':
            ally_state = ally.components.get('state')
            if ally_state:
                hp_pct = ally_state.current_hp / ally_state.max_hp
                if hp_pct < 0.3:
                    score += 40  # Very high priority for critically wounded
                elif hp_pct < 0.6:
                    score += 20
                elif hp_pct > 0.9:
                    score -= 20  # Low priority for healthy allies
        
        # Buff Efficiency - target allies who can use the buff effectively
        if skill.get('type') == 'buff':
            ally_archetype = ally.components.get('archetype')
            if ally_archetype:
                # Example: ATK buff on attackers, MAG buff on mages
                buff_effects = skill.get('effects', [])
                for effect in buff_effects:
                    if 'atk_up' in effect.get('name', '').lower():
                        if 'Attacker' in ally_archetype.archetype_data.get('role_potency', {}):
                            score += 15
                    elif 'mag_up' in effect.get('name', '').lower():
                        if 'Mage' in ally_archetype.archetype_data.get('role_potency', {}):
                            score += 15
        
        # Position Priority - protect front line allies
        position_component = ally.components.get('position')
        if position_component and position_component.row == 0:
            score += 10
        
        # Don't target self unless necessary
        if ally == character:
            score -= 5
        
        return score
    
    def _weighted_random_choice(self, weights):
        """Make a weighted random choice from a dictionary of weights.
        
        Args:
            weights: Dict of choice -> weight
            
        Returns:
            str: Chosen option
        """
        if not weights:
            return 'Attacker'  # Fallback
        
        choices = list(weights.keys())
        weight_values = list(weights.values())
        
        # Ensure all weights are positive
        weight_values = [max(0.1, w) for w in weight_values]
        
        return random.choices(choices, weights=weight_values)[0]
    
    def _get_allies(self, character):
        """Get list of allied characters (including self).
        
        Args:
            character: The character looking for allies
            
        Returns:
            List of allied characters that are alive
        """
        if not character:
            return []
        
        # Determine which team the character is on
        if character in self.battle_context.team_one:
            ally_team = self.battle_context.team_one
        elif character in self.battle_context.team_two:
            ally_team = self.battle_context.team_two
        else:
            return []
        
        # Filter for alive allies
        alive_allies = []
        for ally in ally_team:
            state_component = ally.components.get('state')
            if state_component and state_component.is_alive:
                alive_allies.append(ally)
        
        return alive_allies
    
    def _get_enemies(self, character):
        """Get list of valid enemy targets for the character.
        
        Args:
            character: The character looking for enemies
            
        Returns:
            List of enemy characters that are alive
        """
        if not character:
            return []
        
        # Determine which team the character is on
        if character in self.battle_context.team_one:
            enemy_team = self.battle_context.team_two
        elif character in self.battle_context.team_two:
            enemy_team = self.battle_context.team_one
        else:
            return []
        
        # Filter for alive enemies
        alive_enemies = []
        for enemy in enemy_team:
            state_component = enemy.components.get('state')
            if state_component and state_component.is_alive:
                alive_enemies.append(enemy)
        
        return alive_enemies
    
    def _get_all_valid_targets(self, character):
        """Get all valid targets (both allies and enemies).
        
        Args:
            character: The character looking for targets
            
        Returns:
            List of all valid target characters
        """
        return self._get_allies(character) + self._get_enemies(character)
    
    def _get_average_hp_percentage(self, characters):
        """Calculate average HP percentage for a list of characters.
        
        Args:
            characters: List of characters
            
        Returns:
            float: Average HP percentage (0.0 to 1.0)
        """
        if not characters:
            return 1.0
        
        total_hp_pct = 0.0
        for char in characters:
            state_component = char.components.get('state')
            if state_component and state_component.max_hp > 0:
                hp_pct = state_component.current_hp / state_component.max_hp
                total_hp_pct += hp_pct
        
        return total_hp_pct / len(characters)
    
    def _count_buffs_on_team(self, characters):
        """Count total number of buffs on a team.
        
        Args:
            characters: List of characters to check
            
        Returns:
            int: Total buff count
        """
        total_buffs = 0
        for char in characters:
            effects_component = char.components.get('effects')
            if effects_component:
                active_effects = effects_component.get_active_effects()
                buff_count = len([e for e in active_effects if e.effect_type == 'buff'])
                total_buffs += buff_count
        
        return total_buffs
    
    def _count_debuffs_on_team(self, characters):
        """Count total number of debuffs on a team.
        
        Args:
            characters: List of characters to check
            
        Returns:
            int: Total debuff count
        """
        total_debuffs = 0
        for char in characters:
            effects_component = char.components.get('effects')
            if effects_component:
                active_effects = effects_component.get_active_effects()
                debuff_count = len([e for e in active_effects if e.effect_type == 'debuff'])
                total_debuffs += debuff_count
        
        return total_debuffs