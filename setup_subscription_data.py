#!/usr/bin/env python3
"""
Setup script to populate initial subscription tiers for PicArcade
Run this after the database schema is created
"""

import asyncio
import os
import sys
from typing import Dict, Any

# Add the app directory to the path
sys.path.append('.')

from app.core.database import db_manager

async def setup_subscription_tiers():
    """Setup the three gaming-themed subscription tiers"""
    
    # Define the tiers based on the pricing model
    tiers = [
        {
            "tier_name": "Pixel Rookie",
            "tier_level": 1,
            "tier_display_name": "🎮 Pixel Rookie",
            "tier_description": "Perfect for casual creators getting started with AI",
            "monthly_price_usd": 10.00,
            "monthly_price_aud": 15.00,
            "monthly_xp_allocation": 600,
            "ai_models_included": [
                "flux-1.1-pro", "flux-kontext-max", "runway-gen4-image", 
                "runway-gen2", "stable-diffusion-xl"
            ],
            "generation_types_allowed": [
                "NEW_IMAGE", "NEW_IMAGE_REF", "EDIT_IMAGE", "EDIT_IMAGE_REF",
                "EDIT_IMAGE_ADD_NEW", "IMAGE_TO_VIDEO"
            ],
            "tier_icon": "🎮",
            "tier_color": "#22c55e",
            "smart_routing_enabled": True,
            "priority_processing": False
        },
        {
            "tier_name": "Arcade Artist",
            "tier_level": 2,
            "tier_display_name": "🏆 Arcade Artist",
            "tier_description": "For serious creators who want premium models and more XP",
            "monthly_price_usd": 13.00,
            "monthly_price_aud": 20.00,
            "monthly_xp_allocation": 800,
            "ai_models_included": [
                "flux-1.1-pro", "flux-kontext-max", "runway-gen4-image",
                "runway-gen3-turbo", "runway-gen2", "stable-diffusion-xl",
                "midjourney-v6", "dalle-3"
            ],
            "generation_types_allowed": [
                "NEW_IMAGE", "NEW_IMAGE_REF", "EDIT_IMAGE", "EDIT_IMAGE_REF",
                "EDIT_IMAGE_ADD_NEW", "NEW_VIDEO", "IMAGE_TO_VIDEO"
            ],
            "tier_icon": "🏆",
            "tier_color": "#3b82f6",
            "smart_routing_enabled": True,
            "priority_processing": False
        },
        {
            "tier_name": "Game Master",
            "tier_level": 3,
            "tier_display_name": "👑 Game Master",
            "tier_description": "Ultimate tier with all models, priority processing, and maximum XP",
            "monthly_price_usd": 22.00,
            "monthly_price_aud": 33.00,
            "monthly_xp_allocation": 1400,
            "ai_models_included": [
                "flux-1.1-pro", "flux-kontext-max", "runway-gen4-image",
                "runway-gen3-turbo", "runway-gen2", "stable-diffusion-xl",
                "midjourney-v6", "dalle-3", "claude-3-opus", "gpt-4-vision"
            ],
            "generation_types_allowed": [
                "NEW_IMAGE", "NEW_IMAGE_REF", "EDIT_IMAGE", "EDIT_IMAGE_REF",
                "EDIT_IMAGE_ADD_NEW", "NEW_VIDEO", "NEW_VIDEO_WITH_AUDIO",
                "IMAGE_TO_VIDEO", "EDIT_IMAGE_REF_TO_VIDEO"
            ],
            "tier_icon": "👑",
            "tier_color": "#8b5cf6",
            "smart_routing_enabled": True,
            "priority_processing": True
        }
    ]
    
    print("🚀 Setting up PicArcade subscription tiers...")
    
    for tier_data in tiers:
        try:
            # Check if tier already exists
            existing = db_manager.supabase.table("subscription_tiers")\
                .select("id")\
                .eq("tier_name", tier_data["tier_name"])\
                .execute()
            
            if existing.data:
                print(f"✅ {tier_data['tier_name']} already exists, skipping...")
                continue
            
            # Insert the tier
            result = db_manager.supabase.table("subscription_tiers")\
                .insert(tier_data)\
                .execute()
            
            if result.data:
                print(f"✅ Created tier: {tier_data['tier_display_name']}")
            else:
                print(f"❌ Failed to create tier: {tier_data['tier_name']}")
                
        except Exception as e:
            print(f"❌ Error creating tier {tier_data['tier_name']}: {e}")
    
    print("\n🎯 Subscription tiers setup complete!")
    
    # Show summary
    tiers_result = db_manager.supabase.table("subscription_tiers")\
        .select("tier_name, tier_level, monthly_price_usd, monthly_xp_allocation")\
        .order("tier_level")\
        .execute()
    
    if tiers_result.data:
        print("\n📊 Current Subscription Tiers:")
        print("=" * 60)
        for tier in tiers_result.data:
            print(f"Level {tier['tier_level']}: {tier['tier_name']} - ${tier['monthly_price_usd']}/mo - {tier['monthly_xp_allocation']} XP")
        print("=" * 60)

