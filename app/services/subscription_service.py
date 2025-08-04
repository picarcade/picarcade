"""
Subscription Management Service
Handles user subscriptions, tier management, and Stripe integration
"""

import logging
import os
import stripe
from typing import Dict, Any, Optional, List, Union
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
    
    async def create_initial_xp_balance(
        self, 
        user_id: str, 
        initial_xp: int = 200
    ) -> bool:
        """Create initial XP balance for new users"""
        try:
            logger.info(f"[DEBUG] Creating initial XP balance for user {user_id}")
            
            # Create initial user subscription record with XP balance
            insert_data = {
                "user_id": user_id,
                "xp_balance": initial_xp,
                "xp_allocated_this_period": initial_xp,
                "xp_used_this_period": 0,
                "status": "active",
                "tier_id": None,  # No subscription tier yet
            }
            logger.info(f"[DEBUG] Inserting data: {insert_data}")
            
            result = self.supabase.table("user_subscriptions").insert(insert_data).execute()
            logger.info(f"[DEBUG] Insert result success: {result.data is not None}")
            
            # Create XP allocation transaction
            logger.info(f"[DEBUG] Creating XP allocation transaction")
            await self._create_xp_allocation_transaction(
                user_id,
                initial_xp,
                "Welcome bonus - initial XP allocation"
            )
            logger.info(f"[DEBUG] XP allocation transaction created successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating initial XP balance for {user_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
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
        user_id: Union[str, Any],  # Can be str or UUID
        generation_id: str,
        generation_type: str,
        model_used: str,
        xp_cost: int,
        actual_cost_usd: float,
        routing_decision: Dict[str, Any] = None,
        prompt: str = None
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
                    "p_routing_decision": routing_decision or {},
                    "p_prompt": prompt
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
            logger.info(f"Creating subscription for customer {customer_id} with payment method {payment_method_id} and price {price_id}")
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
            
            logger.info(f"Subscription created successfully: {subscription.id}, status: {subscription.status}")
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start) if hasattr(subscription, 'current_period_start') and subscription.current_period_start else None,
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end) if hasattr(subscription, 'current_period_end') and subscription.current_period_end else None,

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
            
            # Handle current_period_start and current_period_end (could be timestamp or datetime)
            def convert_to_datetime(value):
                if isinstance(value, datetime):
                    return value
                elif isinstance(value, (int, float)):
                    return datetime.fromtimestamp(value)
                else:
                    return datetime.now()
            
            # Update user subscription
            update_data = {
                "tier_id": tier["id"],
                "stripe_subscription_id": subscription_data["id"],
                "status": "active" if subscription_data["status"] == "active" else subscription_data["status"],
                "current_period_start": convert_to_datetime(subscription_data["current_period_start"]).isoformat(),
                "current_period_end": convert_to_datetime(subscription_data["current_period_end"]).isoformat(),
                "current_level": tier["tier_level"],
                "xp_balance": tier["monthly_xp_allocation"],
                "xp_allocated_this_period": tier["monthly_xp_allocation"],
                "xp_used_this_period": 0,
                "last_xp_reset": datetime.now().isoformat()
            }
            

            
            logger.info(f"Updating user subscription for user {user_id} with tier {tier_name} (level {tier['tier_level']})")
            logger.info(f"Update data: {update_data}")
            
            # Check if user already has a subscription record
            existing_subscription = await self.get_user_subscription(user_id)
            
            if existing_subscription:
                # Update existing record
                logger.info(f"Updating existing subscription for user {user_id}")
                result = self.supabase.table("user_subscriptions")\
                    .update(update_data)\
                    .eq("user_id", user_id)\
                    .execute()
            else:
                # Insert new record
                logger.info(f"Creating new subscription for user {user_id}")
                result = self.supabase.table("user_subscriptions")\
                    .insert({"user_id": user_id, **update_data})\
                    .execute()
            
            logger.info(f"Database update result: {result.data if result.data else 'No data returned'}")
            
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
    
    async def cancel_stripe_subscription(self, user_id: str) -> bool:
        """Cancel a Stripe subscription"""
        try:
            # Get user subscription
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                logger.error(f"No subscription found for user {user_id}")
                return False
            
            # Get Stripe subscription ID from metadata or database
            stripe_subscription_id = subscription.get("stripe_subscription_id")
            if not stripe_subscription_id:
                logger.error(f"No Stripe subscription ID found for user {user_id}")
                return False
            
            # Cancel subscription in Stripe
            stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            # Update subscription status in database
            self.supabase.table("user_subscriptions")\
                .update({"status": "canceled"})\
                .eq("user_id", user_id)\
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error canceling Stripe subscription: {e}")
            return False
    
    async def get_user_invoices(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's Stripe invoices"""
        try:
            # Get user subscription to find Stripe customer ID
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return []
            
            # Get or create Stripe customer
            stripe_customer_id = await self.get_stripe_customer_id(user_id)
            if not stripe_customer_id:
                return []
            
            # Get invoices from Stripe
            invoices = stripe.Invoice.list(
                customer=stripe_customer_id,
                limit=20
            )
            
            # Format invoices for frontend
            formatted_invoices = []
            for invoice in invoices.data:
                formatted_invoices.append({
                    "id": invoice.id,
                    "amount_paid": invoice.amount_paid,
                    "currency": invoice.currency,
                    "status": invoice.status,
                    "created": invoice.created,
                    "hosted_invoice_url": invoice.hosted_invoice_url,
                    "invoice_pdf": invoice.invoice_pdf,
                    "period_start": invoice.period_start,
                    "period_end": invoice.period_end
                })
            
            return formatted_invoices
            
        except Exception as e:
            logger.error(f"Error getting user invoices: {e}")
            return []
    
    async def get_user_payment_methods(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's Stripe payment methods"""
        try:
            # Get or create Stripe customer
            stripe_customer_id = await self.get_stripe_customer_id(user_id)
            if not stripe_customer_id:
                return []
            
            # Get payment methods from Stripe
            payment_methods = stripe.PaymentMethod.list(
                customer=stripe_customer_id,
                type="card"
            )
            
            # Get customer to check default payment method
            customer = stripe.Customer.retrieve(stripe_customer_id)
            default_payment_method = customer.invoice_settings.default_payment_method
            
            # Format payment methods for frontend
            formatted_methods = []
            for pm in payment_methods.data:
                formatted_methods.append({
                    "id": pm.id,
                    "type": pm.type,
                    "card": {
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                        "exp_month": pm.card.exp_month,
                        "exp_year": pm.card.exp_year
                    } if pm.card else None,
                    "is_default": pm.id == default_payment_method
                })
            
            return formatted_methods
            
        except Exception as e:
            logger.error(f"Error getting payment methods: {e}")
            return []
    
    async def change_subscription_plan(self, user_id: str, new_tier_name: str) -> bool:
        """Change user's subscription plan"""
        try:
            # Get current subscription
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                logger.error(f"No subscription found for user {user_id}")
                return False
            
            # Get new tier information
            tier_result = self.supabase.table("subscription_tiers")\
                .select("*")\
                .eq("tier_name", new_tier_name)\
                .single()\
                .execute()
            
            if not tier_result.data:
                logger.error(f"Tier {new_tier_name} not found")
                return False
            
            new_tier = tier_result.data
            
            # Get Stripe subscription ID
            stripe_subscription_id = subscription.get("stripe_subscription_id")
            if not stripe_subscription_id:
                logger.error(f"No Stripe subscription ID found for user {user_id}")
                return False
            
            # Get new Stripe price ID
            new_price_id = new_tier.get("stripe_price_id_aud")  # Default to AUD
            if not new_price_id:
                logger.error(f"No Stripe price ID for tier {new_tier_name}")
                return False
            
            # Update subscription in Stripe
            stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            stripe.Subscription.modify(
                stripe_subscription_id,
                items=[{
                    'id': stripe_subscription['items']['data'][0].id,
                    'price': new_price_id,
                }],
                proration_behavior='immediate_without_proration'
            )
            
            # Update subscription in database
            await self.update_user_subscription_from_stripe(user_id, {
                "items": {"data": [{"price": {"id": new_price_id}}]},
                "metadata": {"user_id": user_id, "tier_name": new_tier_name}
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error changing subscription plan: {e}")
            return False
    
    async def get_stripe_customer_id(self, user_id: str) -> Optional[str]:
        """Get or retrieve Stripe customer ID for user"""
        try:
            # Check if we have a customer ID stored
            subscription = await self.get_user_subscription(user_id)
            if subscription and subscription.get("stripe_customer_id"):
                return subscription["stripe_customer_id"]
            
            # If no stored customer ID, we might need to create one
            # This would typically be done during the first subscription creation
            return None
            
        except Exception as e:
            logger.error(f"Error getting Stripe customer ID: {e}")
            return None

    async def check_xp_availability(
        self,
        user_id: str,
        generation_type: str,
        include_guidance: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive XP availability check with user guidance
        
        Returns:
        {
            "has_sufficient_xp": bool,
            "xp_balance": int,
            "xp_required": int,
            "xp_deficit": int,
            "message": str,
            "guidance": str (optional),
            "subscription_url": str (optional),
            "current_tier": dict (optional),
            "recommended_tier": dict (optional)
        }
        """
        try:
            # Get user subscription
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return {
                    "has_sufficient_xp": False,
                    "xp_balance": 0,
                    "xp_required": 0,
                    "xp_deficit": 0,
                    "message": "No subscription found. Please subscribe to use this feature.",
                    "guidance": "Get started with any tier to begin creating amazing AI content!" if include_guidance else None,
                    "subscription_url": "/subscriptions" if include_guidance else None
                }
            
            # Get XP cost for generation type
            current_tier = subscription.get("current_level", 0)
            xp_cost = await self.get_xp_cost_for_generation(generation_type, current_tier)
            xp_balance = subscription.get("xp_balance", 0)
            xp_deficit = max(0, xp_cost - xp_balance)
            
            # Basic result structure
            result = {
                "has_sufficient_xp": xp_balance >= xp_cost,
                "xp_balance": xp_balance,
                "xp_required": xp_cost,
                "xp_deficit": xp_deficit,
                "message": "",
                "subscription_url": "/subscriptions" if include_guidance else None
            }
            
            if result["has_sufficient_xp"]:
                result["message"] = f"Ready to generate! This will cost {xp_cost} XP."
                return result
            
            # User doesn't have enough XP - provide guidance
            if include_guidance:
                # Get tier information for recommendations
                try:
                    tiers_result = self.supabase.table("subscription_tiers")\
                        .select("*")\
                        .order("tier_level")\
                        .execute()
                    
                    current_tier_info = None
                    recommended_tier = None
                    
                    if tiers_result.data:
                        # Find current tier info
                        for tier in tiers_result.data:
                            if tier["tier_level"] == current_tier:
                                current_tier_info = tier
                                break
                        
                        # Find recommended tier (lowest tier that would provide enough monthly XP)
                        for tier in tiers_result.data:
                            monthly_allocation = tier.get("monthly_xp_allocation", 0)
                            if monthly_allocation >= xp_deficit:
                                recommended_tier = tier
                                break
                    
                    result["current_tier"] = current_tier_info
                    result["recommended_tier"] = recommended_tier
                    
                    # Generate user-friendly guidance
                    guidance_parts = []
                    
                    if xp_balance == 0:
                        guidance_parts.append("🎮 You're out of XP credits!")
                    else:
                        guidance_parts.append(f"⚡ You need {xp_deficit} more XP credits.")
                    
                    if current_tier == 0:
                        guidance_parts.append("🚀 Choose a subscription tier to start creating amazing AI content!")
                    else:
                        guidance_parts.append("💎 Upgrade your tier or wait for your monthly XP refresh to continue creating.")
                    
                    if recommended_tier:
                        tier_name = recommended_tier.get("tier_display_name", "higher tier")
                        monthly_xp = recommended_tier.get("monthly_xp_allocation", 0)
                        price_aud = recommended_tier.get("monthly_price_aud", 0)
                        guidance_parts.append(f"🎯 Recommended: {tier_name} (A${price_aud}/month) gives you {monthly_xp} XP monthly!")
                    
                    result["guidance"] = " ".join(guidance_parts)
                    
                except Exception as e:
                    logger.error(f"Error getting tier recommendations: {e}")
                    result["guidance"] = "🎮 You need more XP credits. Check out our subscription tiers to keep creating!"
            
            # Set appropriate message
            if current_tier == 0:
                result["message"] = f"Insufficient credits. You need {xp_cost} XP to generate this content."
            else:
                result["message"] = f"Insufficient credits. Need {xp_cost} XP, have {xp_balance} XP ({xp_deficit} XP short)."
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking XP availability for {user_id}: {e}")
            return {
                "has_sufficient_xp": False,
                "xp_balance": 0,
                "xp_required": 0,
                "xp_deficit": 0,
                "message": "Unable to check XP balance. Please try again.",
                "guidance": "Visit the subscriptions page if you continue to have issues." if include_guidance else None,
                "subscription_url": "/subscriptions" if include_guidance else None
            }

# Global subscription service instance
subscription_service = SubscriptionService() 