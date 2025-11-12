-- ============================================================================
-- Reinforcement Learning Tables Migration
-- ============================================================================
-- Add tables to support Thompson Sampling Contextual Bandit
-- Run this migration before deploying Phase 3
-- ============================================================================

-- Table: project_rl_stats
-- Stores Beta distribution parameters for each project
CREATE TABLE IF NOT EXISTS project_rl_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES github_references(id) ON DELETE CASCADE UNIQUE,
    
    -- Beta distribution parameters
    alpha FLOAT DEFAULT 2.0,  -- Success parameter (starts with optimistic prior)
    beta FLOAT DEFAULT 2.0,   -- Failure parameter (starts with optimistic prior)
    
    -- Derived statistics
    total_samples INTEGER DEFAULT 0,              -- Total interactions processed
    estimated_quality FLOAT DEFAULT 0.5,          -- alpha / (alpha + beta)
    confidence_score FLOAT DEFAULT 0.0,           -- Measure of certainty
    
    -- Performance tracking
    total_impressions INTEGER DEFAULT 0,          -- Times shown
    total_clicks INTEGER DEFAULT 0,               -- Times clicked
    total_bookmarks INTEGER DEFAULT 0,            -- Times bookmarked
    total_feedback_count INTEGER DEFAULT 0,       -- Feedback received
    average_rating FLOAT DEFAULT 0.0,             -- Average feedback rating
    
    -- Reward aggregates
    total_reward FLOAT DEFAULT 0.0,               -- Cumulative reward
    avg_reward_per_interaction FLOAT DEFAULT 0.0, -- Average reward
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_interaction_at TIMESTAMP
);

-- Indexes for project_rl_stats
CREATE INDEX idx_project_rl_stats_quality ON project_rl_stats(estimated_quality DESC);
CREATE INDEX idx_project_rl_stats_samples ON project_rl_stats(total_samples DESC);
CREATE INDEX idx_project_rl_stats_updated ON project_rl_stats(updated_at DESC);

-- Table: rl_training_history
-- Tracks model performance over time for A/B testing
CREATE TABLE IF NOT EXISTS rl_training_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Training metadata
    training_date DATE DEFAULT CURRENT_DATE,
    training_timestamp TIMESTAMP DEFAULT NOW(),
    days_processed INTEGER DEFAULT 1,
    
    -- Performance metrics (before training)
    pre_avg_reward FLOAT,
    pre_positive_rate FLOAT,
    pre_avg_ctr FLOAT,
    
    -- Performance metrics (after training)
    post_avg_reward FLOAT,
    post_positive_rate FLOAT,
    post_avg_ctr FLOAT,
    
    -- Training statistics
    projects_updated INTEGER DEFAULT 0,
    total_interactions_processed INTEGER DEFAULT 0,
    exploration_rate FLOAT DEFAULT 0.15,
    
    -- Improvement metrics
    reward_improvement FLOAT,  -- (post - pre) / pre * 100
    ctr_improvement FLOAT,
    
    -- Notes
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for training history
CREATE INDEX idx_rl_training_history_date ON rl_training_history(training_date DESC);

-- Table: rl_ab_test
-- A/B testing framework for comparing algorithms
CREATE TABLE IF NOT EXISTS rl_ab_test (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Test metadata
    test_name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMP DEFAULT NOW(),
    end_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',  -- active, completed, cancelled
    
    -- Control group (existing algorithm)
    control_algorithm VARCHAR(100) DEFAULT 'similarity_only',
    control_users INTEGER DEFAULT 0,
    control_avg_ctr FLOAT DEFAULT 0.0,
    control_avg_reward FLOAT DEFAULT 0.0,
    control_retention_rate FLOAT DEFAULT 0.0,
    
    -- Treatment group (new algorithm)
    treatment_algorithm VARCHAR(100) DEFAULT 'rl_enhanced',
    treatment_users INTEGER DEFAULT 0,
    treatment_avg_ctr FLOAT DEFAULT 0.0,
    treatment_avg_reward FLOAT DEFAULT 0.0,
    treatment_retention_rate FLOAT DEFAULT 0.0,
    
    -- Statistical significance
    p_value FLOAT,
    is_significant BOOLEAN DEFAULT FALSE,
    
    -- Winner
    winner VARCHAR(50),  -- control, treatment, inconclusive
    
    -- Configuration
    traffic_split FLOAT DEFAULT 0.5,  -- 0.5 = 50/50 split
    exploration_rate FLOAT DEFAULT 0.15,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for A/B tests
CREATE INDEX idx_rl_ab_test_status ON rl_ab_test(status);
CREATE INDEX idx_rl_ab_test_dates ON rl_ab_test(start_date, end_date);

-- Table: user_ab_assignment
-- Tracks which users are in which A/B test group
CREATE TABLE IF NOT EXISTS user_ab_assignment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ab_test_id UUID REFERENCES rl_ab_test(id) ON DELETE CASCADE,
    
    -- Assignment
    group_name VARCHAR(50) NOT NULL,  -- control, treatment
    assigned_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, ab_test_id)
);

