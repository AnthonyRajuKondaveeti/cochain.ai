-- Add cached recommendations table for performance
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS user_cached_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    recommendations JSONB NOT NULL,
    profile_hash TEXT NOT NULL, -- Hash of user profile to detect changes
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_cached_recommendations_user_id ON user_cached_recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_cached_recommendations_updated ON user_cached_recommendations(updated_at DESC);

-- Add RLS policy for cached recommendations
CREATE POLICY "Users can manage their own cached recommendations" ON user_cached_recommendations
FOR ALL 
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());