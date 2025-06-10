from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
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

# Force reload of generator modules to pick up code changes
importlib.reload(app.services.generators.runway)
importlib.reload(app.services.generators.replicate)

from app.services.generators.runway import RunwayGenerator
from app.services.generators.replicate import ReplicateGenerator
from app.services.session_manager import session_manager
from app.services.reference_service import ReferenceService
from app.services.virtual_tryon import VirtualTryOnService
from app.services.enhanced_workflow_service import EnhancedWorkflowService
from app.core.logging import api_logger
from app.api.v1.auth import get_current_user
from typing import Optional, Dict, Any

router = APIRouter()

# Initialize services
intent_parser = BasicIntentParser()
model_router = ModelRouter()
enhanced_workflow_service = EnhancedWorkflowService()

# Initialize generators  
def get_runway_generator():
    """Factory function to create a fresh RunwayGenerator instance"""
    return RunwayGenerator()

def get_replicate_generator():
    """Factory function to create a fresh ReplicateGenerator instance"""
    return ReplicateGenerator()

# Keep module-level instances for backward compatibility, but allow fresh creation
runway_generator = get_runway_generator()
replicate_generator = get_replicate_generator()

# Initialize virtual try-on service
virtual_tryon_service = VirtualTryOnService()

@router.post("/generate", response_model=GenerationResponse)
async def generate_content(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    SIMPLIFIED FLOW: Main generation endpoint using CSV-based decision matrix
    """
    
    generation_id = f"gen_{uuid.uuid4().hex[:12]}"
    start_time = time.time()
    
    try:
        # Import simplified flow service
        from app.services.simplified_flow_service import simplified_flow
        
        # Get current working image from session if available
        current_working_image = None
        print(f"[DEBUG] API: Request session_id: {request.session_id}")
        print(f"[DEBUG] API: Request user_id: {request.user_id}")
        
        # Auto-generate session ID if not provided (for conversational continuity)
        effective_session_id = request.session_id
        if not effective_session_id:
            timestamp = int(time.time())
            effective_session_id = f"auto_session_{request.user_id}_{timestamp}"
            print(f"[DEBUG] API: Auto-generated session_id: {effective_session_id}")
        
        current_working_image = await session_manager.get_current_working_image(effective_session_id)
        print(f"[DEBUG] API: Retrieved working image: {current_working_image}")
        
        # Validate working image
        if current_working_image:
            if not current_working_image.startswith(('http://', 'https://')):
                print(f"[WARNING] API: Invalid working image URL format: {current_working_image}")
                current_working_image = None
            elif len(current_working_image.strip()) == 0:
                print(f"[WARNING] API: Empty working image URL")
                current_working_image = None
            else:
                print(f"[DEBUG] API: Valid working image found: {current_working_image}")
        
        # SIMPLIFIED FLOW: Determine boolean flags for CSV decision matrix
        active_image = bool(current_working_image)
        uploaded_image = bool(request.uploaded_images and len(request.uploaded_images) > 0)
        referenced_image = bool(ReferenceService.has_references(request.prompt))
        
        print(f"[DEBUG] SIMPLIFIED: Boolean flags - Active: {active_image}, Uploaded: {uploaded_image}, Referenced: {referenced_image}")
        
        # Process through simplified flow
        flow_result = await simplified_flow.process_user_request(
            user_prompt=request.prompt,
            active_image=active_image,
            uploaded_image=uploaded_image,
            referenced_image=referenced_image,
            context={
                "user_id": request.user_id,
                "session_id": effective_session_id,
                "working_image": current_working_image,
                "uploaded_images": request.uploaded_images or []
            },
            user_id=request.user_id  # Pass user_id for Sprint 3 infrastructure
        )
        
        print(f"[DEBUG] SIMPLIFIED: Flow result - Type: {flow_result.prompt_type.value}, Model: {flow_result.model_to_use}")
        print(f"[DEBUG] SIMPLIFIED: Enhanced prompt: {flow_result.enhanced_prompt}")
        
        # Handle reference processing if needed
        reference_images = []
        if referenced_image:
            print(f"[DEBUG] SIMPLIFIED: Processing references from prompt")
            if current_working_image:
                # For EDIT_IMAGE_REF, skip reference service enhancement to preserve our structured prompt
                if flow_result.prompt_type.value == "EDIT_IMAGE_REF":
                    print(f"[DEBUG] SIMPLIFIED: Keeping structured prompt from simplified flow for EDIT_IMAGE_REF")
                    print(f"[DEBUG] SIMPLIFIED: Original enhanced prompt: {flow_result.enhanced_prompt}")
                    
                    # Just parse references without enhancing the prompt
                    reference_images, missing_tags = await ReferenceService.parse_reference_mentions(
                        request.prompt,  # Use original prompt to find @mentions
                        request.user_id
                    )
                    if missing_tags:
                        print(f"[WARNING] SIMPLIFIED: Missing references: {missing_tags}")
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
                    print(f"[WARNING] SIMPLIFIED: Missing references: {missing_tags}")
            
            print(f"[DEBUG] SIMPLIFIED: Found {len(reference_images)} reference images")
        
        # Convert simplified flow result to legacy format for compatibility
        from app.models.generation import IntentAnalysis, CreativeIntent
        
        # Map CSV types to legacy intent values
        intent_mapping = {
            "NEW_IMAGE": "generate_image",
            "NEW_IMAGE_REF": "edit_image",  # NEW_IMAGE_REF uses Kontext like editing
            "EDIT_IMAGE": "edit_image", 
            "EDIT_IMAGE_REF": "virtual_tryon" if uploaded_image else "edit_image"
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
        
        print(f"[DEBUG] SIMPLIFIED: Final intent: {basic_intent_value}, Model: {flow_result.model_to_use}")
        
        # Handle virtual try-on requests using the existing multi-image workflow
        # Note: Skip the dedicated virtual try-on service for now since it's not implemented
        # Virtual try-on will be handled by the regular generation pipeline with proper model selection
        if intent_analysis.detected_intent.value == "virtual_tryon":
            print(f"[DEBUG] API: Virtual try-on request detected - will use multi-image workflow")
            # Continue with normal generation flow using the enhanced model selection
            # The multi-image kontext model will handle the virtual try-on
        
        # Phase 2: Route to optimal model - SIMPLIFIED using CSV-based decision
        print(f"[DEBUG] SIMPLIFIED: Using CSV-based model routing")
        
        # Get model parameters from simplified flow
        model_params = await simplified_flow.get_model_parameters(flow_result)
        
        # Create routing decision using simplified flow result
        routing_decision = {
            "model": flow_result.model_to_use,
            "provider": "replicate",  # All CSV models use Replicate
            "parameters": model_params,
            "routing_reason": f"CSV-based flow: {flow_result.reasoning}",
            "estimated_cost": 0.05,  # Default cost estimate
            "estimated_time": 30     # Default time estimate
        }
        
        print(f"[DEBUG] SIMPLIFIED: Selected model: {flow_result.model_to_use}")
        print(f"[DEBUG] SIMPLIFIED: Model parameters: {model_params}")
        
        # Phase 3: Execute generation
        selected_model = routing_decision["model"]
        parameters = routing_decision["parameters"]
        
        print(f"[DEBUG] API: Router selected model: {selected_model}")
        print(f"[DEBUG] API: Router parameters: {parameters}")
        print(f"[DEBUG] API: Router routing reason: {routing_decision.get('routing_reason')}")
        
        # Enhanced image selection logic for virtual try-on scenarios
        image_source = None
        
        # Debug: Log all image sources
        print(f"[DEBUG] Image selection analysis:")
        print(f"[DEBUG]   current_working_image: {current_working_image}")
        print(f"[DEBUG]   request.uploaded_images: {request.uploaded_images}")
        print(f"[DEBUG]   uploaded_images count: {len(request.uploaded_images) if request.uploaded_images else 0}")
        print(f"[DEBUG]   detected_intent: {intent_analysis.detected_intent.value if 'intent_analysis' in locals() and intent_analysis else 'unknown'}")
        print(f"[DEBUG]   flow_result: {flow_result.prompt_type.value if flow_result else 'None'}")
        
        # Check if this is a reference styling request (virtual try-on OR face swap)
        # Using simplified flow data instead of enhanced_intent
        is_reference_styling = flow_result.prompt_type.value == "EDIT_IMAGE_REF"
        
        # Determine if this is face swap by checking flow reasoning
        flow_reasoning = flow_result.reasoning if flow_result else ''
        is_face_swap = is_reference_styling and ("face" in flow_reasoning.lower() and ("replace" in flow_reasoning.lower() or "swap" in flow_reasoning.lower()))
        
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
        
        print(f"[DEBUG] Reference styling conditions:")
        print(f"[DEBUG]   has_working_image: {bool(current_working_image)}")
        print(f"[DEBUG]   has_uploaded_images: {bool(request.uploaded_images and len(request.uploaded_images) > 0)}")
        print(f"[DEBUG]   has_prompt_references: {has_prompt_references}")
        print(f"[DEBUG]   intent_is_edit: {('intent_analysis' in locals() and intent_analysis and intent_analysis.detected_intent.value in ['edit_image'])}")
        print(f"[DEBUG]   is_reference_styling: {is_reference_styling}")
        print(f"[DEBUG]   is_face_swap: {is_face_swap}")
        print(f"[DEBUG]   flow_reasoning: {flow_reasoning}")
        print(f"[DEBUG]   IS_REFERENCE_SCENARIO: {is_reference_scenario}")
        print(f"[DEBUG]   USES_RUNWAY_REFERENCES: {uses_runway_references}")
        
        # Set up Runway reference images for styling workflows
        if uses_runway_references:
            print(f"[DEBUG] Setting up Runway references for {flow_result.prompt_type.value}")
            
            # Use existing reference images from ReferenceService, plus working image if needed
            runway_reference_images = []
            
            # Add existing @references from prompt (like @charlie)
            if hasattr(request, 'reference_images') and request.reference_images:
                for ref_img in request.reference_images:
                    runway_reference_images.append({
                        "uri": ref_img.uri,
                        "tag": ref_img.tag
                    })
                    print(f"[DEBUG] Added prompt reference: @{ref_img.tag} -> {ref_img.uri}")
            
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
                    print(f"[DEBUG] Added working image reference: {current_working_image}")
                else:
                    print(f"[DEBUG] Working image already included in references")
            
            # Add uploaded images as additional references
            if request.uploaded_images:
                for i, uploaded_image in enumerate(request.uploaded_images):
                    runway_reference_images.append({
                        "uri": uploaded_image,
                        "tag": f"reference_{i+1}" if flow_result.prompt_type.value == "EDIT_IMAGE_REF" else f"hair_reference_{i+1}"
                    })
                    print(f"[DEBUG] Added uploaded image reference: {uploaded_image}")
            
            # Update request with all reference images for Runway generator
            if runway_reference_images:
                from app.models.generation import ReferenceImage
                request.reference_images = [
                    ReferenceImage(uri=ref["uri"], tag=ref["tag"]) 
                    for ref in runway_reference_images
                ]
                print(f"[DEBUG] Set {len(runway_reference_images)} reference images for Runway")
                
                # Also add to parameters for backward compatibility
                parameters["reference_images"] = runway_reference_images
                parameters["type"] = "text_to_image_with_references"
        
        if is_face_swap and current_working_image and request.uploaded_images:
            # Face swap with working image: Create reference from uploaded image and use Runway
            print(f"[DEBUG] Face swap detected - will use Runway with references:")
            print(f"[DEBUG]   Base person (working image): {current_working_image}")
            print(f"[DEBUG]   Face source (uploaded): {request.uploaded_images[0]}")
            
            # Set parameters to trigger face swap processing
            parameters["face_swap_base_image"] = current_working_image  # Base person
            parameters["face_swap_source_image"] = request.uploaded_images[0]  # Face to swap
            parameters["is_face_swap"] = True
            parameters["type"] = "text_to_image_with_references"  # Force enhanced routing
            image_source = f"face_swap:base={current_working_image},source={request.uploaded_images[0]}"
            
        elif is_face_swap and not current_working_image and request.uploaded_images:
            # Face swap without working image: User uploaded the base image, needs a reference face
            print(f"[DEBUG] Face swap detected but no working image - user needs to provide source face:")
            print(f"[DEBUG]   Base image (uploaded): {request.uploaded_images[0]}")
            print(f"[DEBUG]   Need: Face source image to swap onto the base")
            
            # For now, just use the uploaded image as base and rely on prompt engineering
            # In the future, we could prompt user to provide a second image
            parameters["image"] = request.uploaded_images[0]
            parameters["uploaded_image"] = request.uploaded_images[0]
            image_source = f"uploaded_image:{request.uploaded_images[0]}"
            print(f"[DEBUG] Using uploaded image as base for face modification: {request.uploaded_images[0]}")
            
        elif is_reference_scenario:
            # Virtual try-on: Use working image as person, uploaded as clothing reference
            parameters["image"] = current_working_image  # Primary image (person)
            parameters["uploaded_image"] = current_working_image  # Backward compatibility
            parameters["reference_image"] = request.uploaded_images[0]  # Clothing reference
            image_source = f"virtual_tryon:person={current_working_image},clothing={request.uploaded_images[0]}"
            print(f"[DEBUG] Virtual try-on detected:")
            print(f"[DEBUG]   Person (working image): {current_working_image}")
            print(f"[DEBUG]   Clothing reference (uploaded): {request.uploaded_images[0]}")
        elif flow_result.prompt_type.value == "NEW_IMAGE_REF":
            # NEW_IMAGE_REF: Use reference image as input for Kontext
            reference_image_url = None
            
            if hasattr(request, 'reference_images') and request.reference_images and len(request.reference_images) > 0:
                # Use first reference image from @mentions
                reference_image_url = request.reference_images[0].uri
                image_source = f"new_image_ref:reference={reference_image_url}"
                print(f"[DEBUG] NEW_IMAGE_REF with @reference: {reference_image_url}")
            elif request.uploaded_images and len(request.uploaded_images) > 0:
                # Use uploaded image as reference
                reference_image_url = request.uploaded_images[0]
                image_source = f"new_image_ref:uploaded={reference_image_url}"
                print(f"[DEBUG] NEW_IMAGE_REF with upload: {reference_image_url}")
            
            if reference_image_url:
                parameters["image"] = reference_image_url  # Input image for Kontext
                parameters["uploaded_image"] = reference_image_url  # Backward compatibility
                print(f"[DEBUG] NEW_IMAGE_REF using reference as input: {reference_image_url}")
            else:
                print(f"[ERROR] NEW_IMAGE_REF classification but no reference image found!")
                print(f"[ERROR] request.reference_images: {getattr(request, 'reference_images', None)}")
                print(f"[ERROR] request.uploaded_images: {request.uploaded_images}")
        elif current_working_image:
            # Standard editing: Use current working image from session for continued editing
            parameters["uploaded_image"] = current_working_image
            parameters["image"] = current_working_image
            image_source = f"working_image:{current_working_image}"
            print(f"[DEBUG] Using working image from session: {current_working_image}")
        elif request.uploaded_images and len(request.uploaded_images) > 0:
            # New upload: Use newly uploaded image
            parameters["uploaded_image"] = request.uploaded_images[0]  # Use first uploaded image
            parameters["image"] = request.uploaded_images[0]  # Alternative parameter name
            image_source = f"uploaded_image:{request.uploaded_images[0]}"
            print(f"[DEBUG] Using uploaded image: {request.uploaded_images[0]}")
        
        # Log image source for debugging
        if selected_model == "flux-kontext":
            print(f"[DEBUG] flux-kontext will use image: {parameters.get('image', 'NO_IMAGE_FOUND')}")
            print(f"[DEBUG] Image source: {image_source or 'no_image'}")
            if not parameters.get('image'):
                print(f"[ERROR] flux-kontext requires an image but none was provided!")
                print(f"[ERROR] current_working_image: {current_working_image}")
                print(f"[ERROR] uploaded_images: {request.uploaded_images}")
                print(f"[ERROR] session_id: {request.session_id}")
        
        # Choose generator based on model - FORCE Runway if references present OR face swap
        print(f"[DEBUG] API: Selecting generator for model: {selected_model}")
        print(f"[DEBUG] API: Has references: {bool(request.reference_images)}")
        print(f"[DEBUG] API: Is face swap: {parameters.get('is_face_swap', False)}")
        
        if parameters.get("is_face_swap", False):
            print(f"[DEBUG] API: Using FRESH RunwayGenerator for face swap")
            generator = get_runway_generator()  # Create fresh instance!
            # Face swap will be handled specially in the generator
        elif uses_runway_references:
            print(f"[DEBUG] API: Using FRESH RunwayGenerator due to runway references workflow")
            generator = get_runway_generator()  # Create fresh instance!
        elif "runway" in selected_model:
            print(f"[DEBUG] API: Using FRESH RunwayGenerator for {selected_model}")
            generator = get_runway_generator()  # Create fresh instance!
            # Don't override the type if it was already set by the model router (e.g., "image_to_video")
            if "type" not in parameters and 'intent_analysis' in locals() and intent_analysis and intent_analysis.detected_intent.value == "generate_video":
                parameters["type"] = "video"
        elif "flux" in selected_model or "dall-e" in selected_model or "google" in selected_model:
            print(f"[DEBUG] API: Using FRESH ReplicateGenerator for {selected_model}")
            generator = get_replicate_generator()  # Create fresh instance!
            parameters["model"] = selected_model
        else:
            print(f"[DEBUG] API: No matching generator found for {selected_model}, falling back to FRESH ReplicateGenerator with flux-1.1-pro")
            # Default fallback
            generator = get_replicate_generator()  # Create fresh instance!
            parameters["model"] = "flux-1.1-pro"
        
        # Add uploaded images to parameters for generator access
        if request.uploaded_images:
            parameters["uploaded_images"] = request.uploaded_images
            print(f"[DEBUG] API: Added {len(request.uploaded_images)} uploaded_images to parameters")

        # Execute generation
        result = await generator.generate(
            request.prompt, 
            parameters,
            generation_id=generation_id
        )
        
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
        
        # Update session with newly generated image for future edits
        if result.success and result.output_url:
            print(f"[DEBUG] API: Setting working image in session {effective_session_id}: {result.output_url}")
            await session_manager.set_current_working_image(
                session_id=effective_session_id,
                image_url=result.output_url,
                user_id=request.user_id
            )
            
            # Verify the working image was set correctly
            verification = await session_manager.get_current_working_image(effective_session_id)
            print(f"[DEBUG] API: Verification - working image is now: {verification}")
            
            # Return the effective session_id to the frontend for future requests
            if not result.metadata:
                result.metadata = {}
            result.metadata["session_id"] = effective_session_id
        
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
        history_data = {
            "generation_id": result.generation_id,
            "user_id": request.user_id,
            "prompt": request.prompt,
            "intent": intent_analysis.detected_intent.value if intent_analysis else "unknown",
            "model_used": result.model_used,
            "output_url": result.output_url,
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
            print(f"Failed to store generation result for {result.generation_id}")
        
    except Exception as e:
        print(f"Error storing generation result: {e}")

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
        
        print(f"[DEBUG] API: Setting working image for session {session_id}: {image_url}")
        
        # Set the working image in the session
        await session_manager.set_current_working_image(
            session_id=session_id,
            image_url=image_url,
            user_id=user_id
        )
        
        # Verify it was set correctly
        verification = await session_manager.get_current_working_image(session_id)
        print(f"[DEBUG] API: Verification - working image is now: {verification}")
        
        return {
            "success": True,
            "message": f"Working image set for session {session_id}",
            "working_image": verification
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to set working image: {e}")
        raise HTTPException(status_code=500, detail=f"Error setting working image: {str(e)}")

async def cleanup_temporary_references_task(user_id: str, generation_id: str):
    """Background task to clean up temporary references after generation"""
    try:
        await ReferenceService.cleanup_temporary_references(user_id, generation_id)
    except Exception as e:
        print(f"Error cleaning up temporary references for {generation_id}: {e}") 