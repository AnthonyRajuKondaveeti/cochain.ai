-- Fix RLS Infinite Recursion Issue
-- ==================================
-- Fixes the infinite recursion error in project_members policy
-- and adds missing RLS policies for user_projects and user_sessions

-- ============================================================================
-- PART 1: Fix collaboration_requests infinite recursion
-- ============================================================================

-- Drop the problematic policy that causes infinite recursion
DROP POLICY IF EXISTS "Users can view their collaboration requests" ON public.collaboration_requests;

-- Create fixed policy without circular reference to project_members
-- Users can view requests where they are:
-- 1. The requester (person sending the request)
-- 2. The project owner (via project_owner_id field)
CREATE POLICY "Users can view their collaboration requests"
ON public.collaboration_requests
FOR SELECT
USING (
  auth.uid() = requester_id 
  OR auth.uid() = project_owner_id
);

-- ============================================================================
-- PART 2: Add RLS policies for user_projects table
-- ============================================================================

-- Enable RLS on user_projects (if not already enabled)
ALTER TABLE public.user_projects ENABLE ROW LEVEL SECURITY;

-- Policy: All authenticated users can view all projects
-- (Projects are meant to be discoverable for collaboration)
DROP POLICY IF EXISTS "All users can view projects" ON public.user_projects;
CREATE POLICY "All users can view projects"
ON public.user_projects
FOR SELECT
USING (auth.role() = 'authenticated');

-- Policy: Users can create their own projects
DROP POLICY IF EXISTS "Users can create their own projects" ON public.user_projects;
CREATE POLICY "Users can create their own projects"
ON public.user_projects
FOR INSERT
WITH CHECK (auth.uid() = creator_id);

-- Policy: Users can update their own projects
DROP POLICY IF EXISTS "Users can update their own projects" ON public.user_projects;
CREATE POLICY "Users can update their own projects"
ON public.user_projects
FOR UPDATE
USING (auth.uid() = creator_id)
WITH CHECK (auth.uid() = creator_id);

-- Policy: Users can delete their own projects
DROP POLICY IF EXISTS "Users can delete their own projects" ON public.user_projects;
CREATE POLICY "Users can delete their own projects"
ON public.user_projects
FOR DELETE
USING (auth.uid() = creator_id);

-- ============================================================================
-- PART 3: Add RLS policies for user_sessions table
-- ============================================================================

-- Enable RLS on user_sessions (if not already enabled)
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own sessions
DROP POLICY IF EXISTS "Users can view own sessions" ON public.user_sessions;
CREATE POLICY "Users can view own sessions"
ON public.user_sessions
FOR SELECT
USING (auth.uid() = user_id);

-- Policy: Users can insert their own sessions
-- CRITICAL: This allows auto-creation of sessions in event_tracker.py
DROP POLICY IF EXISTS "Users can insert own sessions" ON public.user_sessions;
CREATE POLICY "Users can insert own sessions"
ON public.user_sessions
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own sessions
DROP POLICY IF EXISTS "Users can update own sessions" ON public.user_sessions;
CREATE POLICY "Users can update own sessions"
ON public.user_sessions
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- PART 4: Add RLS policies for recommendation_results table
-- ============================================================================

-- Enable RLS on recommendation_results (if not already enabled)
ALTER TABLE public.recommendation_results ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own recommendation results
DROP POLICY IF EXISTS "Users can view own recommendations" ON public.recommendation_results;
CREATE POLICY "Users can view own recommendations"
ON public.recommendation_results
FOR SELECT
USING (auth.uid() = user_id);

-- Policy: Users can insert their own recommendation results
-- CRITICAL: This allows tracking of recommendation impressions
DROP POLICY IF EXISTS "Users can insert own recommendations" ON public.recommendation_results;
CREATE POLICY "Users can insert own recommendations"
ON public.recommendation_results
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- PART 5: Verification Queries
-- ============================================================================

-- Verify RLS is enabled
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename IN ('user_projects', 'user_sessions', 'collaboration_requests', 'project_members', 'recommendation_results');

-- Verify policies exist
SELECT schemaname, tablename, policyname, cmd, qual 
FROM pg_policies 
WHERE tablename IN ('user_projects', 'user_sessions', 'collaboration_requests', 'recommendation_results')
ORDER BY tablename, policyname;

-- Test queries (should work without infinite recursion)
-- Note: These use auth.uid() which will be null in SQL editor
-- Run from application context to test properly
SELECT COUNT(*) FROM public.user_projects;
SELECT COUNT(*) FROM public.user_sessions;
SELECT COUNT(*) FROM public.collaboration_requests;
SELECT COUNT(*) FROM public.recommendation_results;
