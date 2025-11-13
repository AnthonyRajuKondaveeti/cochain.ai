-- ============================================================================
-- Add profile_completed column to users table
-- ============================================================================
-- This column is needed for the login redirect logic to work properly
-- Without it, users are always redirected to profile_setup after login
-- ============================================================================

-- Add profile_completed column to users table if it doesn't exist
DO $$ 
BEGIN
    -- Check if column exists
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'profile_completed'
    ) THEN
        -- Add the column
        ALTER TABLE users ADD COLUMN profile_completed BOOLEAN DEFAULT FALSE;
        
        RAISE NOTICE '✅ Added profile_completed column to users table';
        
        -- Update existing users who have completed profiles
        -- (users who have entries in user_profiles table)
        UPDATE users u
        SET profile_completed = TRUE
        FROM user_profiles up
        WHERE u.id = up.user_id 
        AND up.profile_completed = TRUE;
        
        RAISE NOTICE '✅ Updated existing users with completed profiles';
    ELSE
        RAISE NOTICE 'ℹ️ Column profile_completed already exists in users table';
    END IF;
END $$;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_users_profile_completed ON users(profile_completed);

-- Verify the change
DO $$
DECLARE
    column_exists BOOLEAN;
    users_with_completed_profiles INTEGER;
BEGIN
    -- Check if column exists
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'profile_completed'
    ) INTO column_exists;
    
    IF column_exists THEN
        -- Count users with completed profiles
        SELECT COUNT(*) INTO users_with_completed_profiles
        FROM users
        WHERE profile_completed = TRUE;
        
        RAISE NOTICE '═══════════════════════════════════════════════════════════';
        RAISE NOTICE '✅ Migration completed successfully!';
        RAISE NOTICE '═══════════════════════════════════════════════════════════';
        RAISE NOTICE 'Column profile_completed exists in users table: ✓';
        RAISE NOTICE 'Users with completed profiles: %', users_with_completed_profiles;
        RAISE NOTICE '═══════════════════════════════════════════════════════════';
    ELSE
        RAISE WARNING '⚠️ Migration failed: column was not created';
    END IF;
END $$;
