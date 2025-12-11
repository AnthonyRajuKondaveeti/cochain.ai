-- ============================================================================
-- Phase 3 Schema Verification Script
-- ============================================================================
-- Run this to verify all Phase 3 tables and columns are ready
-- ============================================================================

-- Print header
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE '🔍 Phase 3 Schema Verification';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 1. CHECK CORE TABLES
-- ============================================================================

DO $$
DECLARE
    table_count INTEGER;
    required_tables TEXT[] := ARRAY[
        'users',
        'user_profiles',
        'github_references',
        'github_embeddings',
        'user_interactions',
        'user_feedback',
        'recommendation_results',
        'user_sessions',
        'user_bookmarks',
        'user_cached_recommendations'
    ];
    missing_tables TEXT := '';
    tbl_name TEXT;
BEGIN
    RAISE NOTICE '1️⃣ Checking Core Tables...';
    RAISE NOTICE '─────────────────────────────────────────────────────────';
    
    FOREACH tbl_name IN ARRAY required_tables
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl_name) THEN
            RAISE NOTICE '   ✅ %', tbl_name;
        ELSE
            missing_tables := missing_tables || '   ❌ ' || tbl_name || '
';
        END IF;
    END LOOP;
    
    IF missing_tables != '' THEN
        RAISE WARNING '
Missing core tables:
%', missing_tables;
    END IF;
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 2. CHECK PHASE 3 PREREQUISITE UPDATES
-- ============================================================================

DO $$
DECLARE
    missing_items TEXT := '';
BEGIN
    RAISE NOTICE '2️⃣ Checking Phase 3 Prerequisite Updates...';
    RAISE NOTICE '─────────────────────────────────────────────────────────';
    
    -- Check recommendation_results columns
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'recommendation_results' AND column_name = 'rl_score') THEN
        RAISE NOTICE '   ✅ recommendation_results.rl_score';
    ELSE
        missing_items := missing_items || '   ❌ recommendation_results.rl_score
';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'recommendation_results' AND column_name = 'recommendation_method') THEN
        RAISE NOTICE '   ✅ recommendation_results.recommendation_method';
    ELSE
        missing_items := missing_items || '   ❌ recommendation_results.recommendation_method
';
    END IF;
    
    -- Check user_interactions columns
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_interactions' AND column_name = 'duration_seconds') THEN
        RAISE NOTICE '   ✅ user_interactions.duration_seconds';
    ELSE
        missing_items := missing_items || '   ❌ user_interactions.duration_seconds
';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_interactions' AND column_name = 'session_id') THEN
        RAISE NOTICE '   ✅ user_interactions.session_id';
    ELSE
        missing_items := missing_items || '   ❌ user_interactions.session_id
';
    END IF;
    
    -- Check new tables
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_events') THEN
        RAISE NOTICE '   ✅ user_events table';
    ELSE
        missing_items := missing_items || '   ❌ user_events table
';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'analytics_cache') THEN
        RAISE NOTICE '   ✅ analytics_cache table';
    ELSE
        missing_items := missing_items || '   ❌ analytics_cache table
';
    END IF;
    
    IF missing_items != '' THEN
        RAISE WARNING '
Missing prerequisites:
%
Run phase3_prerequisites.sql!', missing_items;
    END IF;
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 3. CHECK RL TABLES
-- ============================================================================

DO $$
DECLARE
    rl_tables TEXT[] := ARRAY[
        'project_rl_stats',
        'rl_training_history',
        'rl_ab_test',
        'user_ab_assignment'
    ];
    missing_tables TEXT := '';
    tbl_name TEXT;
BEGIN
    RAISE NOTICE '3️⃣ Checking RL Tables...';
    RAISE NOTICE '─────────────────────────────────────────────────────────';
    
    FOREACH tbl_name IN ARRAY rl_tables
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl_name) THEN
            RAISE NOTICE '   ✅ %', tbl_name;
        ELSE
            missing_tables := missing_tables || '   ❌ ' || tbl_name || '
';
        END IF;
    END LOOP;
    
    IF missing_tables != '' THEN
        RAISE WARNING '
