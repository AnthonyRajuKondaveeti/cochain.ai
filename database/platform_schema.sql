-- ============================================================================
-- CoChain.ai - Complete Platform Schema
-- ============================================================================
-- Purpose: GitHub inspiration + User collaboration + Comprehensive analytics
-- Two Systems: 
--   1. GitHub Projects (Inspiration/Reference)
--   2. Live Projects (User Collaboration)
-- Total Tables: 18
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- SECTION 1: GITHUB PROJECTS (Inspiration System)
-- ============================================================================

-- Table 1: GitHub projects for inspiration/reference
CREATE TABLE github_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    domain TEXT,
    required_skills JSONB,
    complexity_level TEXT,
    team_size INTEGER,
    estimated_timeline TEXT,
    repository_url TEXT,
    stars INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table 2: GitHub project embeddings for semantic search
CREATE TABLE github_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id UUID REFERENCES github_references(id) ON DELETE CASCADE,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_github_references_domain ON github_references(domain);
CREATE INDEX idx_github_references_complexity ON github_references(complexity_level);
CREATE INDEX idx_github_references_stars ON github_references(stars DESC);
CREATE INDEX idx_github_embedding ON github_embeddings USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- SECTION 2: USER MANAGEMENT
-- ============================================================================

-- Table 3: User authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Table 4: User profiles (UPDATED - removed team preferences, added bio)
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    
    -- Education & Background
    education_level VARCHAR(50),
    current_year VARCHAR(50),
    field_of_study TEXT,
    
    -- Career & Bio (NEW)
    bio TEXT,
    
    -- Skills & Interests
    programming_languages JSONB,
    frameworks_known JSONB,
    areas_of_interest JSONB,
    overall_skill_level VARCHAR(50) DEFAULT 'intermediate',
    
    -- Learning Goals
    learning_goals TEXT,
    
    -- Profile completion
    profile_completed BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table 5: User bookmarks (for GitHub projects)
CREATE TABLE user_bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    github_reference_id UUID REFERENCES github_references(id) ON DELETE CASCADE,
    notes TEXT,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, github_reference_id)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_user_profiles_user ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_interests ON user_profiles USING GIN(areas_of_interest);
CREATE INDEX idx_user_profiles_languages ON user_profiles USING GIN(programming_languages);
CREATE INDEX idx_user_bookmarks_user ON user_bookmarks(user_id);

-- ============================================================================
-- SECTION 3: LIVE PROJECTS (User Collaboration System)
-- ============================================================================

-- Table 6: User-created projects seeking collaboration
CREATE TABLE user_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Project Details
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    detailed_requirements TEXT,
    project_goals TEXT,
    
    -- Technical Details
    tech_stack JSONB,
    required_skills JSONB,
    complexity_level VARCHAR(50) DEFAULT 'intermediate',
    estimated_duration VARCHAR(100),
    domain VARCHAR(100),
    
    -- Collaboration Settings
    is_open_for_collaboration BOOLEAN DEFAULT TRUE,
    max_collaborators INTEGER DEFAULT 5,
    current_collaborators INTEGER DEFAULT 1,
    needed_roles JSONB,
    
    -- Project Status
    status VARCHAR(50) DEFAULT 'planning',
    start_date DATE,
    target_completion_date DATE,
    
    -- Visibility
    is_public BOOLEAN DEFAULT TRUE,
    view_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table 7: User project embeddings for semantic matching
CREATE TABLE user_project_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES user_projects(id) ON DELETE CASCADE,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table 8: Collaboration requests
CREATE TABLE collaboration_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES user_projects(id) ON DELETE CASCADE,
    requester_id UUID REFERENCES users(id) ON DELETE CASCADE,
    project_owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Request Details
    requested_role VARCHAR(100),
    cover_message TEXT,
    why_interested TEXT,
    relevant_experience TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    response_message TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    responded_at TIMESTAMP
);

-- Table 9: Project team members
CREATE TABLE project_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES user_projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    role VARCHAR(100),
    joined_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE(project_id, user_id)
);

-- Table 10: User compatibility scores (for smart matching)
CREATE TABLE user_compatibility_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id UUID REFERENCES users(id) ON DELETE CASCADE,
    user2_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    skill_match_score FLOAT,
    interest_match_score FLOAT,
    overall_score FLOAT,
    
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user1_id, user2_id)
);

-- Table 11: Project views tracking
CREATE TABLE project_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES user_projects(id) ON DELETE CASCADE,
    viewer_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    view_duration_seconds INTEGER DEFAULT 0,
    viewed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_projects_creator ON user_projects(creator_id);
