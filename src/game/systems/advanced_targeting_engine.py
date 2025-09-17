"""Advanced Targeting Algorithms for multi-target skills and complex targeting patterns."""

from typing import List, Dict, Set, Optional, Tuple, Any
from enum import Enum
import random
import math

class TargetPattern(Enum):
    """Types of target patterns for advanced skills."""
    SINGLE = "single"                           # Single target
    ALL_ENEMIES = "all_enemies"                 # All enemy targets
    ALL_ALLIES = "all_allies"                   # All ally targets
    RANDOM_ENEMIES = "random_enemies"           # Random subset of enemies
    RANDOM_ALLIES = "random_allies"             # Random subset of allies
    FRONT_ROW = "front_row"                     # Front row targets
    BACK_ROW = "back_row"                       # Back row targets
    AOE_SPLASH = "aoe_splash"                   # Area around primary target
    CHAIN_TARGET = "chain_target"               # Chain from primary to nearby
    FORMATION_LINE = "formation_line"           # Entire row/column
    PRIORITY_TARGET = "priority_target"         # Highest/lowest stat target
    CONDITIONAL_TARGET = "conditional_target"   # Based on status/effects
    SELF = "self"                              # Self-target only
    SMART_MULTI = "smart_multi"                # AI-selected multiple targets

class TargetingContext:
    """Context information for advanced targeting decisions."""
    
    def __init__(self, caster, allies, enemies, battle_context=None):
        """Initialize targeting context.
        
        Args:
            caster: Character using the skill
            allies: List of allied characters
            enemies: List of enemy characters
            battle_context: Optional battle context for formation data
        """
        self.caster = caster
        self.allies = allies
        self.enemies = enemies
        self.battle_context = battle_context
        
        # Formation analysis
        self.formation_data = self._analyze_formation()
        
        # Statistical analysis
        self.ally_stats = self._analyze_team_stats(allies)
        self.enemy_stats = self._analyze_team_stats(enemies)
    
    def _analyze_formation(self):
        """Analyze battlefield formation and positioning."""
        formation = {
            'ally_front_row': [],
            'ally_back_row': [],
            'enemy_front_row': [],
            'enemy_back_row': [],
            'ally_positions': {},
            'enemy_positions': {}
        }
        
        # Analyze ally formation
        for i, ally in enumerate(self.allies):
            if not ally:
                continue
            
            # Simulate formation based on character archetype for now
            # In a real implementation, this would use actual position components
            archetype = ally.components.get('archetype')
            if archetype:
                role_potencies = archetype.archetype_data.get('role_potency', {})
                
                # Front row: Defenders, Attackers with high potency
                if (role_potencies.get('Defender', 'F') in ['S', 'A'] or
                    role_potencies.get('Attacker', 'F') in ['S', 'A']):
                    formation['ally_front_row'].append(ally)
                    formation['ally_positions'][ally] = {'row': 0, 'column': len(formation['ally_front_row']) - 1}
                else:
                    formation['ally_back_row'].append(ally)
                    formation['ally_positions'][ally] = {'row': 1, 'column': len(formation['ally_back_row']) - 1}
        
        # Analyze enemy formation (similar logic)
        for i, enemy in enumerate(self.enemies):
            if not enemy:
                continue
            
            archetype = enemy.components.get('archetype')
            if archetype:
                role_potencies = archetype.archetype_data.get('role_potency', {})
                
                if (role_potencies.get('Defender', 'F') in ['S', 'A'] or
                    role_potencies.get('Attacker', 'F') in ['S', 'A']):
                    formation['enemy_front_row'].append(enemy)
                    formation['enemy_positions'][enemy] = {'row': 0, 'column': len(formation['enemy_front_row']) - 1}
                else:
                    formation['enemy_back_row'].append(enemy)
                    formation['enemy_positions'][enemy] = {'row': 1, 'column': len(formation['enemy_back_row']) - 1}
        
        return formation
    
    def _analyze_team_stats(self, team):
        """Analyze statistical information about a team."""
        if not team:
            return {}
        
        stats = {
            'total_hp': 0,
            'average_hp_pct': 0,
            'lowest_hp': None,
            'highest_hp': None,
            'lowest_hp_pct': 1.0,
            'highest_threat': None,
            'total_alive': 0
        }
        
        alive_members = []
        hp_percentages = []
        
        for member in team:
            if not member:
                continue
            
            state = member.components.get('state')
            if not state or not getattr(state, 'is_alive', True):
                continue
            
            alive_members.append(member)
            stats['total_alive'] += 1
            
            hp_pct = state.current_hp / state.max_hp if state.max_hp > 0 else 0
            hp_percentages.append(hp_pct)
            
            stats['total_hp'] += state.current_hp
            
            # Track lowest and highest HP
            if stats['lowest_hp'] is None or hp_pct < stats['lowest_hp_pct']:
                stats['lowest_hp'] = member
                stats['lowest_hp_pct'] = hp_pct
            
            if stats['highest_hp'] is None or hp_pct > hp_percentages[0]:
                stats['highest_hp'] = member
            
            # Calculate threat score for enemies
            if member in self.enemies:
                threat_score = self._calculate_threat_score(member)
                if stats['highest_threat'] is None or threat_score > getattr(stats['highest_threat'], '_threat_score', 0):
                    member._threat_score = threat_score
                    stats['highest_threat'] = member
        
        if hp_percentages:
            stats['average_hp_pct'] = sum(hp_percentages) / len(hp_percentages)
        
        return stats
    
    def _calculate_threat_score(self, character):
        """Calculate threat score for a character."""
        state = character.components.get('state')
        if not state:
            return 0
        
        # Base threat from stats
        threat = (getattr(state, 'atk', 0) + getattr(state, 'mag', 0)) * 0.5
        
        # HP percentage modifier
        hp_pct = state.current_hp / state.max_hp if state.max_hp > 0 else 0
        threat *= (0.5 + hp_pct * 0.5)  # Wounded enemies are less threatening
        
        # Effect modifiers
        effects_component = character.components.get('effects')
        if effects_component:
            active_effects = effects_component.get_active_effects()
            for effect in active_effects:
                effect_name = getattr(effect, 'name', '').lower()
                if 'atk_up' in effect_name or 'mag_up' in effect_name:
                    threat *= 1.3
                elif 'atk_down' in effect_name or 'mag_down' in effect_name:
                    threat *= 0.7
        
        return threat