Missing RL tables:
%
Run add_rl_tables.sql!', missing_tables;
    END IF;
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 4. CHECK INDEXES
-- ============================================================================

DO $$
DECLARE
    critical_indexes TEXT[] := ARRAY[
        'idx_user_interactions_session',
        'idx_user_interactions_time',
        'idx_recommendation_results_method',
        'idx_user_cached_recommendations_user',
        'idx_project_rl_stats_quality',
        'idx_user_events_user',
        'idx_analytics_cache_key'
    ];
    missing_indexes TEXT := '';
    idx_name TEXT;
BEGIN
    RAISE NOTICE '4️⃣ Checking Critical Indexes...';
    RAISE NOTICE '─────────────────────────────────────────────────────────';
    
    FOREACH idx_name IN ARRAY critical_indexes
    LOOP
        IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = idx_name) THEN
            RAISE NOTICE '   ✅ %', idx_name;
        ELSE
            missing_indexes := missing_indexes || '   ❌ ' || idx_name || '
';
        END IF;
    END LOOP;
    
    IF missing_indexes != '' THEN
        RAISE WARNING '
Missing indexes:
%', missing_indexes;
    END IF;
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 5. CHECK VIEWS
-- ============================================================================

DO $$
DECLARE
    required_views TEXT[] := ARRAY[
        'user_engagement_summary',
        'github_ctr_stats',
        'project_rl_performance',
        'rl_model_summary'
    ];
    missing_views TEXT := '';
    vw_name TEXT;
BEGIN
    RAISE NOTICE '5️⃣ Checking Views...';
    RAISE NOTICE '─────────────────────────────────────────────────────────';
    
    FOREACH vw_name IN ARRAY required_views
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'public' AND table_name = vw_name) THEN
            RAISE NOTICE '   ✅ %', vw_name;
        ELSE
            missing_views := missing_views || '   ❌ ' || vw_name || '
';
        END IF;
    END LOOP;
    
    IF missing_views != '' THEN
        RAISE WARNING '
Missing views:
%', missing_views;
    END IF;
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 6. CHECK FUNCTIONS
-- ============================================================================

DO $$
DECLARE
    required_functions TEXT[] := ARRAY[
        'update_project_rl_stats',
        'increment_project_impression',
        'increment_project_click',
        'clean_expired_cache'
    ];
    missing_functions TEXT := '';
    func_name TEXT;
BEGIN
    RAISE NOTICE '6️⃣ Checking Functions...';
    RAISE NOTICE '─────────────────────────────────────────────────────────';
    
    FOREACH func_name IN ARRAY required_functions
    LOOP
        IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = func_name) THEN
            RAISE NOTICE '   ✅ %', func_name;
        ELSE
            missing_functions := missing_functions || '   ❌ ' || func_name || '
';
        END IF;
    END LOOP;
    
    IF missing_functions != '' THEN
        RAISE WARNING '
Missing functions:
%', missing_functions;
    END IF;
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 7. CHECK TRIGGERS
-- ============================================================================

DO $$
DECLARE
    required_triggers TEXT[] := ARRAY[
        'trigger_auto_update_rl_stats',
        'trigger_update_rl_stats_on_feedback'
    ];
    missing_triggers TEXT := '';
    trig_name TEXT;
BEGIN
    RAISE NOTICE '7️⃣ Checking Triggers...';
    RAISE NOTICE '─────────────────────────────────────────────────────────';
    
    FOREACH trig_name IN ARRAY required_triggers
    LOOP
        IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = trig_name) THEN
            RAISE NOTICE '   ✅ %', trig_name;
        ELSE
            missing_triggers := missing_triggers || '   ❌ ' || trig_name || '
';
        END IF;
    END LOOP;
    
    IF missing_triggers != '' THEN
        RAISE WARNING '
Missing triggers:
%', missing_triggers;
    END IF;
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 8. DATA VERIFICATION
-- ============================================================================

DO $$
DECLARE
    user_count INTEGER;
    project_count INTEGER;
    interaction_count INTEGER;
