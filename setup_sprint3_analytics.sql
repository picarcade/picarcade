-- Sprint 3: Analytics and monitoring tables for Supabase
-- Run this in your Supabase SQL Editor: https://icgwpkroorulmsfdiuoh.supabase.co/project/icgwpkroorulmsfdiuoh/sql

-- Intent classification tracking table
CREATE TABLE IF NOT EXISTS intent_classification_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    classified_workflow VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    used_fallback BOOLEAN DEFAULT FALSE,
    cache_hit BOOLEAN DEFAULT FALSE,
    circuit_breaker_state VARCHAR(20),
    rate_limited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_intent_logs_user_time 
ON intent_classification_logs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_intent_logs_workflow 
ON intent_classification_logs (classified_workflow, confidence DESC);

CREATE INDEX IF NOT EXISTS idx_intent_logs_performance 
ON intent_classification_logs (used_fallback, cache_hit, rate_limited);

-- Cost tracking table
CREATE TABLE IF NOT EXISTS cost_tracking (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    estimated_cost FLOAT,
    actual_cost FLOAT,
    model_used VARCHAR(100),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cost_tracking_user_time 
ON cost_tracking (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_cost_tracking_operation 
ON cost_tracking (operation_type, success);

-- Model selection tracking table
CREATE TABLE IF NOT EXISTS model_selection_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    generation_id TEXT,
    workflow_type VARCHAR(50) NOT NULL,
    selected_model VARCHAR(100) NOT NULL,
    fallback_models TEXT[], -- Array of fallback models
    estimated_cost FLOAT,
    actual_cost FLOAT,
    estimated_time INTEGER, -- seconds
    actual_time INTEGER, -- seconds
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_logs_user_time 
ON model_selection_logs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_model_logs_workflow_success 
ON model_selection_logs (workflow_type, success);

-- System performance tracking
CREATE TABLE IF NOT EXISTS system_performance_logs (
    id BIGSERIAL PRIMARY KEY,
    component VARCHAR(50) NOT NULL, -- 'redis', 'circuit_breaker', 'rate_limiter'
    status VARCHAR(20) NOT NULL, -- 'healthy', 'degraded', 'failed'
    metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_performance_logs_component_time 
ON system_performance_logs (component, created_at DESC);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE intent_classification_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_selection_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_performance_logs ENABLE ROW LEVEL SECURITY;

-- Create policies (basic examples - customize based on your auth needs)
CREATE POLICY IF NOT EXISTS "Users can view their own logs" ON intent_classification_logs
    FOR SELECT USING (user_id = auth.jwt() ->> 'sub');

CREATE POLICY IF NOT EXISTS "Users can view their own costs" ON cost_tracking
    FOR SELECT USING (user_id = auth.jwt() ->> 'sub');

CREATE POLICY IF NOT EXISTS "Users can view their own model logs" ON model_selection_logs
    FOR SELECT USING (user_id = auth.jwt() ->> 'sub');

-- Insert function to create triggers will be added after
COMMENT ON TABLE intent_classification_logs IS 'Tracks AI intent classification performance and metrics';
COMMENT ON TABLE cost_tracking IS 'Tracks API costs and usage for billing and optimization';
COMMENT ON TABLE model_selection_logs IS 'Tracks model selection decisions and their outcomes';
COMMENT ON TABLE system_performance_logs IS 'Tracks overall system health and component status'; 