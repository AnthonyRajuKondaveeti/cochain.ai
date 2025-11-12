-- A/B Testing Schema for RL Recommendations
-- Run this in your Supabase SQL editor

-- Table: ab_test_configs
-- Stores configuration for each A/B test
CREATE TABLE IF NOT EXISTS ab_test_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_name VARCHAR(255) NOT NULL,
    description TEXT,
    control_percentage INTEGER NOT NULL CHECK (control_percentage >= 0 AND control_percentage <= 100),
    treatment_percentage INTEGER NOT NULL CHECK (treatment_percentage >= 0 AND treatment_percentage <= 100),
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'ended')),
    winner VARCHAR(50), -- 'control' or 'treatment'
    start_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_date TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table: ab_test_assignments
-- Tracks which users are in which test group
CREATE TABLE IF NOT EXISTS ab_test_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID NOT NULL REFERENCES ab_test_configs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_name VARCHAR(50) NOT NULL CHECK (group_name IN ('control', 'treatment')),
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(test_id, user_id)
);

-- Table: ab_test_results
-- Stores final results of completed A/B tests
CREATE TABLE IF NOT EXISTS ab_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID NOT NULL REFERENCES ab_test_configs(id) ON DELETE CASCADE,
    winner VARCHAR(50), -- 'control', 'treatment', or NULL if inconclusive
    control_ctr DECIMAL(10, 2),
    treatment_ctr DECIMAL(10, 2),
    control_engagement_rate DECIMAL(10, 2),
    treatment_engagement_rate DECIMAL(10, 2),
    p_value DECIMAL(10, 4),
    effect_size DECIMAL(10, 3),
    control_users INTEGER,
    treatment_users INTEGER,
    recommendation TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table: ab_test_metrics_history
-- Tracks metrics over time for ongoing tests
CREATE TABLE IF NOT EXISTS ab_test_metrics_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID NOT NULL REFERENCES ab_test_configs(id) ON DELETE CASCADE,
    group_name VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    bookmarks INTEGER DEFAULT 0,
    total_interactions INTEGER DEFAULT 0,
    ctr DECIMAL(10, 2),
    engagement_rate DECIMAL(10, 2),
    avg_reward DECIMAL(10, 3),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(test_id, group_name, date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ab_test_configs_status ON ab_test_configs(status);
CREATE INDEX IF NOT EXISTS idx_ab_test_configs_dates ON ab_test_configs(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_ab_test_assignments_user ON ab_test_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_ab_test_assignments_test ON ab_test_assignments(test_id);
CREATE INDEX IF NOT EXISTS idx_ab_test_results_test ON ab_test_results(test_id);
CREATE INDEX IF NOT EXISTS idx_ab_test_metrics_test_date ON ab_test_metrics_history(test_id, date);

-- Enable Row Level Security
ALTER TABLE ab_test_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ab_test_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE ab_test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE ab_test_metrics_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies (Admin access only)
CREATE POLICY "Enable read access for authenticated users" ON ab_test_configs
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Enable all access for service role" ON ab_test_configs
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Enable read access for authenticated users" ON ab_test_assignments
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Enable all access for service role" ON ab_test_assignments
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Enable read access for authenticated users" ON ab_test_results
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Enable all access for service role" ON ab_test_results
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Enable read access for authenticated users" ON ab_test_metrics_history
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Enable all access for service role" ON ab_test_metrics_history
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for ab_test_configs
CREATE TRIGGER update_ab_test_configs_updated_at
    BEFORE UPDATE ON ab_test_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE ab_test_configs IS 'Configuration for A/B tests comparing RL vs baseline recommendations';
COMMENT ON TABLE ab_test_assignments IS 'User assignments to test groups (control/treatment)';
COMMENT ON TABLE ab_test_results IS 'Final results of completed A/B tests';
COMMENT ON TABLE ab_test_metrics_history IS 'Daily metrics tracking for ongoing A/B tests';
