-- ============================================================================
-- Phase 3 Prerequisites Migration
-- ============================================================================
-- Patches existing tables to support RL features
-- Run this BEFORE add_rl_tables.sql
-- ============================================================================

-- Print start message
DO $$
BEGIN
    RAISE NOTICE '🔧 Starting Phase 3 Prerequisites Migration...';
END $$;

-- ============================================================================
-- 1. UPDATE recommendation_results TABLE
-- ============================================================================

-- Add RL-specific columns
ALTER TABLE recommendation_results
ADD COLUMN IF NOT EXISTS rl_score FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS recommendation_method VARCHAR(50) DEFAULT 'similarity',
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL;

-- Add indexes for RL queries
CREATE INDEX IF NOT EXISTS idx_recommendation_results_method 
ON recommendation_results(recommendation_method);

CREATE INDEX IF NOT EXISTS idx_recommendation_results_user 
ON recommendation_results(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_recommendation_results_project 
ON recommendation_results(github_reference_id, created_at DESC);

-- Add comment
COMMENT ON COLUMN recommendation_results.rl_score IS 'Thompson Sampling bandit score';
COMMENT ON COLUMN recommendation_results.recommendation_method IS 'Method used: similarity, rl_enhanced, explore, exploit';

DO $$
BEGIN
    RAISE NOTICE '✅ Updated recommendation_results table';
END $$;

-- ============================================================================
-- 2. ADD INDEXES TO user_interactions
-- ============================================================================

-- Add missing indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_user_interactions_session 
ON user_interactions(session_id) WHERE session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_interactions_time 
ON user_interactions(interaction_time DESC);

CREATE INDEX IF NOT EXISTS idx_user_interactions_user_time 
ON user_interactions(user_id, interaction_time DESC) WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_interactions_project_time 
ON user_interactions(github_reference_id, interaction_time DESC);

DO $$
BEGIN
    RAISE NOTICE '✅ Added indexes to user_interactions';
END $$;

-- ============================================================================
-- 3. ADD INDEXES TO user_feedback
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_user_feedback_user 
ON user_feedback(user_id, created_at DESC) WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_feedback_project 
ON user_feedback(github_reference_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_feedback_rating_time 
ON user_feedback(rating, created_at DESC) WHERE rating IS NOT NULL;

DO $$
BEGIN
    RAISE NOTICE '✅ Added indexes to user_feedback';
END $$;

-- ============================================================================
-- 4. OPTIMIZE user_sessions TABLE
-- ============================================================================

-- Add index for session tracking queries
CREATE INDEX IF NOT EXISTS idx_user_sessions_activity 
ON user_sessions(last_activity DESC);

CREATE INDEX IF NOT EXISTS idx_user_sessions_login 
ON user_sessions(login_time DESC);

DO $$
BEGIN
    RAISE NOTICE '✅ Optimized user_sessions indexes';
END $$;

-- ============================================================================
-- 5. CREATE user_events TABLE (Frontend Event Tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    
    -- Event details
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    
    -- Context
    page VARCHAR(255),
    referrer VARCHAR(512),
    user_agent TEXT,
    ip_address VARCHAR(45),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for event queries
CREATE INDEX IF NOT EXISTS idx_user_events_user 
ON user_events(user_id, created_at DESC) WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_events_type 
ON user_events(event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_events_session 
ON user_events(session_id) WHERE session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_events_created 
ON user_events(created_at DESC);

-- Add comment
COMMENT ON TABLE user_events IS 'Frontend event tracking for detailed user behavior analysis';

DO $$
BEGIN
    RAISE NOTICE '✅ Created user_events table';
END $$;

-- ============================================================================
-- 6. CREATE analytics_cache TABLE (Performance Optimization)
-- ============================================================================

CREATE TABLE IF NOT EXISTS analytics_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Cache key
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    
    -- Cached data
    cache_data JSONB NOT NULL,
    
    -- Cache metadata
    computed_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    hits INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for cache queries
CREATE INDEX IF NOT EXISTS idx_analytics_cache_key 
ON analytics_cache(cache_key);

CREATE INDEX IF NOT EXISTS idx_analytics_cache_expires 
ON analytics_cache(expires_at);

-- Add comment
COMMENT ON TABLE analytics_cache IS 'Caches expensive analytics queries for faster dashboard loading';

DO $$
BEGIN
    RAISE NOTICE '✅ Created analytics_cache table';
END $$;

-- ============================================================================
-- 7. CREATE user_preference_history TABLE (Optional - Track Preference Changes)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_preference_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Snapshot of preferences
    areas_of_interest JSONB,
    programming_languages JSONB,
    frameworks_known JSONB,
    overall_skill_level VARCHAR(50),
    
    -- Why this snapshot was taken
    snapshot_reason VARCHAR(100),
    
    -- Timestamp
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Index for preference queries
CREATE INDEX IF NOT EXISTS idx_user_preference_history_user 
ON user_preference_history(user_id, recorded_at DESC);

-- Add comment
COMMENT ON TABLE user_preference_history IS 'Historical snapshots of user preferences to track learning progression';

DO $$
BEGIN
    RAISE NOTICE '✅ Created user_preference_history table';
END $$;

-- ============================================================================
-- 8. ADD HELPER FUNCTIONS
-- ============================================================================

-- Function to clean old analytics cache
CREATE OR REPLACE FUNCTION clean_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM analytics_cache 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION clean_expired_cache() IS 'Removes expired cache entries';

-- Function to increment cache hits
CREATE OR REPLACE FUNCTION increment_cache_hit(p_cache_key VARCHAR)
RETURNS VOID AS $$
BEGIN
    UPDATE analytics_cache 
    SET hits = hits + 1
    WHERE cache_key = p_cache_key;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION increment_cache_hit(VARCHAR) IS 'Increments hit counter for cache analytics';

DO $$
BEGIN
    RAISE NOTICE '✅ Created helper functions';
END $$;

-- ============================================================================
-- 9. UPDATE EXISTING VIEWS (Optional enhancements)
-- ============================================================================

-- Enhanced user engagement summary with more metrics
CREATE OR REPLACE VIEW user_engagement_summary_enhanced AS
SELECT 
    u.id as user_id,
    u.email,
    u.full_name,
    u.created_at as user_since,
    
    -- Session metrics
    COUNT(DISTINCT us.id) as total_sessions,
    COALESCE(SUM(us.total_minutes), 0) as total_minutes_on_platform,
    COALESCE(AVG(us.total_minutes), 0) as avg_session_duration,
    
    -- GitHub activity
    COALESCE(SUM(us.github_recommendations_viewed), 0) as github_views,
    COALESCE(SUM(us.github_projects_clicked), 0) as github_clicks,
    
    -- Calculate CTR
    CASE 
        WHEN SUM(us.github_recommendations_viewed) > 0 
        THEN ROUND((SUM(us.github_projects_clicked)::NUMERIC / SUM(us.github_recommendations_viewed) * 100), 2)
        ELSE 0 
    END as github_ctr,
    
    -- Live projects
    COALESCE(SUM(us.live_projects_viewed), 0) as live_project_views,
    COALESCE(SUM(us.collaboration_requests_sent), 0) as collab_requests_sent,
    COUNT(DISTINCT up.id) as projects_created,
    COUNT(DISTINCT pm.project_id) as projects_joined,
    
    -- Engagement score (composite metric)
    ROUND((
        COALESCE(SUM(us.total_minutes), 0) * 0.3 +
        COALESCE(SUM(us.github_projects_clicked), 0) * 10 +
        COUNT(DISTINCT up.id) * 50 +
        COUNT(DISTINCT pm.project_id) * 30
    ), 2) as engagement_score,
    
    -- Last activity
    MAX(us.last_activity) as last_active_at
    
FROM users u
LEFT JOIN user_sessions us ON u.id = us.user_id
LEFT JOIN user_projects up ON u.id = up.creator_id
LEFT JOIN project_members pm ON u.id = pm.user_id AND pm.is_active = true
GROUP BY u.id, u.email, u.full_name, u.created_at;

COMMENT ON VIEW user_engagement_summary_enhanced IS 'Enhanced user engagement metrics with CTR and engagement score';

DO $$
BEGIN
    RAISE NOTICE '✅ Created enhanced views';
END $$;

-- ============================================================================
-- 10. VERIFICATION QUERIES
-- ============================================================================

-- Verify all changes were applied
DO $$
DECLARE
    missing_items TEXT := '';
    item_exists BOOLEAN;
BEGIN
    RAISE NOTICE '🔍 Verifying prerequisites...';
    
    -- Check recommendation_results columns
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'recommendation_results' AND column_name = 'rl_score'
    ) INTO item_exists;
    IF NOT item_exists THEN
        missing_items := missing_items || '- recommendation_results.rl_score
';
    END IF;
    
    -- Check user_events table
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'user_events'
    ) INTO item_exists;
    IF NOT item_exists THEN
        missing_items := missing_items || '- user_events table
';
    END IF;
    
    -- Check analytics_cache table
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'analytics_cache'
    ) INTO item_exists;
    IF NOT item_exists THEN
        missing_items := missing_items || '- analytics_cache table
';
    END IF;
    
    -- Report results
    IF missing_items = '' THEN
        RAISE NOTICE '✅ All prerequisites verified successfully!';
    ELSE
        RAISE WARNING '⚠️ Missing items:
%', missing_items;
    END IF;
END $$;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE '✅ Phase 3 Prerequisites Migration Complete!';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Tables Updated:';
    RAISE NOTICE '   ✓ recommendation_results (added RL columns)';
    RAISE NOTICE '   ✓ user_interactions (added indexes)';
    RAISE NOTICE '   ✓ user_feedback (added indexes)';
    RAISE NOTICE '   ✓ user_sessions (optimized indexes)';
    RAISE NOTICE '';
    RAISE NOTICE '🆕 New Tables Created:';
    RAISE NOTICE '   ✓ user_events (frontend tracking)';
    RAISE NOTICE '   ✓ analytics_cache (performance)';
    RAISE NOTICE '   ✓ user_preference_history (optional)';
    RAISE NOTICE '';
    RAISE NOTICE '📈 New Views:';
    RAISE NOTICE '   ✓ user_engagement_summary_enhanced';
    RAISE NOTICE '';
    RAISE NOTICE '🔧 Next Step: Run add_rl_tables.sql';
    RAISE NOTICE '';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
END $$;