-- Index for user assignments
CREATE INDEX idx_user_ab_assignment_user ON user_ab_assignment(user_id);
CREATE INDEX idx_user_ab_assignment_test ON user_ab_assignment(ab_test_id);

-- Table: user_cached_recommendations
-- Cache recommendations per user to avoid recomputation
-- (Already exists from Phase 1, but adding index for RL)
CREATE INDEX IF NOT EXISTS idx_user_cached_recommendations_updated 
ON user_cached_recommendations(updated_at DESC);

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- View: project_rl_performance
-- Comprehensive view of project RL performance
CREATE OR REPLACE VIEW project_rl_performance AS
SELECT 
    prs.*,
    gr.title,
    gr.domain,
    gr.complexity_level,
    gr.original_stars,
    gr.original_forks,
    
    -- Performance calculations
    CASE 
        WHEN prs.total_impressions > 0 
        THEN ROUND((prs.total_clicks::NUMERIC / prs.total_impressions * 100), 2)
        ELSE 0 
    END as ctr,
    
    CASE
        WHEN prs.total_clicks > 0
        THEN ROUND((prs.total_bookmarks::NUMERIC / prs.total_clicks * 100), 2)
        ELSE 0
    END as bookmark_rate,
    
    -- Confidence interval width (uncertainty measure)
    ROUND(SQRT((prs.alpha * prs.beta) / 
        ((prs.alpha + prs.beta) * (prs.alpha + prs.beta) * (prs.alpha + prs.beta + 1))) * 1.96 * 2, 4) 
    as confidence_width
    
FROM project_rl_stats prs
JOIN github_references gr ON prs.project_id = gr.id
WHERE prs.total_samples > 0;

-- View: rl_model_summary
-- Overall RL model health
CREATE OR REPLACE VIEW rl_model_summary AS
SELECT 
    COUNT(*) as total_projects_tracked,
    COUNT(*) FILTER (WHERE total_samples >= 10) as projects_with_sufficient_data,
    ROUND(AVG(estimated_quality), 4) as avg_estimated_quality,
    ROUND(AVG(total_reward), 2) as avg_total_reward,
    ROUND(AVG(avg_reward_per_interaction), 2) as avg_reward_per_interaction,
    ROUND(AVG(CASE WHEN total_impressions > 0 
        THEN total_clicks::NUMERIC / total_impressions * 100 
        ELSE 0 END), 2) as avg_ctr,
    MAX(updated_at) as last_model_update
FROM project_rl_stats;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: update_project_rl_stats
-- Helper function to update project stats atomically
CREATE OR REPLACE FUNCTION update_project_rl_stats(
    p_project_id UUID,
    p_alpha_delta FLOAT,
    p_beta_delta FLOAT,
    p_reward FLOAT
) RETURNS VOID AS $$
BEGIN
    INSERT INTO project_rl_stats (
        project_id, 
        alpha, 
        beta, 
        total_reward,
        total_samples,
        updated_at
    )
    VALUES (
        p_project_id,
        2.0 + p_alpha_delta,  -- Start with prior
        2.0 + p_beta_delta,
        p_reward,
        1,
        NOW()
    )
    ON CONFLICT (project_id) DO UPDATE SET
        alpha = project_rl_stats.alpha + p_alpha_delta,
        beta = project_rl_stats.beta + p_beta_delta,
        total_reward = project_rl_stats.total_reward + p_reward,
        total_samples = project_rl_stats.total_samples + 1,
        estimated_quality = (project_rl_stats.alpha + p_alpha_delta) / 
            (project_rl_stats.alpha + p_alpha_delta + project_rl_stats.beta + p_beta_delta),
        avg_reward_per_interaction = (project_rl_stats.total_reward + p_reward) / 
            (project_rl_stats.total_samples + 1),
        updated_at = NOW(),
        last_interaction_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function: increment_project_impression
-- Track when project is shown
CREATE OR REPLACE FUNCTION increment_project_impression(p_project_id UUID) 
RETURNS VOID AS $$
BEGIN
    INSERT INTO project_rl_stats (project_id, total_impressions)
    VALUES (p_project_id, 1)
    ON CONFLICT (project_id) DO UPDATE SET
        total_impressions = project_rl_stats.total_impressions + 1,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function: increment_project_click