async def setup_routing_rules():
    """Verify routing rules are properly configured"""
    
    print("\n🧭 Checking model routing rules...")
    
    # Get existing routing rules
    rules_result = db_manager.supabase.table("model_routing_rules")\
        .select("generation_type, optimal_model, tier_requirement, xp_cost")\
        .order("generation_type, tier_requirement")\
        .execute()
    
    if rules_result.data:
        print(f"✅ Found {len(rules_result.data)} routing rules")
        
        # Group by generation type
        rules_by_type = {}
        for rule in rules_result.data:
            gen_type = rule["generation_type"]
            if gen_type not in rules_by_type:
                rules_by_type[gen_type] = []
            rules_by_type[gen_type].append(rule)
        
        print("\n📋 Routing Rules Summary:")
        print("=" * 80)
        for gen_type, rules in rules_by_type.items():
            print(f"\n{gen_type}:")
            for rule in rules:
                print(f"  Tier {rule['tier_requirement']}: {rule['optimal_model']} ({rule['xp_cost']} XP)")
        print("=" * 80)
    else:
        print("❌ No routing rules found - something went wrong with the migration")

async def test_subscription_flow():
    """Test the subscription workflow with a demo user"""
    
    print("\n🧪 Testing subscription flow...")
    
    # This would typically be done through the API
    test_user_id = "test_user_demo_123"
    
    try:
        # Try to create initial XP balance
        from app.services.subscription_service import subscription_service
        
        success = await subscription_service.create_initial_xp_balance(test_user_id, 200)
        
        if success:
            print("✅ Initial XP balance creation works")
            
            # Get the subscription
            subscription = await subscription_service.get_user_subscription(test_user_id)
            if subscription:
                print(f"✅ Retrieved subscription for tier: {subscription.get('subscription_tiers', {}).get('tier_name', 'Unknown')}")
                print(f"   XP Balance: {subscription.get('xp_balance', 0)}")
                
                # Clean up test user
                db_manager.supabase.table("user_subscriptions")\
                    .delete()\
                    .eq("user_id", test_user_id)\
                    .execute()
                print("🧹 Cleaned up test subscription")
            else:
                print("❌ Failed to retrieve test subscription")
        else:
            print("❌ Initial XP balance creation failed")
            
    except Exception as e:
        print(f"❌ Error testing subscription flow: {e}")

async def main():
    """Main setup function"""
    print("🎮 PicArcade Subscription System Setup")
    print("=" * 50)
    
    try:
        await setup_subscription_tiers()
        await setup_routing_rules()
        await test_subscription_flow()
        
        print("\n🎉 Setup completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Configure Stripe webhook endpoints")
        print("   2. Create Stripe products and price IDs")
        print("   3. Update tier records with Stripe price IDs")
        print("   4. Test the full payment flow")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main()) 