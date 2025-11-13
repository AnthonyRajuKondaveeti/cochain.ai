-- ============================================================================
-- Add RL recommendations cache column
-- ============================================================================
-- This column stores the final RL-ranked recommendations to avoid
-- regenerating them on every page load
-- ============================================================================

-- Add rl_recommendations column to user_cached_recommendations table
DO $$ 
BEGIN
    -- Check if column exists
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_cached_recommendations' 
        AND column_name = 'rl_recommendations'
    ) THEN
        -- Add the column
        ALTER TABLE user_cached_recommendations 
        ADD COLUMN rl_recommendations JSONB;
        
        RAISE NOTICE '✅ Added rl_recommendations column to user_cached_recommendations table';
    ELSE
        RAISE NOTICE 'ℹ️ Column rl_recommendations already exists in user_cached_recommendations table';
    END IF;
END $$;

-- Create index for better query performance on RL recommendations
CREATE INDEX IF NOT EXISTS idx_user_cached_recommendations_rl 
ON user_cached_recommendations(user_id) 
WHERE rl_recommendations IS NOT NULL;

-- Verify the change
DO $$
DECLARE
    column_exists BOOLEAN;
    users_with_rl_cache INTEGER;
BEGIN
    -- Check if column exists
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_cached_recommendations' 
        AND column_name = 'rl_recommendations'
    ) INTO column_exists;
    
    IF column_exists THEN
        -- Count users with RL cache
        SELECT COUNT(*) INTO users_with_rl_cache
        FROM user_cached_recommendations
        WHERE rl_recommendations IS NOT NULL;
        
        RAISE NOTICE '═══════════════════════════════════════════════════════════';
        RAISE NOTICE '✅ Migration completed successfully!';
        RAISE NOTICE '═══════════════════════════════════════════════════════════';
        RAISE NOTICE 'Column rl_recommendations exists: ✓';
        RAISE NOTICE 'Users with RL cache: %', users_with_rl_cache;
        RAISE NOTICE '═══════════════════════════════════════════════════════════';
        RAISE NOTICE '';
        RAISE NOTICE '📝 Note: RL recommendations will be cached on next page load';
        RAISE NOTICE '   This will significantly improve dashboard performance!';
        RAISE NOTICE '';
    ELSE
        RAISE WARNING '⚠️ Migration failed: column was not created';
    END IF;
END $$;
