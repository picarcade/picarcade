# XP Checking System Documentation

## Overview

The XP checking system provides comprehensive functionality to check if users have enough XP credits to complete their requests. When users don't have sufficient XP, the system provides helpful guidance and direct links to the subscription page.

## Key Features

- ✅ **Comprehensive XP Checking** - Checks balance against generation costs
- ✅ **User-Friendly Guidance** - Gaming-style messages with emojis
- ✅ **Subscription Recommendations** - Suggests appropriate tier upgrades
- ✅ **Direct Subscription Links** - Links to `/subscriptions` page
- ✅ **Tier Information** - Shows current and recommended tiers
- ✅ **Seamless Integration** - Works with existing middleware and APIs

## Core Function

### `subscription_service.check_xp_availability()`

The main function that checks XP availability and provides comprehensive guidance.

```python
result = await subscription_service.check_xp_availability(
    user_id="user-uuid",
    generation_type="NEW_IMAGE",
    include_guidance=True  # Optional: include user guidance
)
```

**Returns:**
```python
{
    "has_sufficient_xp": bool,      # Can user proceed?
    "xp_balance": int,              # Current XP balance
    "xp_required": int,             # XP needed for this generation
    "xp_deficit": int,              # How much XP is missing
    "message": str,                 # User-friendly message
    "guidance": str,                # Detailed guidance (if requested)
    "subscription_url": str,        # Link to subscription page
    "current_tier": dict,           # Current tier info
    "recommended_tier": dict        # Suggested upgrade tier
}
```

## API Endpoints

### 1. Check XP Availability

**GET** `/api/v1/subscriptions/check-xp/{generation_type}`

Check if user has enough XP for a specific generation type.

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/subscriptions/check-xp/NEW_IMAGE?include_guidance=true"
```

**Response Example:**
```json
{
    "has_sufficient_xp": false,
    "xp_balance": 5,
    "xp_required": 12,
    "xp_deficit": 7,
    "message": "Insufficient credits. Need 12 XP, have 5 XP (7 XP short).",
    "guidance": "⚡ You need 7 more XP credits. 💎 Upgrade your tier or wait for your monthly XP refresh to continue creating. 🎯 Recommended: Arcade Artist (A$20/month) gives you 800 XP monthly!",
    "subscription_url": "/subscriptions",
    "current_tier": {
        "tier_name": "pixel_rookie",
        "tier_display_name": "Pixel Rookie",
        "tier_level": 1
    },
    "recommended_tier": {
        "tier_name": "arcade_artist",
        "tier_display_name": "Arcade Artist",
        "tier_level": 2,
        "monthly_xp_allocation": 800,
        "monthly_price_aud": 20
    }
}
```

### 2. Preview Generation Cost

**POST** `/api/v1/subscriptions/preview-generation-cost`

Preview XP cost and availability before generation.

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"generation_type": "NEW_IMAGE", "include_guidance": true}' \
  "http://localhost:8000/api/v1/subscriptions/preview-generation-cost"
```

## Utility Functions

The `app/services/xp_utils.py` module provides helper functions:

### Simple XP Check
```python
from app.services.xp_utils import check_user_xp_for_generation

result = await check_user_xp_for_generation(user_id, "NEW_IMAGE")
```

### Get Generation Cost
```python
from app.services.xp_utils import get_generation_cost

cost = await get_generation_cost("NEW_IMAGE", user_tier=1)
```

### Format Messages
```python
from app.services.xp_utils import format_xp_guidance_message

message = format_xp_guidance_message(
    has_xp=False,
    xp_balance=5,
    xp_required=12,
    tier_name="Pixel Rookie"
)
```

## Integration Examples

### Middleware Integration

The tier permissions middleware automatically uses the comprehensive XP checking:

```python
# app/middleware/tier_permissions.py
xp_check = await subscription_service.check_xp_availability(
    user_id=user_id,
    generation_type=generation_type,
    include_guidance=True
)

if not xp_check["has_sufficient_xp"]:
    return JSONResponse(
        status_code=402,
        content={
            "error": "insufficient_xp",
            "message": xp_check["message"],
            "guidance": xp_check.get("guidance"),
            "subscription_url": xp_check.get("subscription_url"),
            "recommended_tier": xp_check.get("recommended_tier")
        }
    )
```

### Frontend Usage

Call the API from your frontend to check XP before generation:

```javascript
const checkXP = async (generationType) => {
    const response = await fetch(
        `/api/v1/subscriptions/check-xp/${generationType}?include_guidance=true`,
        {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }
    );
    
    const result = await response.json();
    
    if (!result.has_sufficient_xp) {
        // Show user guidance
        alert(result.guidance);
        
        // Redirect to subscriptions if needed
        if (result.subscription_url) {
            window.location.href = result.subscription_url;
        }
    }
};
```

## XP Generation Costs

| Generation Type | XP Cost | Model Used |
|----------------|---------|------------|
| NEW_IMAGE | 12 XP | FLUX 1.1 Pro |
| NEW_IMAGE_REF | 18 XP | Runway Gen4 Image |
| EDIT_IMAGE | 9 XP | FLUX Kontext Max |
| EDIT_IMAGE_REF | 18 XP | Runway Gen4 Image |
| EDIT_IMAGE_ADD_NEW | 18 XP | Runway Gen4 Image |
| NEW_VIDEO | 15 XP | Minimax Hailuo-02 |
| NEW_VIDEO_WITH_AUDIO | 720 XP | Google VEO-3 Fast |
| IMAGE_TO_VIDEO | 150 XP | Runway Gen4 Turbo |
| IMAGE_TO_VIDEO_WITH_AUDIO | 720 XP | Google VEO-3 Fast |
| EDIT_IMAGE_REF_TO_VIDEO | 150 XP | Runway Gen4 Turbo |

## Subscription Tiers

### 🎮 Pixel Rookie - Level 1 (A$15/month)
- **600 XP/month** allocation
- Image generation only

### 🏆 Arcade Artist - Level 2 (A$20/month)
- **800 XP/month** allocation  
- Video powers unlocked

### 👑 Game Master - Level 3 (A$33/month)
- **1,320 XP/month** allocation
- Complete AI arsenal with audio

## User Experience Flow

1. **XP Check** - System automatically checks XP before generation
2. **Sufficient XP** - Generation proceeds normally
3. **Insufficient XP** - User sees:
   - Clear explanation of XP shortage
   - Gaming-style guidance message
   - Subscription tier recommendations
   - Direct link to upgrade page

## Error Handling

The system gracefully handles all error conditions:

- **No subscription** - Guides user to initial subscription
- **Insufficient XP** - Shows deficit and upgrade options
- **System errors** - Falls back to generic guidance messages

## Testing

You can test the XP checking system with different scenarios:

```bash
# Test sufficient XP
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/subscriptions/check-xp/EDIT_IMAGE"

# Test insufficient XP  
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/subscriptions/check-xp/NEW_VIDEO_WITH_AUDIO"

# Test no subscription
curl -H "Authorization: Bearer <new-user-token>" \
  "http://localhost:8000/api/v1/subscriptions/check-xp/NEW_IMAGE"
```

## Summary

This XP checking system provides a comprehensive, user-friendly way to:
- ✅ Check XP availability before requests
- ✅ Provide clear guidance when XP is insufficient  
- ✅ Recommend appropriate subscription upgrades
- ✅ Guide users to the subscription page with direct links
- ✅ Maintain consistent messaging across the application

The system integrates seamlessly with existing middleware and can be easily used throughout the application via the API endpoints or utility functions. 