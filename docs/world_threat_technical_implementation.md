# **World-Threat Expeditions: Technical Implementation Guide**

## **Project: Anime Character Auto-Battler - Expansion 2**

### **Table of Contents**

1. **Implementation Overview**
2. **Database Schema Design**
3. **Service Layer Architecture**
4. **API Endpoints & Methods**
5. **Game Logic Implementation**
6. **Discord Bot Integration**
7. **Data Structures & Models**
8. **Deployment & Migration Strategy**
9. **Testing Strategy**
10. **Performance Considerations**

---

## **1. Implementation Overview**

### **1.1 System Architecture**

The World-Threat Expeditions system will be implemented as an **additional game mode** alongside the existing individual expedition system. The architecture follows a layered approach:

```text
Discord Bot Layer (UI/UX)
    ↓
Service Layer (Business Logic)
    ↓
Database Layer (Persistence)
    ↓
Game Engine Layer (Mechanics)
```

### **1.2 Core Components**

- **WorldThreatService**: Main business logic orchestrator
- **WorldThreatManager**: Game state management
- **StrikeResolver**: Combat/analysis resolution engine
- **RewardCalculator**: Reward distribution system
- **Discord Cogs**: User interface and command handling

### **1.3 Integration Points**

- **Existing Character System**: Reuse character models and stats
- **Existing Equipment System**: Equipment can be used in strikes
- **Existing Affinity System**: Leverage affinity calculations
- **Existing Database Service**: Extend with new tables and methods

---

## **2. Database Schema Design**

### **2.1 Simplified 4-Table Schema**

