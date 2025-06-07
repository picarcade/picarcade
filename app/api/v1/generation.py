from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
import uuid
import time
from datetime import datetime

from app.core.database import db_manager
from app.models.generation import GenerationRequest, GenerationResponse
from app.services.intent_parser import BasicIntentParser
from app.services.model_router import ModelRouter
from app.services.generators.runway import RunwayGenerator
from app.services.generators.replicate import ReplicateGenerator
from app.services.session_manager import session_manager
from app.services.reference_service import ReferenceService
from app.core.logging import api_logger
from app.api.v1.auth import get_current_user
from typing import Optional, Dict, Any

router = APIRouter()

# Initialize services
intent_parser = BasicIntentParser()
model_router = ModelRouter()

# Initialize generators
runway_generator = RunwayGenerator()
replicate_generator = ReplicateGenerator()

@router.post("/generate", response_model=GenerationResponse)
async def generate_content(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    Main generation endpoint - this is where the magic happens
    """
    
    generation_id = f"gen_{uuid.uuid4().hex[:12]}"
    start_time = time.time()
    
    try:
        # Get current working image from session if available
        current_working_image = None
        print(f"[DEBUG] API: Request session_id: {request.session_id}")
        print(f"[DEBUG] API: Request user_id: {request.user_id}")
        
        # Auto-generate session ID if not provided (for conversational continuity)
        effective_session_id = request.session_id
        if not effective_session_id:
            effective_session_id = f"auto_session_{request.user_id}"
            print(f"[DEBUG] API: Auto-generated session_id: {effective_session_id}")
        
        current_working_image = await session_manager.get_current_working_image(effective_session_id)
        print(f"[DEBUG] API: Retrieved working image: {current_working_image}")
        
        # Validate working image - ensure it's a valid URL and accessible
        if current_working_image:
            if not current_working_image.startswith(('http://', 'https://')):
                print(f"[WARNING] API: Invalid working image URL format: {current_working_image}")
                current_working_image = None
            elif len(current_working_image.strip()) == 0:
                print(f"[WARNING] API: Empty working image URL")
                current_working_image = None
            else:
                print(f"[DEBUG] API: Valid working image found: {current_working_image}")
        
        # Set the working image on the request object for the model router
        request.current_working_image = current_working_image
        print(f"[DEBUG] API: Set request.current_working_image: {request.current_working_image}")
        
        # Parse reference mentions from prompt 
        reference_images = []
        original_prompt = request.prompt
        
        has_user_references = ReferenceService.has_references(request.prompt)
        
        if has_user_references:
            print(f"[DEBUG] API: User @references detected in prompt: {request.prompt}")
            
            # If we have both user references and a working image, enhance the prompt
            if current_working_image:
                print(f"[DEBUG] API: Enhancing prompt with working image: {current_working_image}")
                enhanced_prompt, reference_images = await ReferenceService.enhance_prompt_with_working_image(
                    request.prompt,
                    request.user_id, 
                    current_working_image
                )
                # Update the request prompt to the enhanced version
                request.prompt = enhanced_prompt
                print(f"[DEBUG] API: Enhanced prompt: {enhanced_prompt}")
            else:
                # No working image, proceed with just user references
                reference_images, missing_tags = await ReferenceService.parse_reference_mentions(
                    request.prompt, 
                    request.user_id
                )
                if missing_tags:
                    print(f"[WARNING] API: Missing references: {missing_tags}")
            
            print(f"[DEBUG] API: Found {len(reference_images)} reference images")
            print(f"[DEBUG] API: Final prompt: {request.prompt}")
            
            # Add to request
            request.reference_images = reference_images
        else:
            # No user references - this is a standard edit/generation request
            # Working image will be used as input for flux-kontext, NOT as a reference
            print(f"[DEBUG] API: No @references in prompt - standard edit/generation request")
            if current_working_image:
                print(f"[DEBUG] API: Working image available for flux-kontext input: {current_working_image}")
            else:
                print(f"[DEBUG] API: No working image - new generation or uploaded image edit")
        
        # Phase 1: Analyze user intent
        intent_analysis = await intent_parser.analyze_intent(
            prompt=request.prompt,
            user_context={},  # Will be populated from Mem0 in later phases
            generation_id=generation_id,
            uploaded_images=request.uploaded_images,
            current_working_image=current_working_image
        )
        
        # Phase 2: Route to optimal model
        routing_decision = await model_router.route_generation(
            request, 
            intent_analysis,
            generation_id=generation_id
        )
        
        # Phase 3: Execute generation
        selected_model = routing_decision["model"]
        parameters = routing_decision["parameters"]
        
        print(f"[DEBUG] API: Router selected model: {selected_model}")
        print(f"[DEBUG] API: Router parameters: {parameters}")
        print(f"[DEBUG] API: Router routing reason: {routing_decision.get('routing_reason')}")
        
        # Add images to parameters for image editing (prioritize current working image)
        image_source = None
        if current_working_image:
            # Use current working image from session for continued editing
            parameters["uploaded_image"] = current_working_image
            parameters["image"] = current_working_image
            image_source = f"working_image:{current_working_image}"
            print(f"[DEBUG] Using working image from session: {current_working_image}")
        elif request.uploaded_images and len(request.uploaded_images) > 0:
            # Use newly uploaded image
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
        
        # Choose generator based on model - FORCE Runway if references present
        print(f"[DEBUG] API: Selecting generator for model: {selected_model}")
        print(f"[DEBUG] API: Has references: {bool(request.reference_images)}")
        
        if request.reference_images and len(request.reference_images) > 0:
            print(f"[DEBUG] API: Using RunwayGenerator due to references")
            generator = runway_generator
        elif "runway" in selected_model:
            print(f"[DEBUG] API: Using RunwayGenerator for {selected_model}")
            generator = runway_generator
            # Don't override the type if it was already set by the model router (e.g., "image_to_video")
            if "type" not in parameters and intent_analysis.detected_intent.value == "generate_video":
                parameters["type"] = "video"
        elif "flux" in selected_model or "dall-e" in selected_model or "google" in selected_model:
            print(f"[DEBUG] API: Using ReplicateGenerator for {selected_model}")
            generator = replicate_generator
            parameters["model"] = selected_model
        else:
            print(f"[DEBUG] API: No matching generator found for {selected_model}, falling back to ReplicateGenerator with flux-1.1-pro")
            # Default fallback
            generator = replicate_generator
            parameters["model"] = "flux-1.1-pro"
        
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
            intent=intent_analysis.detected_intent.value,
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

async def cleanup_temporary_references_task(user_id: str, generation_id: str):
    """Background task to clean up temporary references after generation"""
    try:
        await ReferenceService.cleanup_temporary_references(user_id, generation_id)
    except Exception as e:
        print(f"Error cleaning up temporary references for {generation_id}: {e}") 