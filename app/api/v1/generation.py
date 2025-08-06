from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from fastapi.exceptions import RequestValidationError
import uuid
import time
import re
from datetime import datetime

from app.core.database import db_manager
from app.models.generation import GenerationRequest, GenerationResponse
from app.services.intent_parser import BasicIntentParser
from app.services.model_router import ModelRouter
import importlib
import app.services.generators.runway
import app.services.generators.replicate
import app.services.generators.google_ai

# Force reload of generator modules to pick up code changes
importlib.reload(app.services.generators.runway)
importlib.reload(app.services.generators.replicate)
importlib.reload(app.services.generators.google_ai)

from app.services.generators.runway import RunwayGenerator
from app.services.generators.replicate import ReplicateGenerator
from app.services.generators.google_ai import VertexAIGenerator
from app.services.session_manager import session_manager
from app.services.reference_service import ReferenceService
from app.services.virtual_tryon import VirtualTryOnService
from app.services.simplified_flow_service import simplified_flow
from app.core.logging import api_logger
from app.api.v1.auth import get_current_user
from app.core.model_config import model_config
from typing import Optional, Dict, Any

router = APIRouter()

# Initialize services
intent_parser = BasicIntentParser()
model_router = ModelRouter()
# Enhanced workflow service removed - using simplified_flow instead

# Initialize generators  
def get_runway_generator():
    """Create a FRESH Runway generator instance - no caching!"""
    return app.services.generators.runway.RunwayGenerator()

def get_replicate_generator():
    """Create a FRESH Replicate generator instance - no caching!"""
    return app.services.generators.replicate.ReplicateGenerator()

def get_vertex_ai_generator():
    """Create a FRESH Vertex AI generator instance - no caching!"""
    try:
        return app.services.generators.google_ai.VertexAIGenerator()
    except ValueError as e:
        print(f"[WARNING] Vertex AI generator not available: {e}")
        return None

# Keep module-level instances for backward compatibility, but allow fresh creation
runway_generator = get_runway_generator()
replicate_generator = get_replicate_generator()
vertex_ai_generator = get_vertex_ai_generator()  # This can be None if not configured

# Initialize virtual try-on service
virtual_tryon_service = VirtualTryOnService()

def _determine_reference_type(uri: str) -> str:
    """
    Determine if a reference is an image or video based on its URI.
    
    Args:
        uri: The URI of the reference
        
    Returns:
        "image" or "video" based on the file extension or URL pattern
    """
    # Video file extensions
    video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv']
    
    # Check for video file extensions in the URI
    uri_lower = uri.lower()
    for ext in video_extensions:
        if ext in uri_lower:
            return "video"
    
    # Check for video-related keywords in the URL
    video_keywords = ['video', 'mp4', 'webm', 'mov']
    for keyword in video_keywords:
        if keyword in uri_lower:
            return "video"
    
    # Default to image if no video indicators found
    return "image"

