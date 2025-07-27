-- XP Cost Function Update Migration
-- Run this in your Supabase SQL editor to fix XP pricing

-- Drop the existing function
DROP FUNCTION IF EXISTS get_xp_cost_for_generation(TEXT, INTEGER);

-- Recreate with correct XP costs matching Python code and documentation
CREATE OR REPLACE FUNCTION get_xp_cost_for_generation(
    p_generation_type TEXT,
    p_user_tier INTEGER DEFAULT 0
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- XP cost structure - Updated to match Python XP_COSTS and documentation
    CASE p_generation_type
        WHEN 'NEW_IMAGE' THEN RETURN 12;
        WHEN 'NEW_IMAGE_REF' THEN RETURN 18;
        WHEN 'EDIT_IMAGE' THEN RETURN 9;
        WHEN 'EDIT_IMAGE_REF' THEN RETURN 18;
        WHEN 'EDIT_IMAGE_ADD_NEW' THEN RETURN 18;
        WHEN 'NEW_VIDEO' THEN RETURN 15;
        WHEN 'NEW_VIDEO_WITH_AUDIO' THEN RETURN 720;
        WHEN 'IMAGE_TO_VIDEO' THEN RETURN 150;
        WHEN 'IMAGE_TO_VIDEO_WITH_AUDIO' THEN RETURN 720;
        WHEN 'EDIT_IMAGE_REF_TO_VIDEO' THEN RETURN 150;
        ELSE RETURN 10; -- Default cost
    END CASE;
END;
$$;

-- Test the function to ensure it returns correct values
SELECT 
    'NEW_VIDEO_WITH_AUDIO' as generation_type,
    get_xp_cost_for_generation('NEW_VIDEO_WITH_AUDIO', 1) as xp_cost,
    'Should be 720' as expected;

SELECT 
    'IMAGE_TO_VIDEO_WITH_AUDIO' as generation_type,
    get_xp_cost_for_generation('IMAGE_TO_VIDEO_WITH_AUDIO', 1) as xp_cost,
    'Should be 720' as expected;

SELECT 
    'IMAGE_TO_VIDEO' as generation_type,
    get_xp_cost_for_generation('IMAGE_TO_VIDEO', 1) as xp_cost,
    'Should be 150' as expected; 