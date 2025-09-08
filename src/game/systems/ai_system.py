"""
AI System - Automated decision making for characters in battle.

This system provides:
- Intelligent action selection for AI-controlled characters
- Target prioritization and evaluation
- Multiple AI behavior patterns and personalities
- Threat assessment and strategic positioning
- Decision making with incomplete information
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import random
import logging

from ..core.battle_context import BattleContext
from ..components.character import Character
from ..systems.combat_system import CombatAction, ActionType

logger = logging.getLogger(__name__)

class AIPersonality(Enum):
    """Different AI behavior patterns"""
    AGGRESSIVE = "aggressive"      # Focus on dealing damage
    DEFENSIVE = "defensive"        # Prioritize survival and support
    BALANCED = "balanced"          # Mix of offense and defense
    TACTICAL = "tactical"          # Strategic, analytical decisions
    RECKLESS = "reckless"         # High-risk, high-reward plays
    SUPPORT = "support"           # Focus on healing and buffs

class AIAction(Enum):
    """Types of actions AI can take"""
    ATTACK = "attack"
    SKILL = "skill"
    DEFEND = "defend"
    WAIT = "wait"
    MOVE = "move"

@dataclass
class AIDecision:
    """Represents an AI decision with reasoning"""
    action_type: AIAction
    target_ids: List[str]
    skill_id: Optional[str] = None
    priority: float = 0.0
    confidence: float = 0.0
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ThreatAssessment:
    """Assessment of battlefield threats and opportunities"""
    immediate_threats: List[str] = field(default_factory=list)  # Character IDs
    priority_targets: List[str] = field(default_factory=list)   # Character IDs  
    ally_priorities: List[str] = field(default_factory=list)    # Characters needing help
    tactical_situation: str = "neutral"  # "advantage", "disadvantage", "neutral"
    recommended_strategy: str = "balanced"  # "aggressive", "defensive", "support"

class AIBehavior:
    """Base class for AI behavior patterns"""
    
    def __init__(self, personality: AIPersonality, battle_context: BattleContext):
        self.personality = personality
        self.battle_context = battle_context
        self.memory: Dict[str, Any] = {}  # AI memory for learning
        
        # Personality modifiers
        self.aggression = 0.5
        self.defensiveness = 0.5
        self.risk_tolerance = 0.5
        self.support_tendency = 0.5
        self.tactical_awareness = 0.5
        
        self._setup_personality()
    
    def _setup_personality(self):
        """Configure behavior based on personality"""
        if self.personality == AIPersonality.AGGRESSIVE:
            self.aggression = 0.9
            self.defensiveness = 0.2
            self.risk_tolerance = 0.8
            self.support_tendency = 0.1
            self.tactical_awareness = 0.6
            
        elif self.personality == AIPersonality.DEFENSIVE:
            self.aggression = 0.2
            self.defensiveness = 0.9
            self.risk_tolerance = 0.3
            self.support_tendency = 0.7
            self.tactical_awareness = 0.7
            
        elif self.personality == AIPersonality.BALANCED:
            self.aggression = 0.5
            self.defensiveness = 0.5
            self.risk_tolerance = 0.5
            self.support_tendency = 0.5
            self.tactical_awareness = 0.6
            
        elif self.personality == AIPersonality.TACTICAL:
            self.aggression = 0.4
            self.defensiveness = 0.6
            self.risk_tolerance = 0.4
            self.support_tendency = 0.6
            self.tactical_awareness = 0.9
            
        elif self.personality == AIPersonality.RECKLESS:
            self.aggression = 0.8
            self.defensiveness = 0.1
            self.risk_tolerance = 0.9
            self.support_tendency = 0.2
            self.tactical_awareness = 0.3
            
        elif self.personality == AIPersonality.SUPPORT:
            self.aggression = 0.2
            self.defensiveness = 0.8
            self.risk_tolerance = 0.3
            self.support_tendency = 0.9
            self.tactical_awareness = 0.7
    
    def make_decision(self, character: Character, threat_assessment: ThreatAssessment) -> AIDecision:
        """Make a decision for the character (to be overridden by subclasses)"""
        # Default to basic attack
        enemies = self.battle_context.get_enemy_characters(character.character_id)
        if enemies:
            target = random.choice(enemies)
            return AIDecision(
                action_type=AIAction.ATTACK,
                target_ids=[target.character_id],
                priority=0.5,
                confidence=0.5,
                reasoning="Default attack decision"
            )
        
        return AIDecision(
            action_type=AIAction.WAIT,
            target_ids=[],
            priority=0.1,
            confidence=1.0,
            reasoning="No available targets"
        )

class StandardAIBehavior(AIBehavior):
    """Standard AI behavior with personality-based decision making"""
    
    def make_decision(self, character: Character, threat_assessment: ThreatAssessment) -> AIDecision:
        """Make an intelligent decision based on personality and situation"""
        
        # Get available actions
        possible_decisions = []
        
        # Consider attack actions
        attack_decisions = self._evaluate_attack_options(character, threat_assessment)
        possible_decisions.extend(attack_decisions)
        
        # Consider skill actions
        skill_decisions = self._evaluate_skill_options(character, threat_assessment)
        possible_decisions.extend(skill_decisions)
        
        # Consider defensive actions
        defensive_decisions = self._evaluate_defensive_options(character, threat_assessment)
        possible_decisions.extend(defensive_decisions)
        
        # Select best decision based on personality
        if possible_decisions:
            return self._select_best_decision(possible_decisions, character, threat_assessment)
        
        # Fallback to wait
        return AIDecision(
            action_type=AIAction.WAIT,
            target_ids=[],
            priority=0.1,
            confidence=1.0,
            reasoning="No viable actions available"
        )
    
    def _evaluate_attack_options(self, character: Character, threat_assessment: ThreatAssessment) -> List[AIDecision]:
        """Evaluate basic attack options"""
        decisions = []
        enemies = self.battle_context.get_enemy_characters(character.character_id)
        
        for enemy in enemies:
            if enemy.is_defeated():
                continue
            
            # Calculate priority based on threat level and personality
            priority = 0.3  # Base priority
            
            # Prioritize threats
            if enemy.character_id in threat_assessment.immediate_threats:
                priority += 0.3
            if enemy.character_id in threat_assessment.priority_targets:
                priority += 0.2
            
            # Factor in enemy HP (lower HP = higher priority for aggressive types)
            hp_percentage = enemy.current_hp / enemy.get_stat("hp")
            if self.aggression > 0.5 and hp_percentage < 0.3:
                priority += 0.2  # Finish off weak enemies
            
            # Apply personality modifiers
            priority *= (0.5 + self.aggression * 0.5)
            
            decision = AIDecision(
                action_type=AIAction.ATTACK,
                target_ids=[enemy.character_id],
                priority=priority,
                confidence=0.7,
                reasoning=f"Attack {enemy.name} (HP: {hp_percentage:.1%})"
            )
            decisions.append(decision)
        
        return decisions
    
    def _evaluate_skill_options(self, character: Character, threat_assessment: ThreatAssessment) -> List[AIDecision]:
        """Evaluate skill usage options"""
        decisions = []
        
        # Get available skills from abilities component
        try:
            available_skills = character.abilities.skills
            
            for skill in available_skills:
                # Basic availability check (can be enhanced later with proper skill system)
                try:
                    if hasattr(skill, 'cooldown_remaining') and skill.cooldown_remaining > 0:
                        continue
                except (AttributeError, TypeError):
                    # Skip if skill doesn't have proper structure
                    continue
                
                # Evaluate skill based on basic properties
                skill_decisions = self._evaluate_single_skill(skill, character, threat_assessment)
                decisions.extend(skill_decisions)
                
        except (AttributeError, TypeError):
            # Skills system not fully implemented yet, skip skill evaluation
            pass
        
        return decisions
    
    def _evaluate_single_skill(self, skill: Any, character: Character, 
                              threat_assessment: ThreatAssessment) -> List[AIDecision]:
        """Evaluate a specific skill for use"""
        decisions = []
        
        # Basic skill evaluation - can be enhanced when skill system is more mature
        skill_id = getattr(skill, 'skill_id', 'unknown_skill')
        skill_name = getattr(skill, 'name', skill_id)
        
        # Determine targets based on skill properties
        target_type = getattr(skill, 'target_type', 'enemy')
        
        if target_type in ['enemy', 'single_enemy']:
            potential_targets = self.battle_context.get_enemy_characters(character.character_id)
        elif target_type in ['ally', 'single_ally']:
            potential_targets = self.battle_context.get_ally_characters(character.character_id)
            potential_targets.append(character)  # Can target self
        elif target_type in ['all_enemies', 'area_enemy']:
            potential_targets = self.battle_context.get_enemy_characters(character.character_id)
            if potential_targets:
                # For AOE skills, use all enemies as targets
                priority = self._calculate_skill_priority(skill, potential_targets, character, threat_assessment)
                decision = AIDecision(
                    action_type=AIAction.SKILL,
                    target_ids=[t.character_id for t in potential_targets],
                    skill_id=skill_id,
                    priority=priority,
                    confidence=0.8,
                    reasoning=f"Use {skill_name} on all enemies"
                )
                decisions.append(decision)
            return decisions
        else:
            potential_targets = []
        
        # Evaluate each potential target
        for target in potential_targets:
            if target.is_defeated():
                continue
            
            priority = self._calculate_skill_priority(skill, [target], character, threat_assessment)
            
            decision = AIDecision(
                action_type=AIAction.SKILL,
                target_ids=[target.character_id],
                skill_id=skill_id,
                priority=priority,
                confidence=0.6,
                reasoning=f"Use {skill_name} on {target.name}"
            )
            decisions.append(decision)
        
        return decisions
    
    def _calculate_skill_priority(self, skill: Any, targets: List[Character], 
                                 character: Character, threat_assessment: ThreatAssessment) -> float:
        """Calculate priority for using a skill on specific targets"""
        base_priority = 0.4
        
        # Get skill properties safely
        damage_multiplier = getattr(skill, 'damage_multiplier', 1.0)
        healing_power = getattr(skill, 'healing_power', 0.0)
        
        # Healing skills priority
        if healing_power > 0:
            for target in targets:
                hp_percentage = target.current_hp / target.get_stat("hp")
                if hp_percentage < 0.5:  # Target needs healing
                    base_priority += 0.3 * self.support_tendency
                    if hp_percentage < 0.2:  # Critical condition
                        base_priority += 0.4 * self.support_tendency
        
        # Damage skills priority
        if damage_multiplier > 1.0:
            for target in targets:
                if target.character_id in threat_assessment.immediate_threats:
                    base_priority += 0.3 * self.aggression
                if target.character_id in threat_assessment.priority_targets:
                    base_priority += 0.2 * self.aggression
                
                # High-damage skills more valuable for aggressive personalities
                base_priority += (damage_multiplier - 1.0) * 0.2 * self.aggression
        
        # Tactical considerations
        if len(targets) > 1:  # Multi-target skills
            base_priority += 0.2 * self.tactical_awareness
        
        return min(base_priority, 1.0)  # Cap at 1.0
    
    def _evaluate_defensive_options(self, character: Character, threat_assessment: ThreatAssessment) -> List[AIDecision]:
        """Evaluate defensive actions like defend or wait"""
        decisions = []
        
        # Consider defending if under threat
        if character.character_id in threat_assessment.immediate_threats:
            priority = 0.3 * self.defensiveness
            
            # Higher priority if low on health
            hp_percentage = character.current_hp / character.get_stat("hp")
            if hp_percentage < 0.3:
                priority += 0.4 * self.defensiveness
            
            decision = AIDecision(
                action_type=AIAction.DEFEND,
                target_ids=[character.character_id],
                priority=priority,
                confidence=0.8,
                reasoning=f"Defend due to threat (HP: {hp_percentage:.1%})"
            )
            decisions.append(decision)
        
        # Consider waiting (low priority fallback)
        wait_decision = AIDecision(
            action_type=AIAction.WAIT,
            target_ids=[],
            priority=0.1,
            confidence=1.0,
            reasoning="Wait and observe"
        )
        decisions.append(wait_decision)
        
        return decisions
    
    def _select_best_decision(self, decisions: List[AIDecision], character: Character, 
                             threat_assessment: ThreatAssessment) -> AIDecision:
        """Select the best decision from available options"""
        if not decisions:
            return AIDecision(action_type=AIAction.WAIT, target_ids=[], priority=0.1, confidence=1.0)
        
        # Sort by priority, add some randomness for personality
        randomness_factor = 1.0 - self.tactical_awareness * 0.5
        
        scored_decisions = []
        for decision in decisions:
            # Add personality-based scoring adjustments
            score = decision.priority
            
            # Add controlled randomness
            if randomness_factor > 0:
                random_modifier = (random.random() - 0.5) * randomness_factor * 0.3
                score += random_modifier
            
            scored_decisions.append((score, decision))
        
        # Sort by score and return the best
        scored_decisions.sort(key=lambda x: x[0], reverse=True)
        
        best_decision = scored_decisions[0][1]
        logger.debug("AI decision for %s: %s (priority: %.2f)", 
                    character.name, best_decision.reasoning, best_decision.priority)
        
        return best_decision

class AISystem:
    """Main AI system for automated character decision making"""
    
    def __init__(self, battle_context: BattleContext):
        self.battle_context = battle_context
        self.ai_characters: Dict[str, AIPersonality] = {}
        self.ai_behaviors: Dict[str, AIBehavior] = {}
        self.decision_history: List[Dict[str, Any]] = []
        
        logger.info("Initialized AI system for battle %s", battle_context.battle_id)
    
    def register_ai_character(self, character_id: str, personality: AIPersonality = AIPersonality.BALANCED):
        """Register a character to be controlled by AI"""
        self.ai_characters[character_id] = personality
        self.ai_behaviors[character_id] = StandardAIBehavior(personality, self.battle_context)
        
        logger.debug("Registered AI character %s with personality %s", 
                    character_id, personality.value)
    
    def unregister_ai_character(self, character_id: str):
        """Remove a character from AI control"""
        if character_id in self.ai_characters:
            del self.ai_characters[character_id]
            del self.ai_behaviors[character_id]
            logger.debug("Unregistered AI character %s", character_id)
    
    def is_ai_controlled(self, character_id: str) -> bool:
        """Check if a character is AI controlled"""
        return character_id in self.ai_characters
    
    def make_decision(self, character_id: str) -> Optional[CombatAction]:
        """Make a decision for an AI character"""
        if not self.is_ai_controlled(character_id):
            return None
        
        character = self.battle_context.get_character(character_id)
        if not character or character.is_defeated():
            return None
        
        # Assess battlefield situation
        threat_assessment = self._assess_threats(character)
        
        # Get AI behavior and make decision
        ai_behavior = self.ai_behaviors[character_id]
        decision = ai_behavior.make_decision(character, threat_assessment)
        
        # Convert AI decision to combat action
        combat_action = self._convert_to_combat_action(decision, character)
        
        # Record decision for analysis
        self._record_decision(character_id, decision, threat_assessment)
        
        return combat_action
    
    def _assess_threats(self, character: Character) -> ThreatAssessment:
        """Assess battlefield threats and opportunities"""
        assessment = ThreatAssessment()
        
        enemies = self.battle_context.get_enemy_characters(character.character_id)
        allies = self.battle_context.get_ally_characters(character.character_id)
        
        # Identify immediate threats (enemies who can attack this character)
        for enemy in enemies:
            if enemy.is_defeated():
                continue
            
            # Simple threat calculation based on attack power and proximity
            threat_level = enemy.get_stat("atk")
            if enemy.current_hp < enemy.get_stat("hp") * 0.3:
                threat_level *= 1.5  # Desperate enemies are more dangerous
            
            assessment.immediate_threats.append(enemy.character_id)
        
        # Identify priority targets (low HP enemies, high-value targets)
        for enemy in enemies:
            if enemy.is_defeated():
                continue
            
            hp_percentage = enemy.current_hp / enemy.get_stat("hp")
            attack_power = enemy.get_stat("atk")
            
            # High-value targets: high attack power or low HP
            if hp_percentage < 0.4 or attack_power > 80:
                assessment.priority_targets.append(enemy.character_id)
        
        # Identify allies needing help
        for ally in allies:
            if ally.is_defeated():
                continue
            
            hp_percentage = ally.current_hp / ally.get_stat("hp")
            if hp_percentage < 0.5:
                assessment.ally_priorities.append(ally.character_id)
        
        # Assess tactical situation
        alive_allies = len([a for a in allies if not a.is_defeated()]) + 1  # +1 for self
        alive_enemies = len([e for e in enemies if not e.is_defeated()])
        
        if alive_allies > alive_enemies:
            assessment.tactical_situation = "advantage"
            assessment.recommended_strategy = "aggressive"
        elif alive_allies < alive_enemies:
            assessment.tactical_situation = "disadvantage"
            assessment.recommended_strategy = "defensive"
        else:
            assessment.tactical_situation = "neutral"
            assessment.recommended_strategy = "balanced"
        
        return assessment
    
    def _convert_to_combat_action(self, decision: AIDecision, character: Character) -> Optional[CombatAction]:
        """Convert AI decision to combat action"""
        action_id = f"ai_action_{character.character_id}_{len(self.decision_history)}"
        
        if decision.action_type == AIAction.ATTACK:
            return CombatAction(
                action_id=action_id,
                actor_id=character.character_id,
                action_type=ActionType.ATTACK,
                target_ids=decision.target_ids,
                power=1.0,
                accuracy=0.85,
                critical_chance=0.1
            )
        
        elif decision.action_type == AIAction.SKILL:
            if decision.skill_id:
                return CombatAction(
                    action_id=action_id,
                    actor_id=character.character_id,
                    action_type=ActionType.SKILL,
                    target_ids=decision.target_ids,
                    skill_id=decision.skill_id,
                    power=1.0
                )
        
        elif decision.action_type == AIAction.DEFEND:
            return CombatAction(
                action_id=action_id,
                actor_id=character.character_id,
                action_type=ActionType.DEFEND,
                target_ids=[character.character_id],
                power=1.0
            )
        
        # For WAIT or unhandled actions, return None (skip turn)
        return None
    
    def _record_decision(self, character_id: str, decision: AIDecision, threat_assessment: ThreatAssessment):
        """Record decision for analysis and learning"""
        record = {
            "character_id": character_id,
            "decision": decision,
            "threat_assessment": threat_assessment,
            "timestamp": __import__('time').time(),
            "battle_turn": getattr(self.battle_context, 'turn_number', 0)
        }
        
        self.decision_history.append(record)
        
        # Keep only recent history to prevent memory bloat
        if len(self.decision_history) > 100:
            self.decision_history = self.decision_history[-100:]
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI system status"""
        return {
            "ai_characters": {char_id: personality.value 
                            for char_id, personality in self.ai_characters.items()},
            "active_ai_count": len(self.ai_characters),
            "decision_history_length": len(self.decision_history),
            "battle_id": self.battle_context.battle_id
        }
    
    def update_ai_personality(self, character_id: str, personality: AIPersonality):
        """Update AI personality for a character"""
        if character_id in self.ai_characters:
            self.ai_characters[character_id] = personality
            self.ai_behaviors[character_id] = StandardAIBehavior(personality, self.battle_context)
            logger.debug("Updated AI personality for %s to %s", character_id, personality.value)