-- Track when project is clicked
CREATE OR REPLACE FUNCTION increment_project_click(p_project_id UUID) 
RETURNS VOID AS $$
BEGIN
    UPDATE project_rl_stats 
    SET 
        total_clicks = total_clicks + 1,
        updated_at = NOW()
    WHERE project_id = p_project_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: auto_update_rl_stats_on_interaction
-- Automatically update RL stats when user interacts
CREATE OR REPLACE FUNCTION auto_update_rl_stats() 
RETURNS TRIGGER AS $$
BEGIN
    -- Increment impression count for shown recommendations
    IF NEW.interaction_type = 'impression' THEN
        PERFORM increment_project_impression(NEW.github_reference_id);
    END IF;
    
    -- Increment click count
    IF NEW.interaction_type = 'click' THEN
        PERFORM increment_project_click(NEW.github_reference_id);
    END IF;
    
    -- Increment bookmark count
    IF NEW.interaction_type = 'bookmark_add' THEN
        UPDATE project_rl_stats 
        SET total_bookmarks = total_bookmarks + 1, updated_at = NOW()
        WHERE project_id = NEW.github_reference_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger (only if not exists)
DROP TRIGGER IF EXISTS trigger_auto_update_rl_stats ON user_interactions;
CREATE TRIGGER trigger_auto_update_rl_stats
    AFTER INSERT ON user_interactions
    FOR EACH ROW
    EXECUTE FUNCTION auto_update_rl_stats();

-- Trigger: update_rl_stats_on_feedback
-- Update stats when feedback is given
CREATE OR REPLACE FUNCTION update_rl_stats_on_feedback()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE project_rl_stats
    SET 
        total_feedback_count = total_feedback_count + 1,
        average_rating = (average_rating * total_feedback_count + NEW.rating) / 
            (total_feedback_count + 1),
        updated_at = NOW()
    WHERE project_id = NEW.github_reference_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_rl_stats_on_feedback ON user_feedback;
CREATE TRIGGER trigger_update_rl_stats_on_feedback
    AFTER INSERT ON user_feedback
    FOR EACH ROW
    WHERE NEW.rating IS NOT NULL
    EXECUTE FUNCTION update_rl_stats_on_feedback();

-- ============================================================================
-- INITIAL DATA SEEDING
-- ============================================================================

-- Seed RL stats for existing projects with interaction data
-- This gives the RL system a starting point
INSERT INTO project_rl_stats (project_id, alpha, beta, total_samples, estimated_quality)
SELECT 
    gr.id as project_id,
    2.0 + COUNT(*) FILTER (WHERE ui.interaction_type IN ('click', 'bookmark_add')) as alpha,
    2.0 + COUNT(*) FILTER (WHERE ui.interaction_type IN ('quick_exit', 'bookmark_remove')) as beta,
    COUNT(*) as total_samples,
    (2.0 + COUNT(*) FILTER (WHERE ui.interaction_type IN ('click', 'bookmark_add'))) / 
        (4.0 + COUNT(*)) as estimated_quality
FROM github_references gr
LEFT JOIN user_interactions ui ON gr.id = ui.github_reference_id
WHERE ui.created_at >= NOW() - INTERVAL '30 days' OR ui.id IS NULL
GROUP BY gr.id
ON CONFLICT (project_id) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE project_rl_stats IS 'Thompson Sampling bandit parameters for each project';
COMMENT ON TABLE rl_training_history IS 'Historical record of model training runs';
COMMENT ON TABLE rl_ab_test IS 'A/B testing framework for algorithm comparison';
COMMENT ON TABLE user_ab_assignment IS 'User assignments to A/B test groups';
COMMENT ON VIEW project_rl_performance IS 'Comprehensive project performance with RL stats';
COMMENT ON VIEW rl_model_summary IS 'Overall RL model health metrics';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check that tables were created
SELECT 
    table_name, 
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
AND table_name IN ('project_rl_stats', 'rl_training_history', 'rl_ab_test', 'user_ab_assignment')
ORDER BY table_name;

-- Check RL views
SELECT 
    table_name as view_name
FROM information_schema.views
WHERE table_schema = 'public'
AND table_name IN ('project_rl_performance', 'rl_model_summary');

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ RL tables migration completed successfully!';
    RAISE NOTICE '📊 Tables created: project_rl_stats, rl_training_history, rl_ab_test, user_ab_assignment';
    RAISE NOTICE '👁️ Views created: project_rl_performance, rl_model_summary';
    RAISE NOTICE '⚡ Triggers enabled: auto_update_rl_stats, update_rl_stats_on_feedback';
END $$;