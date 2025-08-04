-- XP Management Functions for PicArcade
-- Run this in your Supabase SQL editor

-- Function to get XP cost for generation based on type and user tier
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
        WHEN 'VIDEO_EDIT' THEN RETURN 300; -- gen4_aleph video editing (50c per 10s)
        WHEN 'VIDEO_EDIT_REF' THEN RETURN 300; -- gen4_aleph video editing with references
        ELSE RETURN 10; -- Default cost
    END CASE;
END;
$$;

-- Function to check if user has permission for generation type
CREATE OR REPLACE FUNCTION check_user_tier_permission(
    p_user_id UUID,
    p_generation_type TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_tier INTEGER;
BEGIN
    -- Get user's current tier level
    SELECT COALESCE(current_level, 0) INTO user_tier
    FROM user_subscriptions
    WHERE user_id = p_user_id;
    
    -- For now, allow all generation types for all users
    -- This can be expanded with tier-specific restrictions later
    RETURN TRUE;
END;
$$;

-- Function to deduct XP for a generation
CREATE OR REPLACE FUNCTION deduct_xp_for_generation(
    p_user_id UUID,
    p_generation_id TEXT,
    p_generation_type TEXT,
    p_model_used TEXT,
    p_xp_cost INTEGER,
    p_actual_cost_usd DECIMAL DEFAULT 0.0,
    p_routing_decision JSONB DEFAULT '{}'::jsonb,
    p_prompt TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    current_balance INTEGER;
    new_balance INTEGER;
BEGIN
    -- Get current XP balance
    SELECT COALESCE(xp_balance, 0) INTO current_balance
    FROM user_subscriptions
    WHERE user_id = p_user_id;
    
    -- Check if user has sufficient balance
    IF current_balance < p_xp_cost THEN
        RETURN FALSE;
    END IF;
    
    -- Calculate new balance
    new_balance := current_balance - p_xp_cost;
    
    -- Update user's XP balance and usage tracking
    UPDATE user_subscriptions
    SET 
        xp_balance = new_balance,
        xp_used_this_period = COALESCE(xp_used_this_period, 0) + p_xp_cost
    WHERE user_id = p_user_id;
    
    -- Create transaction record
    INSERT INTO xp_transactions (
        user_id,
        transaction_type,
        amount,
        balance_after,
        description,
        generation_id,
        generation_type,
        model_used,
        actual_cost_usd,
        routing_decision
    ) VALUES (
        p_user_id,
        'deduction',
        -p_xp_cost,
        new_balance,
        CASE 
            WHEN p_prompt IS NOT NULL AND LENGTH(p_prompt) > 0 THEN
                CASE 
                    WHEN LENGTH(p_prompt) > 200 THEN LEFT(p_prompt, 200) || '...'
                    ELSE p_prompt
                END
            ELSE 'Generation: ' || p_generation_type || ' using ' || p_model_used
        END,
        p_generation_id,
        p_generation_type,
        p_model_used,
        p_actual_cost_usd,
        p_routing_decision
    );
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        -- Return false on any error
        RETURN FALSE;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION get_xp_cost_for_generation TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION check_user_tier_permission TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION deduct_xp_for_generation TO authenticated, service_role; 