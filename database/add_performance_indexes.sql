-- ============================================================================
-- Quick Win Improvements for RL Tracking System
-- ============================================================================
-- Purpose: Performance optimizations that take < 30 minutes to implement
-- Expected Impact: 10-50x faster queries, better data quality
-- ============================================================================

-- ============================================================================
-- IMPROVEMENT #1: Add Composite Index for Faster Recommendation Lookups
-- ============================================================================
-- Problem: Finding recent recommendation_result_id is slow
-- Solution: Composite index on (github_reference_id, created_at DESC)
-- Expected: 10-50x faster lookups

CREATE INDEX IF NOT EXISTS idx_recommendation_results_project_time 
ON recommendation_results(github_reference_id, created_at DESC);

COMMENT ON INDEX idx_recommendation_results_project_time IS 
'Speeds up lookup of recent recommendation_result_id for click tracking';

-- ============================================================================
-- IMPROVEMENT #2: Add Index for User Interactions by Type
-- ============================================================================
-- Problem: Queries filtering by interaction_type are slow
-- Solution: Index on interaction_type for faster filtering

CREATE INDEX IF NOT EXISTS idx_user_interactions_type_time
ON user_interactions(interaction_type, interaction_time DESC);

COMMENT ON INDEX idx_user_interactions_type_time IS
'Speeds up queries filtering by interaction type (click, bookmark, etc.)';

-- ============================================================================
-- IMPROVEMENT #3: Add Index for Session Lookups
-- ============================================================================
-- Problem: Session queries by session_id could be faster
-- Solution: Index already exists (idx_user_sessions_id), verify it

-- Verify existing index
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_user_sessions_id'
    ) THEN
        CREATE INDEX idx_user_sessions_id ON user_sessions(session_id);
        RAISE NOTICE 'Created missing index: idx_user_sessions_id';
    ELSE
        RAISE NOTICE 'Index idx_user_sessions_id already exists';
    END IF;
END $$;

-- ============================================================================
-- IMPROVEMENT #4: Add Index for RL Stats Queries
-- ============================================================================
-- Problem: Queries ordering by total_samples or updated_at are slow
-- Solution: Indexes for common query patterns

CREATE INDEX IF NOT EXISTS idx_project_rl_stats_samples
ON project_rl_stats(total_samples DESC);

CREATE INDEX IF NOT EXISTS idx_project_rl_stats_updated
ON project_rl_stats(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_project_rl_stats_clicks
ON project_rl_stats(total_clicks DESC)
WHERE total_clicks > 0;

COMMENT ON INDEX idx_project_rl_stats_samples IS 'For queries ordering by sample count';
COMMENT ON INDEX idx_project_rl_stats_updated IS 'For queries ordering by last update';
COMMENT ON INDEX idx_project_rl_stats_clicks IS 'For finding projects with clicks (partial index)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check that indexes were created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('recommendation_results', 'user_interactions', 'user_sessions', 'project_rl_stats')
AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;

-- ============================================================================
-- PERFORMANCE TEST QUERIES
-- ============================================================================

-- Test 1: Find recent recommendation_result_id (should use new index)
EXPLAIN ANALYZE
SELECT id 
FROM recommendation_results
WHERE github_reference_id = (SELECT id FROM github_references LIMIT 1)
ORDER BY created_at DESC
LIMIT 1;

-- Test 2: Count interactions by type (should use new index)
EXPLAIN ANALYZE
SELECT interaction_type, COUNT(*) 
FROM user_interactions
WHERE interaction_time > NOW() - INTERVAL '24 hours'
GROUP BY interaction_type;

-- Test 3: Get top RL projects (should use new index)
EXPLAIN ANALYZE
SELECT * 
FROM project_rl_stats
WHERE total_clicks > 0
ORDER BY total_clicks DESC
LIMIT 10;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Quick Win Improvements Applied Successfully!';
    RAISE NOTICE '📊 Added 6 performance indexes';
    RAISE NOTICE '⚡ Expected 10-50x speedup for click tracking queries';
    RAISE NOTICE '🎯 Run ANALYZE to update query planner statistics';
END $$;

-- Update statistics for query planner
ANALYZE recommendation_results;
ANALYZE user_interactions;
ANALYZE user_sessions;
ANALYZE project_rl_stats;
