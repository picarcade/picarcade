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
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)

class TierPermissionMiddleware:
    """Middleware to enforce tier-based permissions and XP validation"""
    
    def __init__(self, app):
        self.app = app
        
        # Define which endpoints require tier checking
        self.protected_endpoints = {
            r"/api/v1/generation/generate.*": "generation",
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
            "edit_image_ref_to_video": "EDIT_IMAGE_REF_TO_VIDEO",
            "video_edit": "VIDEO_EDIT",
            "video_edit_ref": "VIDEO_EDIT_REF"
        }
    
    async def __call__(self, request: Request, call_next):
        """Process request through tier validation"""
        
        # Debug logging
        logger.info(f"🔍 MIDDLEWARE: Processing request to {request.url.path}")
        
        # Check if this endpoint needs tier validation
        if not self._needs_tier_validation(request):
            logger.info(f"⚪ MIDDLEWARE: {request.url.path} does not need tier validation")
            return await call_next(request)
        
        try:
            # Extract user from request
            user_id = await self._extract_user_id(request)
            if not user_id:
                logger.info(f"⚪ MIDDLEWARE: No user ID found, proceeding without tier validation")
                return await call_next(request)  # Let auth middleware handle it
            
            logger.info(f"🔍 MIDDLEWARE: Found user ID: {user_id}")
            
            # Determine generation type from request
            generation_type = await self._determine_generation_type(request)
            if not generation_type:
                logger.info(f"⚪ MIDDLEWARE: Could not determine generation type, proceeding")
                return await call_next(request)  # Can't determine type, proceed
            
            logger.info(f"🔍 MIDDLEWARE: Determined generation type: {generation_type}")
            
            # Check tier permissions
            has_permission = await subscription_service.check_user_tier_permission(
                user_id, generation_type
            )
            
            if not has_permission:
                logger.warning(f"❌ MIDDLEWARE: User {user_id} lacks permission for {generation_type}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "insufficient_tier",
                        "message": f"Your subscription tier doesn't allow {generation_type}",
                        "generation_type": generation_type,
                        "requires_upgrade": True
                    }
                )
            
            # Check XP balance using comprehensive function
            xp_check = await subscription_service.check_xp_availability(
                user_id=user_id,
                generation_type=generation_type,
                include_guidance=True
            )
            
            if not xp_check["has_sufficient_xp"]:
                # Determine error type and status code
                if xp_check["xp_balance"] == 0 and xp_check["xp_required"] == 0:
                    # No subscription
                    error_type = "no_subscription"
                    logger.warning(f"❌ MIDDLEWARE: No subscription found for user {user_id}")
                else:
                    # Insufficient XP
                    error_type = "insufficient_xp"
                    logger.warning(f"❌ MIDDLEWARE: Insufficient XP for user {user_id} - Need {xp_check['xp_required']}, have {xp_check['xp_balance']}")
                
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": error_type,
                        "message": xp_check["message"],
                        "guidance": xp_check.get("guidance"),
                        "xp_required": xp_check["xp_required"],
                        "xp_balance": xp_check["xp_balance"],
                        "xp_deficit": xp_check["xp_deficit"],
                        "redirect_to_subscriptions": True,
                        "subscription_url": xp_check.get("subscription_url"),
                        "current_tier": xp_check.get("current_tier"),
                        "recommended_tier": xp_check.get("recommended_tier")
                    }
                )
            
            # Add tier and XP info to request state for use by generation endpoints
            current_tier_info = xp_check.get("current_tier", {})
            current_tier = current_tier_info.get("tier_level", 0) if current_tier_info else 0
            xp_cost = xp_check["xp_required"]
            
            request.state.user_tier = current_tier
            request.state.xp_cost = xp_cost
            request.state.generation_type = generation_type
            
            logger.info(f"✅ MIDDLEWARE: Set state - XP Cost: {xp_cost}, Generation Type: {generation_type}, User Tier: {current_tier}")
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"❌ MIDDLEWARE: Error in tier permission middleware: {e}")
            # Don't block request on middleware errors
            return await call_next(request)
    
    def _needs_tier_validation(self, request: Request) -> bool:
        """Check if request path needs tier validation"""
        path = request.url.path
        method = request.method
        
        logger.info(f"🔍 MIDDLEWARE: Checking validation need - Path: {path}, Method: {method}")
        
        # Only check POST requests to generation endpoints
        if method != "POST":
            logger.info(f"⚪ MIDDLEWARE: Skipping non-POST request")
            return False
        
        for pattern, _ in self.protected_endpoints.items():
            if re.match(pattern, path):
                logger.info(f"✅ MIDDLEWARE: Path {path} matches pattern {pattern} - needs validation")
                return True
        
        logger.info(f"⚪ MIDDLEWARE: Path {path} does not match any protected patterns")
        return False
    
    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request using the same logic as get_current_user"""
        try:
            # Get Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                logger.info(f"⚪ MIDDLEWARE: No valid Authorization header found")
                return None
            
            # Extract the token
            access_token = auth_header.split(" ", 1)[1]
            logger.info(f"🔍 MIDDLEWARE: Extracted token: {access_token[:20]}...")
            
            # Use session manager to validate token and get user (same as get_current_user)
            user = await session_manager.get_user_from_token(access_token)
            
            if not user:
                logger.info(f"⚪ MIDDLEWARE: Token validation failed - no user returned")
                return None
            
            user_id = user.get('id')
            logger.info(f"✅ MIDDLEWARE: User validated successfully: {user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"❌ MIDDLEWARE: Error extracting user ID: {e}")
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
            
            # For the main generation endpoint, try to peek at the request body
            if "/api/v1/generation/generate" in path:
                try:
                    # Get the request body
                    body = await request.body()
                    
                    # Reset the request body for the actual endpoint to consume
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
                    
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
                            
                            # Note: The generation endpoint will correct the generation type
                            # after the simplified flow runs, so we just need a reasonable default here
                                
                            # Infer from other fields in request body
                            has_reference_images = bool(data.get("reference_images"))
                            has_working_image = bool(data.get("working_image"))
                            
                            if has_reference_images:
                                if has_working_image:
                                    return "EDIT_IMAGE_REF"
                                else:
                                    return "NEW_IMAGE_REF"
                            elif has_working_image:
                                return "EDIT_IMAGE"
                            else:
                                return "NEW_IMAGE"
                                
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.error(f"❌ MIDDLEWARE: Error parsing request body: {e}")
                except Exception as e:
                    logger.error(f"❌ MIDDLEWARE: Error reading request body: {e}")
            
            # Default fallback
            return "NEW_IMAGE"
            
        except Exception as e:
            logger.error(f"❌ MIDDLEWARE: Error determining generation type: {e}")
            return "NEW_IMAGE"  # Safe default

async def add_tier_permission_middleware(app):
    """Add tier permission middleware to FastAPI app"""
    middleware = TierPermissionMiddleware(app)
    app.middleware("http")(middleware) 