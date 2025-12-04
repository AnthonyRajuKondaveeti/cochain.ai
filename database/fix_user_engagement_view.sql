-- Fix user_engagement_summary view to count clicks from user_interactions table
-- Drop the existing view if it exists
DROP VIEW IF EXISTS user_engagement_summary;

-- Recreate the view with proper click counting
CREATE OR REPLACE VIEW user_engagement_summary AS
SELECT 
    u.id AS user_id,
    u.email,
    u.full_name,
    
    -- Session metrics
    COALESCE(COUNT(DISTINCT s.id), 0) AS total_sessions,
    COALESCE(SUM(s.total_minutes), 0) AS total_minutes_on_platform,
    
    -- GitHub activity metrics (from sessions)
    COALESCE(SUM(s.github_recommendations_viewed), 0) AS github_views,
    
    -- GitHub clicks (from user_interactions table, not sessions)
    COALESCE((
        SELECT COUNT(*) 
        FROM user_interactions ui 
        WHERE ui.user_id = u.id 
        AND ui.interaction_type = 'click'
    ), 0) AS github_clicks,
    
    -- Live projects activity
    COALESCE(SUM(s.live_projects_viewed), 0) AS live_project_views,
    COALESCE(SUM(s.collaboration_requests_sent), 0) AS collab_requests_sent,
    
    -- Projects created and joined
    COALESCE((
        SELECT COUNT(*) 
        FROM user_projects up 
        WHERE up.creator_id = u.id
    ), 0) AS projects_created,
    
    COALESCE((
        SELECT COUNT(*) 
        FROM project_members pm 
        WHERE pm.user_id = u.id
    ), 0) AS projects_joined

FROM users u
LEFT JOIN user_sessions s ON u.id = s.user_id
GROUP BY u.id, u.email, u.full_name;

-- Grant access to the view
GRANT SELECT ON user_engagement_summary TO authenticated;
GRANT SELECT ON user_engagement_summary TO anon;
