from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class WorldThreatBoss(BaseModel):
    boss_name: str
    dominant_stats: List[str]
    cursed_stat: str
    buffs: Dict[str, List[str]]
    curses: Dict[str, List[str]]
    buff_cap: int
    curse_cap: int
    server_total_points: int = 0
    total_research_actions: int = 0
    adaptation_level: int = 0

class WorldThreatPlayerStatus(BaseModel):
    discord_id: str
    cumulative_points: int = 0
    last_action_timestamp: Optional[datetime] = None
    research_stacks: int = 0
    claimed_personal_checkpoints: List[int] = Field(default_factory=list)
    claimed_server_checkpoints: List[int] = Field(default_factory=list)
