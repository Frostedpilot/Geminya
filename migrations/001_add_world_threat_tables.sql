-- World-Threat Expeditions Migration SQL
-- Run this directly in your PostgreSQL database server
-- This will create all 4 tables needed for the World-Threat system

-- Table 1: Raid Info Data (Comprehensive)
CREATE TABLE IF NOT EXISTS world_threat_raids (
    id SERIAL PRIMARY KEY,
    raid_name VARCHAR(255) NOT NULL,
    boss_name VARCHAR(255) NOT NULL,
    total_hp BIGINT NOT NULL,
    current_hp BIGINT NOT NULL,
    
    -- Boss Configuration
    dominant_stats JSON NOT NULL,
    initial_weaknesses JSON NOT NULL,
    initial_resistances JSON NOT NULL,
    
    -- Dynamic State
    current_weaknesses JSON DEFAULT '[]',
    current_curses JSON DEFAULT '[]',
    
    -- Curse System Configuration
    curse_pool JSON NOT NULL,
    curse_limits JSON NOT NULL,
    curse_trigger_threshold INTEGER DEFAULT 100,
    strikes_since_last_curse INTEGER DEFAULT 0,
    
    -- Analysis System
    analysis_thresholds JSON NOT NULL,
    current_analysis_points BIGINT DEFAULT 0,
    thresholds_unlocked INTEGER DEFAULT 0,
    analysis_reward_pool JSON NOT NULL,
    
    -- Event State
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    created_by VARCHAR(255),
    
    -- Metadata
    description TEXT,
    victory_rewards JSON,
    analysis_milestone_rewards JSON
);

-- Table 2: Character Usage Tracking
CREATE TABLE IF NOT EXISTS world_threat_character_usage (
    id SERIAL PRIMARY KEY,
    raid_id INTEGER NOT NULL REFERENCES world_threat_raids(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    character_id INTEGER NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(raid_id, user_id, character_id)
);

-- Table 3: Strike Logging (Enhanced)
CREATE TABLE IF NOT EXISTS world_threat_strikes (
    id SERIAL PRIMARY KEY,
    raid_id INTEGER NOT NULL REFERENCES world_threat_raids(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type VARCHAR(20) NOT NULL,
    
    -- Team Details
    team_characters JSON NOT NULL,
    team_size INTEGER NOT NULL,
    equipped_equipment_id INTEGER REFERENCES equipment(id),
    
    -- Calculations
    base_score BIGINT NOT NULL,
    affinity_multiplier DECIMAL(5,3) NOT NULL,
    final_score BIGINT NOT NULL,
    
    -- Results
    damage_dealt BIGINT DEFAULT 0,
    
    -- Context Tracking
    boss_hp_before BIGINT NOT NULL,
    boss_hp_after BIGINT NOT NULL,
    boss_weaknesses_at_time JSON NOT NULL,
    boss_curses_at_time JSON NOT NULL,
    
    -- Rewards
    strike_rewards JSON,
    
    struck_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 4: Analysis Logging (Enhanced)
CREATE TABLE IF NOT EXISTS world_threat_analysis (
    id SERIAL PRIMARY KEY,
    raid_id INTEGER NOT NULL REFERENCES world_threat_raids(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Analysis Details
    team_characters JSON NOT NULL,
    team_size INTEGER NOT NULL,
    equipped_equipment_id INTEGER REFERENCES equipment(id),
    
    -- Calculations
    base_score BIGINT NOT NULL,
    affinity_multiplier DECIMAL(5,3) NOT NULL,
    final_score BIGINT NOT NULL,
    analysis_points BIGINT NOT NULL,
    
    -- Context Tracking
    boss_weaknesses_at_time JSON NOT NULL,
    boss_curses_at_time JSON NOT NULL,
    
    -- Milestone Tracking
    milestone_triggered BOOLEAN DEFAULT FALSE,
    threshold_reached INTEGER NULL,
    
    -- Rewards
    analysis_rewards JSON,
    
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_world_threat_raids_status ON world_threat_raids(status);
CREATE INDEX IF NOT EXISTS idx_world_threat_raids_created_at ON world_threat_raids(created_at);

CREATE INDEX IF NOT EXISTS idx_world_threat_character_usage_raid_user ON world_threat_character_usage(raid_id, user_id);
CREATE INDEX IF NOT EXISTS idx_world_threat_character_usage_character ON world_threat_character_usage(character_id);

CREATE INDEX IF NOT EXISTS idx_world_threat_strikes_user_action ON world_threat_strikes(raid_id, user_id, action_type);
CREATE INDEX IF NOT EXISTS idx_world_threat_strikes_timestamp ON world_threat_strikes(struck_at);

CREATE INDEX IF NOT EXISTS idx_world_threat_analysis_milestone ON world_threat_analysis(raid_id, milestone_triggered);
CREATE INDEX IF NOT EXISTS idx_world_threat_analysis_user ON world_threat_analysis(raid_id, user_id);

-- Migration complete message
DO $$
BEGIN
    RAISE NOTICE 'World-Threat Expeditions tables created successfully!';
    RAISE NOTICE 'Tables created: world_threat_raids, world_threat_character_usage, world_threat_strikes, world_threat_analysis';
    RAISE NOTICE 'Performance indexes created for optimal query performance';
END $$;