"""
Subscription Management Service
Handles user subscriptions, tier management, and Stripe integration
"""

import logging
import os
import stripe
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.database import db_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Stripe  
from app.core.config import settings
stripe.api_key = settings.stripe_secret_key

class SubscriptionService:
    """Service for managing user subscriptions and tiers"""
    
    def __init__(self):
        self.supabase = db_manager.supabase
        
    async def get_subscription_tiers(self) -> List[Dict[str, Any]]:
        """Get all active subscription tiers"""
        try:
            result = self.supabase.table("subscription_tiers")\
                .select("*")\
                .eq("is_active", True)\
                .order("tier_level")\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error fetching subscription tiers: {e}")
            return []
    
    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's current subscription with tier details"""
        try:
            result = self.supabase.table("user_subscriptions")\
                .select("""
                    *,
                    subscription_tiers:tier_id (
                        tier_name,
                        tier_level,
                        tier_display_name,
                        tier_description,
                        monthly_xp_allocation,
                        ai_models_included,
                        generation_types_allowed,
                        tier_icon,
                        tier_color,
                        priority_processing
                    )
                """)\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.warning(f"No subscription found for user {user_id}: {e}")
            return None
    
    async def create_trial_subscription(
        self, 
        user_id: str, 
        tier_name: str = "Pixel Rookie"
    ) -> bool:
        """Create a trial subscription for new users"""
        try:
            # Call the database function to create trial
            result = self.supabase.rpc(
                "create_trial_subscription",
                {
                    "p_user_id": user_id,
                    "p_tier_name": tier_name
                }
            ).execute()
            
            return result.data if result.data is not None else True
            
        except Exception as e:
            logger.error(f"Error creating trial subscription for {user_id}: {e}")
            return False
    
    async def check_user_tier_permission(
        self, 
        user_id: str, 
        generation_type: str
    ) -> bool:
        """Check if user has permission for generation type"""
        try:
            result = self.supabase.rpc(
                "check_user_tier_permission",
                {
                    "p_user_id": user_id,
                    "p_generation_type": generation_type
                }
            ).execute()
            
            return result.data if result.data is not None else False
            
        except Exception as e:
            logger.error(f"Error checking tier permission: {e}")
            return False
    
    async def get_xp_cost_for_generation(
        self, 
        generation_type: str,
        user_tier: int = 1
    ) -> int:
        """Get XP cost for generation type"""
        try:
            result = self.supabase.rpc(
                "get_xp_cost_for_generation",
                {
                    "p_generation_type": generation_type,
                    "p_user_tier": user_tier
                }
            ).execute()
            
            return result.data if result.data is not None else 10
            
        except Exception as e:
            logger.error(f"Error getting XP cost: {e}")
            return 10
    
    async def deduct_xp_for_generation(
        self,
        user_id: str,
        generation_id: str,
        generation_type: str,
        model_used: str,
        xp_cost: int,
        actual_cost_usd: float,
        routing_decision: Dict[str, Any] = None
    ) -> bool:
        """Deduct XP for a generation"""
        try:
            result = self.supabase.rpc(
                "deduct_xp_for_generation",
                {
                    "p_user_id": user_id,
                    "p_generation_id": generation_id,
                    "p_generation_type": generation_type,
                    "p_model_used": model_used,
                    "p_xp_cost": xp_cost,
                    "p_actual_cost_usd": actual_cost_usd,
                    "p_routing_decision": routing_decision or {}
                }
            ).execute()
            
            return result.data if result.data is not None else False
            
        except Exception as e:
            logger.error(f"Error deducting XP: {e}")
            return False
    
    async def get_user_xp_balance(self, user_id: str) -> int:
        """Get user's current XP balance"""
        try:
            result = self.supabase.table("user_subscriptions")\
                .select("xp_balance")\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            return result.data.get("xp_balance", 0) if result.data else 0
            
        except Exception as e:
            logger.error(f"Error getting XP balance: {e}")
            return 0
    
    async def get_user_xp_transactions(
        self, 
        user_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's XP transaction history"""
        try:
            result = self.supabase.table("xp_transactions")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error fetching XP transactions: {e}")
            return []
    
    async def create_stripe_customer(
        self, 
        user_id: str, 
        email: str,
        name: str = None
    ) -> Optional[str]:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id}
            )
            
            return customer.id
            
        except Exception as e:
            logger.error(f"Error creating Stripe customer: {e}")
            return None
    
    async def create_stripe_subscription(
        self,
        user_id: str,
        tier_name: str,
        customer_id: str,
        payment_method_id: str,
        currency: str = "usd"
    ) -> Optional[Dict[str, Any]]:
        """Create a Stripe subscription"""
        try:
            # Get tier information
            tier_result = self.supabase.table("subscription_tiers")\
                .select("*")\
                .eq("tier_name", tier_name)\
                .single()\
                .execute()
            
            if not tier_result.data:
                logger.error(f"Tier {tier_name} not found")
                return None
            
            tier = tier_result.data
            
            # Get the appropriate Stripe price ID
            price_id = tier.get(f"stripe_price_id_{currency}")
            if not price_id:
                logger.error(f"No Stripe price ID for tier {tier_name} in {currency}")
                return None
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                default_payment_method=payment_method_id,
                expand=["latest_invoice.payment_intent"],
                metadata={
                    "user_id": user_id,
                    "tier_name": tier_name
                }
            )
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "trial_end": subscription.trial_end
            }
            
        except Exception as e:
            logger.error(f"Error creating Stripe subscription: {e}")
            return None
    
    async def update_user_subscription_from_stripe(
        self,
        user_id: str,
        subscription_data: Dict[str, Any]
    ) -> bool:
        """Update user subscription from Stripe webhook data"""
        try:
            # Get tier from subscription metadata or items
            tier_name = subscription_data.get("metadata", {}).get("tier_name")
            if not tier_name:
                logger.error("No tier_name in subscription metadata")
                return False
            
            # Get tier info
            tier_result = self.supabase.table("subscription_tiers")\
                .select("*")\
                .eq("tier_name", tier_name)\
                .single()\
                .execute()
            
            if not tier_result.data:
                logger.error(f"Tier {tier_name} not found")
                return False
            
            tier = tier_result.data
            
            # Update user subscription
            update_data = {
                "tier_id": tier["id"],
                "stripe_subscription_id": subscription_data["id"],
                "status": "active" if subscription_data["status"] == "active" else subscription_data["status"],
                "current_period_start": datetime.fromtimestamp(subscription_data["current_period_start"]),
                "current_period_end": datetime.fromtimestamp(subscription_data["current_period_end"]),
                "current_level": tier["tier_level"],
                "xp_balance": tier["monthly_xp_allocation"],
                "xp_allocated_this_period": tier["monthly_xp_allocation"],
                "xp_used_this_period": 0,
                "last_xp_reset": datetime.now()
            }
            
            if subscription_data.get("trial_end"):
                update_data["trial_end"] = datetime.fromtimestamp(subscription_data["trial_end"])
            
            result = self.supabase.table("user_subscriptions")\
                .upsert({"user_id": user_id, **update_data})\
                .execute()
            
            # Create XP allocation transaction
            await self._create_xp_allocation_transaction(
                user_id, 
                tier["monthly_xp_allocation"],
                "Subscription activated - XP allocation"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating subscription from Stripe: {e}")
            return False
    
    async def _create_xp_allocation_transaction(
        self,
        user_id: str,
        amount: int,
        description: str
    ):
        """Create an XP allocation transaction"""
        try:
            self.supabase.table("xp_transactions").insert({
                "user_id": user_id,
                "transaction_type": "allocation",
                "amount": amount,
                "balance_after": amount,
                "description": description
            }).execute()
            
        except Exception as e:
            logger.error(f"Error creating XP allocation transaction: {e}")
    
    async def handle_stripe_webhook(
        self, 
        event_type: str, 
        event_data: Dict[str, Any]
    ) -> bool:
        """Handle Stripe webhook events"""
        try:
            if event_type == "customer.subscription.created":
                subscription = event_data
                user_id = subscription.get("metadata", {}).get("user_id")
                if user_id:
                    return await self.update_user_subscription_from_stripe(user_id, subscription)
            
            elif event_type == "customer.subscription.updated":
                subscription = event_data
                user_id = subscription.get("metadata", {}).get("user_id")
                if user_id:
                    return await self.update_user_subscription_from_stripe(user_id, subscription)
            
            elif event_type == "customer.subscription.deleted":
                subscription = event_data
                user_id = subscription.get("metadata", {}).get("user_id")
                if user_id:
                    # Cancel user subscription
                    self.supabase.table("user_subscriptions")\
                        .update({"status": "canceled"})\
                        .eq("user_id", user_id)\
                        .execute()
                    return True
            
            elif event_type == "invoice.payment_succeeded":
                invoice = event_data
                subscription_id = invoice.get("subscription")
                if subscription_id:
                    # Get subscription to find user
                    subscription = stripe.Subscription.retrieve(subscription_id)
                    user_id = subscription.metadata.get("user_id")
                    if user_id:
                        # Reset XP allocation for the new period
                        await self._handle_successful_payment(user_id)
                        return True
            
            elif event_type == "invoice.payment_failed":
                invoice = event_data
                subscription_id = invoice.get("subscription")
                if subscription_id:
                    subscription = stripe.Subscription.retrieve(subscription_id)
                    user_id = subscription.metadata.get("user_id")
                    if user_id:
                        # Mark subscription as past_due
                        self.supabase.table("user_subscriptions")\
                            .update({"status": "past_due"})\
                            .eq("user_id", user_id)\
                            .execute()
                        return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling Stripe webhook {event_type}: {e}")
            return False
    
    async def _handle_successful_payment(self, user_id: str):
        """Handle successful payment - allocate XP for new period"""
        try:
            # Get user subscription with tier info
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return
            
            tier = subscription.get("subscription_tiers")
            if not tier:
                return
            
            # Reset XP allocation
            self.supabase.table("user_subscriptions")\
                .update({
                    "xp_balance": tier["monthly_xp_allocation"],
                    "xp_allocated_this_period": tier["monthly_xp_allocation"],
                    "xp_used_this_period": 0,
                    "last_xp_reset": datetime.now().isoformat(),
                    "status": "active"
                })\
                .eq("user_id", user_id)\
                .execute()
            
            # Create allocation transaction
            await self._create_xp_allocation_transaction(
                user_id,
                tier["monthly_xp_allocation"],
                "Monthly XP allocation - payment successful"
            )
            
        except Exception as e:
            logger.error(f"Error handling successful payment: {e}")

# Global subscription service instance
subscription_service = SubscriptionService() 