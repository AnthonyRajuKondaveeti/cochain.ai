-- Fix Additional Security Issues
-- ================================
-- This script addresses:
-- 1. Functions with mutable search_path (security risk)
-- 2. Vector extension in public schema (should be in extensions schema)
--
-- NOTE: Run this script after fix_rls_security_issues.sql

-- ============================================================================
-- PART 1: Fix Functions with Mutable Search Path
-- ============================================================================
-- Setting search_path on functions prevents search path injection attacks

-- 1. update_updated_at_column
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- 2. increment_project_impression
CREATE OR REPLACE FUNCTION public.increment_project_impression(p_project_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    INSERT INTO project_rl_stats (project_id, total_impressions)
    VALUES (p_project_id, 1)
    ON CONFLICT (project_id) DO UPDATE SET
        total_impressions = project_rl_stats.total_impressions + 1,
        updated_at = NOW();
END;
$$;

-- 3. auto_update_rl_stats
CREATE OR REPLACE FUNCTION public.auto_update_rl_stats()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
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
$$;

-- 4. clean_expired_cache
CREATE OR REPLACE FUNCTION public.clean_expired_cache()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM analytics_cache 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- 5. increment_cache_hit
CREATE OR REPLACE FUNCTION public.increment_cache_hit(p_cache_key VARCHAR)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    UPDATE analytics_cache 
    SET hits = hits + 1
    WHERE cache_key = p_cache_key;
END;
$$;

-- 6. update_rl_stats_on_feedback
CREATE OR REPLACE FUNCTION public.update_rl_stats_on_feedback()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
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
$$;

-- 7. update_project_rl_stats
CREATE OR REPLACE FUNCTION public.update_project_rl_stats(
    p_project_id UUID,
    p_alpha_delta FLOAT,
    p_beta_delta FLOAT,
    p_reward FLOAT
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
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
$$;

-- 8. increment_project_click
CREATE OR REPLACE FUNCTION public.increment_project_click(p_project_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    UPDATE project_rl_stats 
    SET 
        total_clicks = total_clicks + 1,
        updated_at = NOW()
    WHERE project_id = p_project_id;
END;
$$;

-- ============================================================================
-- PART 2: Move Vector Extension to Extensions Schema
-- ============================================================================
-- NOTE: This requires superuser/admin privileges and may need to be done
-- through Supabase dashboard or support team

-- Step 1: Create extensions schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS extensions;

-- Step 2: Move vector extension (THIS MAY REQUIRE SUPABASE SUPPORT)
-- You cannot directly move an extension in PostgreSQL
-- Instead, you need to:
-- 1. Drop the extension from public schema
-- 2. Reinstall in extensions schema
-- 
-- However, this will break existing vector columns!
-- Safer approach: Contact Supabase support or use Supabase CLI
--
-- Alternative: Set search_path to include extensions schema
ALTER DATABASE postgres SET search_path TO public, extensions;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check functions with search_path set
SELECT 
    n.nspname as schema_name,
    p.proname as function_name,
    pg_get_function_arguments(p.oid) as arguments,
    CASE 
        WHEN p.proconfig IS NULL THEN 'NO SEARCH_PATH SET'
        ELSE array_to_string(p.proconfig, ', ')
    END as configuration
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
    AND p.proname IN (
        'update_updated_at_column',
        'increment_project_impression',
        'auto_update_rl_stats',
        'clean_expired_cache',
        'increment_cache_hit',
        'update_rl_stats_on_feedback',
        'update_project_rl_stats',
        'increment_project_click'
    )
ORDER BY p.proname;

-- Check extension location
SELECT 
    e.extname as extension_name,
    n.nspname as schema_name
FROM pg_extension e
JOIN pg_namespace n ON e.extnamespace = n.oid
WHERE e.extname = 'vector';

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. All functions now have 'SET search_path = public, pg_temp' to prevent
--    search path injection attacks
--
-- 2. Functions are SECURITY DEFINER, meaning they run with the privileges
--    of the function creator (necessary for RLS-protected tables)
--
-- 3. Vector extension migration:
--    - Moving the vector extension requires dropping and recreating it
--    - This will break all existing vector columns
--    - RECOMMENDED: Leave as-is or contact Supabase support
--    - Alternative: Ensure search_path includes extensions schema
--
-- 4. HaveIBeenPwned (HIBP) password checking:
--    - This must be enabled through Supabase Dashboard
--    - Go to: Authentication > Settings > Password Policy
--    - Enable "Check passwords against HaveIBeenPwned"
--    - Cannot be set via SQL
--
-- 5. Test all functions after applying these changes to ensure they work
--    correctly with the new search_path settings