CREATE INDEX idx_user_projects_open ON user_projects(is_open_for_collaboration);
CREATE INDEX idx_user_projects_status ON user_projects(status);
CREATE INDEX idx_user_projects_domain ON user_projects(domain);
CREATE INDEX idx_user_project_embeddings ON user_project_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_collaboration_requests_project ON collaboration_requests(project_id);
CREATE INDEX idx_collaboration_requests_requester ON collaboration_requests(requester_id);
CREATE INDEX idx_collaboration_requests_status ON collaboration_requests(status);
CREATE INDEX idx_project_members_project ON project_members(project_id);
CREATE INDEX idx_project_members_user ON project_members(user_id);
CREATE INDEX idx_project_views_project ON project_views(project_id);
CREATE INDEX idx_project_views_viewer ON project_views(viewer_id);

-- ============================================================================
-- SECTION 4: GITHUB RECOMMENDATION ANALYTICS
-- ============================================================================

-- Table 12: User queries for GitHub recommendations
CREATE TABLE user_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    project_idea TEXT NOT NULL,
    objectives TEXT,
    achievements TEXT,
    existing_skills TEXT,
    want_to_learn TEXT,
    complexity_level INTEGER DEFAULT 2,
    num_recommendations INTEGER DEFAULT 10,
    query_text TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table 13: User query embeddings
CREATE TABLE user_query_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_query_id UUID REFERENCES user_queries(id) ON DELETE CASCADE,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table 14: GitHub recommendation results
CREATE TABLE recommendation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_query_id UUID REFERENCES user_queries(id) ON DELETE CASCADE,
    github_reference_id UUID REFERENCES github_references(id) ON DELETE CASCADE,
    
    similarity_score FLOAT,
    rank_position INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table 15: User interactions with GitHub recommendations
CREATE TABLE user_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_query_id UUID REFERENCES user_queries(id) ON DELETE CASCADE,
    github_reference_id UUID REFERENCES github_references(id) ON DELETE CASCADE,
    recommendation_result_id UUID REFERENCES recommendation_results(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    interaction_type VARCHAR(50) NOT NULL,
    rank_position INTEGER,
    similarity_score FLOAT,
    session_id VARCHAR(255),
    duration_seconds INTEGER DEFAULT 0,
    
    interaction_time TIMESTAMP DEFAULT NOW(),
    user_agent TEXT,
    additional_data JSONB
);

-- Table 16: User feedback on GitHub recommendations
CREATE TABLE user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_query_id UUID REFERENCES user_queries(id) ON DELETE CASCADE,
    github_reference_id UUID REFERENCES github_references(id) ON DELETE CASCADE,
    recommendation_result_id UUID REFERENCES recommendation_results(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    is_relevant BOOLEAN,
    is_helpful BOOLEAN,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_queries_user ON user_queries(user_id, created_at);
CREATE INDEX idx_user_query_embeddings_query ON user_query_embeddings(user_query_id);
CREATE INDEX idx_recommendation_results_query ON recommendation_results(user_query_id);
CREATE INDEX idx_user_interactions_query ON user_interactions(user_query_id);
CREATE INDEX idx_user_interactions_type ON user_interactions(interaction_type);
CREATE INDEX idx_user_feedback_rating ON user_feedback(rating);

-- ============================================================================
-- SECTION 5: SESSION & ENGAGEMENT TRACKING
-- ============================================================================

-- Table 17: User sessions (for both GitHub and Live Projects)
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    
    login_time TIMESTAMP DEFAULT NOW(),
    logout_time TIMESTAMP,
    last_activity TIMESTAMP DEFAULT NOW(),
    total_minutes INTEGER,
    
    -- GitHub activity
    github_recommendations_viewed INTEGER DEFAULT 0,
    github_projects_clicked INTEGER DEFAULT 0,
    
    -- Live projects activity
    live_projects_viewed INTEGER DEFAULT 0,
    collaboration_requests_sent INTEGER DEFAULT 0,
    
    pages_visited INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table 18: Collaboration analytics (track success of matches)
CREATE TABLE collaboration_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Match details
    project_id UUID REFERENCES user_projects(id) ON DELETE CASCADE,
    matched_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- How they found it
    discovery_method VARCHAR(50),
    similarity_score FLOAT,
    compatibility_score FLOAT,
    
    -- Outcome tracking
    viewed BOOLEAN DEFAULT FALSE,
    request_sent BOOLEAN DEFAULT FALSE,
    request_accepted BOOLEAN DEFAULT FALSE,
    collaboration_started BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    shown_at TIMESTAMP DEFAULT NOW(),
    viewed_at TIMESTAMP,
    request_sent_at TIMESTAMP,
    accepted_at TIMESTAMP
);

CREATE INDEX idx_user_sessions_user ON user_sessions(user_id, created_at);
CREATE INDEX idx_user_sessions_id ON user_sessions(session_id);
CREATE INDEX idx_collaboration_analytics_project ON collaboration_analytics(project_id);
CREATE INDEX idx_collaboration_analytics_user ON collaboration_analytics(matched_user_id);

