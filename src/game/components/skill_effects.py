"""
Skill effect handlers for the DataDrivenSkill system.
"""

from typing import Dict, Any, List, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ...models.character import Character

logger = logging.getLogger(__name__)

class SkillEffectHandler:
    """Handler for all skill effects in the data-driven system"""
    
    @staticmethod
    def execute_skill_effects(effects: List[Dict[str, Any]], caster: 'Character', targets: List['Character'], battle_context=None) -> Dict[str, Any]:
        """Execute all effects from a skill."""
        result = {
            "damage_dealt": 0.0,
            "healing_done": 0.0,
            "effects_applied": [],
            "status_effects": [],
            "special_effects": []
        }
        
        for effect_data in effects:
            effect_type = effect_data.get('type', 'damage')
            
            if effect_type == 'damage':
                damage_result = SkillEffectHandler._handle_damage_effect(effect_data, caster, targets)
                result["damage_dealt"] += damage_result["damage"]
                result["effects_applied"].extend(damage_result["effects"])
                
            elif effect_type == 'heal':
                heal_result = SkillEffectHandler._handle_heal_effect(effect_data, caster, targets)
                result["healing_done"] += heal_result["healing"]
                result["effects_applied"].extend(heal_result["effects"])
                
            elif effect_type == 'chain_damage':
                chain_result = SkillEffectHandler._handle_chain_damage_effect(effect_data, caster, targets, battle_context)
                result["damage_dealt"] += chain_result["damage"]
                result["effects_applied"].extend(chain_result["effects"])
                
            elif effect_type == 'splash_damage':
                splash_result = SkillEffectHandler._handle_splash_damage_effect(effect_data, caster, targets, battle_context)
                result["damage_dealt"] += splash_result["damage"]
                result["effects_applied"].extend(splash_result["effects"])
                
            elif effect_type == 'status_effect':
                status_result = SkillEffectHandler._handle_status_effect(effect_data, caster, targets)
                result["status_effects"].extend(status_result["effects"])
                result["effects_applied"].extend(status_result["descriptions"])
                
            elif effect_type == 'shield':
                shield_result = SkillEffectHandler._handle_shield_effect(effect_data, caster, targets)
                result["special_effects"].extend(shield_result["effects"])
                result["effects_applied"].extend(shield_result["descriptions"])
                
            elif effect_type == 'revive':
                revive_result = SkillEffectHandler._handle_revive_effect(effect_data, caster, targets)
                result["healing_done"] += revive_result["healing"]
                result["effects_applied"].extend(revive_result["effects"])
                
            elif effect_type == 'counter_attack':
                counter_result = SkillEffectHandler._handle_counter_attack_effect(effect_data, caster, targets)
                result["special_effects"].extend(counter_result["effects"])
                result["effects_applied"].extend(counter_result["descriptions"])
                
            elif effect_type == 'reflect_magic':
                reflect_result = SkillEffectHandler._handle_reflect_magic_effect(effect_data, caster, targets)
                result["special_effects"].extend(reflect_result["effects"])
                result["effects_applied"].extend(reflect_result["descriptions"])
                
            elif effect_type == 'damage_redirect':
                redirect_result = SkillEffectHandler._handle_damage_redirect_effect(effect_data, caster, targets)
                result["special_effects"].extend(redirect_result["effects"])
                result["effects_applied"].extend(redirect_result["descriptions"])
                
            elif effect_type == 'action_gauge_boost':
                boost_result = SkillEffectHandler._handle_action_gauge_boost_effect(effect_data, caster, targets)
                result["special_effects"].extend(boost_result["effects"])
                result["effects_applied"].extend(boost_result["descriptions"])
                
            elif effect_type == 'cleanse_debuffs':
                cleanse_result = SkillEffectHandler._handle_cleanse_debuffs_effect(effect_data, caster, targets)
                result["special_effects"].extend(cleanse_result["effects"])
                result["effects_applied"].extend(cleanse_result["descriptions"])
                
            elif effect_type == 'dispel_buff':
                dispel_result = SkillEffectHandler._handle_dispel_buff_effect(effect_data, caster, targets)
                result["special_effects"].extend(dispel_result["effects"])
                result["effects_applied"].extend(dispel_result["descriptions"])
                
            elif effect_type == 'recoil_damage':
                recoil_result = SkillEffectHandler._handle_recoil_damage_effect(effect_data, caster, targets)
                result["damage_dealt"] += recoil_result["damage"]
                result["effects_applied"].extend(recoil_result["effects"])
                
            else:
                logger.warning(f"Unknown effect type: {effect_type}")
                result["effects_applied"].append(f"Unknown effect: {effect_type}")
        
        return result
    
    @staticmethod
    def _handle_damage_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle basic damage effects with conditional modifiers."""
        from ..core.universal_scaling import UniversalScaling, ScalingParameters
        
        total_damage = 0.0
        effects = []
        
        damage_type = effect_data.get('damage_type', 'physical')
        armor_pen = effect_data.get('armor_penetration', 0)
        conditional_mult = effect_data.get('conditional_multiplier', {})
        
        for target in targets:
            # Calculate base damage using skill data
            base_damage = SkillEffectHandler._calculate_skill_damage(caster, target, effect_data)
            
            # Apply conditional multipliers
            multiplier = 1.0
            if conditional_mult:
                condition = conditional_mult.get('condition')
                if condition == 'target_hp_below_30' and SkillEffectHandler._get_hp_percentage(target) <= 30:
                    multiplier = conditional_mult.get('multiplier', 1.0)
                elif condition == 'caster_hp_below_50' and SkillEffectHandler._get_hp_percentage(caster) <= 50:
                    multiplier = conditional_mult.get('multiplier', 1.0)
                elif condition == 'target_has_debuff' and SkillEffectHandler._has_debuffs(target):
                    multiplier = conditional_mult.get('multiplier', 1.0)
            
            # Apply armor penetration
            if armor_pen > 0:
                multiplier *= (1 + armor_pen / 100)
            
            final_damage = base_damage * multiplier
            SkillEffectHandler._apply_damage(target, final_damage)
            
            total_damage += final_damage
            effects.append(f"Dealt {final_damage:.1f} {damage_type} damage to {target.name}")
        
        return {"damage": total_damage, "effects": effects}
    
    @staticmethod
    def _handle_heal_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle healing effects."""
        total_healing = 0.0
        effects = []
        
        base_heal = effect_data.get('heal', 0)
        heal_percentage = effect_data.get('heal_percentage', 0)
        
        for target in targets:
            # Calculate healing amount
            healing = base_heal
            if heal_percentage > 0:
                max_hp = SkillEffectHandler._get_max_hp(target)
                healing += max_hp * (heal_percentage / 100)
            
            # Apply healing
            actual_healing = SkillEffectHandler._apply_healing(target, healing)
            total_healing += actual_healing
            effects.append(f"Healed {actual_healing:.1f} HP to {target.name}")
        
        return {"healing": total_healing, "effects": effects}
    
    @staticmethod
    def _handle_chain_damage_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character'], battle_context=None) -> Dict[str, Any]:
        """Handle chain damage that spreads to additional targets."""
        total_damage = 0.0
        effects = []
        
        base_damage = SkillEffectHandler._calculate_skill_damage(caster, targets[0] if targets else None, effect_data)
        chain_multiplier = effect_data.get('damage_multiplier', 0.5)
        max_chains = effect_data.get('max_chains', 3)
        
        # Apply initial damage
        if targets:
            SkillEffectHandler._apply_damage(targets[0], base_damage)
            total_damage += base_damage
            effects.append(f"Initial chain damage: {base_damage:.1f} to {targets[0].name}")
            
            # Implement actual chain spreading
            if battle_context and hasattr(battle_context, 'get_all_characters'):
                # Get all valid chain targets (enemies of the original target)
                chained_targets = []
                hit_targets = {targets[0]}  # Track already hit targets
                current_target = targets[0]
                
                # Find enemies of the current target for chaining
                all_characters = battle_context.get_all_characters()
                enemy_team = 'team_2' if current_target.team_id == 'team_1' else 'team_1'
                potential_targets = [char for char in all_characters 
                                   if char.team_id == enemy_team and char.is_alive() and char not in hit_targets]
                
                chain_damage = base_damage * chain_multiplier
                chains_performed = 0
                
                while chains_performed < max_chains and potential_targets:
                    # Pick closest target (or random for simplicity)
                    next_target = potential_targets[0] if potential_targets else None
                    if next_target:
                        SkillEffectHandler._apply_damage(next_target, chain_damage)
                        total_damage += chain_damage
                        effects.append(f"Chain {chains_performed + 1}: {chain_damage:.1f} damage to {next_target.name}")
                        
                        # Update for next chain
                        hit_targets.add(next_target)
                        potential_targets = [char for char in potential_targets if char != next_target]
                        chain_damage *= chain_multiplier  # Diminishing returns
                        chains_performed += 1
            else:
                # Fallback: simulate chains when battle context not available
                chain_damage = base_damage * chain_multiplier
                simulated_chains = min(max_chains, 2)
                for i in range(simulated_chains):
                    total_damage += chain_damage
                    effects.append(f"Chain {i+1}: {chain_damage:.1f} damage (simulated)")
                    chain_damage *= chain_multiplier
        
        return {"damage": total_damage, "effects": effects}
    
    @staticmethod
    def _handle_splash_damage_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character'], battle_context=None) -> Dict[str, Any]:
        """Handle splash damage to multiple targets."""
        total_damage = 0.0
        effects = []
        
        base_damage = SkillEffectHandler._calculate_skill_damage(caster, targets[0] if targets else None, effect_data)
        splash_multiplier = effect_data.get('splash_multiplier', 0.5)
        
        # Apply main damage to primary target
        if targets:
            SkillEffectHandler._apply_damage(targets[0], base_damage)
            total_damage += base_damage
            effects.append(f"Primary splash damage: {base_damage:.1f} to {targets[0].name}")
            
            # Apply splash damage to remaining targets
            splash_damage = base_damage * splash_multiplier
            for target in targets[1:]:
                SkillEffectHandler._apply_damage(target, splash_damage)
                total_damage += splash_damage
                effects.append(f"Splash damage: {splash_damage:.1f} to {target.name}")
        
        return {"damage": total_damage, "effects": effects}
    
    @staticmethod
    def _handle_status_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle status effects like bleed, speed reduction, etc."""
        effects = []
        descriptions = []
        
        effect_name = effect_data.get('effect', 'unknown')
        duration = effect_data.get('duration', 1)
        magnitude = effect_data.get('magnitude', 0)
        
        for target in targets:
            status_effect = {
                "type": effect_name,
                "duration": duration,
                "magnitude": magnitude,
                "source": caster.name if hasattr(caster, 'name') else "Unknown"
            }
            effects.append(status_effect)
            descriptions.append(f"Applied {effect_name} to {target.name} (duration: {duration})")
        
        return {"effects": effects, "descriptions": descriptions}
    
    @staticmethod
    def _handle_shield_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle shield/barrier effects."""
        effects = []
        descriptions = []
        
        shield_amount = effect_data.get('shield', 0)
        duration = effect_data.get('duration', 3)
        shield_type = effect_data.get('shield_type', 'physical')
        
        for target in targets:
            shield_effect = {
                "type": "shield",
                "amount": shield_amount,
                "duration": duration,
                "shield_type": shield_type
            }
            effects.append(shield_effect)
            descriptions.append(f"Applied {shield_amount} {shield_type} shield to {target.name}")
        
        return {"effects": effects, "descriptions": descriptions}
    
    @staticmethod
    def _handle_revive_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle revival effects."""
        total_healing = 0.0
        effects = []
        
        hp_percentage = effect_data.get('hp_percentage', 50)
        
        for target in targets:
            current_hp = SkillEffectHandler._get_current_hp(target)
            if current_hp <= 0:
                max_hp = SkillEffectHandler._get_max_hp(target)
                revive_hp = max_hp * (hp_percentage / 100)
                SkillEffectHandler._set_current_hp(target, revive_hp)
                total_healing += revive_hp
                effects.append(f"Revived {target.name} with {revive_hp:.1f} HP")
        
        return {"healing": total_healing, "effects": effects}
    
    @staticmethod
    def _handle_counter_attack_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle counter attack effects."""
        effects = []
        descriptions = []
        
        counter_chance = effect_data.get('chance', 100)
        counter_multiplier = effect_data.get('multiplier', 1.0)
        duration = effect_data.get('duration', 1)
        
        for target in targets:
            counter_effect = {
                "type": "counter_attack",
                "chance": counter_chance,
                "multiplier": counter_multiplier,
                "duration": duration
            }
            effects.append(counter_effect)
            descriptions.append(f"Applied counter attack to {target.name} ({counter_chance}% chance)")
        
        return {"effects": effects, "descriptions": descriptions}
    
    @staticmethod
    def _handle_reflect_magic_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle magic reflection effects."""
        effects = []
        descriptions = []
        
        reflect_chance = effect_data.get('chance', 100)
        reflect_multiplier = effect_data.get('multiplier', 1.0)
        duration = effect_data.get('duration', 1)
        
        for target in targets:
            reflect_effect = {
                "type": "reflect_magic",
                "chance": reflect_chance,
                "multiplier": reflect_multiplier,
                "duration": duration
            }
            effects.append(reflect_effect)
            descriptions.append(f"Applied magic reflect to {target.name} ({reflect_chance}% chance)")
        
        return {"effects": effects, "descriptions": descriptions}
    
    @staticmethod
    def _handle_damage_redirect_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle damage redirection effects."""
        effects = []
        descriptions = []
        
        redirect_percentage = effect_data.get('percentage', 50)
        duration = effect_data.get('duration', 3)
        
        for target in targets:
            redirect_effect = {
                "type": "damage_redirect",
                "percentage": redirect_percentage,
                "duration": duration,
                "redirector": caster.name if hasattr(caster, 'name') else "Unknown"
            }
            effects.append(redirect_effect)
            descriptions.append(f"Applied damage redirect to {target.name} ({redirect_percentage}%)")
        
        return {"effects": effects, "descriptions": descriptions}
    
    @staticmethod
    def _handle_action_gauge_boost_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle action gauge manipulation effects."""
        effects = []
        descriptions = []
        
        boost_amount = effect_data.get('boost', 0)
        boost_type = effect_data.get('boost_type', 'flat')  # flat or percentage
        
        for target in targets:
            gauge_effect = {
                "type": "action_gauge_boost",
                "amount": boost_amount,
                "boost_type": boost_type
            }
            effects.append(gauge_effect)
            descriptions.append(f"Boosted action gauge of {target.name} by {boost_amount}")
        
        return {"effects": effects, "descriptions": descriptions}
    
    @staticmethod
    def _handle_cleanse_debuffs_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle debuff cleansing effects."""
        effects = []
        descriptions = []
        
        cleanse_type = effect_data.get('cleanse_type', 'all')
        cleanse_count = effect_data.get('count', -1)  # -1 means all
        
        for target in targets:
            cleanse_effect = {
                "type": "cleanse_debuffs",
                "cleanse_type": cleanse_type,
                "count": cleanse_count
            }
            effects.append(cleanse_effect)
            descriptions.append(f"Cleansed debuffs from {target.name}")
        
        return {"effects": effects, "descriptions": descriptions}
    
    @staticmethod
    def _handle_dispel_buff_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle buff dispelling effects."""
        effects = []
        descriptions = []
        
        dispel_type = effect_data.get('dispel_type', 'all')
        dispel_count = effect_data.get('count', -1)  # -1 means all
        
        for target in targets:
            dispel_effect = {
                "type": "dispel_buff",
                "dispel_type": dispel_type,
                "count": dispel_count
            }
            effects.append(dispel_effect)
            descriptions.append(f"Dispelled buffs from {target.name}")
        
        return {"effects": effects, "descriptions": descriptions}
    
    @staticmethod
    def _handle_recoil_damage_effect(effect_data: Dict[str, Any], caster: 'Character', targets: List['Character']) -> Dict[str, Any]:
        """Handle recoil damage to the caster."""
        recoil_percentage = effect_data.get('percentage', 10)
        base_damage = effect_data.get('base_damage', 0)
        
        # Calculate recoil damage
        if base_damage > 0:
            recoil_damage = base_damage * (recoil_percentage / 100)
        else:
            # Calculate from caster's max HP
            max_hp = SkillEffectHandler._get_max_hp(caster)
            recoil_damage = max_hp * (recoil_percentage / 100)
        
        # Apply recoil to caster
        SkillEffectHandler._apply_damage(caster, recoil_damage)
        
        return {
            "damage": recoil_damage,
            "effects": [f"Recoil damage: {recoil_damage:.1f} to {caster.name}"]
        }
    
    # Helper methods for character interaction
    @staticmethod
    def _calculate_skill_damage(caster: 'Character', target: 'Character', effect_data: Dict[str, Any]) -> float:
        """Calculate damage for a skill effect using universal scaling."""
        from ..core.universal_scaling import UniversalScaling, ScalingParameters
        
        # Get base damage from effect data
        base_damage = effect_data.get('damage', 0)
        if base_damage > 0:
            return base_damage
        
        # If no base damage, try to calculate using scaling
        # This would need skill parameters - for now return placeholder
        try:
            # Get caster stats
            if hasattr(caster, 'stats') and hasattr(caster.stats, 'get_stat'):
                atk = caster.stats.get_stat('atk')
                mag = caster.stats.get_stat('mag')
            else:
                atk = 100  # Default fallback
                mag = 100
            
            # Get target stats
            if hasattr(target, 'stats') and hasattr(target.stats, 'get_stat'):
                vit = target.stats.get_stat('vit')
                spr = target.stats.get_stat('spr')
            else:
                vit = 50  # Default fallback
                spr = 50
            
            caster_stats = {"atk": float(atk), "mag": float(mag), "int": float(mag), "spr": float(spr)}
            target_stats = {"vit": float(vit), "spr": float(spr)}
            
            # Use basic scaling parameters
            scaling_params = ScalingParameters(
                floor=20,
                ceiling=0,
                softcap_1=50,
                softcap_2=200,
                post_cap_rate=0.5
            )
            
            # Determine damage type
            damage_type = effect_data.get('damage_type', 'physical')
            is_magical = damage_type in ['magical', 'lightning', 'fire', 'ice', 'earth', 'wind', 'water', 'dark', 'light']
            
            # Calculate damage
            damage = UniversalScaling.calculate_final_damage(
                caster_stats=caster_stats,
                target_stats=target_stats,
                scaling_params=scaling_params,
                skill_multiplier=1.0,
                is_magical=is_magical
            )
            
            return damage
            
        except Exception as e:
            logger.warning("Error calculating skill damage: %s", e)
            return 50.0  # Fallback damage
    
    @staticmethod
    def _apply_damage(character: 'Character', damage: float) -> None:
        """Apply damage to a character."""
        if hasattr(character, 'take_damage'):
            character.take_damage(damage)
        elif hasattr(character, 'stats'):
            current_hp = SkillEffectHandler._get_current_hp(character)
            new_hp = max(0, current_hp - damage)
            SkillEffectHandler._set_current_hp(character, new_hp)
    
    @staticmethod
    def _apply_healing(character: 'Character', healing: float) -> float:
        """Apply healing to a character and return actual healing done."""
        if hasattr(character, 'heal'):
            return character.heal(healing)
        elif hasattr(character, 'stats'):
            current_hp = SkillEffectHandler._get_current_hp(character)
            max_hp = SkillEffectHandler._get_max_hp(character)
            new_hp = min(max_hp, current_hp + healing)
            actual_healing = new_hp - current_hp
            SkillEffectHandler._set_current_hp(character, new_hp)
            return actual_healing
        return 0.0
    
    @staticmethod
    def _get_current_hp(character: 'Character') -> float:
        """Get character's current HP."""
        if hasattr(character, 'current_hp'):
            return character.current_hp
        elif hasattr(character, 'stats') and hasattr(character.stats, 'get_stat'):
            return character.stats.get_stat('hp')
        return 100.0  # Default fallback
    
    @staticmethod
    def _get_max_hp(character: 'Character') -> float:
        """Get character's maximum HP."""
        if hasattr(character, 'max_hp'):
            return character.max_hp
        elif hasattr(character, 'stats') and hasattr(character.stats, 'get_base_stat'):
            return character.stats.get_base_stat('hp')
        return 100.0  # Default fallback
    
    @staticmethod
    def _set_current_hp(character: 'Character', hp: float) -> None:
        """Set character's current HP."""
        if hasattr(character, 'current_hp'):
            character.current_hp = hp
        elif hasattr(character, 'stats') and hasattr(character.stats, 'set_stat'):
            character.stats.set_stat('hp', hp)
    
    @staticmethod
    def _get_hp_percentage(character: 'Character') -> float:
        """Get character's HP as a percentage."""
        current = SkillEffectHandler._get_current_hp(character)
        maximum = SkillEffectHandler._get_max_hp(character)
        return (current / maximum) * 100 if maximum > 0 else 0
    
    @staticmethod
    def _has_debuffs(character: 'Character') -> bool:
        """Check if character has any debuffs."""
        if not hasattr(character, 'effects') or not character.effects:
            return False
        
        # Check for debuff effects on the character
        debuff_types = ['poison', 'burn', 'freeze', 'stun', 'silence', 'weakness', 'curse', 'bleed']
        
        for effect in character.effects.active_effects:
            if effect.effect_type.lower() in debuff_types:
                return True
            # Also check if effect has negative stat modifiers
            if hasattr(effect, 'stat_modifiers'):
                for mod in effect.stat_modifiers:
                    if mod.get('value', 0) < 0:  # Negative modifier = debuff
                        return True
        
        return False
