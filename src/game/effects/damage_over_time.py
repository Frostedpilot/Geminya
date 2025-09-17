"""Damage over time and heal over time effects."""

from src.game.effects.base_effect import BaseEffect

class DamageOverTimeEffect(BaseEffect):
    """Effect that applies damage each turn (Bleed, Burn, Poison, etc.)."""
    
    def __init__(self, source_character, target_character, duration, damage_per_turn, damage_type="physical"):
        """Initialize damage over time effect.
        
        Args:
            source_character: Character who applied this effect
            target_character: Character affected by this effect
            duration: Number of turns this effect lasts
            damage_per_turn: Amount of damage to apply each turn
            damage_type: Type of damage ("physical", "magical", "true")
        """
        effect_data = {
            "damage_per_turn": damage_per_turn,
            "damage_type": damage_type
        }
        super().__init__(source_character, target_character, duration, effect_data)
        self.damage_per_turn = damage_per_turn
        self.damage_type = damage_type
    
    def apply_effect(self, event_bus):
        """Apply the DoT effect (initial application)."""
        event_bus.publish("EffectApplied", {
            "effect": self,
            "character": self.target_character,
            "damage_per_turn": self.damage_per_turn,
            "damage_type": self.damage_type
        })
    
    def on_turn_start(self, event_bus):
        """Apply damage at the start of the affected character's turn."""
        if not self.is_active:
            return
        
        target_state = self.target_character.components.get('state')
        if not target_state or not target_state.is_alive:
            return
        
        # Calculate final damage (accounting for resistances in future)
        final_damage = self.damage_per_turn
        if self.damage_type == "physical":
            # Physical DoT can be reduced by VIT in future implementations
            pass
        elif self.damage_type == "magical":
            # Magical DoT can be reduced by SPR in future implementations
            pass
        # "true" damage bypasses all defenses
        
        # Apply damage
        old_hp = target_state.current_hp
        target_state.current_hp = max(0, target_state.current_hp - final_damage)
        
        # Publish events
        event_bus.publish("HPChanged", {
            "character": self.target_character,
            "old_hp": old_hp,
            "new_hp": target_state.current_hp,
            "damage": final_damage,
            "source": self.source_character,
            "damage_type": "dot"
        })
        
        # Check if character was defeated by DoT
        if target_state.current_hp <= 0 and target_state.is_alive:
            target_state.is_alive = False
            event_bus.publish("CharacterDefeated", {
                "character": self.target_character,
                "killer": self.source_character,
                "cause": "dot"
            })
    
    def get_description(self):
        """Get a human-readable description of this effect."""
        return f"{self.damage_type.title()} DoT: -{self.damage_per_turn} HP/turn ({self.duration} turns)"


class HealOverTimeEffect(BaseEffect):
    """Effect that applies healing each turn (Regeneration, etc.)."""
    
    def __init__(self, source_character, target_character, duration, heal_per_turn):
        """Initialize heal over time effect.
        
        Args:
            source_character: Character who applied this effect
            target_character: Character affected by this effect
            duration: Number of turns this effect lasts
            heal_per_turn: Amount of healing to apply each turn
        """
        effect_data = {
            "heal_per_turn": heal_per_turn
        }
        super().__init__(source_character, target_character, duration, effect_data)
        self.heal_per_turn = heal_per_turn
    
    def apply_effect(self, event_bus):
        """Apply the HoT effect (initial application)."""
        event_bus.publish("EffectApplied", {
            "effect": self,
            "character": self.target_character,
            "heal_per_turn": self.heal_per_turn
        })
    
    def on_turn_start(self, event_bus):
        """Apply healing at the start of the affected character's turn."""
        if not self.is_active:
            return
        
        target_state = self.target_character.components.get('state')
        if not target_state or not target_state.is_alive:
            return
        
        # Apply healing
        old_hp = target_state.current_hp
        max_hp = target_state.max_hp
        target_state.current_hp = min(max_hp, target_state.current_hp + self.heal_per_turn)
        
        # Publish healing event
        event_bus.publish("HPChanged", {
            "character": self.target_character,
            "old_hp": old_hp,
            "new_hp": target_state.current_hp,
            "heal": self.heal_per_turn,
            "source": self.source_character,
            "heal_type": "hot"
        })
    
    def get_description(self):
        """Get a human-readable description of this effect."""
        return f"Regeneration: +{self.heal_per_turn} HP/turn ({self.duration} turns)"