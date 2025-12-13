-- Remove pre-training columns and improvement columns from rl_training_history
-- Improvement is now calculated dynamically by comparing consecutive training sessions

-- These columns will be dropped:
-- pre_avg_reward, pre_positive_rate, pre_avg_ctr (redundant - always same as historical data)
-- reward_improvement, ctr_improvement (now calculated in API)

ALTER TABLE rl_training_history 
  DROP COLUMN IF EXISTS pre_avg_reward,
  DROP COLUMN IF EXISTS pre_positive_rate,
  DROP COLUMN IF EXISTS pre_avg_ctr,
  DROP COLUMN IF EXISTS reward_improvement,
  DROP COLUMN IF EXISTS ctr_improvement;

-- Verify remaining columns
\d rl_training_history;
