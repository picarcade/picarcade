-- User Sessions Table Setup for PicArcade
-- Run this in your Supabase SQL editor: https://icgwpkroorulmsfdiuoh.supabase.co/project/icgwpkroorulmsfdiuoh/sql

-- Create the user_sessions table for managing user sessions and working images
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    current_working_image TEXT,
    current_working_video TEXT,
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Enable Row Level Security
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user_sessions
-- Users can only access their own sessions
CREATE POLICY IF NOT EXISTS "Users can access their own sessions" ON user_sessions
    FOR ALL USING (user_id = auth.jwt() ->> 'sub');

-- Service role can access all sessions (for cleanup, etc.)
CREATE POLICY IF NOT EXISTS "Service role can access all sessions" ON user_sessions
    FOR ALL USING (current_setting('role') = 'service_role');

-- Add helpful comments
COMMENT ON TABLE user_sessions IS 'Stores user session data including current working images and session metadata';
COMMENT ON COLUMN user_sessions.session_id IS 'Unique session identifier, typically the JWT access token';
COMMENT ON COLUMN user_sessions.user_id IS 'Supabase user ID from auth.users';
COMMENT ON COLUMN user_sessions.current_working_image IS 'URL of the current working image for this session';
COMMENT ON COLUMN user_sessions.current_working_video IS 'URL of the current working video for this session';
COMMENT ON COLUMN user_sessions.metadata IS 'Additional session metadata as JSON';
COMMENT ON COLUMN user_sessions.expires_at IS 'When this session expires and should be cleaned up';

-- Create a function to automatically clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM user_sessions 
    WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a trigger to automatically update the updated_at column
CREATE OR REPLACE FUNCTION update_user_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_sessions_updated_at
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_user_sessions_updated_at();

-- Optional: Create a periodic cleanup job (uncomment if you want automatic cleanup)
-- This requires the pg_cron extension to be enabled in your Supabase project
-- SELECT cron.schedule('cleanup-expired-sessions', '0 * * * *', 'SELECT cleanup_expired_sessions();');

GRANT ALL ON user_sessions TO authenticated;
GRANT ALL ON user_sessions TO service_role; 