```sql
-- Table 1: Raid Info Data (Comprehensive)
CREATE TABLE world_threat_raids (
    id SERIAL PRIMARY KEY,
    raid_name VARCHAR(255) NOT NULL,
    boss_name VARCHAR(255) NOT NULL,
    total_hp BIGINT NOT NULL,
    current_hp BIGINT NOT NULL,
    
    -- Boss Configuration
    dominant_stats JSON NOT NULL, -- ["atk", "spd", "lck"]
    initial_weaknesses JSON NOT NULL, -- Starting favored affinities
    initial_resistances JSON NOT NULL, -- Starting disfavored affinities
    
    -- Dynamic State
    current_weaknesses JSON DEFAULT '[]', -- Unlocked weaknesses (favored affinities)
    current_curses JSON DEFAULT '[]', -- Applied curses (disfavored affinities)
    
    -- Curse System Configuration
    curse_pool JSON NOT NULL, -- Available curses to apply
    curse_limits JSON NOT NULL, -- {"elemental": 2, "genre": 1}
    curse_trigger_threshold INTEGER DEFAULT 100, -- Strikes before new curse
    strikes_since_last_curse INTEGER DEFAULT 0,
    
    -- Analysis System
    analysis_thresholds JSON NOT NULL, -- [50000000, 120000000, ...]
    current_analysis_points BIGINT DEFAULT 0,
    thresholds_unlocked INTEGER DEFAULT 0,
    analysis_reward_pool JSON NOT NULL, -- Weighted pools for weakness types
    
    -- Stage System
    current_stage INTEGER DEFAULT 1, -- Raid progression stage
    stage_thresholds JSON NOT NULL, -- HP/analysis thresholds for stage progression
    stage_effects JSON NOT NULL, -- Effects applied at each stage
    
    -- Event State
    status VARCHAR(50) DEFAULT 'active', -- active, completed, paused
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    created_by VARCHAR(255), -- Admin who created the event
    
    -- Metadata
    description TEXT,
    victory_rewards JSON, -- Rewards for defeating the boss
    analysis_milestone_rewards JSON -- Rewards for analysis contributions
);

-- Table 2: Character Usage Tracking
CREATE TABLE world_threat_character_usage (
    id SERIAL PRIMARY KEY,
    raid_id INTEGER NOT NULL REFERENCES world_threat_raids(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    character_id INTEGER NOT NULL, -- user_waifu_id from existing system
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(raid_id, user_id, character_id) -- Enforce one-use rule
);

-- Table 3: Strike Logging (Enhanced)
CREATE TABLE world_threat_strikes (
    id SERIAL PRIMARY KEY,
    raid_id INTEGER NOT NULL REFERENCES world_threat_raids(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type VARCHAR(20) NOT NULL, -- 'fight' or 'analyze'
    
    -- Team Details
    team_characters JSON NOT NULL, -- Character IDs and their stats at time of strike
    team_size INTEGER NOT NULL,
    equipped_equipment_id INTEGER REFERENCES equipment(id),
    
    -- Calculations
    base_score BIGINT NOT NULL, -- Sum of dominant stats
    affinity_multiplier DECIMAL(5,3) NOT NULL, -- Final multiplier applied
    final_score BIGINT NOT NULL, -- base_score * affinity_multiplier
    
    -- Results
    damage_dealt BIGINT DEFAULT 0,
    
    -- Context Tracking
    stage_at_strike INTEGER NOT NULL, -- Which stage the raid was in
    boss_hp_before BIGINT NOT NULL,
    boss_hp_after BIGINT NOT NULL,
    boss_weaknesses_at_time JSON NOT NULL, -- Boss state at time of strike
    boss_curses_at_time JSON NOT NULL,
    
    -- Rewards
    strike_rewards JSON, -- Immediate rewards for this strike
    
    struck_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 4: Analysis Logging (Enhanced)
CREATE TABLE world_threat_analysis (
    id SERIAL PRIMARY KEY,
    raid_id INTEGER NOT NULL REFERENCES world_threat_raids(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Analysis Details
    team_characters JSON NOT NULL, -- Character IDs used for analysis
    team_size INTEGER NOT NULL,
    equipped_equipment_id INTEGER REFERENCES equipment(id),
    
    -- Calculations
    base_score BIGINT NOT NULL, -- Sum of dominant stats
    affinity_multiplier DECIMAL(5,3) NOT NULL, -- Final multiplier applied
    final_score BIGINT NOT NULL, -- base_score * affinity_multiplier
    analysis_points BIGINT NOT NULL, -- Converted analysis contribution
    
    -- Context Tracking
    stage_at_analysis INTEGER NOT NULL, -- Which stage the raid was in
    boss_weaknesses_at_time JSON NOT NULL, -- Boss state at time of analysis
    boss_curses_at_time JSON NOT NULL,
    
    -- Milestone Tracking
    milestone_triggered BOOLEAN DEFAULT FALSE, -- Did this analysis trigger a breakthrough?
    threshold_reached INTEGER NULL, -- Which threshold was reached (if any)
    
    -- Rewards
    analysis_rewards JSON, -- Immediate rewards for this analysis
    
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **2.2 Enhanced Indexes**

```sql
-- Comprehensive indexes for the enhanced 4-table schema
CREATE INDEX idx_world_threat_character_usage_raid_user ON world_threat_character_usage(raid_id, user_id);
CREATE INDEX idx_world_threat_character_usage_character ON world_threat_character_usage(character_id);

CREATE INDEX idx_world_threat_strikes_raid_stage ON world_threat_strikes(raid_id, stage_at_strike);
CREATE INDEX idx_world_threat_strikes_user_action ON world_threat_strikes(raid_id, user_id, action_type);
CREATE INDEX idx_world_threat_strikes_timestamp ON world_threat_strikes(struck_at);

CREATE INDEX idx_world_threat_analysis_raid_stage ON world_threat_analysis(raid_id, stage_at_analysis);
CREATE INDEX idx_world_threat_analysis_milestone ON world_threat_analysis(raid_id, milestone_triggered);
CREATE INDEX idx_world_threat_analysis_user ON world_threat_analysis(raid_id, user_id);
```

### **2.3 Simplified Database Service Extensions**

```python
# Simplified methods for DatabaseService class
async def create_world_threat_raid(self, raid_data: Dict[str, Any]) -> int:
    """Create a new world threat raid"""
    