BEGIN
    RAISE NOTICE '8️⃣ Checking Data...';
    RAISE NOTICE '─────────────────────────────────────────────────────────';
    
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO project_count FROM github_references;
    SELECT COUNT(*) INTO interaction_count FROM user_interactions;
    
    RAISE NOTICE '   📊 Users: %', user_count;
    RAISE NOTICE '   📊 GitHub Projects: %', project_count;
    RAISE NOTICE '   📊 User Interactions: %', interaction_count;
    
    IF user_count = 0 THEN
        RAISE WARNING '   ⚠️ No users in database!';
    END IF;
    
    IF project_count = 0 THEN
        RAISE WARNING '   ⚠️ No GitHub projects in database!';
    END IF;
    
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 9. GENERATE SUMMARY
-- ============================================================================

DO $$
DECLARE
    total_tables INTEGER;
    rl_tables INTEGER;
    total_indexes INTEGER;
    total_views INTEGER;
    total_functions INTEGER;
    readiness_score FLOAT;
BEGIN
    RAISE NOTICE '9️⃣ Summary';
    RAISE NOTICE '─────────────────────────────────────────────────────────';
    
    -- Count tables
    SELECT COUNT(*) INTO total_tables 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    
    SELECT COUNT(*) INTO rl_tables 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN ('project_rl_stats', 'rl_training_history', 'rl_ab_test', 'user_ab_assignment');
    
    -- Count indexes
    SELECT COUNT(*) INTO total_indexes 
    FROM pg_indexes 
    WHERE schemaname = 'public';
    
    -- Count views
    SELECT COUNT(*) INTO total_views 
    FROM information_schema.views 
    WHERE table_schema = 'public';
    
    -- Count functions
    SELECT COUNT(*) INTO total_functions 
    FROM pg_proc 
    WHERE pronamespace = 'public'::regnamespace;
    
    RAISE NOTICE '   Total Tables: %', total_tables;
    RAISE NOTICE '   RL Tables: %/4', rl_tables;
    RAISE NOTICE '   Total Indexes: %', total_indexes;
    RAISE NOTICE '   Total Views: %', total_views;
    RAISE NOTICE '   Total Functions: %', total_functions;
    RAISE NOTICE '';
    
    -- Calculate readiness
    IF rl_tables = 4 THEN
        RAISE NOTICE '   🎯 Phase 3 Readiness: 100%% - READY TO GO! 🚀';
    ELSIF rl_tables > 0 THEN
        readiness_score := (rl_tables::FLOAT / 4) * 100;
        RAISE NOTICE '   🎯 Phase 3 Readiness: %%% - Almost there!', ROUND(readiness_score);
    ELSE
        RAISE NOTICE '   🎯 Phase 3 Readiness: 0%% - Run migrations!';
    END IF;
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 10. RECOMMENDATIONS
-- ============================================================================

DO $$
DECLARE
    has_prerequisites BOOLEAN;
    has_rl_tables BOOLEAN;
    recommendations TEXT := '';
BEGIN
    RAISE NOTICE '🔧 Recommendations';
    RAISE NOTICE '─────────────────────────────────────────────────────────';
    
    -- Check prerequisites
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'recommendation_results' AND column_name = 'rl_score'
    ) INTO has_prerequisites;
    
    -- Check RL tables
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'project_rl_stats'
    ) INTO has_rl_tables;
    
    IF NOT has_prerequisites THEN
        recommendations := recommendations || '   1. Run: phase3_prerequisites.sql
';
    END IF;
    
    IF NOT has_rl_tables THEN
        recommendations := recommendations || '   2. Run: add_rl_tables.sql
';
    END IF;
    
    IF recommendations = '' THEN
        RAISE NOTICE '   ✅ All migrations complete!';
        RAISE NOTICE '   ✅ Schema is ready for Phase 3!';
        RAISE NOTICE '';
        RAISE NOTICE '   Next steps:';
        RAISE NOTICE '   1. Copy Phase 3 service files';
        RAISE NOTICE '   2. Install dependencies: pip install APScheduler';
        RAISE NOTICE '   3. Update app.py with RL integration';
        RAISE NOTICE '   4. Start application and test!';
    ELSE
        RAISE NOTICE '   Run these migrations in order:
%', recommendations;
    END IF;
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- FOOTER
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE '✅ Verification Complete!';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE '';
END $$;