@router.post("/generate", response_model=GenerationResponse)
async def generate_content(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    SIMPLIFIED FLOW: Main generation endpoint using CSV-based decision matrix
    """
    
    generation_id = f"gen_{uuid.uuid4().hex[:12]}"
    start_time = time.time()
    
    # DEBUG: Log request details to help diagnose 422 errors
    api_logger.debug("Generation request received", extra={
        "generation_id": generation_id,
        "prompt_length": len(request.prompt) if request.prompt else 0,
        "user_id": request.user_id,
        "session_id": request.session_id,
        "quality_priority": request.quality_priority,
        "uploaded_images_count": len(request.uploaded_images) if request.uploaded_images else 0,
        "current_user": current_user is not None
    })
    
    try:
        # Import simplified flow service
        from app.services.simplified_flow_service import simplified_flow
        
        # Get current working image from session if available
        current_working_image = None
        api_logger.debug("API request details", extra={"session_id": request.session_id, "user_id": request.user_id})
        
        # Auto-generate session ID if not provided (for conversational continuity)
        effective_session_id = request.session_id
        if not effective_session_id:
            timestamp = int(time.time())
            effective_session_id = f"auto_session_{request.user_id}_{timestamp}"
            api_logger.debug("Auto-generated session_id", extra={"session_id": effective_session_id})
        
        try:
            current_working_image = await session_manager.get_current_working_image(effective_session_id)
            api_logger.debug("Retrieved working image", extra={"working_image": current_working_image})
        except Exception as session_error:
            api_logger.warning("Session manager error, continuing without working image", extra={
                "session_id": effective_session_id,
                "error": str(session_error)
            })
            current_working_image = None
        
        # Get current working video for video editing (if method exists)
        current_working_video = request.current_working_video
        try:
            if hasattr(session_manager, 'get_current_working_video'):
                current_working_video = current_working_video or await session_manager.get_current_working_video(effective_session_id)
                api_logger.debug("Retrieved working video", extra={"working_video": current_working_video})
        except Exception as session_error:
            api_logger.warning("Session manager error retrieving working video", extra={
                "session_id": effective_session_id,
                "error": str(session_error)
            })
            current_working_video = None
        
        # Validate working image
        if current_working_image:
            if not current_working_image.startswith(('http://', 'https://')):
                api_logger.debug("Invalid working image URL format", extra={"working_image": current_working_image})
                current_working_image = None
            elif len(current_working_image.strip()) == 0:
                api_logger.debug("Empty working image URL")
                current_working_image = None
            else:
                api_logger.debug("Valid working image found", extra={"working_image": current_working_image})
        
        # SIMPLIFIED FLOW: Determine boolean flags for CSV decision matrix
        active_image = bool(current_working_image)
        active_video = bool(current_working_video)
        uploaded_image = bool(request.uploaded_images and len(request.uploaded_images) > 0)
        referenced_image = bool(ReferenceService.has_references(request.prompt))
        
        api_logger.debug("Simplified flow flags", extra={
            "active_image": active_image,
            "active_video": active_video, 
            "uploaded_image": uploaded_image, 
            "referenced_image": referenced_image
        })
        
        # Process through simplified flow
        flow_result = await simplified_flow.process_user_request(
            user_prompt=request.prompt,
            active_image=active_image,
            active_video=active_video,
            uploaded_image=uploaded_image,
            referenced_image=referenced_image,
            context={
                "user_id": request.user_id,
                "session_id": effective_session_id,
                "working_image": current_working_image,
                "working_video": current_working_video,
                "uploaded_images": request.uploaded_images or []
            },
            user_id=request.user_id  # Pass user_id for Sprint 3 infrastructure
        )
        
        api_logger.debug("Simplified flow result", extra={
            "prompt_type": flow_result.prompt_type.value,
            "model": flow_result.model_to_use,
            "enhanced_prompt_length": len(flow_result.enhanced_prompt)
        })

        # Update request state with correct generation type from simplified flow
        if hasattr(http_request.state, 'generation_type'):
            # Override middleware's generation type with the correct one from simplified flow
            correct_generation_type = flow_result.prompt_type.value
            original_generation_type = getattr(http_request.state, 'generation_type', 'unknown')
            
            if correct_generation_type != original_generation_type:
                api_logger.info(f"🔄 GENERATION: Updating generation type from {original_generation_type} to {correct_generation_type}")
                http_request.state.generation_type = correct_generation_type
                
                # Also update XP cost based on correct generation type
                from app.services.subscription_service import subscription_service
                user_tier = getattr(http_request.state, 'user_tier', 0)
                correct_xp_cost = await subscription_service.get_xp_cost_for_generation(
                    correct_generation_type, user_tier
                )
                original_xp_cost = getattr(http_request.state, 'xp_cost', 0)
                
                if correct_xp_cost != original_xp_cost:
                    api_logger.info(f"🔄 GENERATION: Updating XP cost from {original_xp_cost} to {correct_xp_cost}")
                    http_request.state.xp_cost = correct_xp_cost
        
        # Handle reference processing if needed
        reference_images = []
        if referenced_image:
            api_logger.debug("Processing references from prompt")
            if current_working_image:
                # For EDIT_IMAGE_REF and EDIT_IMAGE_ADD_NEW, skip reference service enhancement to preserve our structured prompt
                if flow_result.prompt_type.value in ["EDIT_IMAGE_REF", "EDIT_IMAGE_ADD_NEW"]:
                    api_logger.debug("Keeping structured prompt for", extra={"prompt_type": flow_result.prompt_type.value, "enhanced_prompt_length": len(flow_result.enhanced_prompt)})
                    
                    # Just parse references without enhancing the prompt
                    reference_images, missing_tags = await ReferenceService.parse_reference_mentions(
                        request.prompt,  # Use original prompt to find @mentions
                        request.user_id
                    )
                    if missing_tags:
                        api_logger.debug("Missing references", extra={"missing_tags": missing_tags})
                        
                    # For EDIT_IMAGE_ADD_NEW, manually add working image reference since we skipped ReferenceService enhancement
                    if flow_result.prompt_type.value == "EDIT_IMAGE_ADD_NEW":
                        from app.models.generation import ReferenceImage
                        working_image_ref = ReferenceImage(uri=current_working_image, tag="working_image")
                        reference_images.append(working_image_ref)
                        api_logger.debug("Manually added working image reference for EDIT_IMAGE_ADD_NEW")
                else:
                    # For other types, use full reference service enhancement
                    enhanced_prompt, reference_images = await ReferenceService.enhance_prompt_with_working_image(
                        flow_result.enhanced_prompt,  # Use our structured enhanced prompt
                        request.user_id, 
                        current_working_image
                    )
                    flow_result.enhanced_prompt = enhanced_prompt
            else:
                # Parse references from original prompt to get reference images
                reference_images, missing_tags = await ReferenceService.parse_reference_mentions(
                    request.prompt,  # Use original prompt to find @mentions
                    request.user_id
                )
                if missing_tags:
                    api_logger.debug("Missing references", extra={"missing_tags": missing_tags})
            
            # Add working video to reference images if doing video editing
            if current_working_video and flow_result.prompt_type.value in ["VIDEO_EDIT", "VIDEO_EDIT_REF"]:
                from app.models.generation import ReferenceImage
                working_video_ref = ReferenceImage(uri=current_working_video, tag="working_video")
                reference_images.append(working_video_ref)
                api_logger.debug("Added working video reference for VIDEO_EDIT")
            
            api_logger.debug("Found reference images", extra={"count": len(reference_images)})
        
        # Convert simplified flow result to legacy format for compatibility
        from app.models.generation import IntentAnalysis, CreativeIntent
        
        # Map CSV types to legacy intent values
        intent_mapping = {
            "NEW_IMAGE": "generate_image",
            "NEW_IMAGE_REF": "edit_image",  # NEW_IMAGE_REF uses Kontext like editing
            "EDIT_IMAGE": "edit_image", 
            "EDIT_IMAGE_REF": "virtual_tryon" if uploaded_image else "edit_image",
            "EDIT_IMAGE_ADD_NEW": "edit_image",  # New: Adding elements to scenes
            "VIDEO_EDIT": "video_edit",  # New: Video editing with gen4_aleph
            "VIDEO_EDIT_REF": "video_edit"  # New: Video editing with references
        }
        
        basic_intent_value = intent_mapping.get(flow_result.prompt_type.value, "generate_image")
        
        intent_analysis = IntentAnalysis(
            detected_intent=CreativeIntent(basic_intent_value),
            confidence=0.95,  # High confidence from simplified flow
            content_type="general_image",
            reasoning=flow_result.reasoning,
            complexity_level="moderate",
            suggested_model=flow_result.model_to_use,
            suggested_enhancements=[],
            metadata={
                "simplified_flow": True,
                "csv_based": True,
                "workflow_type": flow_result.prompt_type.value,
                "ai_classified": True
            }
        )
        
        # Update request with processed data
        request.prompt = flow_result.enhanced_prompt
        request.current_working_image = current_working_image
        request.reference_images = reference_images
        
        api_logger.debug("Final intent and model", extra={"intent": basic_intent_value, "model": flow_result.model_to_use})
        
        # Handle virtual try-on requests using the existing multi-image workflow
        # Note: Skip the dedicated virtual try-on service for now since it's not implemented
        # Virtual try-on will be handled by the regular generation pipeline with proper model selection
        if intent_analysis.detected_intent.value == "virtual_tryon":
            api_logger.debug("Virtual try-on request detected - using multi-image workflow")
            # Continue with normal generation flow using the enhanced model selection
            # The multi-image kontext model will handle the virtual try-on
        
        # Phase 2: Route to optimal model - SIMPLIFIED using CSV-based decision
        api_logger.debug("Using CSV-based model routing")
        
        # Build context for model parameters
        context = {
            "uploaded_images": request.uploaded_images or [],
            "reference_images": []
        }
        
        # Add working image to context for EDIT_IMAGE_ADD_NEW flows
        if flow_result.prompt_type.value == "EDIT_IMAGE_ADD_NEW" and current_working_image:
            context["working_image"] = current_working_image
            api_logger.debug("Added working image to context for EDIT_IMAGE_ADD_NEW", extra={"working_image": current_working_image})
        
        # Add reference images from ReferenceService processing
        if reference_images:
            for ref_img in reference_images:
                context["reference_images"].append({
                    "url": ref_img.uri,
                    "tag": ref_img.tag
                })
            api_logger.debug("Added reference images from ReferenceService", extra={"count": len(reference_images)})
        
        # Add reference images from request if they exist (fallback/additional)
        if hasattr(request, 'reference_images') and request.reference_images:
            for ref_img in request.reference_images:
                # Avoid duplicates by checking if URI already exists
                existing_urls = [existing["url"] for existing in context["reference_images"]]
                if ref_img.uri not in existing_urls:
                    context["reference_images"].append({
                        "url": ref_img.uri,
                        "tag": ref_img.tag
                    })
                    api_logger.debug("Added additional reference from request", extra={"tag": ref_img.tag})
        
        api_logger.debug("Model parameters context", extra={
            "context": context,
            "flow_type": flow_result.prompt_type.value,
            "model": flow_result.model_to_use
        })
        
        # Get model parameters from simplified flow
        model_params = await simplified_flow.get_model_parameters(flow_result, context)
        
        api_logger.debug("Final model parameters", extra={"params": model_params})
        
        # Create routing decision using simplified flow result
        routing_decision = {
            "model": flow_result.model_to_use,
            "provider": "replicate",  # All CSV models use Replicate
            "parameters": model_params,
            "routing_reason": f"CSV-based flow: {flow_result.reasoning}",
            "estimated_cost": 0.05,  # Default cost estimate
            "estimated_time": 30     # Default time estimate
        }
        
        api_logger.debug("Simplified flow result", extra={"model": flow_result.model_to_use, "params": model_params})
        
        # Phase 3: Execute generation
        selected_model = routing_decision["model"]
        parameters = routing_decision["parameters"]
        
        api_logger.debug("Router selection", extra={
            "model": selected_model,
            "parameters": parameters,
            "routing_reason": routing_decision.get('routing_reason')
        })
        
        # Enhanced image selection logic for virtual try-on scenarios
        image_source = None
        
        # Debug: Log all image sources
        api_logger.debug("Image selection analysis", extra={
            "working_image": current_working_image,
            "uploaded_count": len(request.uploaded_images) if request.uploaded_images else 0,
            "detected_intent": intent_analysis.detected_intent.value if 'intent_analysis' in locals() and intent_analysis else 'unknown',
            "flow_type": flow_result.prompt_type.value if flow_result else 'None'
        })
        
        # Check if this is a reference styling request (virtual try-on OR face swap)
        # Using simplified flow data instead of enhanced_intent
        is_reference_styling = flow_result.prompt_type.value == "EDIT_IMAGE_REF"
        
        # Get flow reasoning for other checks
        flow_reasoning = flow_result.reasoning if flow_result else ''
        
        is_reference_scenario = (
            current_working_image and 
            request.uploaded_images and 
            len(request.uploaded_images) > 0 and
            ('intent_analysis' in locals() and intent_analysis and intent_analysis.detected_intent.value in ["edit_image", "virtual_tryon"]) and
            is_reference_styling
        )
        
        # Check if prompt has @references (for hair styling with reference images)
        has_prompt_references = bool(re.findall(r'@\w+', request.prompt))
        
        # Reference styling (virtual try-on) uses Runway when any images are provided
        # Hair styling uses Runway when uploaded images OR @references in prompt are provided
        uses_runway_references = (
            is_reference_styling and
            (current_working_image or (request.uploaded_images and len(request.uploaded_images) > 0))
        ) or (
            # Hair styling would be EDIT_IMAGE with hair-related reasoning in simplified flow
            flow_result.prompt_type.value == "EDIT_IMAGE" and 
            "hair" in flow_reasoning.lower() and
            (
                (request.uploaded_images and len(request.uploaded_images) > 0) or  # Uploaded reference images
                has_prompt_references  # @references in prompt
            )
        )
        
        api_logger.debug("Reference styling conditions", extra={
            "has_working_image": bool(current_working_image),
            "has_uploaded_images": bool(request.uploaded_images and len(request.uploaded_images) > 0),
            "has_prompt_references": has_prompt_references,
            "is_reference_styling": is_reference_styling,
            "is_reference_scenario": is_reference_scenario,
            "uses_runway_references": uses_runway_references
        })
        
        # Set up Runway reference images for styling workflows
        if uses_runway_references:
            api_logger.debug("Setting up Runway references", extra={"flow_type": flow_result.prompt_type.value})
            
            # Use existing reference images from ReferenceService, plus working image if needed
            runway_reference_images = []
            
            # Add existing @references from prompt (like @charlie)
            if hasattr(request, 'reference_images') and request.reference_images:
                for ref_img in request.reference_images:
                    runway_reference_images.append({
                        "uri": ref_img.uri,
                        "tag": ref_img.tag
                    })
                    api_logger.debug("Added prompt reference", extra={"tag": ref_img.tag, "uri": ref_img.uri})
            
            # Add working image as base reference if not already included
            if current_working_image:
                # Check if working image is already in references (to avoid duplicates)
                working_already_added = any(
                    ref["uri"] == current_working_image 
                    for ref in runway_reference_images
                )
                if not working_already_added:
                    runway_reference_images.append({
                        "uri": current_working_image,
                        "tag": "working_image"
                    })
                    api_logger.debug("Added working image reference", extra={"image": current_working_image})
                else:
                    api_logger.debug("Working image already included in references")
            
            # Add uploaded images as additional references
            if request.uploaded_images:
                for i, uploaded_image in enumerate(request.uploaded_images):
                    runway_reference_images.append({
                        "uri": uploaded_image,
                        "tag": f"reference_{i+1}" if flow_result.prompt_type.value == "EDIT_IMAGE_REF" else f"hair_reference_{i+1}"
                    })
                    api_logger.debug("Added uploaded image reference", extra={"image": uploaded_image})
            
            # Update request with all reference images for Runway generator
            if runway_reference_images:
                from app.models.generation import ReferenceImage
                request.reference_images = [
                    ReferenceImage(uri=ref["uri"], tag=ref["tag"]) 
                    for ref in runway_reference_images
                ]
                api_logger.debug("Set reference images for Runway", extra={"count": len(runway_reference_images)})
                
                # Also add to parameters for backward compatibility
                parameters["reference_images"] = runway_reference_images
                parameters["type"] = "text_to_image_with_references"
        

            parameters["uploaded_image"] = request.uploaded_images[0]
            image_source = f"uploaded_image:{request.uploaded_images[0]}"
            api_logger.debug("Using uploaded image as base for face modification", extra={"image": request.uploaded_images[0]})
            
        elif is_reference_scenario:
            # Virtual try-on: Use working image as person, uploaded as clothing reference
            parameters["image"] = current_working_image  # Primary image (person)
            parameters["uploaded_image"] = current_working_image  # Backward compatibility
            parameters["reference_image"] = request.uploaded_images[0]  # Clothing reference
            image_source = f"virtual_tryon:person={current_working_image},clothing={request.uploaded_images[0]}"
            api_logger.debug("Virtual try-on detected", extra={
                "person_image": current_working_image,
                "clothing_reference": request.uploaded_images[0]
            })
        elif flow_result.prompt_type.value == "NEW_IMAGE_REF":
            # NEW_IMAGE_REF: Use reference image as input for Kontext
            reference_image_url = None
            
            if hasattr(request, 'reference_images') and request.reference_images and len(request.reference_images) > 0:
                # Use first reference image from @mentions
                reference_image_url = request.reference_images[0].uri
                image_source = f"new_image_ref:reference={reference_image_url}"
                api_logger.debug("NEW_IMAGE_REF with @reference", extra={"reference": reference_image_url})
            elif request.uploaded_images and len(request.uploaded_images) > 0:
                # Use uploaded image as reference
                reference_image_url = request.uploaded_images[0]
                image_source = f"new_image_ref:uploaded={reference_image_url}"
                api_logger.debug("NEW_IMAGE_REF with upload", extra={"reference": reference_image_url})
            
            if reference_image_url:
                parameters["image"] = reference_image_url  # Input image for Kontext
                parameters["uploaded_image"] = reference_image_url  # Backward compatibility
                api_logger.debug("NEW_IMAGE_REF using reference as input", extra={"reference": reference_image_url})
            else:
                api_logger.debug("NEW_IMAGE_REF classification but no reference image found", extra={
                    "reference_images": getattr(request, 'reference_images', None),
                    "uploaded_images": request.uploaded_images
                })
        elif current_working_image:
            # Standard editing: Use current working image from session for continued editing
            parameters["uploaded_image"] = current_working_image
            parameters["image"] = current_working_image
            image_source = f"working_image:{current_working_image}"
            api_logger.debug("Using working image from session", extra={"image": current_working_image})
        elif request.uploaded_images and len(request.uploaded_images) > 0:
            # New upload: Use newly uploaded image
            parameters["uploaded_image"] = request.uploaded_images[0]  # Use first uploaded image
            parameters["image"] = request.uploaded_images[0]  # Alternative parameter name
            image_source = f"uploaded_image:{request.uploaded_images[0]}"
            api_logger.debug("Using uploaded image", extra={"image": request.uploaded_images[0]})
        
        # Log image source for debugging
        if selected_model == "flux-kontext":
            api_logger.debug("flux-kontext image info", extra={
                "image": parameters.get('image', 'NO_IMAGE_FOUND'),
                "source": image_source or 'no_image'
            })
            if not parameters.get('image'):
                api_logger.debug("flux-kontext requires image but none provided", extra={
                    "working_image": current_working_image,
                    "uploaded_images": request.uploaded_images,
                    "session_id": request.session_id
                })
        
        # Choose generator based on model - FORCE Runway if references present
        api_logger.debug("Selecting generator", extra={
            "model": selected_model,
            "has_references": bool(request.reference_images)
        })
        
        # NEW: Apply updated video routing logic based on input image/video presence and audio requirements
        is_video_generation = flow_result.prompt_type.value in ["NEW_VIDEO", "NEW_VIDEO_WITH_AUDIO", "IMAGE_TO_VIDEO", "IMAGE_TO_VIDEO_WITH_AUDIO", "EDIT_IMAGE_REF_TO_VIDEO", "VIDEO_EDIT", "VIDEO_EDIT_REF"]
        has_input_image = bool(current_working_image or (request.uploaded_images and len(request.uploaded_images) > 0))
        has_input_video = bool(current_working_video)
        
        # Audio detection - check for audio keywords in prompt or explicit audio request
        audio_keywords = ["singing", "song", "music", "audio", "sound", "voice", "speak", "talk", "lyrics", "melody", "vocal", "narration", "dialogue", "conversation"]
        requires_audio = (flow_result.prompt_type.value in ["NEW_VIDEO_WITH_AUDIO", "IMAGE_TO_VIDEO_WITH_AUDIO"] or 
                         any(keyword in request.prompt.lower() for keyword in audio_keywords)) if is_video_generation else False
        
        if is_video_generation:
            # Video editing requests: Always use gen4_aleph via Runway
            if flow_result.prompt_type.value in ["VIDEO_EDIT", "VIDEO_EDIT_REF"]:
                api_logger.debug("Video editing detected: routing to gen4_aleph via Runway", extra={
                    "prompt_type": flow_result.prompt_type.value,
                    "has_working_video": has_input_video
                })
                selected_model = "gen4_aleph"
                configured_generator = "replicate"  # Route runway models through replicate
                generator = get_replicate_generator()
                
            elif requires_audio:
                # Audio requests: Use VEO-3-Fast (only model that supports audio)
                api_logger.debug("Audio video detected: routing to VEO-3-Fast", extra={
                    "prompt_type": flow_result.prompt_type.value,
                    "audio_detected": requires_audio
                })
                selected_model = "google/veo-3-fast"
                configured_generator = "replicate"
            elif has_input_image:
                # Image-to-video: Use Runway directly (bypass Hailuo-02 safety restrictions)
                api_logger.debug("Image-to-video detected: routing directly to Runway", extra={
                    "working_image": current_working_image,
                    "uploaded_images": len(request.uploaded_images) if request.uploaded_images else 0,
                    "reason": "bypassing_hailuo_safety_restrictions"
                })
                selected_model = "gen4_turbo"
                configured_generator = "runway"
            else:
                # Text-to-video (no audio): Use Minimax Hailuo-02 as primary, VEO-3-Fast as fallback
                api_logger.debug("Text-to-video detected: routing to Minimax Hailuo-02", extra={
                    "prompt_type": flow_result.prompt_type.value
                })
                selected_model = "minimax/hailuo-02"
                configured_generator = "replicate"
        else:
            # Check generator configuration from model config
            configured_generator = model_config.get_generator_for_type(flow_result.prompt_type.value)
        
        api_logger.debug("Generator routing decision", extra={
            "selected_model": selected_model,
            "configured_generator": configured_generator,
            "uses_runway_references": uses_runway_references,
            "has_input_image": has_input_image,
            "is_video_generation": is_video_generation,
            "requires_audio": requires_audio if is_video_generation else False,
            "prompt_type": flow_result.prompt_type.value
        })
        
        if uses_runway_references:
            # Image generation with references - keep using runway generator for now
            # TODO: migrate to flux-kontext or another reference-capable model
            api_logger.debug("Using FRESH RunwayGenerator for runway references (image generation)")
            generator = get_runway_generator()  # Create fresh instance!
        elif configured_generator == "runway" or "runway" in selected_model or selected_model in ["gen3a_turbo", "gen4_turbo"]:
            # Video generation - use replicate
            if selected_model == "runway_gen4_image":
                api_logger.debug("Using FRESH RunwayGenerator for image generation", extra={"model": selected_model, "configured_generator": configured_generator})
                generator = get_runway_generator()  # Create fresh instance for image generation
            else:
                api_logger.debug("Using FRESH ReplicateGenerator for runway video models via replicate", extra={"model": selected_model, "configured_generator": configured_generator})
                generator = get_replicate_generator()  # Create fresh instance for video models
            
            # Configure for video editing generation (gen4_aleph)
            if selected_model == "gen4_aleph" and flow_result.prompt_type.value in ["VIDEO_EDIT", "VIDEO_EDIT_REF"]:
                api_logger.debug("Configuring Runway for video editing", extra={
                    "model": selected_model,
                    "working_video": current_working_video,
                    "references": len(reference_images) if reference_images else 0
                })
                parameters["model"] = selected_model
                parameters["type"] = "video_edit"  # Set the correct type
                parameters["promptText"] = flow_result.enhanced_prompt
                parameters["videoUri"] = current_working_video
                parameters["current_working_video"] = current_working_video
                if reference_images:
                    # For video editing, only include image references (Runway gen4_aleph doesn't support video references)
                    image_references = []
                    for ref in reference_images:
                        ref_type = _determine_reference_type(ref.uri)
                        if ref_type == "image":
                            image_references.append({"type": "image", "uri": ref.uri})
                        else:
                            # Log that video references are being filtered out
                            api_logger.warning(f"🎬 VIDEO_EDIT: Filtering out video reference {ref.uri} - gen4_aleph only supports image references")
                    
                    if image_references:
                        parameters["references"] = image_references
                        api_logger.info(f"🎬 VIDEO_EDIT with {len(image_references)} image reference(s)")
                    else:
                        api_logger.info("🎬 VIDEO_EDIT: No valid image references found")
                
                api_logger.info(f"🎬 VIDEO_EDIT configured: {parameters}")
            
            # Configure for image-to-video generation
            elif selected_model in ["gen3a_turbo", "gen4_turbo"] and has_input_image:
                api_logger.debug("Configuring Runway for image-to-video", extra={
                    "model": selected_model,
                    "working_image": current_working_image,
                    "uploaded_images": len(request.uploaded_images) if request.uploaded_images else 0
                })
                parameters["model"] = selected_model
                parameters["type"] = "image_to_video"  # Set the correct type
                parameters["promptText"] = request.prompt
                
                # Set the input image for image-to-video (use both parameter names for compatibility)
                if current_working_image:
                    parameters["image"] = current_working_image
                    parameters["uploaded_image"] = current_working_image
                    api_logger.debug("Using working image for Runway image-to-video", extra={"image": current_working_image})
                elif request.uploaded_images and len(request.uploaded_images) > 0:
                    parameters["image"] = request.uploaded_images[0]
                    parameters["uploaded_image"] = request.uploaded_images[0]
                    api_logger.debug("Using uploaded image for Runway image-to-video", extra={"image": request.uploaded_images[0]})
                
                # Set video generation parameters
                parameters["duration"] = 5  # Default 5 seconds
                if selected_model == "gen3a_turbo":
                    parameters["ratio"] = "1280:768"
                else:  # gen4_turbo
                    parameters["ratio"] = "1280:720"
                    
            # Don't override the type if it was already set by the model router (e.g., "image_to_video")
            elif "type" not in parameters and 'intent_analysis' in locals() and intent_analysis and intent_analysis.detected_intent.value == "generate_video":
                parameters["type"] = "video"
        elif configured_generator == "vertex_ai" or (configured_generator != "replicate" and "veo" in selected_model):
            api_logger.debug("Using FRESH Vertex AI Generator", extra={"model": selected_model, "configured_generator": configured_generator})
            generator = get_vertex_ai_generator()  # Create fresh instance!
            
            if not generator:
                api_logger.error("Vertex AI generator not available - Google Cloud not configured")
                raise HTTPException(
                    status_code=503,
                    detail="Vertex AI generator not available. Google Cloud project not configured."
                )
            
            parameters["model"] = selected_model
            
            # For VEO models that need input images, ensure the working image is passed
            if current_working_image and flow_result.prompt_type.value in ["IMAGE_TO_VIDEO", "IMAGE_TO_VIDEO_WITH_AUDIO", "EDIT_IMAGE_REF_TO_VIDEO"]:
                api_logger.debug("VEO model needs input image", extra={"working_image": current_working_image})
                parameters["image"] = current_working_image
                parameters["uploaded_image"] = current_working_image
        elif configured_generator == "replicate" or "flux" in selected_model or "dall-e" in selected_model or "google" in selected_model or "minimax" in selected_model:
            api_logger.debug("Using FRESH ReplicateGenerator", extra={"model": selected_model, "configured_generator": configured_generator})
            generator = get_replicate_generator()  # Create fresh instance!
            parameters["model"] = selected_model
            
            # Special handling for different models
            if selected_model == "minimax/hailuo-02":
                api_logger.debug("Configuring Minimax Hailuo-02", extra={
                    "prompt": request.prompt,
                    "has_image": has_input_image,
                    "requires_audio": requires_audio
                })
                
                # Hailuo-02 required and default parameters
                parameters["prompt"] = request.prompt
                parameters["prompt_optimizer"] = parameters.get("prompt_optimizer", True)
                parameters["resolution"] = parameters.get("resolution", "1080p")
                parameters["duration"] = parameters.get("duration", 6)
                
                api_logger.debug("Hailuo-02 base parameters", extra={
                    "prompt_optimizer": parameters["prompt_optimizer"],
                    "resolution": parameters["resolution"],
                    "duration": parameters["duration"]
                })
                
                # For text-to-video mode: ensure no image parameters
                parameters.pop("image", None)
                parameters.pop("uploaded_image", None)
                parameters.pop("first_frame_image", None)
                api_logger.debug("Hailuo-02 text-to-video mode", extra={"mode": "text-to-video"})
                
            elif selected_model == "gen3a_turbo" and "runway" in selected_model:
                # Runway image-to-video configuration via replicate
                api_logger.debug("Configuring Runway for image-to-video via replicate", extra={
                    "prompt": request.prompt,
                    "has_image": has_input_image
                })
                
                # Set Runway-specific parameters
                parameters["type"] = "image_to_video"
                parameters["prompt_text"] = request.prompt
                parameters["duration"] = parameters.get("duration", 5)
                parameters["ratio"] = parameters.get("ratio", "1280:720")
                
                # Map the input image to Runway's expected parameter
                if current_working_image:
                    parameters["prompt_image"] = current_working_image
                    parameters["image"] = current_working_image
                    api_logger.debug("Added prompt_image from working image", extra={
                        "image_url": current_working_image[:50] + "...",
                        "mode": "runway-image-to-video"
                    })
                elif request.uploaded_images and len(request.uploaded_images) > 0:
                    parameters["prompt_image"] = request.uploaded_images[0]
                    parameters["image"] = request.uploaded_images[0]
                    api_logger.debug("Added prompt_image from uploaded image", extra={
                        "image_url": request.uploaded_images[0][:50] + "...",
                        "mode": "runway-image-to-video"
                    })
                
                # Remove Hailuo-02 specific parameters
                parameters.pop("prompt_optimizer", None)
                parameters.pop("resolution", None)
                parameters.pop("first_frame_image", None)
                
            elif selected_model == "google/veo-3-fast":
                api_logger.debug("Configuring VEO-3-Fast for text-to-video", extra={"prompt": request.prompt})
                # VEO-3-Fast uses "prompt" parameter instead of "model"
                parameters["prompt"] = request.prompt
                # Remove any image parameters for text-to-video
                parameters.pop("image", None)
                parameters.pop("uploaded_image", None)
                
            # For video models that need input images, ensure the working image is passed
            elif "video" in selected_model and current_working_image and flow_result.prompt_type.value in ["IMAGE_TO_VIDEO", "IMAGE_TO_VIDEO_WITH_AUDIO", "EDIT_IMAGE_REF_TO_VIDEO"]:
                api_logger.debug("Video model needs input image", extra={"working_image": current_working_image})
                parameters["image"] = current_working_image
                parameters["uploaded_image"] = current_working_image
        else:
            api_logger.debug("No matching generator found, falling back", extra={"selected_model": selected_model, "fallback": "flux-1.1-pro"})
            # Default fallback
            generator = get_replicate_generator()  # Create fresh instance!
            parameters["model"] = "flux-1.1-pro"
        
        # Add uploaded images to parameters for generator access
        if request.uploaded_images:
            parameters["uploaded_images"] = request.uploaded_images
            api_logger.debug("Added uploaded_images to parameters", extra={"count": len(request.uploaded_images)})

        # Log final parameters before generation
        if selected_model == "minimax/hailuo-02":
            api_logger.debug("Final Hailuo-02 parameters", extra={
                "all_parameters": {k: v[:50] + "..." if isinstance(v, str) and len(v) > 50 else v 
                                 for k, v in parameters.items()},
                "generation_mode": "text-to-video"
            })
        elif selected_model == "gen3a_turbo" and "runway" in selected_model:
            api_logger.debug("Final Runway parameters via replicate", extra={
                "all_parameters": {k: v[:50] + "..." if isinstance(v, str) and len(v) > 50 else v 
                                 for k, v in parameters.items()},
                "has_prompt_image": "prompt_image" in parameters,
                "generation_mode": "image-to-video"
            })
        
        # Execute generation with fallback support
        result = await generator.generate(
            request.prompt, 
            parameters,
            generation_id=generation_id
        )
        
        # Check for fallback scenarios (only for text-to-video now since image-to-video goes directly to Runway)
        if not result.success and selected_model == "minimax/hailuo-02" and configured_generator == "replicate":
            # Only text-to-video requests use Hailuo-02 now, so fallback to VEO-3-Fast
            if not has_input_image and not requires_audio:
                api_logger.debug("Minimax Hailuo-02 text-to-video failed, falling back to VEO-3-Fast", extra={
                    "error": result.error_message,
                    "fallback_model": "google/veo-3-fast"
                })
                
                try:
                    fallback_parameters = parameters.copy()
                    fallback_parameters["model"] = "google/veo-3-fast"
                    # VEO-3-Fast doesn't support prompt_optimizer, resolution, duration
                    fallback_parameters.pop("prompt_optimizer", None)
                    fallback_parameters.pop("resolution", None)
                    fallback_parameters.pop("duration", None)
                    
                    api_logger.debug("Retrying with VEO-3-Fast fallback", extra={"model": "google/veo-3-fast"})
                    fallback_result = await generator.generate(
                        request.prompt, 
                        fallback_parameters,
                        generation_id=generation_id + "_fallback"
                    )
                    
                    if fallback_result.success:
                        api_logger.info("VEO-3-Fast fallback succeeded", extra={"original_error": result.error_message})
                        result = fallback_result
                        result.model_used = "google/veo-3-fast (fallback)"
                        
                except Exception as fallback_error:
                    api_logger.warning("Fallback to VEO-3-Fast also failed", extra={"fallback_error": str(fallback_error)})
        
        # Calculate total execution time
        total_time = time.time() - start_time
        result.execution_time = total_time
        result.generation_id = generation_id
        
        # Set input image information for debugging/verification
        if selected_model == "flux-kontext":
            result.input_image_used = parameters.get("image")
            if current_working_image:
                result.image_source_type = "working_image" 
            elif request.uploaded_images:
                result.image_source_type = "uploaded"
            else:
                result.image_source_type = "none"
        
        # Update session with newly generated content for future edits
        if result.success and result.output_url:
            # Set working image for image generations
            if flow_result.prompt_type.value in ["NEW_IMAGE", "NEW_IMAGE_REF", "EDIT_IMAGE", "EDIT_IMAGE_REF", "EDIT_IMAGE_ADD_NEW"]:
                api_logger.debug("Setting working image in session", extra={"session_id": effective_session_id, "image_url": result.output_url})
                await session_manager.set_current_working_image(
                    session_id=effective_session_id,
                    image_url=result.output_url,
                    user_id=request.user_id
                )
            
            # Set working video for video generations and edits
            elif flow_result.prompt_type.value in ["NEW_VIDEO", "NEW_VIDEO_WITH_AUDIO", "IMAGE_TO_VIDEO", "IMAGE_TO_VIDEO_WITH_AUDIO", "EDIT_IMAGE_REF_TO_VIDEO", "VIDEO_EDIT", "VIDEO_EDIT_REF"]:
                api_logger.debug("Setting working video in session", extra={"session_id": effective_session_id, "video_url": result.output_url})
                if hasattr(session_manager, 'set_current_working_video'):
                    await session_manager.set_current_working_video(
                        session_id=effective_session_id,
                        video_url=result.output_url,
                        user_id=request.user_id
                    )
            
            # Verify the working image was set correctly
            verification = await session_manager.get_current_working_image(effective_session_id)
            api_logger.debug("Working image verification", extra={"verification": verification})
            
            # Return the effective session_id to the frontend for future requests
            if not result.metadata:
                result.metadata = {}
            result.metadata["session_id"] = effective_session_id
        

        
        # Deduct XP for successful generation
        api_logger.info(f"🔍 GENERATION: Checking XP deduction - Success: {result.success}, Has XP Cost: {hasattr(http_request.state, 'xp_cost')}, Has Gen Type: {hasattr(http_request.state, 'generation_type')}")
        
        if result.success and hasattr(http_request.state, 'xp_cost') and hasattr(http_request.state, 'generation_type'):
            try:
                from app.services.subscription_service import subscription_service
                
                xp_cost = getattr(http_request.state, 'xp_cost', 10)
                generation_type = getattr(http_request.state, 'generation_type', 'NEW_IMAGE')
                
                api_logger.info(f"💰 GENERATION: Starting XP deduction - Cost: {xp_cost}, Type: {generation_type}, User: {request.user_id}")
                
                api_logger.debug("Deducting XP for successful generation", extra={
                    "user_id": request.user_id,
                    "generation_id": generation_id,
                    "xp_cost": xp_cost,
                    "generation_type": generation_type
                })
                
                deduction_success = await subscription_service.deduct_xp_for_generation(
                    user_id=request.user_id,  # Pass UUID directly to database function
                    generation_id=generation_id,
                    generation_type=generation_type,
                    model_used=result.model_used or "unknown",
                    xp_cost=xp_cost,
                    actual_cost_usd=0.50 if generation_type in ["VIDEO_EDIT", "VIDEO_EDIT_REF"] else 0.0,
                    routing_decision=getattr(routing_decision, 'routing_logic', {}) if 'routing_decision' in locals() and routing_decision else {},
                    prompt=request.prompt
                )
                
                if deduction_success:
                    api_logger.info(f"✅ GENERATION: XP deducted successfully - {xp_cost} XP from user {request.user_id}")
                
                    # Enhanced success logging for video editing
                    if generation_type in ["VIDEO_EDIT", "VIDEO_EDIT_REF"]:
                        api_logger.info(f"🎬 VIDEO_EDIT XP DEDUCTION SUCCESS: {xp_cost} XP charged for gen4_aleph video editing")
                        
                else:
                    api_logger.warning(f"❌ GENERATION: XP deduction failed - User: {request.user_id}, Cost: {xp_cost}")
                    
                    # Enhanced failure logging for video editing
                    if generation_type in ["VIDEO_EDIT", "VIDEO_EDIT_REF"]:
                        api_logger.error(f"🎬 VIDEO_EDIT XP DEDUCTION FAILED: {xp_cost} XP could not be charged for gen4_aleph video editing")
                        
            except Exception as deduction_error:
                api_logger.error(f"💥 GENERATION: XP deduction error - {str(deduction_error)} - User: {request.user_id}")
                # Don't fail the generation if XP deduction fails - log and continue
        else:
            if result.success:
                api_logger.warning(f"⚠️ GENERATION: Successful generation but no XP deduction - Missing state variables")
        
        # Log final generation summary
        api_logger.log_generation_summary(
            generation_id=generation_id,
            prompt=request.prompt,
            intent=intent_analysis.detected_intent.value if 'intent_analysis' in locals() and intent_analysis else "unknown",
            model_used=result.model_used,
            success=result.success,
            total_time=total_time,
            output_url=result.output_url
        )
        
        # Store result in Supabase (background task)
        background_tasks.add_task(
            store_generation_result,
            request, intent_analysis, routing_decision, result
        )
        
        # Add witty messages to the result if available from the flow service
        if result.success and 'flow_result' in locals() and flow_result and flow_result.witty_messages:
            result.witty_messages = flow_result.witty_messages
            api_logger.debug("Added witty messages to response", extra={"message_count": len(flow_result.witty_messages)})
            api_logger.info(f"WITTY MESSAGES: Generated {len(flow_result.witty_messages)} messages for user {request.user_id}")
        
        # Clean up temporary references created for this generation (background task)
        if result.success:
            background_tasks.add_task(
                cleanup_temporary_references_task,
                request.user_id, generation_id
            )
        
        return result
        
    except Exception as e:
        # Handle errors gracefully
        total_time = time.time() - start_time
        error_message = str(e)
        
        error_result = GenerationResponse(
            success=False,
            generation_id=generation_id,
            error_message=error_message,
            execution_time=total_time
        )
        
        # Log failed generation summary
        intent_value = intent_analysis.detected_intent.value if 'intent_analysis' in locals() else "unknown"
        api_logger.log_generation_summary(
            generation_id=generation_id,
            prompt=request.prompt,
            intent=intent_value,
            model_used="unknown",
            success=False,
            total_time=total_time
        )
        
        # Still store failed attempts for learning
        background_tasks.add_task(
            store_generation_result,
            request, 
            intent_analysis if 'intent_analysis' in locals() else None,
            routing_decision if 'routing_decision' in locals() else None, 
            error_result
        )
        
        return error_result

@router.get("/history/{user_id}")
async def get_user_history(
    user_id: str,
    limit: int = 20,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Get user's generation history"""
    
    try:
        history = await db_manager.get_user_history(user_id, limit)
        
        return [
            {
                "generation_id": h["generation_id"],
                "prompt": h["prompt"],
                "model_used": h["model_used"],
                "success": h["success"],
                "output_url": h["output_url"],
                "thumbnail_url": h.get("thumbnail_url"),
                "created_at": h["created_at"],
                "execution_time": h["execution_time"]
            }
            for h in history
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")

@router.get("/generation/{generation_id}")
async def get_generation(generation_id: str):
    """Get specific generation details"""
    
    try:
        generation = await db_manager.get_generation_by_id(generation_id)
        
        if not generation:
            raise HTTPException(status_code=404, detail="Generation not found")
        
        return generation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching generation: {str(e)}")

@router.get("/session/{session_id}")
async def get_session_info(
    session_id: str,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Get current session information including working image"""
    
    try:
        session_info = await session_manager.get_session_info(session_id)
        
        if not session_info:
            return {
                "session_id": session_id,
                "exists": False,
                "current_working_image": None,
                "message": "Session not found or expired"
            }
        
        return {
            "session_id": session_id,
            "exists": True,
            "current_working_image": session_info["current_working_image"],
            "user_id": session_info["user_id"],
            "metadata": session_info["metadata"],
            "created_at": session_info["created_at"],
            "updated_at": session_info["updated_at"],
            "expires_at": session_info["expires_at"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching session: {str(e)}")

@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Clear a session and its working image"""
    
    try:
        await session_manager.clear_session(session_id)
        return {"message": f"Session {session_id} cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")

@router.post("/tag-image")
async def tag_generated_image(
    request: dict,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Tag a generated image as a reference"""
    
    try:
        user_id = request.get("user_id")
        tag = request.get("tag")
        image_url = request.get("image_url")
        display_name = request.get("display_name")
        description = request.get("description", "Tagged from generation history")
        category = request.get("category", "general")
        
        if not all([user_id, tag, image_url]):
            raise HTTPException(status_code=400, detail="user_id, tag, and image_url are required")
        
        # Create the reference
        reference = await ReferenceService.create_reference(
            user_id=user_id,
            tag=tag,
            image_url=image_url,
            display_name=display_name or tag,
            description=description,
            category=category,
            source_type="generated"  # Mark as generated image
        )
        
        if reference:
            return {"message": f"Image tagged as @{tag} successfully", "reference": reference}
        else:
            raise HTTPException(status_code=500, detail="Failed to create reference")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tagging image: {str(e)}")

async def store_generation_result(
    request: GenerationRequest,
    intent_analysis,
    routing_decision,
    result: GenerationResponse
):
    """Store generation result in Supabase for learning and history"""
    
    try:
        from app.services.storage import storage_service
        
        output_url = result.output_url
        thumbnail_url = None
        
        # Check if the output_url is from an external service that might expire
        if output_url and result.success:
            external_domains = ['replicate.delivery', 'runway.com', 'storage.googleapis.com', 'cloudfront.net']
            is_external = any(domain in output_url for domain in external_domains)
            
            if is_external:
                print(f"Downloading and storing external image: {output_url}")
                
                # Download and store the image permanently with thumbnail
                success, file_path, permanent_url, thumb_url = await storage_service.download_and_store_image(
                    image_url=output_url,
                    user_id=request.user_id,
                    resize_max=2048,
                    thumbnail_size=256
                )
                
                if success:
                    output_url = permanent_url
                    thumbnail_url = thumb_url
                    print(f"Successfully stored permanent image: {permanent_url}")
                    print(f"Generated thumbnail: {thumb_url}")
                else:
                    print(f"Failed to store permanent image, keeping original URL")
        
        history_data = {
            "generation_id": result.generation_id,
            "user_id": request.user_id,
            "prompt": request.prompt,
            "intent": intent_analysis.detected_intent.value if intent_analysis else "unknown",
            "model_used": result.model_used,
            "output_url": output_url,
            "thumbnail_url": thumbnail_url,
            "success": "success" if result.success else "failed",
            "execution_time": int(result.execution_time * 1000) if result.execution_time else None,
            "metadata": {
                "intent_confidence": intent_analysis.confidence if intent_analysis else None,
                "routing_reason": routing_decision.get("routing_reason") if routing_decision else None,
                "estimated_time": routing_decision.get("estimated_time") if routing_decision else None,
                "quality_priority": request.quality_priority.value,
                "error_message": result.error_message if not result.success else None,
                "complexity_level": intent_analysis.complexity_level if intent_analysis else None,
                "content_type": intent_analysis.content_type if intent_analysis else None
            }
        }
        
        success = await db_manager.insert_generation_history(history_data)
        if not success:
            api_logger.debug("Failed to store generation result", extra={"generation_id": result.generation_id})
        
    except Exception as e:
        api_logger.debug("Error storing generation result", extra={"error": str(e)})

@router.post("/session/set-working-image")
async def set_working_image(
    request: dict,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Set the working image for a session (used when selecting from history)"""
    
    try:
        session_id = request.get("session_id")
        image_url = request.get("image_url")
        user_id = request.get("user_id")
        
        if not all([session_id, image_url, user_id]):
            raise HTTPException(status_code=400, detail="session_id, image_url, and user_id are required")
        
        api_logger.debug("Setting working image for session", extra={"session_id": session_id, "image_url": image_url})
        
        # Set the working image in the session
        await session_manager.set_current_working_image(
            session_id=session_id,
            image_url=image_url,
            user_id=user_id
        )
        
        # Verify it was set correctly
        verification = await session_manager.get_current_working_image(session_id)
        api_logger.debug("Working image verification", extra={"verification": verification})
        
        return {
            "success": True,
            "message": f"Working image set for session {session_id}",
            "working_image": verification
        }
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.debug("Failed to set working image", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Error setting working image: {str(e)}")

async def cleanup_temporary_references_task(user_id: str, generation_id: str):
    """Background task to clean up temporary references after generation"""
    try:
        await ReferenceService.cleanup_temporary_references(user_id, generation_id)
    except Exception as e:
        api_logger.debug("Error cleaning up temporary references", extra={"generation_id": generation_id, "error": str(e)})

@router.post("/generate-witty-messages")
async def generate_witty_messages(
    request: dict,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Generate witty messages for the current request"""
    
    try:
        user_prompt = request.get("user_prompt")
        prompt_type = request.get("prompt_type", "NEW_IMAGE")
        context = request.get("context", {})
        
        if not user_prompt:
            raise HTTPException(status_code=400, detail="user_prompt is required")
        
        # Import witty message service
        from app.services.witty_message_service import witty_message_service
        
        # Generate witty messages
        witty_messages = await witty_message_service.generate_witty_messages(
            user_prompt=user_prompt,
            prompt_type=prompt_type,
            estimated_time=30,  # Default estimate
            context=context
        )
        
        return {
            "success": True,
            "witty_messages": witty_messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Error generating witty messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating witty messages: {str(e)}") 