async def get_active_raid(self) -> Optional[Dict[str, Any]]:
    """Get the currently active raid"""
    
async def update_raid_hp(self, raid_id: int, new_hp: int) -> bool:
    """Update boss HP after damage"""
    
async def update_raid_stage(self, raid_id: int, new_stage: int) -> bool:
    """Update raid stage progression"""
    
async def record_strike(self, raid_id: int, user_id: int, action_type: str, team_characters: List[int], damage: int, stage: int) -> int:
    """Record a strike action"""
    
async def record_analysis(self, raid_id: int, user_id: int, analysis_points: int, stage: int) -> int:
    """Record analysis contribution"""
    
async def mark_characters_used(self, raid_id: int, user_id: int, character_ids: List[int]) -> bool:
    """Mark characters as used in raid"""
    
async def get_available_characters(self, raid_id: int, user_id: int) -> List[int]:
    """Get character IDs not yet used in this raid"""
    
async def get_raid_participation_summary(self, raid_id: int, user_id: int) -> Dict[str, Any]:
    """Get user's participation stats calculated from logs"""
```

---

## **3. Service Layer Architecture**

### **3.1 Simplified WorldThreatService**

```python
class WorldThreatService:
    """Simplified service for World-Threat Expeditions"""
    
    def __init__(self, database_service: DatabaseService):
        self.db = database_service
        self.logger = logging.getLogger(__name__)
    
    # Core Actions
    async def execute_strike(self, user_id: str, action_type: str, character_ids: List[int]) -> Dict[str, Any]:
        """Execute fight or analyze action with stage tracking"""
        
    async def get_raid_status(self) -> Optional[Dict[str, Any]]:
        """Get current raid status including stage"""
        
    async def get_user_participation(self, user_id: str) -> Dict[str, Any]:
        """Get user's participation calculated from strike/analysis logs"""
        
    # Stage Management
    async def check_stage_progression(self, raid_id: int) -> bool:
        """Check if raid should progress to next stage based on HP/analysis thresholds"""
        
    async def advance_stage(self, raid_id: int) -> Dict[str, Any]:
        """Advance raid to next stage and apply changes"""
```

### **3.2 WorldThreatManager**

```python
class WorldThreatManager:
    """Manages world threat game state and mechanics"""
    
    def calculate_affinity_multiplier(self, characters: List[Character], boss_state: Dict) -> float:
        """Calculate team affinity multiplier against current boss state"""
        
    def select_random_curse(self, boss_config: Dict) -> Dict[str, Any]:
        """Select and apply a random curse from boss pool"""
        
    def select_random_weakness(self, boss_config: Dict) -> Dict[str, Any]:
        """Select a random weakness from analysis reward pool"""
        
    def calculate_team_score(self, characters: List[Character], dominant_stats: List[str]) -> int:
        """Calculate base team score using only dominant stats"""
        
    def check_curse_limits(self, current_curses: List[Dict], curse_limits: Dict, new_curse: Dict) -> List[Dict]:
        """Apply curse limits, replacing if necessary"""
```

### **3.3 StrikeResolver**

```python
class StrikeResolver:
    """Resolves strike actions and calculates results"""
    
    def resolve_fight_action(self, base_score: int, affinity_multiplier: float) -> int:
        """Convert score to damage: floor(final_score / 10)"""
        
    def resolve_analyze_action(self, base_score: int, affinity_multiplier: float) -> int:
        """Convert score to analysis points: floor(final_score / 10)"""
        
    def calculate_strike_rewards(self, action_type: str, final_score: int, boss_tier: int) -> Dict[str, Any]:
        """Calculate immediate rewards for strike"""
