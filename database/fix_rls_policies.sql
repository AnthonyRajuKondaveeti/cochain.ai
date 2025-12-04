-- ============================================================================
-- FIX: Row Level Security (RLS) Policies for CoChain.ai
-- ============================================================================
-- Problem: Users can't be created because Supabase RLS blocks INSERTs
-- Solution: Add proper RLS policies to allow authenticated users to create/access their data
-- ============================================================================

-- Disable RLS temporarily to allow setup (will re-enable after adding policies)

-- ============================================================================
-- USERS TABLE POLICIES
-- ============================================================================

-- Policy 1: Allow users to insert their own profile during registration
CREATE POLICY "Allow users to create their own profile"
ON users
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = id);

-- Policy 2: Allow users to read their own data
CREATE POLICY "Allow users to read their own data"
ON users
FOR SELECT
TO authenticated
USING (auth.uid() = id);

-- Policy 3: Allow users to update their own profile
CREATE POLICY "Allow users to update their own profile"
ON users
FOR UPDATE
TO authenticated
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

-- ============================================================================
-- USER_PROFILES TABLE POLICIES
-- ============================================================================

-- Policy 4: Allow users to insert their own profile
CREATE POLICY "Allow users to create their own user_profile"
ON user_profiles
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Policy 5: Allow users to read their own profile
CREATE POLICY "Allow users to read their own user_profile"
ON user_profiles
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy 6: Allow users to update their own profile
CREATE POLICY "Allow users to update their own user_profile"
ON user_profiles
FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- USER_BOOKMARKS TABLE POLICIES
-- ============================================================================

-- Policy 7: Allow users to create their own bookmarks
CREATE POLICY "Allow users to create bookmarks"
ON user_bookmarks
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Policy 8: Allow users to read their own bookmarks
CREATE POLICY "Allow users to read their own bookmarks"
ON user_bookmarks
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy 9: Allow users to update their own bookmarks
CREATE POLICY "Allow users to update their own bookmarks"
ON user_bookmarks
FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Policy 10: Allow users to delete their own bookmarks
CREATE POLICY "Allow users to delete their own bookmarks"
ON user_bookmarks
FOR DELETE
TO authenticated
USING (auth.uid() = user_id);

-- ============================================================================
-- USER_QUERIES TABLE POLICIES
-- ============================================================================

-- Policy 11: Allow authenticated users to insert queries
CREATE POLICY "Allow users to create queries"
ON user_queries
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

-- Policy 12: Allow users to read their own queries
CREATE POLICY "Allow users to read their own queries"
ON user_queries
FOR SELECT
TO authenticated
USING (auth.uid() = user_id OR user_id IS NULL);

-- ============================================================================
-- USER_SESSIONS TABLE POLICIES
-- ============================================================================

-- Policy 13: Allow users to create their own sessions
CREATE POLICY "Allow users to create sessions"
ON user_sessions
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Policy 14: Allow users to read their own sessions
CREATE POLICY "Allow users to read their own sessions"
ON user_sessions
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy 15: Allow users to update their own sessions
CREATE POLICY "Allow users to update their own sessions"
ON user_sessions
FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- USER_INTERACTIONS TABLE POLICIES
-- ============================================================================

-- Policy 16: Allow authenticated users to create interactions
CREATE POLICY "Allow users to create interactions"
ON user_interactions
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

-- Policy 17: Allow users to read their own interactions
CREATE POLICY "Allow users to read their own interactions"
ON user_interactions
FOR SELECT
TO authenticated
USING (auth.uid() = user_id OR user_id IS NULL);

-- ============================================================================
-- GITHUB_REFERENCES TABLE POLICIES (PUBLIC READ)
-- ============================================================================

-- Policy 18: Allow everyone to read GitHub references
CREATE POLICY "Allow authenticated users to read github_references"
ON github_references
FOR SELECT
TO authenticated
USING (true);

-- ============================================================================
-- GITHUB_EMBEDDINGS TABLE POLICIES (PUBLIC READ)
-- ============================================================================

-- Policy 19: Allow everyone to read GitHub embeddings
CREATE POLICY "Allow authenticated users to read github_embeddings"
ON github_embeddings
FOR SELECT
TO authenticated
USING (true);

-- ============================================================================
-- USER_PROJECTS TABLE POLICIES
-- ============================================================================

-- Policy 20: Allow users to create their own projects
CREATE POLICY "Allow users to create projects"
ON user_projects
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = creator_id);

-- Policy 21: Allow users to read public projects or their own projects
CREATE POLICY "Allow users to read projects"
ON user_projects
FOR SELECT
TO authenticated
USING (is_public = true OR auth.uid() = creator_id);

-- Policy 22: Allow users to update their own projects
CREATE POLICY "Allow users to update their own projects"
ON user_projects
FOR UPDATE
TO authenticated
USING (auth.uid() = creator_id)
WITH CHECK (auth.uid() = creator_id);

-- Policy 23: Allow users to delete their own projects
CREATE POLICY "Allow users to delete their own projects"
ON user_projects
FOR DELETE
TO authenticated
USING (auth.uid() = creator_id);

-- ============================================================================
-- RECOMMENDATION_RESULTS TABLE POLICIES
-- ============================================================================

-- Policy 24: Allow system to insert recommendation results
CREATE POLICY "Allow authenticated users to create recommendation_results"
ON recommendation_results
FOR INSERT
TO authenticated
WITH CHECK (true);

-- Policy 25: Allow users to read recommendation results
CREATE POLICY "Allow users to read recommendation_results"
ON recommendation_results
FOR SELECT
TO authenticated
USING (true);

-- ============================================================================
-- USER_FEEDBACK TABLE POLICIES
-- ============================================================================

-- Policy 26: Allow users to create feedback
CREATE POLICY "Allow users to create feedback"
ON user_feedback
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

-- Policy 27: Allow users to read their own feedback
CREATE POLICY "Allow users to read their own feedback"
ON user_feedback
FOR SELECT
TO authenticated
USING (auth.uid() = user_id OR user_id IS NULL);

-- ============================================================================
-- Enable RLS on all tables
-- ============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_bookmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE github_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE github_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check which policies exist
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Check RLS status
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
