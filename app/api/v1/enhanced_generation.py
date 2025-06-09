from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
import re
import os
from typing import Optional, Dict, Any
from app.services.enhanced_workflow_service import EnhancedWorkflowService
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/api/v1/enhanced", tags=["enhanced-generation"])

class EnhancedGenerationRequest(BaseModel):
    prompt: str
    working_image_url: Optional[str] = None
    user_preferences: Optional[Dict[str, str]] = None
    use_ai_classification: bool = True  # Allow fallback to existing system
    session_id: Optional[str] = None  # For session management
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if not v or not v.strip():
            raise ValueError('Prompt cannot be empty')
        
        if len(v) > 2000:  # Reasonable limit
            raise ValueError('Prompt too long (max 2000 characters)')
        
        # Check for potential injection attempts
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'data:.*,.*',
            r'vbscript:',
            r'onclick\s*=',
            r'onerror\s*=',
            r'onload\s*=',
            r'\bon\w+\s*=',  # Generic event handlers
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Invalid characters detected in prompt')
        
        return v.strip()
    
    @validator('working_image_url')
    def validate_image_url(cls, v):
        if v:
            if not re.match(r'^https?://', v):
                raise ValueError('Invalid image URL format')
            
            # Add domain whitelist for security
            allowed_domains = [
                'supabase.co', 
                'your-domain.com',
                'localhost',
                '127.0.0.1'
            ]
            
            from urllib.parse import urlparse
            parsed = urlparse(v)
            domain = parsed.netloc.lower()
            
            # Check if domain is in whitelist
            if not any(allowed in domain for allowed in allowed_domains):
                raise ValueError('Image URL from unauthorized domain')
            
            # Prevent SSRF attacks
            if domain in ['169.254.169.254', '127.0.0.1', 'localhost'] and not os.getenv('DEBUG'):
                raise ValueError('Access to internal URLs not allowed')
        
        return v
    
    @validator('user_preferences')
    def validate_preferences(cls, v):
        if v:
            # Sanitize preference values
            allowed_keys = {'quality', 'style', 'format'}
            allowed_quality_values = {'speed', 'balanced', 'quality'}
            
            sanitized = {}
            for key, value in v.items():
                if key in allowed_keys:
                    if key == 'quality' and value not in allowed_quality_values:
                        raise ValueError(f'Invalid quality preference: {value}')
                    sanitized[key] = str(value)[:50]  # Limit value length
            
            return sanitized
        return v

# Initialize service lazily to avoid environment loading issues
enhanced_workflow_service = None

def get_enhanced_workflow_service():
    """Get or create the enhanced workflow service instance"""
    global enhanced_workflow_service
    if enhanced_workflow_service is None:
        enhanced_workflow_service = EnhancedWorkflowService()
    return enhanced_workflow_service

@router.post("/process")
async def process_enhanced_request(
    request: EnhancedGenerationRequest,
    user = Depends(get_current_user)
):
    """
    Enhanced request processing with AI intent classification
    """
    
    try:
        service = get_enhanced_workflow_service()
        
        if request.use_ai_classification:
            # Use new AI-powered workflow
            result = await service.process_request(
                prompt=request.prompt,
                user_id=user.id,
                working_image_url=request.working_image_url,
                user_preferences=request.user_preferences,
                session_id=request.session_id
            )
        else:
            # Fallback to existing workflow (for comparison/debugging)
            result = await process_with_existing_system(request, user)
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Enhanced generation request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_metrics(user = Depends(get_current_user)):
    """Get AI classification metrics including Sprint 2 web search stats"""
    service = get_enhanced_workflow_service()
    return service.get_metrics()

