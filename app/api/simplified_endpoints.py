"""
Simplified API endpoints using the new CSV-based flow

These endpoints demonstrate how to integrate the simplified flow into your FastAPI app
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging

from app.services.simplified_flow_service import simplified_flow, SimplifiedFlowResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["simplified_flow"])


class SimplifiedRequest(BaseModel):
    """Request model for simplified flow"""
    prompt: str = Field(..., description="User prompt")
    active_image: bool = Field(default=False, description="Has an active/working image")
    uploaded_image: bool = Field(default=False, description="User uploaded reference image") 
    referenced_image: bool = Field(default=False, description="Has referenced image from search/URL")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Additional context")


class SimplifiedResponse(BaseModel):
    """Response model for simplified flow"""
    success: bool
    prompt_type: str
    model_to_use: str
    enhanced_prompt: str
    original_prompt: str
    reasoning: str
    estimated_cost: Optional[float] = None
    estimated_time: Optional[int] = None
    model_parameters: Dict[str, Any]
    
    # Debug info
    classification_flags: Dict[str, bool]


@router.post("/process", response_model=SimplifiedResponse)
async def process_simplified_request(request: SimplifiedRequest):
    """
    Process user request through simplified CSV-based flow
    
    This single endpoint:
    1. Takes user prompt and boolean flags
    2. Uses LLM to classify intent and enhance prompt 
    3. Routes to appropriate model
    4. Returns everything needed for generation
    """
    
    try:
        logger.info(f"Processing simplified request: '{request.prompt}'")
        logger.info(f"Flags - Active: {request.active_image}, Uploaded: {request.uploaded_image}, Referenced: {request.referenced_image}")
        
        # Process through simplified flow
        result: SimplifiedFlowResult = await simplified_flow.process_user_request(
            user_prompt=request.prompt,
            active_image=request.active_image,
            uploaded_image=request.uploaded_image,
            referenced_image=request.referenced_image,
            context=request.context
        )
        
        # Get model parameters
        model_params = await simplified_flow.get_model_parameters(result, request.context)
        
        # Estimate costs (simplified)
        estimated_cost = _estimate_cost(result.model_to_use)
        estimated_time = _estimate_time(result.model_to_use)
        
        return SimplifiedResponse(
            success=True,
            prompt_type=result.prompt_type.value,
            model_to_use=result.model_to_use,
            enhanced_prompt=result.enhanced_prompt,
            original_prompt=result.original_prompt,
            reasoning=result.reasoning,
            estimated_cost=estimated_cost,
            estimated_time=estimated_time,
            model_parameters=model_params,
            classification_flags={
                "active_image": result.active_image,
                "uploaded_image": result.uploaded_image, 
                "referenced_image": result.referenced_image
            }
        )
        
    except Exception as e:
        logger.error(f"Simplified flow processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@router.get("/models/available")
async def get_available_models():
    """
    Get list of available models from CSV mapping
    """
    return {
        "models": {
            # Image generation models
            "NEW_IMAGE": "black-forest-labs/flux-1.1-pro",
            "NEW_IMAGE_REF": "runway_gen4_image",
            "EDIT_IMAGE": "black-forest-labs/flux-kontext-max",
            "EDIT_IMAGE_REF": "runway_gen4_image",
            "EDIT_IMAGE_ADD_NEW": "runway_gen4_image",
            # Video generation models
            "NEW_VIDEO": "minimax/video-01",
            "NEW_VIDEO_WITH_AUDIO": "google/veo-3",
            "IMAGE_TO_VIDEO": "minimax/video-01",
            "IMAGE_TO_VIDEO_WITH_AUDIO": "minimax/video-01",
            "EDIT_IMAGE_REF_TO_VIDEO": "minimax/video-01"
        },
        "csv_based": True,
        "description": "Models are automatically selected based on CSV decision matrix including video generation flows"
    }


@router.post("/classify-only")
async def classify_only(request: SimplifiedRequest):
    """
    Just classify intent without full processing (for debugging)
    """
    
    try:
        result = await simplified_flow.process_user_request(
            user_prompt=request.prompt,
            active_image=request.active_image,
            uploaded_image=request.uploaded_image,
            referenced_image=request.referenced_image,
            context=request.context
        )
        
        return {
            "prompt_type": result.prompt_type.value,
            "reasoning": result.reasoning,
            "enhanced_prompt": result.enhanced_prompt,
            "model_selected": result.model_to_use,
            "csv_decision": _explain_csv_decision(
                request.active_image, 
                request.uploaded_image, 
                request.referenced_image
            )
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )


@router.get("/decision-matrix")
async def get_decision_matrix():
    """
    Return the CSV decision matrix for transparency
    """
    return {
        "image_flows": [
            {
                "active_image": False,
                "uploaded_image": False, 
                "referenced_image": False,
                "type": "NEW_IMAGE",
                "model": "Flux 1.1 Pro",
                "enhancement": "None"
            },
            {
                "active_image": True,
                "uploaded_image": False,
                "referenced_image": False, 
                "type": "NEW_IMAGE (no edit intent) or EDIT_IMAGE (edit intent)",
                "model": "Flux 1.1 Pro or Kontext",
                "enhancement": "None or Add: Maintain all other aspects of the original image"
            },
            {
                "active_image": False,
                "uploaded_image": False,
                "referenced_image": True,
                "type": "NEW_IMAGE_REF", 
                "model": "Runway",
                "enhancement": "Add: Preserve all facial features, likeness, and identity of referenced people exactly. Maintain all other aspects of the original image."
            },
            {
                "active_image": False,
                "uploaded_image": True,
                "referenced_image": False,
                "type": "NEW_IMAGE_REF",
                "model": "Runway", 
                "enhancement": "Add: Preserve all facial features, likeness, and identity of referenced people exactly. Maintain all other aspects of the original image."
            },
            {
                "active_image": True,
                "uploaded_image": True,
                "referenced_image": False,
                "type": "EDIT_IMAGE_REF", 
                "model": "Runway",
                "enhancement": "Add: Maintain all other aspects of the [target ref]"
            },
            {
                "active_image": True,
                "uploaded_image": False,
                "referenced_image": True,
                "type": "EDIT_IMAGE_REF",
                "model": "Runway", 
                "enhancement": "Add: Maintain all other aspects of the [target ref]"
            },
            {
                "active_image": True,
                "uploaded_image": True,
                "referenced_image": True,
                "type": "EDIT_IMAGE_REF",
                "model": "Runway",
                "enhancement": "Add: Maintain all other aspects of the [target ref]"
            }
        ],
        "video_flows": [
            {
                "prompt_type": "Create new video",
                "active_image": False,
                "uploaded_image": False,
                "referenced_image": False,
                "type": "NEW_VIDEO",
                "model": "Veo 3",
                "enhancement": "Transform to comprehensive video prompt with scene description, visual style, camera movement, etc."
            },
            {
                "prompt_type": "Create new video",
                "active_image": True,
                "uploaded_image": False,
                "referenced_image": False,
                "type": "IMAGE_TO_VIDEO",
                "model": "Runway",
                "enhancement": "None - use original prompt for image animation"
            },
            {
                "prompt_type": "Create new video",
                "active_image": True,
                "uploaded_image": True,
                "referenced_image": False,
                "type": "EDIT_IMAGE_REF_TO_VIDEO",
                "model": "Flux Kontext to Runway",
                "enhancement": "Use Kontext to update image first, then send to Runway"
            },
            {
                "prompt_type": "Create new video",
                "active_image": True,
                "uploaded_image": False,
                "referenced_image": True,
                "type": "EDIT_IMAGE_REF_TO_VIDEO",
                "model": "Flux Kontext to Runway",
                "enhancement": "Use Kontext to update image first, then send to Runway"
            }
        ],
        "notes": [
            "VIDEO DETECTION: System first checks for video intent keywords before applying image flows",
            "Video keywords: 'create video', 'make video', 'generate video', 'animate', 'animation', etc.",
            "LLM determines edit intent when active_image=True and no other images (for image flows)",
            "NEW_IMAGE_REF handles creating new images with reference/uploaded images",
            "All prompt enhancement logic is handled by the LLM",
            "Model selection is deterministic based on CSV rules",
            "SPECIAL RULE: 2+ reference images (any combination of @refs + uploads) → Runway (overrides CSV model for image flows)",
            "Two-step process for EDIT_IMAGE_REF_TO_VIDEO: Flux Kontext updates image, then Runway creates video"
        ]
    }


def _estimate_cost(model_name: str) -> float:
    """Simple cost estimation based on model"""
    cost_map = {
        # Image models
        "black-forest-labs/flux-1.1-pro": 0.04,
        "black-forest-labs/flux-kontext-max": 0.03,
        "runway_gen4_image": 0.06,
        # Video models
                    "google/veo-3": 0.75,  # Per second, so 10 seconds = $7.50
            "minimax/video-01": 0.40,  # Per second for MiniMax video
        "runway_gen3_video": 0.20,  # Per second, so 5 seconds = $1.00
        "flux-kontext-to-runway": 0.23  # Combined cost of both steps
    }
    return cost_map.get(model_name, 0.05)


def _estimate_time(model_name: str) -> int:
    """Simple time estimation in seconds"""
    time_map = {
        # Image models
        "black-forest-labs/flux-1.1-pro": 25,
        "black-forest-labs/flux-kontext-max": 30, 
        "runway_gen4_image": 45,
        # Video models  
                    "google/veo-3": 120,  # 2 minutes for Veo 3 video generation
            "minimax/video-01": 90,  # 1.5 minutes for MiniMax video generation
        "runway_gen3_video": 90,  # 1.5 minutes for Runway video
        "flux-kontext-to-runway": 150  # 2.5 minutes for two-step process
    }
    return time_map.get(model_name, 30)


def _explain_csv_decision(active: bool, uploaded: bool, referenced: bool) -> str:
    """Explain the CSV decision logic"""
    
    base_explanation = ""
    
    if not active and not uploaded and not referenced:
        base_explanation = "No images → NEW_IMAGE → Flux 1.1 Pro (or NEW_VIDEO → Veo 3 if video intent)"
    elif not active and not uploaded and referenced:
        base_explanation = "No active, No uploaded, Referenced → NEW_IMAGE_REF → Runway (or EDIT_IMAGE_REF_TO_VIDEO if video intent)"
    elif not active and uploaded and not referenced:
        base_explanation = "No active, Uploaded, No referenced → NEW_IMAGE_REF → Runway (or EDIT_IMAGE_REF_TO_VIDEO if video intent)"
    elif active and not uploaded and not referenced:
        base_explanation = "Active image only → LLM determines edit intent → EDIT_IMAGE (Kontext) or NEW_IMAGE (Flux), or IMAGE_TO_VIDEO (Runway) if video intent"
    elif active and uploaded and not referenced:
        base_explanation = "Active + Uploaded → EDIT_IMAGE_REF → Runway (or EDIT_IMAGE_REF_TO_VIDEO if video intent)"
    elif active and not uploaded and referenced:
        base_explanation = "Active + Referenced → EDIT_IMAGE_REF → Runway (or EDIT_IMAGE_REF_TO_VIDEO if video intent)" 
    elif active and uploaded and referenced:
        base_explanation = "Active + Uploaded + Referenced → EDIT_IMAGE_REF → Runway (or EDIT_IMAGE_REF_TO_VIDEO if video intent)"
    else:
        base_explanation = "Unusual combination - fallback logic applied"
    
    return base_explanation + "\n\nNOTE: System first checks for video intent keywords before applying image flows."


# Example usage in main app
"""
# In your main FastAPI app (main.py or wherever):

from app.api.simplified_endpoints import router as simplified_router

app = FastAPI()
app.include_router(simplified_router)

# Then you can call:
# POST /api/v2/process
# {
#   "prompt": "Change the background to a beach",
#   "active_image": true,
#   "uploaded_image": false,
#   "referenced_image": false
# }
""" 