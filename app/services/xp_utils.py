"""
XP Utility Functions
Helper functions for XP checking and user guidance
"""

from typing import Dict, Any, Optional
from .subscription_service import subscription_service


async def check_user_xp_for_generation(
    user_id: str, 
    generation_type: str
) -> Dict[str, Any]:
    """
    Simple wrapper for XP checking with user guidance
    
    Returns:
    {
        "can_generate": bool,
        "message": str,
        "guidance": str,
        "subscription_url": str,
        "xp_info": dict
    }
    """
    result = await subscription_service.check_xp_availability(
        user_id=user_id,
        generation_type=generation_type,
        include_guidance=True
    )
    
    return {
        "can_generate": result["has_sufficient_xp"],
        "message": result["message"],
        "guidance": result.get("guidance", ""),
        "subscription_url": result.get("subscription_url", "/subscriptions"),
        "xp_info": {
            "balance": result["xp_balance"],
            "required": result["xp_required"],
            "deficit": result["xp_deficit"]
        },
        "tier_info": {
            "current": result.get("current_tier"),
            "recommended": result.get("recommended_tier")
        }
    }


async def get_generation_cost(generation_type: str, user_tier: int = 1) -> int:
    """Get XP cost for a generation type"""
    return await subscription_service.get_xp_cost_for_generation(
        generation_type=generation_type,
        user_tier=user_tier
    )


def format_xp_guidance_message(
    has_xp: bool,
    xp_balance: int,
    xp_required: int,
    tier_name: Optional[str] = None
) -> str:
    """
    Format a user-friendly XP guidance message
    
    Args:
        has_xp: Whether user has sufficient XP
        xp_balance: Current XP balance
        xp_required: XP required for action
        tier_name: Optional current tier name
    
    Returns:
        Formatted message string
    """
    if has_xp:
        return f"✅ Ready to generate! This will cost {xp_required} XP."
    
    if xp_balance == 0:
        if tier_name:
            return f"🎮 You're out of XP credits! Need {xp_required} XP to continue creating."
        else:
            return f"🚀 Subscribe to start creating! This generation needs {xp_required} XP."
    
    deficit = xp_required - xp_balance
    return f"⚡ Need {deficit} more XP credits! You have {xp_balance} XP, need {xp_required} XP."


def get_subscription_cta_message(
    current_tier: Optional[Dict[str, Any]] = None,
    recommended_tier: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get a call-to-action message for subscription
    
    Returns:
        CTA message string
    """
    if not current_tier:
        return "🎮 Choose a subscription tier to start creating amazing AI content!"
    
    if recommended_tier:
        tier_name = recommended_tier.get("tier_display_name", "higher tier")
        monthly_xp = recommended_tier.get("monthly_xp_allocation", 0)
        price = recommended_tier.get("monthly_price_aud", 0)
        return f"🎯 Upgrade to {tier_name} (A${price}/month) for {monthly_xp} XP monthly!"
    
    return "💎 Upgrade your tier or wait for your monthly XP refresh to continue creating."


# XP cost constants for easy reference
XP_COSTS = {
    "NEW_IMAGE": 12,
    "NEW_IMAGE_REF": 18,
    "EDIT_IMAGE": 9,
    "EDIT_IMAGE_REF": 18,
    "EDIT_IMAGE_ADD_NEW": 18,
    "NEW_VIDEO": 15,
    "NEW_VIDEO_WITH_AUDIO": 720,
    "IMAGE_TO_VIDEO": 150,
    "IMAGE_TO_VIDEO_WITH_AUDIO": 720,
    "EDIT_IMAGE_REF_TO_VIDEO": 150
}


def get_xp_cost_estimate(generation_type: str) -> int:
    """Get estimated XP cost for a generation type (for quick reference)"""
    return XP_COSTS.get(generation_type, 10)  # Default to 10 if unknown 