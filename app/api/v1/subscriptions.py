"""
Subscription Management API Endpoints
Handles subscription tiers, user subscriptions, XP tracking, and Stripe integration
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import stripe
import os
import logging

from app.api.v1.auth import get_current_user
from app.services.subscription_service import subscription_service
from app.services.model_routing_service import model_routing_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Configure Stripe
from app.core.config import settings
stripe.api_key = settings.stripe_secret_key
stripe_webhook_secret = settings.stripe_webhook_secret

# Request/Response Models
class CreateSubscriptionRequest(BaseModel):
    tier_name: str
    payment_method_id: str
    currency: str = "usd"

class XPTransactionResponse(BaseModel):
    id: str
    transaction_type: str
    amount: int
    balance_after: int
    generation_type: Optional[str]
    model_used: Optional[str]
    description: Optional[str]
    created_at: str

class SubscriptionResponse(BaseModel):
    id: str
    tier_name: str
    tier_level: int
    tier_display_name: str
    status: str
    xp_balance: int
    xp_allocated_this_period: int
    xp_used_this_period: int
    current_period_end: Optional[str]
    trial_end: Optional[str]

class TierResponse(BaseModel):
    id: str
    tier_name: str
    tier_level: int
    tier_display_name: str
    tier_description: str
    monthly_price_usd: float
    monthly_price_aud: float
    monthly_xp_allocation: int
    ai_models_included: List[str]
    generation_types_allowed: List[str]
    tier_icon: str
    tier_color: str
    priority_processing: bool

@router.get("/tiers", response_model=List[TierResponse])
async def get_subscription_tiers():
    """Get all available subscription tiers"""
    try:
        tiers = await subscription_service.get_subscription_tiers()
        return tiers
    except Exception as e:
        logger.error(f"Error fetching tiers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription tiers")

@router.get("/current", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(current_user: dict = Depends(get_current_user)):
    """Get current user's subscription details"""
    try:
        user_id = current_user["id"]
        subscription = await subscription_service.get_user_subscription(user_id)
        
        if not subscription:
            # Create trial subscription for new users
            trial_created = await subscription_service.create_trial_subscription(user_id)
            if trial_created:
                subscription = await subscription_service.get_user_subscription(user_id)
        
        if subscription and subscription.get("subscription_tiers"):
            tier = subscription["subscription_tiers"]
            return SubscriptionResponse(
                id=subscription["id"],
                tier_name=tier["tier_name"],
                tier_level=tier["tier_level"],
                tier_display_name=tier["tier_display_name"],
                status=subscription["status"],
                xp_balance=subscription["xp_balance"],
                xp_allocated_this_period=subscription["xp_allocated_this_period"],
                xp_used_this_period=subscription["xp_used_this_period"],
                current_period_end=subscription.get("current_period_end"),
                trial_end=subscription.get("trial_end")
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Error fetching user subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription")

@router.post("/create")
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new subscription with Stripe"""
    try:
        user_id = current_user["id"]
        user_email = current_user.get("email")
        
        if not user_email:
            raise HTTPException(status_code=400, detail="User email required")
        
        # Create or get Stripe customer
        stripe_customer_id = await subscription_service.create_stripe_customer(
            user_id=user_id,
            email=user_email,
            name=current_user.get("user_metadata", {}).get("full_name")
        )
        
        if not stripe_customer_id:
            raise HTTPException(status_code=500, detail="Failed to create Stripe customer")
        
        # Attach payment method to customer
        stripe.PaymentMethod.attach(
            request.payment_method_id,
            customer=stripe_customer_id,
        )
        
        # Set as default payment method
        stripe.Customer.modify(
            stripe_customer_id,
            invoice_settings={
                "default_payment_method": request.payment_method_id,
            },
        )
        
        # Create subscription
        subscription_result = await subscription_service.create_stripe_subscription(
            user_id=user_id,
            tier_name=request.tier_name,
            customer_id=stripe_customer_id,
            payment_method_id=request.payment_method_id,
            currency=request.currency
        )
        
        if not subscription_result:
            raise HTTPException(status_code=500, detail="Failed to create subscription")
        
        return {
            "success": True,
            "subscription_id": subscription_result["subscription_id"],
            "status": subscription_result["status"],
            "message": "Subscription created successfully"
        }
        
    except stripe.CardError as e:
        logger.error(f"Stripe card error: {e}")
        raise HTTPException(status_code=400, detail=f"Card error: {e.user_message}")
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")

@router.get("/xp/balance")
async def get_xp_balance(current_user: dict = Depends(get_current_user)):
    """Get user's current XP balance"""
    try:
        user_id = current_user["id"]
        balance = await subscription_service.get_user_xp_balance(user_id)
        
        return {
            "xp_balance": balance,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error fetching XP balance: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch XP balance")

@router.get("/xp/transactions", response_model=List[XPTransactionResponse])
async def get_xp_transactions(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get user's XP transaction history"""
    try:
        user_id = current_user["id"]
        transactions = await subscription_service.get_user_xp_transactions(user_id, limit)
        
        return [
            XPTransactionResponse(
                id=t["id"],
                transaction_type=t["transaction_type"],
                amount=t["amount"],
                balance_after=t["balance_after"],
                generation_type=t.get("generation_type"),
                model_used=t.get("model_used"),
                description=t.get("description"),
                created_at=t["created_at"]
            )
            for t in transactions
        ]
        
    except Exception as e:
        logger.error(f"Error fetching XP transactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch XP transactions")

@router.get("/xp/cost/{generation_type}")
async def get_xp_cost(
    generation_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Get XP cost for a specific generation type"""
    try:
        user_id = current_user["id"]
        
        # Get user's tier level
        subscription = await subscription_service.get_user_subscription(user_id)
        user_tier = subscription.get("current_level", 1) if subscription else 1
        
        # Get XP cost
        xp_cost = await subscription_service.get_xp_cost_for_generation(generation_type, user_tier)
        
        # Check if user has permission for this generation type
        has_permission = await subscription_service.check_user_tier_permission(user_id, generation_type)
        
        return {
            "generation_type": generation_type,
            "xp_cost": xp_cost,
            "user_tier": user_tier,
            "has_permission": has_permission
        }
        
    except Exception as e:
        logger.error(f"Error getting XP cost: {e}")
        raise HTTPException(status_code=500, detail="Failed to get XP cost")

@router.post("/xp/deduct")
async def deduct_xp(
    generation_id: str,
    generation_type: str,
    model_used: str,
    xp_cost: int,
    actual_cost_usd: float,
    current_user: dict = Depends(get_current_user)
):
    """Deduct XP for a generation (called by generation service)"""
    try:
        user_id = current_user["id"]
        
        # Get routing decision for this generation
        routing_decision = await model_routing_service.determine_optimal_model(
            generation_type=generation_type,
            user_id=user_id
        )
        
        success = await subscription_service.deduct_xp_for_generation(
            user_id=user_id,
            generation_id=generation_id,
            generation_type=generation_type,
            model_used=model_used,
            xp_cost=xp_cost,
            actual_cost_usd=actual_cost_usd,
            routing_decision=routing_decision.routing_logic if routing_decision else {}
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Insufficient XP balance")
        
        # Get new balance
        new_balance = await subscription_service.get_user_xp_balance(user_id)
        
        return {
            "success": True,
            "new_balance": new_balance,
            "deducted": xp_cost
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deducting XP: {e}")
        raise HTTPException(status_code=500, detail="Failed to deduct XP")

@router.get("/routing/recommend/{generation_type}")
async def get_model_recommendation(
    generation_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Get optimal model recommendation for generation type"""
    try:
        user_id = current_user["id"]
        
        # Get routing decision
        decision = await model_routing_service.determine_optimal_model(
            generation_type=generation_type,
            user_id=user_id
        )
        
        if not decision:
            raise HTTPException(status_code=400, detail="No suitable model found for your tier")
        
        return {
            "generation_type": generation_type,
            "recommended_model": decision.selected_model,
            "provider": decision.provider,
            "xp_cost": decision.xp_cost,
            "actual_cost_usd": decision.actual_cost_usd,
            "reasoning": decision.reasoning,
            "tier_requirement": decision.tier_requirement
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model recommendation: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendation")

@router.get("/analytics/usage")
async def get_user_analytics(current_user: dict = Depends(get_current_user)):
    """Get user's usage analytics and recommendations"""
    try:
        user_id = current_user["id"]
        
        # Get recommendations
        recommendations = await model_routing_service.get_model_recommendations(user_id)
        
        # Get current subscription
        subscription = await subscription_service.get_user_subscription(user_id)
        
        # Get recent transactions for usage breakdown
        transactions = await subscription_service.get_user_xp_transactions(user_id, limit=100)
        
        # Calculate usage statistics
        total_spent = sum(abs(t["amount"]) for t in transactions if t["transaction_type"] == "deduction")
        generations_count = len([t for t in transactions if t["transaction_type"] == "deduction"])
        
        return {
            "user_id": user_id,
            "current_tier": subscription.get("current_level", 1) if subscription else 1,
            "xp_balance": subscription.get("xp_balance", 0) if subscription else 0,
            "total_xp_spent": total_spent,
            "total_generations": generations_count,
            "recommendations": recommendations,
            "usage_breakdown": {
                "models": recommendations.get("usage_patterns", {}).get("models", {}),
                "generation_types": recommendations.get("usage_patterns", {}).get("generation_types", {})
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching user analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        if not stripe_webhook_secret:
            logger.warning("Stripe webhook secret not configured")
            # In development, you might want to skip signature verification
            event = stripe.Event.construct_from(
                await request.json(), stripe.api_key
            )
        else:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, stripe_webhook_secret
                )
            except ValueError:
                logger.error("Invalid payload in webhook")
                raise HTTPException(status_code=400, detail="Invalid payload")
            except stripe.SignatureVerificationError:
                logger.error("Invalid signature in webhook")
                raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        success = await subscription_service.handle_stripe_webhook(
            event["type"],
            event["data"]["object"]
        )
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Webhook processing failed")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")

@router.post("/trial/create")
async def create_trial(current_user: dict = Depends(get_current_user)):
    """Create a trial subscription for the user"""
    try:
        user_id = current_user["id"]
        
        # Check if user already has a subscription
        existing = await subscription_service.get_user_subscription(user_id)
        if existing:
            return {
                "success": False,
                "message": "User already has a subscription"
            }
        
        # Create trial
        success = await subscription_service.create_trial_subscription(user_id)
        
        if success:
            return {
                "success": True,
                "message": "Trial subscription created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create trial")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating trial: {e}")
        raise HTTPException(status_code=500, detail="Failed to create trial")

@router.get("/permissions/{generation_type}")
async def check_generation_permission(
    generation_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if user has permission for a generation type"""
    try:
        user_id = current_user["id"]
        
        has_permission = await subscription_service.check_user_tier_permission(
            user_id, generation_type
        )
        
        # Get subscription info for context
        subscription = await subscription_service.get_user_subscription(user_id)
        current_tier = subscription.get("current_level", 1) if subscription else 1
        
        return {
            "generation_type": generation_type,
            "has_permission": has_permission,
            "current_tier": current_tier,
            "requires_upgrade": not has_permission
        }
        
    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        raise HTTPException(status_code=500, detail="Failed to check permission") 