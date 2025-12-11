-- Fix user_interactions table to allow NULL for user_query_id and recommendation_result_id
-- These fields are not always available when tracking interactions

-- Make user_query_id nullable
ALTER TABLE user_interactions 
ALTER COLUMN user_query_id DROP NOT NULL;

-- Make recommendation_result_id nullable  
ALTER TABLE user_interactions 
ALTER COLUMN recommendation_result_id DROP NOT NULL;

-- Add comment to clarify
COMMENT ON COLUMN user_interactions.user_query_id IS 'Optional: Only present if interaction came from a specific search query';
COMMENT ON COLUMN user_interactions.recommendation_result_id IS 'Optional: Only present if interaction is for a recommendation result';
