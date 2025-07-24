"""
Model Routing Service
Handles smart routing decisions for optimal AI model selection
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from app.core.database import db_manager
from app.services.subscription_service import subscription_service

logger = logging.getLogger(__name__)

@dataclass
class RoutingDecision:
    """Represents a model routing decision"""
    selected_model: str
    provider: str
    xp_cost: int
    actual_cost_usd: float
    reasoning: str
    fallback_used: bool = False
    tier_requirement: int = 1
    routing_logic: Dict[str, Any] = None

class ModelRoutingService:
    """Service for smart AI model routing and selection"""
    
    def __init__(self):
        self.supabase = db_manager.supabase
        self._routing_cache = {}  # Cache routing rules for performance
        
    async def get_routing_rules(self, refresh_cache: bool = False) -> List[Dict[str, Any]]:
        """Get all active routing rules with caching"""
        if refresh_cache or not self._routing_cache:
            try:
                result = self.supabase.table("model_routing_rules")\
                    .select("*")\
                    .eq("is_active", True)\
                    .order("generation_type, tier_requirement, priority")\
                    .execute()
                
                self._routing_cache = result.data
                logger.info(f"Loaded {len(self._routing_cache)} routing rules")
                
            except Exception as e:
                logger.error(f"Error loading routing rules: {e}")
                return []
        
        return self._routing_cache
    
    async def determine_optimal_model(
        self,
        generation_type: str,
        user_id: str,
        prompt: str = "",
        user_preferences: Dict[str, Any] = None
    ) -> Optional[RoutingDecision]:
        """
        Determine the optimal model for a generation request
        
        Args:
            generation_type: Type of generation (NEW_IMAGE, NEW_VIDEO, etc.)
            user_id: User making the request
            prompt: User's prompt (for context-aware routing)
            user_preferences: User's model preferences
            
        Returns:
            RoutingDecision with selected model and reasoning
        """
        try:
            # Get user subscription and tier
            subscription = await subscription_service.get_user_subscription(user_id)
            if not subscription:
                logger.warning(f"No subscription found for user {user_id}")
                return None
            
            user_tier = subscription.get("current_level", 1)
            tier_info = subscription.get("subscription_tiers", {})
            
            # Check if generation type is allowed for user's tier
            allowed_types = tier_info.get("generation_types_allowed", [])
            if generation_type not in allowed_types:
                logger.warning(f"Generation type {generation_type} not allowed for tier {user_tier}")
                return None
            
            # Get routing rules
            routing_rules = await self.get_routing_rules()
            
            # Find applicable rules for this generation type and tier
            applicable_rules = [
                rule for rule in routing_rules
                if rule["generation_type"] == generation_type
                and rule["tier_requirement"] <= user_tier
            ]
            
            if not applicable_rules:
                logger.error(f"No routing rules found for {generation_type} with tier {user_tier}")
                return None
            
            # Sort by tier requirement (desc) and priority (asc) to get best match
            applicable_rules.sort(
                key=lambda x: (-x["tier_requirement"], x["priority"])
            )
            
            selected_rule = applicable_rules[0]
            
            # Check if user has enough XP
            xp_balance = await subscription_service.get_user_xp_balance(user_id)
            if xp_balance < selected_rule["xp_cost"]:
                logger.warning(f"Insufficient XP: {xp_balance} < {selected_rule['xp_cost']}")
                return None
            
            # Apply user preferences if available
            preferred_model = self._apply_user_preferences(
                selected_rule,
                user_preferences,
                tier_info.get("ai_models_included", [])
            )
            
            # Create routing decision
            decision = RoutingDecision(
                selected_model=preferred_model or selected_rule["optimal_model"],
                provider=selected_rule["routing_logic"].get("provider", "Unknown"),
                xp_cost=selected_rule["xp_cost"],
                actual_cost_usd=float(selected_rule["cost_per_generation_usd"]),
                reasoning=selected_rule["routing_logic"].get("reason", "Optimal model for generation type"),
                tier_requirement=selected_rule["tier_requirement"],
                routing_logic=selected_rule["routing_logic"],
                fallback_used=False
            )
            
            logger.info(f"Selected model {decision.selected_model} for {generation_type} (tier {user_tier})")
            return decision
            
        except Exception as e:
            logger.error(f"Error determining optimal model: {e}")
            return None
    
    def _apply_user_preferences(
        self,
        selected_rule: Dict[str, Any],
        user_preferences: Dict[str, Any],
        allowed_models: List[str]
    ) -> Optional[str]:
        """Apply user preferences to model selection"""
        if not user_preferences:
            return None
        
        # Check if user has a preferred model for this generation type
        preferred_models = user_preferences.get("preferred_models", {})
        generation_type = selected_rule["generation_type"]
        
        if generation_type in preferred_models:
            preferred_model = preferred_models[generation_type]
            
            # Verify the preferred model is allowed for their tier
            if preferred_model in allowed_models:
                logger.info(f"Using user's preferred model: {preferred_model}")
                return preferred_model
        
        return None
    
    async def apply_fallback_strategy(
        self,
        original_decision: RoutingDecision,
        error_reason: str,
        user_tier: int
    ) -> Optional[RoutingDecision]:
        """Apply fallback model selection when primary model fails"""
        try:
            # Get routing rules for fallback options
            routing_rules = await self.get_routing_rules()
            
            # Find the original rule
            original_rule = None
            for rule in routing_rules:
                if rule["optimal_model"] == original_decision.selected_model:
                    original_rule = rule
                    break
            
            if not original_rule:
                logger.error("Original rule not found for fallback")
                return None
            
            # Get fallback models from the rule
            fallback_models = original_rule.get("fallback_models", [])
            
            if not fallback_models:
                logger.warning("No fallback models configured")
                return None
            
            # Select first available fallback model
            # In a more sophisticated implementation, we could check model availability
            fallback_model = fallback_models[0]
            
            # Create fallback decision
            fallback_decision = RoutingDecision(
                selected_model=fallback_model,
                provider=original_decision.provider,
                xp_cost=original_decision.xp_cost,  # Keep same cost
                actual_cost_usd=original_decision.actual_cost_usd,
                reasoning=f"Fallback due to {error_reason}",
                tier_requirement=original_decision.tier_requirement,
                routing_logic=original_decision.routing_logic,
                fallback_used=True
            )
            
            logger.info(f"Applied fallback: {original_decision.selected_model} -> {fallback_model}")
            return fallback_decision
            
        except Exception as e:
            logger.error(f"Error applying fallback strategy: {e}")
            return None
    
    async def log_routing_decision(
        self,
        user_id: str,
        generation_id: str,
        decision: RoutingDecision,
        success: bool,
        response_time_ms: int = None,
        error_message: str = None
    ):
        """Log routing decision for analytics and learning"""
        try:
            # Log to model usage analytics
            await self._update_model_analytics(
                decision.selected_model,
                decision.provider,
                success,
                decision.actual_cost_usd,
                decision.xp_cost,
                response_time_ms
            )
            
            # Log routing decision details
            log_data = {
                "user_id": user_id,
                "generation_id": generation_id,
                "selected_model": decision.selected_model,
                "provider": decision.provider,
                "generation_type": decision.routing_logic.get("generation_type"),
                "xp_cost": decision.xp_cost,
                "actual_cost_usd": decision.actual_cost_usd,
                "fallback_used": decision.fallback_used,
                "tier_requirement": decision.tier_requirement,
                "success": success,
                "response_time_ms": response_time_ms,
                "error_message": error_message,
                "routing_reasoning": decision.reasoning,
                "routing_logic": decision.routing_logic
            }
            
            # Store in database (you might want to create a routing_decisions table)
            logger.info(f"Routing decision logged: {decision.selected_model} for {generation_id}")
            
        except Exception as e:
            logger.error(f"Error logging routing decision: {e}")
    
    async def _update_model_analytics(
        self,
        model_name: str,
        provider: str,
        success: bool,
        cost_usd: float,
        xp_spent: int,
        response_time_ms: int = None
    ):
        """Update model usage analytics"""
        try:
            from datetime import date
            today = date.today()
            
            # Get existing analytics record
            result = self.supabase.table("model_usage_analytics")\
                .select("*")\
                .eq("model_name", model_name)\
                .eq("date_recorded", today.isoformat())\
                .execute()
            
            if result.data:
                # Update existing record
                analytics = result.data[0]
                
                updated_data = {
                    "total_uses": analytics["total_uses"] + 1,
                    "successful_uses": analytics["successful_uses"] + (1 if success else 0),
                    "failed_uses": analytics["failed_uses"] + (0 if success else 1),
                    "total_cost_usd": float(analytics["total_cost_usd"]) + cost_usd,
                    "total_xp_spent": analytics["total_xp_spent"] + xp_spent
                }
                
                # Update average response time if provided
                if response_time_ms and success:
                    current_avg = analytics.get("avg_response_time_ms", 0) or 0
                    successful_uses = analytics["successful_uses"]
                    new_avg = ((current_avg * successful_uses) + response_time_ms) / (successful_uses + 1)
                    updated_data["avg_response_time_ms"] = int(new_avg)
                
                self.supabase.table("model_usage_analytics")\
                    .update(updated_data)\
                    .eq("id", analytics["id"])\
                    .execute()
            
            else:
                # Create new record
                new_analytics = {
                    "model_name": model_name,
                    "provider": provider,
                    "generation_type": "mixed",  # Could be more specific
                    "total_uses": 1,
                    "successful_uses": 1 if success else 0,
                    "failed_uses": 0 if success else 1,
                    "total_cost_usd": cost_usd,
                    "total_xp_spent": xp_spent,
                    "avg_response_time_ms": response_time_ms if success else None,
                    "date_recorded": today.isoformat()
                }
                
                self.supabase.table("model_usage_analytics")\
                    .insert(new_analytics)\
                    .execute()
            
        except Exception as e:
            logger.error(f"Error updating model analytics: {e}")
    
    async def get_model_recommendations(
        self, 
        user_id: str
    ) -> Dict[str, Any]:
        """Get model recommendations based on user's usage patterns"""
        try:
            # Get user's XP transaction history
            transactions = await subscription_service.get_user_xp_transactions(user_id, limit=100)
            
            # Analyze usage patterns
            model_usage = {}
            generation_types = {}
            
            for transaction in transactions:
                if transaction["transaction_type"] == "deduction":
                    model = transaction.get("model_used")
                    gen_type = transaction.get("generation_type")
                    
                    if model:
                        model_usage[model] = model_usage.get(model, 0) + 1
                    
                    if gen_type:
                        generation_types[gen_type] = generation_types.get(gen_type, 0) + 1
            
            # Get most used models and generation types
            most_used_model = max(model_usage.items(), key=lambda x: x[1])[0] if model_usage else None
            most_used_gen_type = max(generation_types.items(), key=lambda x: x[1])[0] if generation_types else None
            
            # Get subscription info for tier recommendations
            subscription = await subscription_service.get_user_subscription(user_id)
            current_tier = subscription.get("current_level", 1) if subscription else 1
            
            recommendations = {
                "most_used_model": most_used_model,
                "most_used_generation_type": most_used_gen_type,
                "current_tier": current_tier,
                "usage_patterns": {
                    "models": model_usage,
                    "generation_types": generation_types
                }
            }
            
            # Add tier upgrade recommendations
            if current_tier < 3:
                # Check if user is trying generation types not available in their tier
                routing_rules = await self.get_routing_rules()
                higher_tier_types = [
                    rule["generation_type"] for rule in routing_rules
                    if rule["tier_requirement"] > current_tier
                ]
                
                attempted_higher_tier = any(
                    gen_type in higher_tier_types 
                    for gen_type in generation_types.keys()
                )
                
                if attempted_higher_tier:
                    recommendations["upgrade_recommended"] = True
                    recommendations["upgrade_reason"] = "Access to more generation types"
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting model recommendations: {e}")
            return {}
    
    async def update_routing_rules_based_on_analytics(self):
        """Update routing rules based on performance analytics"""
        try:
            # Get recent analytics data
            from datetime import date, timedelta
            week_ago = date.today() - timedelta(days=7)
            
            result = self.supabase.table("model_usage_analytics")\
                .select("*")\
                .gte("date_recorded", week_ago.isoformat())\
                .execute()
            
            analytics_data = result.data
            
            # Analyze performance by model
            model_performance = {}
            for record in analytics_data:
                model = record["model_name"]
                if model not in model_performance:
                    model_performance[model] = {
                        "total_uses": 0,
                        "success_rate": 0,
                        "avg_response_time": 0,
                        "avg_quality": 0
                    }
                
                perf = model_performance[model]
                perf["total_uses"] += record["total_uses"]
                
                if record["total_uses"] > 0:
                    success_rate = record["successful_uses"] / record["total_uses"]
                    perf["success_rate"] = (perf["success_rate"] + success_rate) / 2
                
                if record["avg_response_time_ms"]:
                    perf["avg_response_time"] = (perf["avg_response_time"] + record["avg_response_time_ms"]) / 2
                
                if record["avg_quality_score"]:
                    perf["avg_quality"] = (perf["avg_quality"] + float(record["avg_quality_score"])) / 2
            
            # TODO: Implement rule optimization logic based on performance data
            # For now, just log the insights
            logger.info(f"Model performance analysis: {model_performance}")
            
        except Exception as e:
            logger.error(f"Error updating routing rules: {e}")

# Global model routing service instance
model_routing_service = ModelRoutingService() 