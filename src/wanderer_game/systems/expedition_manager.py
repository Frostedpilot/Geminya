"""
Expedition Manager - Core system for managing expedition lifecycle

Handles:
- Available expedition generation and rotation
- Expedition dispatch and tracking 
- Active expedition state management
- Reward claiming and completion
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from ..models import (
    Expedition, ExpeditionTemplate, ActiveExpedition, ExpeditionStatus,
    Team
)


@dataclass
class ExpeditionSlot:
    """Represents an expedition slot that can hold an active expedition"""
    slot_id: int
    active_expedition: Optional[ActiveExpedition] = None
    
    def is_available(self) -> bool:
        """Check if this slot is available for a new expedition"""
        return self.active_expedition is None
    
    def is_complete(self, current_time: float) -> bool:
        """Check if the expedition in this slot is complete"""
        if not self.active_expedition:
            return False
        return self.active_expedition.is_complete(current_time)


class ExpeditionManager:
    """
    Stateful, persistent system for managing expeditions
    
    Responsibilities:
    - Generate daily available expeditions from templates
    - Manage expedition dispatch and active tracking
    - Handle expedition completion and reward claiming
    """
    
    def __init__(self, max_expedition_slots: int = 10):
        self.max_expedition_slots = max_expedition_slots
        self.available_expeditions: List[Expedition] = []
        self.expedition_slots: Dict[int, ExpeditionSlot] = {}
        self.expedition_templates: List[ExpeditionTemplate] = []
        self.last_generation_timestamp: float = 0
        self.generation_interval: float = 24 * 60 * 60  # 24 hours in seconds
        
        # Initialize expedition slots
        for i in range(max_expedition_slots):
            self.expedition_slots[i] = ExpeditionSlot(slot_id=i)
    
    def load_expedition_templates(self, templates_data: List[Dict]) -> None:
        """Load expedition templates from JSON data"""
        self.expedition_templates = []
        for template_data in templates_data:
            template = ExpeditionTemplate.from_dict(template_data)
            self.expedition_templates.append(template)
    
    def should_regenerate_expeditions(self, current_time: float) -> bool:
        """Check if it's time to regenerate available expeditions"""
        return (current_time - self.last_generation_timestamp) >= self.generation_interval
    
    def generate_available_expeditions(self, current_time: float, 
                                     num_expeditions: int = 5) -> None:
        """
        Generate a fresh list of available expeditions from templates
        Called daily or when the rotation timer expires
        """
        if not self.expedition_templates:
            return
        
        self.available_expeditions = []
        
        # Select random templates (can repeat) and generate expedition instances
        import random
        selected_templates = random.choices(
            self.expedition_templates, 
            k=min(num_expeditions, len(self.expedition_templates) * 2)
        )
        
        for template in selected_templates:
            expedition = template.generate_expedition()
            self.available_expeditions.append(expedition)
        
        self.last_generation_timestamp = current_time
    
    def get_available_expeditions(self, current_time: float) -> List[Expedition]:
        """Get list of available expeditions, regenerating if needed"""
        if self.should_regenerate_expeditions(current_time):
            self.generate_available_expeditions(current_time)
        
        return self.available_expeditions.copy()
    
    def get_available_slots(self) -> List[int]:
        """Get list of available expedition slot IDs"""
        return [slot_id for slot_id, slot in self.expedition_slots.items() 
                if slot.is_available()]
    
    def get_active_expeditions(self) -> Dict[int, ActiveExpedition]:
        """Get all currently active expeditions"""
        return {slot_id: slot.active_expedition 
                for slot_id, slot in self.expedition_slots.items() 
                if slot.active_expedition is not None}
    
    def dispatch_expedition(self, expedition_id: str, team: Team, 
                          current_time: float) -> Optional[int]:
        """
        Dispatch an expedition with the given team
        
        Returns:
            The slot ID if successful, None if failed
        """
        # Find the expedition in available list
        expedition = None
        for exp in self.available_expeditions:
            if exp.expedition_id == expedition_id:
                expedition = exp
                break
        
        if not expedition:
            raise ValueError(f"Expedition {expedition_id} not found in available expeditions")
        
        # Find an available slot
        available_slots = self.get_available_slots()
        if not available_slots:
            raise ValueError("No available expedition slots")
        
        slot_id = available_slots[0]  # Use first available slot
        
        # Update expedition with team's series IDs for dynamic encounter tags
        team_series_ids = team.get_series_ids()
        expedition.encounter_pool_tags.extend([str(sid) for sid in team_series_ids])
        
        # Calculate end time
        duration_seconds = expedition.duration_hours * 60 * 60
        end_time = current_time + duration_seconds
        
        # Create active expedition
        active_expedition = ActiveExpedition(
            expedition=expedition,
            team_character_ids=[char.waifu_id for char in team.characters],
            start_timestamp=current_time,
            end_timestamp=end_time,
            status=ExpeditionStatus.ACTIVE
        )
        
        # Assign to slot
        self.expedition_slots[slot_id].active_expedition = active_expedition
        
        # Remove from available expeditions
        self.available_expeditions.remove(expedition)
        
        return slot_id
    
    def can_claim_expedition(self, slot_id: int, current_time: float) -> bool:
        """Check if an expedition in the given slot can be claimed"""
        if slot_id not in self.expedition_slots:
            return False
        
        slot = self.expedition_slots[slot_id]
        return slot.is_complete(current_time)
    
    def get_expedition_time_remaining(self, slot_id: int, current_time: float) -> float:
        """Get remaining time for expedition in seconds (0 if complete)"""
        if slot_id not in self.expedition_slots:
            return 0.0
        
        slot = self.expedition_slots[slot_id]
        if not slot.active_expedition:
            return 0.0
        
        return slot.active_expedition.get_time_remaining(current_time)
    
    def cancel_expedition(self, slot_id: int) -> bool:
        """
        Cancel an active expedition (forfeit all progress and rewards)
        
        Returns:
            True if successfully cancelled, False if slot was empty or invalid
        """
        if slot_id not in self.expedition_slots:
            return False
        
        slot = self.expedition_slots[slot_id]
        if not slot.active_expedition:
            return False
        
        # Mark as cancelled and clear slot
        slot.active_expedition.status = ExpeditionStatus.CANCELLED
        slot.active_expedition = None
        return True
    
    def prepare_expedition_for_resolution(self, slot_id: int) -> Optional[ActiveExpedition]:
        """
        Prepare an expedition for resolution without clearing the slot
        Used by ExpeditionResolver to process completed expeditions
        """
        if slot_id not in self.expedition_slots:
            return None
        
        slot = self.expedition_slots[slot_id]
        if not slot.active_expedition:
            return None
        
        return slot.active_expedition
    
    def complete_expedition(self, slot_id: int) -> bool:
        """
        Mark an expedition as completed and clear the slot
        Called after ExpeditionResolver has processed the results
        """
        if slot_id not in self.expedition_slots:
            return False
        
        slot = self.expedition_slots[slot_id]
        if not slot.active_expedition:
            return False
        
        slot.active_expedition.status = ExpeditionStatus.COMPLETED
        slot.active_expedition = None
        return True
    
    def get_status_summary(self, current_time: float) -> Dict:
        """Get a summary of the current expedition manager state"""
        available_count = len(self.available_expeditions)
        active_expeditions = self.get_active_expeditions()
        available_slots = self.get_available_slots()
        
        # Check which active expeditions are ready to claim
        ready_to_claim = []
        for slot_id in active_expeditions:
            if self.can_claim_expedition(slot_id, current_time):
                ready_to_claim.append(slot_id)
        
        return {
            'available_expeditions': available_count,
            'active_expeditions': len(active_expeditions),
            'available_slots': len(available_slots),
            'ready_to_claim': len(ready_to_claim),
            'ready_to_claim_slots': ready_to_claim,
            'next_regeneration': self.last_generation_timestamp + self.generation_interval,
            'time_until_regeneration': max(0, (self.last_generation_timestamp + self.generation_interval) - current_time)
        }