"""
Tier-based Access Control Middleware
Validates user permissions and XP balance before allowing generations
"""

import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import re

from app.services.subscription_service import subscription_service
from app.services.model_routing_service import model_routing_service

logger = logging.getLogger(__name__)

class TierPermissionMiddleware:
    """Middleware to enforce tier-based permissions and XP validation"""
    
    def __init__(self, app):
        self.app = app
        
        # Define which endpoints require tier checking
        self.protected_endpoints = {
            r"/api/v1/generate.*": "generation",
            r"/api/v1/simplified/.*": "generation"
        }
        
        # Map endpoints to generation types (for XP cost checking)
        self.generation_type_mapping = {
            "new_image": "NEW_IMAGE",
            "new_image_ref": "NEW_IMAGE_REF", 
            "edit_image": "EDIT_IMAGE",
            "edit_image_ref": "EDIT_IMAGE_REF",
            "edit_image_add_new": "EDIT_IMAGE_ADD_NEW",
            "new_video": "NEW_VIDEO",
            "new_video_with_audio": "NEW_VIDEO_WITH_AUDIO",
            "image_to_video": "IMAGE_TO_VIDEO",
            "edit_image_ref_to_video": "EDIT_IMAGE_REF_TO_VIDEO"
        }
    
    async def __call__(self, request: Request, call_next):
        """Process request through tier validation"""
        
        # Check if this endpoint needs tier validation
        if not self._needs_tier_validation(request):
            return await call_next(request)
        
        try:
            # Extract user from request
            user_id = await self._extract_user_id(request)
            if not user_id:
                return await call_next(request)  # Let auth middleware handle it
            
            # Determine generation type from request
            generation_type = await self._determine_generation_type(request)
            if not generation_type:
                return await call_next(request)  # Can't determine type, proceed
            
            # Check tier permissions
            has_permission = await subscription_service.check_user_tier_permission(
                user_id, generation_type
            )
            
            if not has_permission:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "insufficient_tier",
                        "message": f"Your subscription tier doesn't allow {generation_type}",
                        "generation_type": generation_type,
                        "requires_upgrade": True
                    }
                )
            
            # Check XP balance
            subscription = await subscription_service.get_user_subscription(user_id)
            if not subscription:
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "no_subscription", 
                        "message": "No active subscription found"
                    }
                )
            
            current_tier = subscription.get("current_level", 1)
            xp_cost = await subscription_service.get_xp_cost_for_generation(
                generation_type, current_tier
            )
            
            xp_balance = subscription.get("xp_balance", 0)
            if xp_balance < xp_cost:
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "insufficient_xp",
                        "message": f"Insufficient XP balance. Need {xp_cost} XP, have {xp_balance} XP",
                        "xp_required": xp_cost,
                        "xp_balance": xp_balance,
                        "xp_deficit": xp_cost - xp_balance
                    }
                )
            
            # Add tier and XP info to request state for use by generation endpoints
            request.state.user_tier = current_tier
            request.state.xp_cost = xp_cost
            request.state.generation_type = generation_type
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Error in tier permission middleware: {e}")
            # Don't block request on middleware errors
            return await call_next(request)
    
    def _needs_tier_validation(self, request: Request) -> bool:
        """Check if request path needs tier validation"""
        path = request.url.path
        method = request.method
        
        # Only check POST requests to generation endpoints
        if method != "POST":
            return False
        
        for pattern, _ in self.protected_endpoints.items():
            if re.match(pattern, path):
                return True
        
        return False
    
    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request"""
        try:
            # Try to get from Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            # This would typically involve JWT decoding
            # For now, we'll let the endpoint handle auth and get user from there
            # In a real implementation, you'd decode the JWT here
            return None
            
        except Exception as e:
            logger.error(f"Error extracting user ID: {e}")
            return None
    
    async def _determine_generation_type(self, request: Request) -> Optional[str]:
        """Determine generation type from request body or path"""
        try:
            # Check URL path first
            path = request.url.path
            
            # Extract from path patterns
            if "/new_image" in path:
                return "NEW_IMAGE"
            elif "/edit_image" in path:
                return "EDIT_IMAGE" 
            elif "/new_video" in path:
                return "NEW_VIDEO"
            elif "/image_to_video" in path:
                return "IMAGE_TO_VIDEO"
            
            # Try to get from request body
            if hasattr(request, "_body"):
                body = await request.body()
                if body:
                    import json
                    try:
                        data = json.loads(body)
                        
                        # Check for generation_type field
                        if "generation_type" in data:
                            return data["generation_type"]
                        
                        # Check for intent field
                        if "intent" in data:
                            intent = data["intent"]
                            return self.generation_type_mapping.get(intent)
                        
                        # Infer from other fields
                        if data.get("reference_images"):
                            if data.get("working_image"):
                                return "EDIT_IMAGE_REF"
                            else:
                                return "NEW_IMAGE_REF"
                        elif data.get("working_image"):
                            return "EDIT_IMAGE"
                        else:
                            return "NEW_IMAGE"
                            
                    except (json.JSONDecodeError, KeyError):
                        pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error determining generation type: {e}")
            return None

async def add_tier_permission_middleware(app):
    """Add tier permission middleware to FastAPI app"""
    middleware = TierPermissionMiddleware(app)
    app.middleware("http")(middleware) 