```

### **3.4 RewardCalculator**

```python
class RewardCalculator:
    """Handles reward calculations and distributions"""
    
    def calculate_milestone_rewards(self, milestone_type: str, contribution_level: str) -> Dict[str, Any]:
        """Calculate rewards for reaching analysis milestones"""
        
    def calculate_victory_rewards(self, participation_level: str, final_damage_contribution: int) -> Dict[str, Any]:
        """Calculate final victory rewards based on participation"""
        
    def calculate_strike_rewards(self, action_type: str, score: int) -> Dict[str, Any]:
        """Calculate immediate strike rewards"""
```

---

## **4. API Endpoints & Methods**

### **4.1 Core Strike Action**

```python
async def execute_strike(self, discord_id: str, action_type: str, character_ids: List[int], equipment_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a strike action (fight or analyze)
    
    Args:
        discord_id: Player's Discord ID
        action_type: 'fight' or 'analyze'
        character_ids: List of character IDs to use (1-6 characters)
        equipment_id: Optional equipment to use
    
    Returns:
        {
            'success': bool,
            'damage_dealt': int (if fight),
            'analysis_contributed': int (if analyze),
            'rewards': dict,
            'boss_hp_remaining': int,
            'curse_triggered': dict or None,
            'breakthrough_achieved': dict or None,
            'victory': bool
        }
    
    Raises:
        CooldownError: If user is still on cooldown
        CharacterAlreadyUsedError: If any character was already used
        InvalidTeamSizeError: If team size is not 1-6
        NoActiveEventError: If no active world threat event
    """
```

### **4.2 Game State Queries**

```python
async def get_world_threat_status(self) -> Dict[str, Any]:
    """Get complete world threat status for display"""
    
async def get_user_participation(self, discord_id: str) -> Dict[str, Any]:
    """Get user's participation summary and available actions"""
    
async def get_leaderboard(self, sort_by: str = 'damage', limit: int = 10) -> List[Dict[str, Any]]:
    """Get participation leaderboard"""
```

### **4.3 Admin Functions**

```python
async def create_world_threat(self, admin_id: str, boss_config: Dict[str, Any]) -> int:
    """Create new world threat event (admin only)"""
    
async def modify_world_threat(self, admin_id: str, event_id: int, modifications: Dict[str, Any]) -> bool:
    """Modify active world threat (admin only)"""
    
async def force_end_world_threat(self, admin_id: str, event_id: int) -> bool:
    """Force end world threat event (admin only)"""
```

---

## **5. Game Logic Implementation**

### **5.1 Simplified Strike Resolution with Stage Tracking**

```python
async def execute_strike(self, user_id: str, action_type: str, character_ids: List[int]) -> Dict[str, Any]:
    """
    Simplified strike execution with stage tracking
    """
    # Get active raid
    raid = await self.db.get_active_raid()
    if not raid:
        raise NoActiveRaidError("No active raid found")
    
    # Verify characters are available
    available_chars = await self.db.get_available_characters(raid['id'], user_id)
    if any(char_id not in available_chars for char_id in character_ids):
        raise CharacterAlreadyUsedError("One or more characters already used")
    
    # Calculate damage/analysis based on current stage
    current_stage = raid['current_stage']
    result = self.resolve_action(character_ids, action_type, raid, current_stage)
    
    # Record the action with stage information
    if action_type == 'fight':
        await self.db.record_strike(raid['id'], user_id, action_type, character_ids, result['damage'], current_stage)
        await self.db.update_raid_hp(raid['id'], raid['current_hp'] - result['damage'])
    else:  # analyze
        await self.db.record_analysis(raid['id'], user_id, result['analysis_points'], current_stage)
    
    # Mark characters as used
    await self.db.mark_characters_used(raid['id'], user_id, character_ids)
    
    # Check for stage progression
    await self.check_stage_progression(raid['id'])
    
    return result

def resolve_action(self, character_ids: List[int], action_type: str, raid: Dict, stage: int) -> Dict[str, Any]:
    """
    Resolve strike/analysis action based on current stage
    Stage affects multipliers and effectiveness
    """
    # Basic calculation (simplified)
    base_score = self.calculate_team_score(character_ids, raid['dominant_stats'])
    
    # Stage-based multipliers
    stage_multiplier = 1.0 + (stage - 1) * 0.1  # Each stage increases effectiveness by 10%
    
    final_score = int(base_score * stage_multiplier)
    
    if action_type == 'fight':
        damage = final_score // 10
        return {'damage': damage, 'stage': stage}
    else:
        analysis_points = final_score // 10
        return {'analysis_points': analysis_points, 'stage': stage}
```

### **5.2 Stage Progression System**

```python
async def check_stage_progression(self, raid_id: int) -> bool:
    """
    Check if raid should advance to next stage based on HP thresholds or analysis milestones
    """
    raid = await self.db.get_raid_by_id(raid_id)
    
    # HP-based stage progression (e.g., every 25% HP lost)
    hp_percentage = raid['current_hp'] / raid['total_hp']
    hp_stage = 5 - int(hp_percentage * 4)  # Stage 1-5 based on HP
    
    # Analysis-based stage progression (e.g., every 1M analysis points)
    analysis_stage = (raid['analysis_points'] // 1000000) + 1
    
    # Use the higher of HP or analysis stage
    new_stage = max(hp_stage, analysis_stage, raid['current_stage'])
    
    if new_stage > raid['current_stage']:
        await self.advance_stage(raid_id, new_stage)
        return True
    
    return False

async def advance_stage(self, raid_id: int, new_stage: int) -> Dict[str, Any]:
    """
    Advance raid to next stage and apply stage-specific changes
    """
    await self.db.update_raid_stage(raid_id, new_stage)
    
    # Stage-specific effects (simplified)
    stage_effects = {
        2: {"new_weakness": "fire", "message": "The boss shows vulnerability to fire!"},
        3: {"new_curse": "water", "message": "The boss gains water-based defenses!"},
        4: {"new_weakness": "lightning", "message": "Lightning attacks become more effective!"},
        5: {"final_stage": True, "message": "Final stage! All attacks deal double damage!"}
    }
    
    effect = stage_effects.get(new_stage, {})
    
    # Apply stage effects to raid data
    if "new_weakness" in effect:
        await self.add_weakness_to_raid(raid_id, effect["new_weakness"])
    if "new_curse" in effect:
        await self.add_curse_to_raid(raid_id, effect["new_curse"])
    
    return {"new_stage": new_stage, "effects": effect}
```

### **5.3 Curse Trigger System**

```python
async def check_and_apply_curse(self, event_id: int) -> Optional[Dict[str, Any]]:
    """
    Check if curse should be applied and apply it
    """
    event = await self.db.get_world_threat_event(event_id)
    
    # Check if threshold reached
    if event['strikes_since_last_curse'] >= event['curse_trigger_threshold']:
        # Select random curse from pool
        available_curses = self.get_available_curses(event)
        new_curse = random.choice(available_curses)
        
        # Apply curse limits (replace if needed)
        updated_curses = self.apply_curse_limits(
            event['current_curses'], 
            event['curse_limits'], 
            new_curse
        )
        
        # Update database
        await self.db.update_world_threat_curses(event_id, updated_curses)
        await self.db.reset_curse_strike_counter(event_id)
        
        # Log event
        await self.db.add_world_threat_log(
            event_id, 
            'curse_applied', 
            f"The {event['boss_name']} grows stronger!",
            f"New curse applied: {new_curse['type']} - {new_curse['value']}",
            {'curse': new_curse}
        )
        
        return new_curse
    
    return None
```

### **5.4 Analysis Breakthrough System**

```python
async def check_analysis_breakthrough(self, event_id: int, new_analysis_points: int) -> Optional[Dict[str, Any]]:
    """
    Check if analysis points trigger a breakthrough
    """
    event = await self.db.get_world_threat_event(event_id)
    
    old_total = event['current_analysis_points']
    new_total = old_total + new_analysis_points
    
    thresholds = event['analysis_thresholds']
    unlocked = event['thresholds_unlocked']
    
    # Check if we crossed a threshold
    if unlocked < len(thresholds) and new_total >= thresholds[unlocked]:
        # Breakthrough achieved!
        new_weakness = self.select_breakthrough_weakness(event)
        
        # Update database
        await self.db.add_world_threat_weakness(event_id, new_weakness)
        await self.db.update_analysis_progress(event_id, new_total, unlocked + 1)
        
        # Distribute milestone rewards to all contributors
        await self.distribute_milestone_rewards(event_id, unlocked + 1)
        
        # Log breakthrough
        await self.db.add_world_threat_log(
            event_id,
            'weakness_unlocked',
            "Breakthrough! New weakness discovered!",
            f"Analysis reveals weakness to: {new_weakness['type']} - {new_weakness['value']}",
            {'weakness': new_weakness, 'threshold': unlocked + 1}
        )
        
        return new_weakness
    
    return None
```

---

## **6. Discord Bot Integration**

### **6.1 New Cog Structure**

```python
# cogs/commands/world_threat.py
class WorldThreatCog(commands.Cog):
    """Discord commands for World-Threat Expeditions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.world_threat_service = WorldThreatService(bot.database_service)
    
    @app_commands.command(name="raid_status", description="View current world threat status")
    async def raid_status(self, interaction: discord.Interaction):
        """Display current raid boss status and progress"""
        
    @app_commands.command(name="raid_strike", description="Launch a strike against the world threat")
    async def raid_strike(self, interaction: discord.Interaction):
        """Open strike action interface"""
        
    @app_commands.command(name="raid_team", description="View your available characters and participation")
    async def raid_team(self, interaction: discord.Interaction):
        """Show user's available characters and usage status"""
        
    @app_commands.command(name="raid_leaderboard", description="View raid participation leaderboard")
    async def raid_leaderboard(self, interaction: discord.Interaction):
        """Display damage and analysis contribution leaderboards"""
```

### **6.2 Strike Action UI**

```python
class StrikeActionView(discord.ui.View):
    """Interactive UI for executing strikes"""
    
    def __init__(self, user_id: str, world_threat_service: WorldThreatService):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.service = world_threat_service
        self.selected_characters = []
        self.selected_equipment = None
        self.action_type = None
    
    @discord.ui.button(label="⚔️ Fight", style=discord.ButtonStyle.danger)
    async def fight_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select fight action"""
        
    @discord.ui.button(label="🔍 Analyze", style=discord.ButtonStyle.primary) 
    async def analyze_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select analyze action"""
        
    @discord.ui.select(placeholder="Select characters for your team (1-6)...")
    async def character_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Character selection dropdown"""
        
    @discord.ui.button(label="🚀 Execute Strike", style=discord.ButtonStyle.success)
    async def execute_strike(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Execute the configured strike"""
```

### **6.3 Real-time Updates**

```python
class WorldThreatEventHandler:
    """Handle real-time world threat events"""
    
    async def on_curse_applied(self, event_data: Dict[str, Any]):
        """Announce new curse to all channels"""
        
    async def on_weakness_unlocked(self, event_data: Dict[str, Any]):
        """Announce breakthrough to all channels"""
        
    async def on_boss_defeated(self, event_data: Dict[str, Any]):
        """Announce victory and distribute rewards"""
        
    async def process_pending_announcements(self):
        """Background task to check for pending announcements"""
```

---

## **7. Data Structures & Models**

### **7.1 Enhanced Core Models**

```python
@dataclass
class WorldThreatRaid:
    id: int
    raid_name: str
    boss_name: str
    total_hp: int
    current_hp: int
    dominant_stats: List[str]
    initial_weaknesses: List[Dict[str, str]]
    initial_resistances: List[Dict[str, str]]
    current_weaknesses: List[Dict[str, str]]
    current_curses: List[Dict[str, str]]
    curse_pool: Dict[str, List[str]]
    curse_limits: Dict[str, int]
    analysis_thresholds: List[int]
    current_analysis_points: int
    thresholds_unlocked: int
    current_stage: int
    stage_thresholds: Dict[str, List[int]]
    stage_effects: Dict[str, Dict[str, Any]]
    status: str
    created_at: datetime

@dataclass 
class StrikeAction:
    raid_id: int
    user_id: int
    action_type: str  # 'fight' or 'analyze'
    team_characters: List[Dict[str, Any]]
    team_size: int
    base_score: int
    affinity_multiplier: float
    final_score: int
    damage_dealt: int
    stage_at_strike: int
    boss_hp_before: int
    boss_hp_after: int
    boss_weaknesses_at_time: List[Dict[str, str]]
    boss_curses_at_time: List[Dict[str, str]]
    struck_at: datetime

@dataclass
class AnalysisAction:
    raid_id: int
    user_id: int
    team_characters: List[Dict[str, Any]]
    team_size: int
    base_score: int
    affinity_multiplier: float
    final_score: int
    analysis_points: int
    stage_at_analysis: int
    boss_weaknesses_at_time: List[Dict[str, str]]
    boss_curses_at_time: List[Dict[str, str]]
    milestone_triggered: bool
    threshold_reached: Optional[int]
    analyzed_at: datetime
```

### **7.2 Configuration Models**

```python
@dataclass
class BossConfiguration:
    """Configuration for creating a new world threat boss"""
    name: str
    total_hp: int
    dominant_stats: List[str]
    initial_weaknesses: List[str]
    initial_resistances: List[str]
    curse_pool: Dict[str, List[str]]  # Organized by affinity type
    curse_limits: Dict[str, int]
    curse_trigger_threshold: int
    analysis_thresholds: List[int]
    analysis_reward_pool: Dict[str, float]  # Weighted chances
    victory_rewards: Dict[str, Any]
    description: str

@dataclass
class RewardConfiguration:
    """Reward structure configuration"""
    strike_base_rewards: Dict[str, Any]
    milestone_rewards: Dict[int, Dict[str, Any]]  # Per threshold
    victory_rewards_by_tier: Dict[str, Dict[str, Any]]  # Based on contribution
```

---

## **8. Deployment & Migration Strategy**

### **8.1 Database Migration Plan**

```sql
-- Migration Script: 001_create_world_threat_tables.sql
-- Create all world threat tables
-- Add indexes
-- Create initial admin functions

-- Migration Script: 002_add_world_threat_permissions.sql  
-- Add admin role checks
-- Create default configurations

-- Migration Script: 003_create_sample_event.sql
-- Insert sample world threat event for testing
```

### **8.2 Feature Deployment Strategy**

1. **Phase 1: Core Backend**
   - Deploy database migrations
   - Implement WorldThreatService
   - Add basic admin commands for event creation

2. **Phase 2: Basic UI**
   - Deploy Discord cog with basic commands
   - Implement strike action workflow
   - Add status display commands

3. **Phase 3: Advanced Features**
   - Real-time announcements
   - Leaderboards and statistics
   - Advanced reward systems

4. **Phase 4: Polish & Optimization**
   - Performance optimizations
   - Enhanced UI/UX
   - Additional admin tools

### **8.3 Configuration Management**

```python
# config/world_threat_config.py
WORLD_THREAT_CONFIG = {
    'max_team_size': 6,
    'min_team_size': 1,
    'action_cooldown_hours': 1,
    'damage_conversion_rate': 10,  # final_score / 10
    'analysis_conversion_rate': 10,  # final_score / 10
    'weakness_multiplier': 1.5,
    'curse_multiplier': 0.75,
    'default_curse_threshold': 100,
    'max_active_events': 1,
    'admin_roles': ['Admin', 'Moderator']
}
```

---

## **9. Testing Strategy**

### **9.1 Unit Tests**

```python
# tests/test_world_threat_service.py
class TestWorldThreatService:
    async def test_strike_resolution_fight(self):
        """Test fight action damage calculation"""
        
    async def test_strike_resolution_analyze(self):
        """Test analyze action point calculation"""
        
    async def test_affinity_multiplier_calculation(self):
        """Test complex affinity multiplier scenarios"""
        
    async def test_curse_application(self):
        """Test curse trigger and application logic"""
        
    async def test_breakthrough_mechanics(self):
        """Test analysis breakthrough detection"""

# tests/test_world_threat_database.py  
class TestWorldThreatDatabase:
    async def test_event_creation(self):
        """Test world threat event creation"""
        
    async def test_strike_recording(self):
        """Test strike action persistence"""
        
    async def test_character_usage_tracking(self):
        """Test one-use character enforcement"""
```

### **9.2 Integration Tests**

```python
# tests/integration/test_world_threat_flow.py
class TestWorldThreatIntegration:
    async def test_complete_strike_workflow(self):
        """Test end-to-end strike execution"""
        
    async def test_event_lifecycle(self):
        """Test complete event from creation to victory"""
        
    async def test_concurrent_strikes(self):
        """Test multiple simultaneous strikes"""
```

### **9.3 Load Testing**

```python
# tests/load/test_world_threat_performance.py
class TestWorldThreatPerformance:
    async def test_high_concurrency_strikes(self):
        """Test system under high strike volume"""
        
    async def test_database_performance(self):
        """Test database performance under load"""
```

---

## **10. Performance Considerations**

### **10.1 Database Optimization**

- **Connection Pooling**: Utilize existing asyncpg connection pool
- **Query Optimization**: Use appropriate indexes for common queries
- **Batch Operations**: Batch multiple updates in transactions
- **Read Replicas**: Consider read replicas for leaderboard queries

### **10.2 Caching Strategy**

```python
# Use Redis or in-memory caching for:
- Active event data (boss state, analysis progress)
- User cooldown timers
- Available character lists
- Leaderboard data (refresh every 5 minutes)
```

### **10.3 Rate Limiting**

```python
# Implement rate limiting for:
- Strike actions (enforced by cooldown system)
- Status queries (prevent spam)
- Leaderboard requests (cache-based)
```

### **10.4 Monitoring & Alerts**

- **Strike Volume**: Monitor strikes per minute
- **Database Performance**: Query execution times
- **Event Health**: Boss HP progression, analysis point accumulation
- **Error Rates**: Failed strike attempts, database errors

---

## **11. Error Handling & Edge Cases**

### **11.1 Common Error Scenarios**

```python
class WorldThreatError(Exception):
    """Base exception for world threat operations"""
    
class CooldownError(WorldThreatError):
    """User is still on cooldown"""
    
class CharacterAlreadyUsedError(WorldThreatError):
    """One or more characters already used in this event"""
    
class NoActiveEventError(WorldThreatError):
    """No active world threat event"""
    
class InvalidTeamSizeError(WorldThreatError):
    """Team size not within 1-6 range"""
    
class BossAlreadyDefeatedError(WorldThreatError):
    """Attempting action on defeated boss"""
```

### **11.2 Data Consistency**

- **Atomic Operations**: Use database transactions for multi-table updates
- **Optimistic Locking**: Handle concurrent boss HP updates
- **Rollback Procedures**: Ability to rollback failed operations

---

This technical implementation guide provides a comprehensive roadmap for implementing the World-Threat Expeditions system while maintaining integration with the existing codebase and ensuring scalability and performance.