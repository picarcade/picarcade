from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class WorkflowType(str, Enum):
    """Simplified workflow types for Phase 1"""
    
    # Core generation workflows
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"  # Text-to-video with audio support
    IMAGE_TO_VIDEO = "image_to_video"  # Animate existing images into video
    TEXT_TO_VIDEO = "text_to_video"  # Text-to-video without audio
    
    # Image modification workflows
    IMAGE_EDITING = "image_editing"
    IMAGE_ENHANCEMENT = "image_enhancement"
    
    # Reference-based workflows
    REFERENCE_STYLING = "reference_styling"  # Combines celebrity/event/fashion/virtual try-on
    HAIR_STYLING = "hair_styling"
    
    # Style workflows
    STYLE_TRANSFER = "style_transfer"

class IntentClassification(BaseModel):
    """Result of intent classification"""
    workflow_type: WorkflowType
    confidence: float
    reasoning: str
    requires_web_search: bool = False
    web_search_query: Optional[str] = None
    enhancement_needed: bool = False
    metadata: Dict[str, Any] = {}

class ModelSelection(BaseModel):
    """Selected model for workflow execution"""
    model_id: str
    provider: str
    reasoning: str
    fallback_models: List[str] = []
    estimated_cost: float = 0.0
    estimated_time: int = 30  # seconds 