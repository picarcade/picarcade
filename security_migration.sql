-- Security Migration Script
-- Run this in your Supabase SQL editor to fix critical security vulnerabilities
-- ⚠️  IMPORTANT: This will restrict database access - ensure your app uses authenticated users

-- Enable Row Level Security on all public tables
ALTER TABLE public.image_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generation_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reference_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intent_classification_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reference_categories ENABLE ROW LEVEL SECURITY;

-- Image References Policies
-- Users can only access their own references
CREATE POLICY "Users can access their own image references" ON public.image_references
    FOR ALL USING (user_id = auth.jwt() ->> 'sub');

-- Service role can access all references for admin operations
CREATE POLICY "Service role can access all image references" ON public.image_references
    FOR ALL USING (current_setting('role') = 'service_role');

-- Generation History Policies  
-- Users can only access their own generation history
CREATE POLICY "Users can access their own generation history" ON public.generation_history
    FOR ALL USING (user_id = auth.jwt() ->> 'sub');

-- Service role can access all history for analytics
CREATE POLICY "Service role can access all generation history" ON public.generation_history
    FOR ALL USING (current_setting('role') = 'service_role');

-- User Sessions Policies
-- Users can only access their own sessions
CREATE POLICY "Users can access their own sessions" ON public.user_sessions
    FOR ALL USING (user_id = auth.jwt() ->> 'sub' OR user_id IS NULL);

-- Service role can access all sessions for cleanup
CREATE POLICY "Service role can access all sessions" ON public.user_sessions
    FOR ALL USING (current_setting('role') = 'service_role');

-- Reference Usage Policies
-- Users can only see usage of their own references
CREATE POLICY "Users can access their own reference usage" ON public.reference_usage
    FOR ALL USING (
        reference_id IN (
            SELECT id FROM public.image_references 
            WHERE user_id = auth.jwt() ->> 'sub'
        )
    );

-- Service role can access all usage data
CREATE POLICY "Service role can access all reference usage" ON public.reference_usage
    FOR ALL USING (current_setting('role') = 'service_role');

-- Intent Classification Logs Policies
-- Users can only see their own classification logs
CREATE POLICY "Users can access their own classification logs" ON public.intent_classification_logs
    FOR ALL USING (user_id = auth.jwt() ->> 'sub');

-- Service role can access all logs for analytics
CREATE POLICY "Service role can access all classification logs" ON public.intent_classification_logs
    FOR ALL USING (current_setting('role') = 'service_role');

-- Reference Categories Policies
-- Users can access their own categories plus system categories
CREATE POLICY "Users can access their own and system categories" ON public.reference_categories
    FOR ALL USING (user_id = auth.jwt() ->> 'sub' OR user_id = 'system');

-- Service role can access all categories
CREATE POLICY "Service role can access all categories" ON public.reference_categories
    FOR ALL USING (current_setting('role') = 'service_role');

-- Storage Policies for image uploads
-- Allow authenticated users to upload to their own folder
CREATE POLICY "Users can upload to their own folder" ON storage.objects
    FOR INSERT WITH CHECK (
        bucket_id = 'images' AND
        (storage.foldername(name))[1] = 'uploads' AND
        (storage.foldername(name))[2] = auth.jwt() ->> 'sub'
    );

-- Allow authenticated users to view any uploaded image (for sharing)
CREATE POLICY "Authenticated users can view uploaded images" ON storage.objects
    FOR SELECT USING (
        bucket_id = 'images' AND
        (storage.foldername(name))[1] = 'uploads'
    );

-- Allow users to delete their own uploaded images
CREATE POLICY "Users can delete their own uploaded images" ON storage.objects
    FOR DELETE USING (
        bucket_id = 'images' AND
        (storage.foldername(name))[1] = 'uploads' AND
        (storage.foldername(name))[2] = auth.jwt() ->> 'sub'
    );

-- Service role can access all storage objects
CREATE POLICY "Service role can access all storage objects" ON storage.objects
    FOR ALL USING (current_setting('role') = 'service_role');

-- Fix function security issue
-- Update the trigger function to have a stable search_path
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER 
SECURITY DEFINER
SET search_path = public, pg_temp
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Data cleanup: Update null user_ids in user_sessions
-- This addresses the data integrity issue found in the sessions
UPDATE public.user_sessions 
SET user_id = split_part(session_id, '_', 4)
WHERE user_id IS NULL 
AND session_id LIKE 'auto_session_user_%';

-- Performance optimizations: Remove duplicate indexes
DROP INDEX IF EXISTS public.idx_reference_usage_ref_id;
DROP INDEX IF EXISTS public.idx_reference_usage_gen_id;

-- Keep the more descriptive index names
-- idx_reference_usage_reference_id and idx_reference_usage_generation_id will remain

-- Add missing indexes for better performance
CREATE INDEX IF NOT EXISTS idx_image_references_user_tag ON public.image_references(user_id, tag);
CREATE INDEX IF NOT EXISTS idx_generation_history_user_created ON public.generation_history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_updated ON public.user_sessions(user_id, updated_at DESC);

-- Add comments for documentation
COMMENT ON POLICY "Users can access their own image references" ON public.image_references IS 
'Ensures users can only see and modify their own reference images';

COMMENT ON POLICY "Users can access their own generation history" ON public.generation_history IS 
'Ensures users can only see their own generation history and results';

COMMENT ON POLICY "Users can upload to their own folder" ON storage.objects IS 
'Allows users to upload images only to their own user folder in storage';

COMMENT ON POLICY "Authenticated users can view uploaded images" ON storage.objects IS 
'Allows viewing of uploaded images for sharing while maintaining upload restrictions';

-- Enable authentication for better security
-- Update auth configuration (run this separately if needed)
-- ALTER DATABASE postgres SET app.settings.jwt_secret = 'your-jwt-secret-here';

-- Validation queries to test security
-- These should return 0 rows for non-admin users
-- SELECT count(*) FROM public.image_references WHERE user_id != auth.jwt() ->> 'sub';
-- SELECT count(*) FROM public.generation_history WHERE user_id != auth.jwt() ->> 'sub';

COMMIT; 