-- ============================================================================
-- ANALYTICS VIEWS
-- ============================================================================

-- View 1: GitHub recommendation CTR
CREATE OR REPLACE VIEW github_ctr_stats AS
SELECT 
    u.id as user_id,
    u.email,
    COUNT(DISTINCT rr.id) as total_github_recommendations,
    COUNT(DISTINCT CASE WHEN ui.interaction_type = 'click' THEN ui.id END) as github_clicks,
    ROUND(
        COUNT(DISTINCT CASE WHEN ui.interaction_type = 'click' THEN ui.id END)::NUMERIC / 
        NULLIF(COUNT(DISTINCT rr.id), 0) * 100, 2
    ) as github_ctr
FROM users u
LEFT JOIN user_queries uq ON u.id = uq.user_id
LEFT JOIN recommendation_results rr ON uq.id = rr.user_query_id
LEFT JOIN user_interactions ui ON rr.id = ui.recommendation_result_id
GROUP BY u.id, u.email;

-- View 2: Live project engagement
CREATE OR REPLACE VIEW live_project_engagement AS
SELECT 
    up.id as project_id,
    up.title,
    up.creator_id,
    u.full_name as creator_name,
    up.view_count,
    COUNT(DISTINCT pv.viewer_id) as unique_viewers,
    COUNT(DISTINCT cr.requester_id) as collaboration_requests,
    COUNT(DISTINCT pm.user_id) as current_members,
    up.status
FROM user_projects up
JOIN users u ON up.creator_id = u.id
LEFT JOIN project_views pv ON up.id = pv.project_id
LEFT JOIN collaboration_requests cr ON up.id = cr.project_id
LEFT JOIN project_members pm ON up.id = pm.project_id AND pm.is_active = true
GROUP BY up.id, up.title, up.creator_id, u.full_name, up.view_count, up.status;

-- View 3: User engagement summary
CREATE OR REPLACE VIEW user_engagement_summary AS
SELECT 
    u.id as user_id,
    u.email,
    u.full_name,
    COUNT(DISTINCT us.id) as total_sessions,
    COALESCE(SUM(us.total_minutes), 0) as total_minutes_on_platform,
    COALESCE(SUM(us.github_recommendations_viewed), 0) as github_views,
    COALESCE(SUM(us.github_projects_clicked), 0) as github_clicks,
    COALESCE(SUM(us.live_projects_viewed), 0) as live_project_views,
    COALESCE(SUM(us.collaboration_requests_sent), 0) as collab_requests_sent,
    COUNT(DISTINCT up.id) as projects_created,
    COUNT(DISTINCT pm.project_id) as projects_joined
FROM users u
LEFT JOIN user_sessions us ON u.id = us.user_id
LEFT JOIN user_projects up ON u.id = up.creator_id
LEFT JOIN project_members pm ON u.id = pm.user_id AND pm.is_active = true
GROUP BY u.id, u.email, u.full_name;

-- View 4: Collaboration success rate
CREATE OR REPLACE VIEW collaboration_success_metrics AS
SELECT 
    DATE_TRUNC('day', ca.shown_at) as date,
    COUNT(*) as recommendations_shown,
    COUNT(*) FILTER (WHERE ca.viewed = true) as viewed,
    COUNT(*) FILTER (WHERE ca.request_sent = true) as requests_sent,
    COUNT(*) FILTER (WHERE ca.request_accepted = true) as requests_accepted,
    COUNT(*) FILTER (WHERE ca.collaboration_started = true) as collaborations_started,
    ROUND(COUNT(*) FILTER (WHERE ca.viewed = true)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) as view_rate,
    ROUND(COUNT(*) FILTER (WHERE ca.request_sent = true)::NUMERIC / NULLIF(COUNT(*) FILTER (WHERE ca.viewed = true), 0) * 100, 2) as request_rate,
    ROUND(COUNT(*) FILTER (WHERE ca.request_accepted = true)::NUMERIC / NULLIF(COUNT(*) FILTER (WHERE ca.request_sent = true), 0) * 100, 2) as acceptance_rate
FROM collaboration_analytics ca
WHERE ca.shown_at >= NOW() - INTERVAL '90 days'
GROUP BY DATE_TRUNC('day', ca.shown_at)
ORDER BY date DESC;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE github_references IS 'GitHub projects for inspiration only';
COMMENT ON TABLE user_projects IS 'User-created projects seeking collaboration';
COMMENT ON TABLE collaboration_requests IS 'Requests to join user projects';
COMMENT ON TABLE collaboration_analytics IS 'Track recommendation → collaboration conversion';
COMMENT ON TABLE user_sessions IS 'Session tracking for both GitHub and Live Projects';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================