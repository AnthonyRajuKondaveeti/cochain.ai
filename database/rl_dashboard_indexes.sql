-- Performance Indexes for RL Dashboard
-- Run this in your Supabase SQL editor to speed up the RL dashboard

-- 1. Index on user_interactions for time-based queries
CREATE INDEX IF NOT EXISTS idx_user_interactions_time 
ON user_interactions(interaction_time DESC);

-- 2. Index on user_interactions for project-based queries
CREATE INDEX IF NOT EXISTS idx_user_interactions_project 
ON user_interactions(github_reference_id);

-- 3. Composite index for interaction type and time (for CTR calculations)
CREATE INDEX IF NOT EXISTS idx_user_interactions_type_time 
ON user_interactions(interaction_type, interaction_time DESC);

-- 4. Index on rl_training_history for dashboard queries
CREATE INDEX IF NOT EXISTS idx_rl_training_history_timestamp 
ON rl_training_history(training_timestamp DESC);

-- 5. Index on recommendation_results for CTR calculations
CREATE INDEX IF NOT EXISTS idx_recommendation_results_created_at 
ON recommendation_results(created_at DESC);

-- 6. Composite index for filtering out notifications from interactions
CREATE INDEX IF NOT EXISTS idx_user_interactions_type_project_time 
ON user_interactions(interaction_type, github_reference_id, interaction_time DESC)
WHERE interaction_type NOT IN ('notification_read', 'notification_view');

-- Verify indexes were created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('user_interactions', 'rl_training_history', 'recommendation_results')
ORDER BY tablename, indexname;
