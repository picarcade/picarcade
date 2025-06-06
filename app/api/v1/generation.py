from fastapi import APIRouter, HTTPException, BackgroundTasks
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
from app.core.logging import api_logger

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
    background_tasks: BackgroundTasks
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
        
        current_working_image = session_manager.get_current_working_image(effective_session_id)
        print(f"[DEBUG] API: Retrieved working image: {current_working_image}")
        
        # Set the working image on the request object for the model router
        request.current_working_image = current_working_image
        print(f"[DEBUG] API: Set request.current_working_image: {request.current_working_image}")
        
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
        
        # Choose generator based on model
        print(f"[DEBUG] API: Selecting generator for model: {selected_model}")
        
        if "runway" in selected_model:
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
            session_manager.set_current_working_image(
                session_id=effective_session_id,
                image_url=result.output_url,
                user_id=request.user_id
            )
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
    limit: int = 20
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
async def get_session_info(session_id: str):
    """Get current session information including working image"""
    
    try:
        session_info = session_manager.get_session_info(session_id)
        
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
            "last_updated": session_info["last_updated"],
            "created_at": session_info["created_at"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching session: {str(e)}")

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a session and its working image"""
    
    try:
        session_manager.clear_session(session_id)
        return {"message": f"Session {session_id} cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")

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