@router.post("/test-virtual-tryon")
async def test_virtual_tryon(
    request: EnhancedGenerationRequest,
    user = Depends(get_current_user)
):
    """
    Sprint 2: Test virtual try-on capabilities with enhanced model selection
    """
    
    try:
        service = get_enhanced_workflow_service()
        
        # Force reference styling workflow for testing
        result = await service.process_request(
            prompt=request.prompt,
            user_id=user.id,
            working_image_url=request.working_image_url,
            user_preferences=request.user_preferences,
            session_id=request.session_id
        )
        
        # Add Sprint 2 specific metadata
        result["sprint2_features"] = {
            "virtual_tryon_optimized": result["workflow_type"] == "reference_styling",
            "multi_image_support": "multi-image-kontext-max" in result["model_selection"]["model_id"],
            "web_search_enhanced": result["metadata"].get("requires_web_search", False),
            "styling_keywords": result["metadata"].get("styling_data", {}).get("styling_inspiration", [])
        }
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Virtual try-on test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-web-search")
async def test_web_search(
    prompt: str,
    user = Depends(get_current_user)
):
    """
    Sprint 2: Test web search functionality for celebrity/event styling
    """
    
    try:
        service = get_enhanced_workflow_service()
        
        # Test web search detection
        should_search, search_query = await service.web_search_service.should_search_for_reference(
            prompt, {}
        )
        
        styling_data = None
        if should_search and search_query:
            styling_data = await service.web_search_service.search_for_styling_references(search_query)
        
        return {
            "prompt": prompt,
            "should_search": should_search,
            "search_query": search_query,
            "styling_data": styling_data,
            "enhanced_prompt": service.web_search_service.enhance_prompt_with_styling_context(
                prompt, styling_data
            ) if styling_data else prompt
        }
        
    except Exception as e:
        print(f"[ERROR] Web search test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare")
async def compare_workflows(
    request: EnhancedGenerationRequest,
    user = Depends(get_current_user)
):
    """
    Compare AI classification vs existing system (for debugging)
    """
    
    try:
        service = get_enhanced_workflow_service()
        
        # Process with both systems
        ai_result = await service.process_request(
            prompt=request.prompt,
            user_id=user.id,
            working_image_url=request.working_image_url,
            user_preferences=request.user_preferences,
            session_id=request.session_id
        )
        
        existing_result = await process_with_existing_system(request, user)
        
        return {
            "ai_classification": ai_result,
            "existing_system": existing_result,
            "differences": {
                "workflow_type": ai_result["workflow_type"] != existing_result.get("workflow_type"),
                "model_selection": ai_result["model_selection"]["model_id"] != existing_result.get("model_id"),
                "prompt_changes": ai_result["final_prompt"] != request.prompt
            }
        }
    except Exception as e:
        print(f"[ERROR] Workflow comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_with_existing_system(request: EnhancedGenerationRequest, user) -> Dict[str, Any]:
    """
    Process using existing system for comparison
    """
    # Import your existing services
    from app.services.intent_parser import BasicIntentParser
    from app.services.model_router import ModelRouter
    
    intent_parser = BasicIntentParser()
    model_router = ModelRouter()
    
    # Use existing intent analysis
    intent_analysis = await intent_parser.analyze_intent(
        prompt=request.prompt,
        user_context={},
        generation_id="comparison_test",
        uploaded_images=None,
        current_working_image=request.working_image_url
    )
    
    # Map to enhanced workflow format for comparison
    workflow_mapping = {
        "generate_image": "image_generation",
        "generate_video": "video_generation", 
        "edit_image": "image_editing",
        "enhance_image": "image_enhancement",
        "virtual_tryon": "reference_styling"
    }
    
    return {
        "success": True,
        "workflow_type": workflow_mapping.get(intent_analysis.detected_intent.value, "image_generation"),
        "final_prompt": request.prompt,
        "model_id": intent_analysis.suggested_model,
        "confidence": intent_analysis.confidence,
        "reasoning": f"Existing system: {intent_analysis.detected_intent.value}",
        "processing_time": 0.05,
        "estimated_cost": 0.04,
        "estimated_time": 30,
        "system": "existing"
    } 