from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

class CreativeIntent(str, Enum):
    GENERATE_IMAGE = "generate_image"
    GENERATE_VIDEO = "generate_video"
    EDIT_IMAGE = "edit_image"
    ENHANCE_IMAGE = "enhance_image"
    VIRTUAL_TRYON = "virtual_tryon"
    VIDEO_EDIT = "video_edit"

class QualityPriority(str, Enum):
    SPEED = "speed"
    BALANCED = "balanced"
    QUALITY = "quality"

class ReferenceImage(BaseModel):
    uri: str = Field(..., description="URL of the reference image")
    tag: str = Field(..., description="Tag for @mention in prompt")

class GenerationRequest(BaseModel):
    prompt: str = Field(..., description="User's generation prompt")
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(None, description="Conversation/session identifier for tracking working images")
    intent: Optional[CreativeIntent] = None
    quality_priority: QualityPriority = QualityPriority.BALANCED
    uploaded_images: Optional[List[str]] = Field(None, description="URLs of uploaded images")
    current_working_image: Optional[str] = Field(None, description="URL of the current working image in this session")
    current_working_video: Optional[str] = Field(None, description="URL of the current working video in this session")
    reference_images: Optional[List[ReferenceImage]] = Field(None, description="Reference images with tags for @mentions")
    additional_params: Optional[Dict[str, Any]] = None

class GenerationResponse(BaseModel):
    success: bool
    generation_id: str
    output_url: Optional[str] = None
    model_used: Optional[str] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
    input_image_used: Optional[str] = Field(None, description="URL of the input image that was edited (for flux-kontext)")
    image_source_type: Optional[str] = Field(None, description="Source of input image: 'uploaded', 'working_image', or None")
    references_used: Optional[List[ReferenceImage]] = Field(None, description="Reference images used in generation")
    witty_messages: Optional[List[str]] = Field(None, description="Engaging messages to display during generation")
    metadata: Optional[Dict[str, Any]] = None

class IntentAnalysis(BaseModel):
    detected_intent: CreativeIntent
    confidence: float = Field(..., ge=0.0, le=1.0)
    content_type: str  # "photo", "artwork", "video", etc.
    complexity_level: str  # "simple", "moderate", "complex"
    suggested_model: Optional[str] = None
    reasoning: Optional[str] = None  # AI reasoning for the classification
    suggested_enhancements: Optional[List[str]] = None  # Suggested prompt improvements
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata for enhanced classification 