-- References Feature Database Schema
-- Run this in your Supabase SQL editor

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Image references table for storing tagged images
CREATE TABLE IF NOT EXISTS image_references (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    display_name TEXT,
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    description TEXT,
    category TEXT DEFAULT 'general',
    source_type TEXT DEFAULT 'uploaded', -- 'uploaded', 'generated', 'external'
    source_generation_id TEXT, -- Link to original generation if from history
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique tags per user
    UNIQUE(user_id, tag)
);

-- Categories table for organizing references
CREATE TABLE IF NOT EXISTS reference_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#6366f1',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, name)
);

-- Usage tracking for references
CREATE TABLE IF NOT EXISTS reference_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_id UUID REFERENCES image_references(id) ON DELETE CASCADE,
    generation_id TEXT NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_image_references_user_id ON image_references(user_id);
CREATE INDEX IF NOT EXISTS idx_image_references_tag ON image_references(user_id, tag);
CREATE INDEX IF NOT EXISTS idx_image_references_category ON image_references(category);
CREATE INDEX IF NOT EXISTS idx_reference_usage_ref_id ON reference_usage(reference_id);
CREATE INDEX IF NOT EXISTS idx_reference_usage_gen_id ON reference_usage(generation_id);

-- Insert some default categories
INSERT INTO reference_categories (user_id, name, color) VALUES 
('system', 'Characters', '#8b5cf6'),
('system', 'Locations', '#10b981'),
('system', 'Objects', '#f59e0b'),
('system', 'Styles', '#ef4444')
ON CONFLICT (user_id, name) DO NOTHING;

-- Add RLS (Row Level Security) policies for multi-tenant access
ALTER TABLE image_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE reference_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE reference_usage ENABLE ROW LEVEL SECURITY;

-- Policies for image_references table
CREATE POLICY "Users can only access their own references" ON image_references
    FOR ALL USING (user_id = current_setting('app.current_user_id', true));

-- Policies for reference_categories table
CREATE POLICY "Users can only access their own categories" ON reference_categories
    FOR ALL USING (user_id = current_setting('app.current_user_id', true) OR user_id = 'system');

-- Policies for reference_usage table
CREATE POLICY "Users can only access their own usage data" ON reference_usage
    FOR ALL USING (
        reference_id IN (
            SELECT id FROM image_references WHERE user_id = current_setting('app.current_user_id', true)
        )
    );

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at on image_references
CREATE TRIGGER update_image_references_updated_at 
    BEFORE UPDATE ON image_references 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 