class AdvancedTargetingEngine:
    """Engine for processing complex targeting patterns and AoE skills."""
    
    def __init__(self):
        """Initialize the advanced targeting engine."""
        self.pattern_handlers = {
            TargetPattern.SINGLE: self._handle_single_target,
            TargetPattern.ALL_ENEMIES: self._handle_all_enemies,
            TargetPattern.ALL_ALLIES: self._handle_all_allies,
            TargetPattern.RANDOM_ENEMIES: self._handle_random_enemies,
            TargetPattern.RANDOM_ALLIES: self._handle_random_allies,
            TargetPattern.FRONT_ROW: self._handle_front_row,
            TargetPattern.BACK_ROW: self._handle_back_row,
            TargetPattern.AOE_SPLASH: self._handle_aoe_splash,
            TargetPattern.CHAIN_TARGET: self._handle_chain_target,
            TargetPattern.FORMATION_LINE: self._handle_formation_line,
            TargetPattern.PRIORITY_TARGET: self._handle_priority_target,
            TargetPattern.CONDITIONAL_TARGET: self._handle_conditional_target,
            TargetPattern.SELF: self._handle_self_target,
            TargetPattern.SMART_MULTI: self._handle_smart_multi
        }
        
        # Special target type mappings
        self.special_target_types = {
            'ally_lowest_hp': (TargetPattern.PRIORITY_TARGET, {'priority': 'lowest_hp', 'team': 'allies'}),
            'ally_highest_hp': (TargetPattern.PRIORITY_TARGET, {'priority': 'highest_hp', 'team': 'allies'}),
            'enemy_lowest_hp': (TargetPattern.PRIORITY_TARGET, {'priority': 'lowest_hp', 'team': 'enemies'}),
            'enemy_highest_hp': (TargetPattern.PRIORITY_TARGET, {'priority': 'highest_hp', 'team': 'enemies'}),
            'enemy_highest_threat': (TargetPattern.PRIORITY_TARGET, {'priority': 'highest_threat', 'team': 'enemies'}),
            'ally_most_debuffed': (TargetPattern.CONDITIONAL_TARGET, {'condition': 'most_debuffed', 'team': 'allies'}),
            'enemy_most_buffed': (TargetPattern.CONDITIONAL_TARGET, {'condition': 'most_buffed', 'team': 'enemies'}),
            'all_enemies': (TargetPattern.ALL_ENEMIES, {}),
            'all_allies': (TargetPattern.ALL_ALLIES, {}),
            'front_enemies': (TargetPattern.FRONT_ROW, {'team': 'enemies'}),
            'back_enemies': (TargetPattern.BACK_ROW, {'team': 'enemies'}),
            'front_allies': (TargetPattern.FRONT_ROW, {'team': 'allies'}),
            'back_allies': (TargetPattern.BACK_ROW, {'team': 'allies'}),
            'aoe_splash': (TargetPattern.AOE_SPLASH, {}),
            'chain_target': (TargetPattern.CHAIN_TARGET, {}),
            'formation_line': (TargetPattern.FORMATION_LINE, {}),
            'smart_multi': (TargetPattern.SMART_MULTI, {}),
            'self': (TargetPattern.SELF, {})
        }
    
    def resolve_targets(self, skill_data: Dict, context: TargetingContext, 
                       primary_target=None) -> List:
        """Resolve complex targeting patterns for a skill.
        
        Args:
            skill_data: Dictionary containing skill information
            context: TargetingContext with battlefield information
            primary_target: Optional primary target for some patterns
            
        Returns:
            List of target characters
        """
        target_type = skill_data.get('target_type', 'single')
        target_count = skill_data.get('target_count', 1)
        
        # Handle special target types
        if target_type in self.special_target_types:
            pattern, params = self.special_target_types[target_type]
            return self._resolve_pattern(pattern, context, skill_data, params, primary_target)
        
        # Handle basic patterns
        try:
            pattern = TargetPattern(target_type)
            return self._resolve_pattern(pattern, context, skill_data, {}, primary_target)
        except ValueError:
            # Default to single target if pattern not recognized
            return self._handle_single_target(context, skill_data, {}, primary_target)
    
    def _resolve_pattern(self, pattern: TargetPattern, context: TargetingContext,
                        skill_data: Dict, params: Dict, primary_target=None) -> List:
        """Resolve a specific targeting pattern.
        
        Args:
            pattern: TargetPattern to resolve
            context: TargetingContext with battlefield information
            skill_data: Skill data dictionary
            params: Additional parameters for the pattern
            primary_target: Optional primary target
            
        Returns:
            List of target characters
        """
        handler = self.pattern_handlers.get(pattern, self._handle_single_target)
        targets = handler(context, skill_data, params, primary_target)
        
        # Apply target count limits
        target_count = skill_data.get('target_count', len(targets) if targets else 1)
        if len(targets) > target_count:
            targets = targets[:target_count]
        
        return targets
    
    def _handle_single_target(self, context: TargetingContext, skill_data: Dict,
                             params: Dict, primary_target=None) -> List:
        """Handle single target selection."""
        if primary_target:
            return [primary_target]
        
        skill_type = skill_data.get('type', 'damage')
        if skill_type in ['damage', 'debuff']:
            candidates = [e for e in context.enemies if self._is_valid_target(e)]
        elif skill_type in ['heal', 'buff']:
            candidates = [a for a in context.allies if self._is_valid_target(a)]
        else:
            candidates = [t for t in context.allies + context.enemies if self._is_valid_target(t)]
        
        return [candidates[0]] if candidates else []
    
    def _handle_all_enemies(self, context: TargetingContext, skill_data: Dict,
                           params: Dict, primary_target=None) -> List:
        """Handle all enemies targeting."""
        return [e for e in context.enemies if self._is_valid_target(e)]
    
    def _handle_all_allies(self, context: TargetingContext, skill_data: Dict,
                          params: Dict, primary_target=None) -> List:
        """Handle all allies targeting."""
        return [a for a in context.allies if self._is_valid_target(a)]
    
    def _handle_random_enemies(self, context: TargetingContext, skill_data: Dict,
                              params: Dict, primary_target=None) -> List:
        """Handle random enemy targeting."""
        candidates = [e for e in context.enemies if self._is_valid_target(e)]
        target_count = skill_data.get('target_count', min(2, len(candidates)))
        
        if len(candidates) <= target_count:
            return candidates
        
        return random.sample(candidates, target_count)
    
    def _handle_random_allies(self, context: TargetingContext, skill_data: Dict,
                             params: Dict, primary_target=None) -> List:
        """Handle random ally targeting."""
        candidates = [a for a in context.allies if self._is_valid_target(a)]
        target_count = skill_data.get('target_count', min(2, len(candidates)))
        
        if len(candidates) <= target_count:
            return candidates
        
        return random.sample(candidates, target_count)
    
    def _handle_front_row(self, context: TargetingContext, skill_data: Dict,
                         params: Dict, primary_target=None) -> List:
        """Handle front row targeting."""
        team = params.get('team', 'enemies')
        if team == 'enemies':
            return context.formation_data['enemy_front_row']
        else:
            return context.formation_data['ally_front_row']
    
    def _handle_back_row(self, context: TargetingContext, skill_data: Dict,
                        params: Dict, primary_target=None) -> List:
        """Handle back row targeting."""
        team = params.get('team', 'enemies')
        if team == 'enemies':
            return context.formation_data['enemy_back_row']
        else:
            return context.formation_data['ally_back_row']
    
    def _handle_aoe_splash(self, context: TargetingContext, skill_data: Dict,
                          params: Dict, primary_target=None) -> List:
        """Handle area-of-effect splash damage around primary target."""
        if not primary_target:
            # If no primary target specified, select one first
            primary_target = self._handle_single_target(context, skill_data, params)
            if not primary_target:
                return []
            primary_target = primary_target[0]  # Get the actual target from list
        
        splash_radius = skill_data.get('splash_radius', 1)
        targets = [primary_target]
        
        # For simplified testing, use position-based splash
        primary_pos = getattr(primary_target, 'position', 0)
        
        # Find characters in team opposite to primary target
        if primary_target in context.enemies:
            candidates = context.enemies
        else:
            candidates = context.allies
        
        for character in candidates:
            if character == primary_target or not self._is_valid_target(character):
                continue
            
            # Calculate distance based on position
            char_pos = getattr(character, 'position', 0)
            distance = abs(char_pos - primary_pos)
            if distance <= splash_radius:
                targets.append(character)
        
        return targets
    
    def _handle_chain_target(self, context: TargetingContext, skill_data: Dict,
                            params: Dict, primary_target=None) -> List:
        """Handle chain targeting (like chain lightning)."""
        if not primary_target:
            # Select a primary target first
            primary_targets = self._handle_single_target(context, skill_data, params)
            if not primary_targets:
                return []
            primary_target = primary_targets[0]
        
        max_chains = skill_data.get('chain_count', 3)
        chain_range = skill_data.get('chain_range', 2)
        
        targets = [primary_target]
        current_target = primary_target
        
        # Determine candidate pool
        if primary_target in context.enemies:
            candidates = [e for e in context.enemies if e != primary_target and self._is_valid_target(e)]
        else:
            candidates = [a for a in context.allies if a != primary_target and self._is_valid_target(a)]
        
        for _ in range(max_chains - 1):
            if not candidates:
                break
            
            # Simplified position-based chaining for testing
            current_pos = getattr(current_target, 'position', 0)
            
            # Find closest valid target by position
            closest = None
            closest_distance = float('inf')
            
            for candidate in candidates:
                if candidate in targets:
                    continue
                
                candidate_pos = getattr(candidate, 'position', 0)
                distance = abs(candidate_pos - current_pos)
                
                if distance <= chain_range and distance < closest_distance:
                    closest = candidate
                    closest_distance = distance
            
            if closest:
                targets.append(closest)
                current_target = closest
                candidates.remove(closest)
            else:
                break
        
        return targets
        
        return targets
    
    def _handle_formation_line(self, context: TargetingContext, skill_data: Dict,
                              params: Dict, primary_target=None) -> List:
        """Handle entire formation line targeting."""
        line_type = skill_data.get('line_type', 'row')
        
        # For testing purposes, simplified formation line targeting
        # Just target all enemies if no specific formation data
        if line_type == 'row':
            return [e for e in context.enemies if self._is_valid_target(e)]
        elif line_type == 'column':
            # Return enemies in same column (position mod 3)
            if primary_target:
                target_column = getattr(primary_target, 'position', 0) % 3
                return [e for e in context.enemies if self._is_valid_target(e) and 
                       getattr(e, 'position', 0) % 3 == target_column]
        
        return [e for e in context.enemies if self._is_valid_target(e)]
    
    def _handle_priority_target(self, context: TargetingContext, skill_data: Dict,
                               params: Dict, primary_target=None) -> List:
        """Handle priority-based targeting (lowest HP, highest threat, etc.)."""
        priority = params.get('priority', 'lowest_hp')
        team = params.get('team', 'enemies')
        
        candidates = context.enemies if team == 'enemies' else context.allies
        candidates = [c for c in candidates if self._is_valid_target(c)]
        
        if not candidates:
            return []
        
        if priority == 'lowest_hp':
            target = min(candidates, key=lambda c: self._get_hp_percentage(c))
        elif priority == 'highest_hp':
            target = max(candidates, key=lambda c: self._get_hp_percentage(c))
        elif priority == 'highest_threat':
            target = max(candidates, key=lambda c: getattr(c, '_threat_score', 0))
        elif priority == 'lowest_defense':
            target = min(candidates, key=lambda c: self._get_stat(c, 'def'))
        elif priority == 'highest_magic':
            target = max(candidates, key=lambda c: self._get_stat(c, 'mag'))
        else:
            target = candidates[0]
        
        return [target]
    
    def _handle_conditional_target(self, context: TargetingContext, skill_data: Dict,
                                  params: Dict, primary_target=None) -> List:
        """Handle conditional targeting based on status effects."""
        condition = params.get('condition', 'most_debuffed')
        team = params.get('team', 'enemies')
        
        candidates = context.enemies if team == 'enemies' else context.allies
        candidates = [c for c in candidates if self._is_valid_target(c)]
        
        if not candidates:
            return []
        
        if condition == 'most_debuffed':
            target = max(candidates, key=lambda c: self._count_debuffs(c))
        elif condition == 'most_buffed':
            target = max(candidates, key=lambda c: self._count_buffs(c))
        elif condition == 'has_status':
            status_type = params.get('status_type', 'poison')
            matching = [c for c in candidates if self._has_effect(c, status_type)]
            target = matching[0] if matching else candidates[0]
        elif condition == 'no_status':
            status_type = params.get('status_type', 'any')
            clean_targets = [c for c in candidates if not self._has_any_effects(c)]
            target = clean_targets[0] if clean_targets else candidates[0]
        else:
            target = candidates[0]
        
        return [target]
    
    def _handle_self_target(self, context: TargetingContext, skill_data: Dict,
                           params: Dict, primary_target=None) -> List:
        """Handle self-targeting."""
        return [context.caster]
    
    def _handle_smart_multi(self, context: TargetingContext, skill_data: Dict,
                           params: Dict, primary_target=None) -> List:
        """Handle intelligent multi-target selection based on AI analysis."""
        skill_type = skill_data.get('type', 'damage')
        target_count = skill_data.get('target_count', 2)
        
        if skill_type in ['damage', 'debuff']:
            candidates = [e for e in context.enemies if self._is_valid_target(e)]
            
            # Prioritize by threat level and HP percentage
            scored_targets = []
            for candidate in candidates:
                threat_score = getattr(candidate, '_threat_score', 0)
                hp_pct = self._get_hp_percentage(candidate)
                
                # Higher score for high threat, low HP enemies
                score = threat_score * (2.0 - hp_pct)
                scored_targets.append((candidate, score))
            
            # Sort by score and take top targets
            scored_targets.sort(key=lambda x: x[1], reverse=True)
            return [target for target, score in scored_targets[:target_count]]
        
        elif skill_type in ['heal', 'buff']:
            candidates = [a for a in context.allies if self._is_valid_target(a)]
            
            # Prioritize by need (low HP for healing, high stats for buffing)
            scored_targets = []
            for candidate in candidates:
                hp_pct = self._get_hp_percentage(candidate)
                
                if skill_type == 'heal':
                    # Higher score for lower HP
                    score = 2.0 - hp_pct
                else:  # buff
                    # Higher score for higher potential (ATK/MAG)
                    atk = self._get_stat(candidate, 'atk')
                    mag = self._get_stat(candidate, 'mag')
                    score = (atk + mag) * hp_pct  # Only buff healthy allies
                
                scored_targets.append((candidate, score))
            
            scored_targets.sort(key=lambda x: x[1], reverse=True)
            return [target for target, score in scored_targets[:target_count]]
        
        # Default case - just return some candidates
        candidates = [e for e in context.enemies if self._is_valid_target(e)]
        return candidates[:target_count] if candidates else []
    
    def _is_valid_target(self, character):
        """Check if a character is a valid target."""
        if not character:
            return False
        
        state = character.components.get('state')
        return state and getattr(state, 'is_alive', True)
    
    def _get_hp_percentage(self, character):
        """Get character's HP percentage."""
        state = character.components.get('state')
        if not state or state.max_hp <= 0:
            return 0.0
        return state.current_hp / state.max_hp
    
    def _get_stat(self, character, stat_name):
        """Get character's stat value."""
        state = character.components.get('state')
        return getattr(state, stat_name, 0) if state else 0
    
    def _count_debuffs(self, character):
        """Count active debuffs on character."""
        # Try both the standard component system and simplified mock system
        if hasattr(character, 'debuff_count'):
            return character.debuff_count
            
        effects_component = character.components.get('effects')
        if not effects_component:
            return 0
        
        active_effects = effects_component.get_active_effects()
        return len([e for e in active_effects if e.get('type') == 'debuff' or 
                   getattr(e, 'effect_type', '') == 'debuff'])
    
    def _count_buffs(self, character):
        """Count active buffs on character."""
        # Try both the standard component system and simplified mock system
        if hasattr(character, 'buff_count'):
            return character.buff_count
            
        effects_component = character.components.get('effects')
        if not effects_component:
            return 0
        
        active_effects = effects_component.get_active_effects()
        return len([e for e in active_effects if e.get('type') == 'buff' or 
                   getattr(e, 'effect_type', '') == 'buff'])
    
    def _has_effect(self, character, effect_name):
        """Check if character has a specific effect."""
        effects_component = character.components.get('effects')
        if not effects_component:
            return False
        
        active_effects = effects_component.get_active_effects()
        return any(getattr(e, 'name', '').lower() == effect_name.lower() for e in active_effects)
    
    def _has_any_effects(self, character):
        """Check if character has any active effects."""
        effects_component = character.components.get('effects')
        if not effects_component:
            return False
        
        active_effects = effects_component.get_active_effects()
        return len(active_effects) > 0
    
    def calculate_aoe_efficiency(self, skill_data: Dict, context: TargetingContext) -> float:
        """Calculate efficiency score for AoE skills based on target count and quality.
        
        Args:
            skill_data: Skill data dictionary
            context: TargetingContext
            
        Returns:
            float: Efficiency score (higher = better)
        """
        targets = self.resolve_targets(skill_data, context)
        if not targets:
            return 0.0
        
        efficiency = len(targets)  # Base efficiency from target count
        
        skill_type = skill_data.get('type', 'damage')
        
        if skill_type in ['damage', 'debuff']:
            # Factor in target quality for offensive skills
            for target in targets:
                threat_score = getattr(target, '_threat_score', 0)
                hp_pct = self._get_hp_percentage(target)
                
                # Higher efficiency for high threat or low HP targets
                target_quality = (threat_score / 100) + (2.0 - hp_pct)
                efficiency += target_quality
        
        elif skill_type in ['heal', 'buff']:
            # Factor in need for supportive skills
            for target in targets:
                hp_pct = self._get_hp_percentage(target)
                
                if skill_type == 'heal':
                    # Higher efficiency for wounded allies
                    efficiency += (1.0 - hp_pct) * 2
                else:  # buff
                    # Higher efficiency for healthy, strong allies
                    stats_total = self._get_stat(target, 'atk') + self._get_stat(target, 'mag')
                    efficiency += (stats_total / 100) * hp_pct
        
        return efficiency