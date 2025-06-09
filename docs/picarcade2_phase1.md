# Phase 1 Implementation Plan - AI Intent Classification System

## Overview

This Phase 1 implementation focuses on building a robust, simplified AI intent classification system that integrates seamlessly with your existing frontend and backend infrastructure, delivered through incremental sprints.

## Core Objectives

1. **Replace basic rule-based intent parsing** with AI-powered classification
2. **Integrate verified FLUX Kontext models** for optimal quality
3. **Maintain backward compatibility** with existing frontend
4. **Implement robust error handling** and fallbacks
5. **Optimize for performance and cost**

## 🚀 Sprint Implementation Plan

### Sprint 1: Core AI Intent Classification (Week 1-2)
**Goal**: Basic AI-powered intent classification testable via existing frontend
**Deliverable**: Side-by-side comparison of AI vs existing classification

### Sprint 2: Enhanced Model Selection & Virtual Try-on (Week 3-4)  
**Goal**: Improved model mappings and virtual try-on capabilities
**Deliverable**: New virtual try-on workflow with web search integration

### Sprint 3: Production Infrastructure (Week 5-6)
**Goal**: Redis cache, rate limiting, and circuit breaker reliability
**Deliverable**: Production-ready performance and error handling

### Sprint 4: Advanced Video Workflows (Week 7-8)
**Goal**: Granular video generation with optimized model selection
**Deliverable**: Image-to-video, text-to-video, and premium video workflows

### Sprint 5: Frontend Enhancement & Analytics (Week 9-10)
**Goal**: Enhanced UI components and comprehensive monitoring
**Deliverable**: Complete user experience with analytics dashboard

## Simplified Workflow Types

```python
# app/models/workflows.py
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
```

---

# 🏃‍♂️ Sprint 1: Core AI Intent Classification
**Duration**: Week 1-2  
**Goal**: Basic AI-powered intent classification testable via existing frontend  
**Deliverable**: Side-by-side comparison of AI vs existing classification

## Sprint 1 Scope
- ✅ Basic AI intent classifier with OpenAI GPT-4o-mini
- ✅ Simple model selection service
- ✅ Integration with existing workflow service
- ✅ Comparison endpoint for testing
- ✅ Minimal error handling and fallbacks

## Core Services Implementation (Sprint 1)

### 1. Intent Classification Service

```python
# app/services/intent_classifier.py
import asyncio
import json
import re
import random
import redis
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from app.models.workflows import WorkflowType, IntentClassification
from app.core.cache import DistributedCache
from app.core.circuit_breaker import CircuitBreaker
from app.core.rate_limiter import RateLimiter
import os

def retry_with_exponential_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Retry decorator with exponential backoff and jitter"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        break
                    
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator

class IntentClassifier:
    """Sprint 1: Basic AI-powered intent classification (will be enhanced in Sprint 3)"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
        
        # Sprint 1: Simple in-memory cache (will be replaced with Redis in Sprint 3)
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        self.cache_timestamps = {}
        
        # Sprint 3 additions (commented out for now):
        # self.circuit_breaker = CircuitBreaker(...)
        # self.rate_limiter = RateLimiter(...)
        
        # Fallback patterns for when AI fails
        self.fallback_patterns = {
            WorkflowType.VIDEO_GENERATION: ["video with audio", "video with sound", "music video", "cinematic"],
            WorkflowType.IMAGE_TO_VIDEO: ["animate", "animate this", "bring to life", "make this move"],
            WorkflowType.TEXT_TO_VIDEO: ["video", "movie", "clip", "scene", "footage"],
            WorkflowType.HAIR_STYLING: ["hair", "haircut", "hairstyle", "blonde", "brunette"],
            WorkflowType.REFERENCE_STYLING: ["taylor swift", "celebrity", "like", "grammy", "met gala", "put @", "try on", "wear this", "outfit", "dress up"],
            WorkflowType.IMAGE_EDITING: ["edit", "change", "modify", "adjust"],
            WorkflowType.IMAGE_ENHANCEMENT: ["enhance", "improve", "upscale", "sharpen"],
            WorkflowType.STYLE_TRANSFER: ["style", "artistic", "painting", "sketch"]
        }
    
    async def classify_intent(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> IntentClassification:
        """
        Sprint 1: Basic classification with simple caching
        (Sprint 3 will add rate limiting and circuit breaker protection)
        """
        
        # Generate cache key
        cache_key = self._generate_cache_key(prompt, context)
        
        # Check simple in-memory cache first
        if cache_key in self.cache:
            timestamp = self.cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self.cache_ttl:
                return self.cache[cache_key]
            else:
                # Clean up expired cache entry
                del self.cache[cache_key]
                del self.cache_timestamps[cache_key]
        
        try:
            # Try AI classification (Sprint 1: direct call, Sprint 3: with circuit breaker)
            result = await self._ai_classify(prompt, context)
            
            # Cache successful result (Sprint 1: in-memory, Sprint 3: Redis)
            self.cache[cache_key] = result
            self.cache_timestamps[cache_key] = time.time()
            
            return result
            
        except Exception as e:
            print(f"[WARNING] AI classification failed: {e}")
            # Fall back to pattern matching
            return self._fallback_classify(prompt, context, reason=str(e))
    
    @retry_with_exponential_backoff(max_retries=2, base_delay=0.5)
    async def _ai_classify(self, prompt: str, context: Optional[Dict[str, Any]]) -> IntentClassification:
        """AI-powered classification using GPT-4o-mini with retry logic"""
        
        system_prompt = """You are an expert at classifying user intents for creative AI workflows.

Available workflow types:
- image_generation: Create new images from text
- video_generation: Create videos with audio support (premium, uses Veo 3)
- image_to_video: Animate existing images into video (most efficient for image animation)
- text_to_video: Create videos from text without audio (cost-effective option)
- image_editing: Modify existing images
- image_enhancement: Improve image quality (upscale, sharpen, etc.)
- reference_styling: Style based on celebrities, events, fashion references, or virtual try-on (putting person in different outfits)
- hair_styling: Change hair color, cut, or style
- style_transfer: Apply artistic styles to images

Context clues:
- If user has uploaded/working images and wants video → image_to_video
- Audio/music video requests → video_generation
- Basic video requests without audio → text_to_video
- Celebrity names + events → reference_styling
- Virtual try-on phrases like "put @person in", "try on", "wear this outfit" → reference_styling
- Hair-related terms → hair_styling
- Art/style terms → style_transfer

Respond in JSON format:
{
    "workflow_type": "workflow_name",
    "confidence": 0.95,
    "reasoning": "brief explanation",
    "requires_web_search": false,
    "web_search_query": null,
    "enhancement_needed": false
}"""

        user_prompt = f"""
Classify this user request:
"{prompt}"

Context: {self._build_context_string(context)}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=300
        )
        
        # Parse JSON response
        result_text = response.choices[0].message.content.strip()
        
        # Handle potential markdown formatting
        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
        
        result_data = json.loads(result_text)
        
        return IntentClassification(
            workflow_type=WorkflowType(result_data["workflow_type"]),
            confidence=result_data["confidence"],
            reasoning=result_data["reasoning"],
            requires_web_search=result_data.get("requires_web_search", False),
            web_search_query=result_data.get("web_search_query"),
            enhancement_needed=result_data.get("enhancement_needed", False)
        )
    
    def _fallback_classify(self, prompt: str, context: Optional[Dict[str, Any]], reason: str = "ai_failed") -> IntentClassification:
        """Pattern-based fallback classification with enhanced security validation"""
        
        # Input validation and sanitization
        if not prompt or len(prompt.strip()) == 0:
            return IntentClassification(
                workflow_type=WorkflowType.IMAGE_GENERATION,
                confidence=0.3,
                reasoning="Empty prompt - defaulting to image generation",
                requires_web_search=False,
                enhancement_needed=True
            )
        
        # Security check for potentially malicious content
        if self._contains_suspicious_content(prompt):
            return IntentClassification(
                workflow_type=WorkflowType.IMAGE_GENERATION,
                confidence=0.3,
                reasoning="Suspicious content detected - using safe default",
                requires_web_search=False,
                enhancement_needed=True
            )
        
        prompt_lower = prompt.lower()
        
        # Check context first
        if context and context.get("working_images"):
            # User has images, likely editing
            if any(word in prompt_lower for word in ["enhance", "improve", "upscale"]):
                workflow = WorkflowType.IMAGE_ENHANCEMENT
            else:
                workflow = WorkflowType.IMAGE_EDITING
        else:
            # No images, check patterns
            workflow = WorkflowType.IMAGE_GENERATION  # Default
            
            for wf_type, patterns in self.fallback_patterns.items():
                if any(pattern in prompt_lower for pattern in patterns):
                    workflow = wf_type
                    break
        
        # Check if web search might be needed
        requires_search = any(indicator in prompt_lower for indicator in [
            "taylor swift", "celebrity", "grammy", "met gala", "like", "style of"
        ])
        
        return IntentClassification(
            workflow_type=workflow,
            confidence=0.6,  # Lower confidence for fallback
            reasoning=f"Fallback classification ({reason}) based on keyword patterns",
            requires_web_search=requires_search,
            enhancement_needed=len(prompt.split()) < 5
        )
    
    def _contains_suspicious_content(self, prompt: str) -> bool:
        """Check for potentially malicious or inappropriate content"""
        
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'data:.*,.*',
            r'vbscript:',
            r'onclick\s*=',
            r'onerror\s*=',
            r'onload\s*=',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                return True
        
        return False
    
    def _generate_cache_key(self, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for classification"""
        context_str = ""
        if context:
            has_images = bool(context.get("working_images") or context.get("uploaded_images"))
            context_str = f"_images:{has_images}"
        
        return f"intent_{hash(prompt.lower())}{context_str}"
    
    def _build_context_string(self, context: Optional[Dict[str, Any]]) -> str:
        """Build context string for AI"""
        if not context:
            return "No additional context"
        
        parts = []
        if context.get("working_images"):
            parts.append(f"User has {len(context['working_images'])} working images")
        if context.get("uploaded_images"):
            parts.append(f"User uploaded {len(context['uploaded_images'])} new images")
        
        return "; ".join(parts) if parts else "No additional context"

---

# 🏃‍♂️ Sprint 2: Enhanced Model Selection & Virtual Try-on  
**Duration**: Week 3-4  
**Goal**: Improved model mappings and virtual try-on capabilities  
**Deliverable**: New virtual try-on workflow with web search integration

## Sprint 2 Scope
- ✅ Enhanced model mappings with virtual try-on support
- ✅ `flux-kontext-apps/multi-image-kontext-max` integration
- ✅ Web search integration for reference styling
- ✅ Improved workflow detection patterns
- ✅ Basic video workflow support

## Sprint 2 Enhancements
```

### 1. Enhanced Model Selection Service (Sprint 2)

```python
# app/services/model_selector.py
from typing import Dict, List, Optional
from app.models.workflows import WorkflowType, ModelSelection, IntentClassification

class ModelSelector:
    """Intelligent model selection based on workflow type and requirements"""
    
    def __init__(self):
        # Verified model mappings based on actual FLUX Kontext Apps
        self.image_models = {
            WorkflowType.HAIR_STYLING: {
                "primary": "flux-kontext-apps/change-haircut",
                "fallback": ["flux-kontext-apps/professional-headshot", "zsxkib/flux-kontext-pro"],
                "cost_per_generation": 0.05
            },
            WorkflowType.REFERENCE_STYLING: {
                "primary": "flux-kontext-apps/multi-image-kontext-max",
                "fallback": ["flux-kontext-apps/professional-headshot", "flux-kontext-apps/face-to-many-kontext"],
                "cost_per_generation": 0.06
            },
            WorkflowType.IMAGE_ENHANCEMENT: {
                "primary": "flux-kontext-apps/restore-image",
                "fallback": ["flux-kontext-apps/depth-of-field", "zsxkib/flux-kontext-pro"],
                "cost_per_generation": 0.04
            },
            WorkflowType.IMAGE_EDITING: {
                "primary": "zsxkib/flux-kontext-pro",
                "fallback": ["flux-kontext-apps/filters", "black-forest-labs/flux-1.1-pro"],
                "cost_per_generation": 0.03
            },
            WorkflowType.STYLE_TRANSFER: {
                "primary": "flux-kontext-apps/cartoonify",
                "fallback": ["flux-kontext-apps/renaissance", "zsxkib/flux-kontext-pro"],
                "cost_per_generation": 0.04
            },
            WorkflowType.IMAGE_GENERATION: {
                "primary": "black-forest-labs/flux-1.1-pro",
                "fallback": ["black-forest-labs/flux-schnell", "black-forest-labs/flux-1.1-pro-ultra"],
                "cost_per_generation": 0.04
            }
        }
        
        self.video_models = {
            WorkflowType.VIDEO_GENERATION: {
                "primary": "google/veo-3",  # Best for video with audio support
                "fallback": ["google/veo-2", "minimax/video-01"],
                "cost_per_second": 0.75
            },
            WorkflowType.IMAGE_TO_VIDEO: {
                "primary": "lightricks/ltx-video",  # Optimized for image-to-video animation
                "fallback": ["minimax/video-01", "wavespeedai/wan-2.1-i2v-720p"],
                "cost_per_second": 0.20
            },
            WorkflowType.TEXT_TO_VIDEO: {
                "primary": "minimax/video-01",  # Cost-effective text-to-video without audio
                "fallback": ["lightricks/ltx-video", "kwaivgi/kling-v1.6-standard"],
                "cost_per_second": 0.30
            }
        }
    
    def select_model(
        self, 
        intent: IntentClassification,
        user_preferences: Optional[Dict[str, str]] = None
    ) -> ModelSelection:
        """
        Select optimal model based on workflow type and preferences
        """
        
        workflow_type = intent.workflow_type
        
        # Select model based on workflow type
        if workflow_type in [WorkflowType.VIDEO_GENERATION, WorkflowType.IMAGE_TO_VIDEO, WorkflowType.TEXT_TO_VIDEO]:
            model_config = self.video_models[workflow_type]
            video_duration = 6 if workflow_type == WorkflowType.TEXT_TO_VIDEO else 10  # Minimax supports 6s, others 10s
            cost_estimate = model_config["cost_per_second"] * video_duration
            time_estimate = 90 if workflow_type == WorkflowType.IMAGE_TO_VIDEO else 120  # Image-to-video is faster
        else:
            model_config = self.image_models.get(workflow_type, self.image_models[WorkflowType.IMAGE_GENERATION])
            cost_estimate = model_config["cost_per_generation"]
            time_estimate = 30  # 30 seconds for image
        
        # Adjust for user preferences
        selected_model = model_config["primary"]
        
        if user_preferences:
            quality_pref = user_preferences.get("quality", "balanced")
            
            if quality_pref == "speed" and workflow_type == WorkflowType.IMAGE_GENERATION:
                selected_model = "black-forest-labs/flux-schnell"
                cost_estimate = 0.02
                time_estimate = 15
            elif quality_pref == "quality" and workflow_type == WorkflowType.IMAGE_GENERATION:
                selected_model = "black-forest-labs/flux-1.1-pro-ultra"
                cost_estimate = 0.08
                time_estimate = 45
        
        reasoning = f"Selected {selected_model} for {workflow_type.value}"
        if intent.confidence < 0.8:
            reasoning += f" (low confidence: {intent.confidence:.2f})"
        
        return ModelSelection(
            model_id=selected_model,
            provider="replicate",
            reasoning=reasoning,
            fallback_models=model_config["fallback"],
            estimated_cost=cost_estimate,
            estimated_time=time_estimate
        )
```

### 3. Enhanced Workflow Service

```python
# app/services/enhanced_workflow_service.py
import asyncio
import time
from typing import Dict, Any, Optional
from app.services.intent_classifier import IntentClassifier
from app.services.model_selector import ModelSelector
from app.services.reference_service import ReferenceService  # Your existing service
from app.models.workflows import WorkflowType, IntentClassification, ModelSelection

class EnhancedWorkflowService:
    """Main orchestration service that integrates AI intent classification"""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.model_selector = ModelSelector()
        self.reference_service = ReferenceService()  # Your existing service
        
        # Performance tracking
        self.metrics = {
            "classifications": 0,
            "cache_hits": 0,
            "fallbacks": 0,
            "errors": 0
        }
    
    async def process_request(
        self,
        prompt: str,
        user_id: str,
        working_image_url: Optional[str] = None,
        user_preferences: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing user requests with AI intent classification
        """
        
        start_time = time.time()
        
        try:
            # Step 1: Build context
            context = await self._build_context(user_id, working_image_url)
            
            # Step 2: Classify intent using AI with rate limiting
            intent = await self.intent_classifier.classify_intent(prompt, context, user_id)
            self.metrics["classifications"] += 1
            
            # Step 3: Select optimal model
            model_selection = self.model_selector.select_model(intent, user_preferences)
            
            # Step 4: Process with existing reference system
            final_prompt, references = await self._integrate_with_references(
                prompt, user_id, working_image_url, intent
            )
            
            # Step 5: Apply quick prompt enhancement if needed
            if intent.enhancement_needed:
                final_prompt = self._quick_enhance_prompt(final_prompt, intent)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "workflow_type": intent.workflow_type.value,
                "final_prompt": final_prompt,
                "model_selection": model_selection.dict(),
                "references": references,
                "intent_confidence": intent.confidence,
                "reasoning": f"{intent.reasoning} | {model_selection.reasoning}",
                "processing_time": processing_time,
                "estimated_cost": model_selection.estimated_cost,
                "estimated_time": model_selection.estimated_time,
                "metadata": {
                    "requires_web_search": intent.requires_web_search,
                    "web_search_query": intent.web_search_query,
                    "enhancement_applied": intent.enhancement_needed
                }
            }
            
        except Exception as e:
            self.metrics["errors"] += 1
            print(f"[ERROR] Enhanced workflow processing failed: {e}")
            
            # Graceful fallback to existing system
            return await self._fallback_to_existing_system(
                prompt, user_id, working_image_url, str(e)
            )
    
    async def _build_context(self, user_id: str, working_image_url: Optional[str]) -> Dict[str, Any]:
        """Build context for intent classification"""
        
        context = {"user_id": user_id}
        
        if working_image_url:
            context["working_images"] = [working_image_url]
        
        # Add any other relevant context from your existing system
        return context
    
    async def _integrate_with_references(
        self,
        prompt: str,
        user_id: str,
        working_image_url: Optional[str],
        intent: IntentClassification
    ) -> tuple[str, list]:
        """
        Integrate with your existing reference system
        """
        
        try:
            if working_image_url:
                # Use your existing reference enhancement
                enhanced_prompt, references = await self.reference_service.enhance_prompt_with_working_image(
                    prompt, user_id, working_image_url
                )
                return enhanced_prompt, references
            else:
                # Parse reference mentions
                references, missing_tags = await self.reference_service.parse_reference_mentions(
                    prompt, user_id
                )
                return prompt, references
        except Exception as e:
            print(f"[WARNING] Reference integration failed: {e}")
            return prompt, []
    
    def _quick_enhance_prompt(self, prompt: str, intent: IntentClassification) -> str:
        """
        Quick rule-based prompt enhancement (no AI call for performance)
        """
        
        word_count = len(prompt.split())
        
        # Only enhance very short prompts
        if word_count >= 8:
            return prompt
        
        # Add basic quality descriptors based on workflow type
        if intent.workflow_type == WorkflowType.IMAGE_GENERATION:
            return f"{prompt}, high quality, detailed, professional"
        elif intent.workflow_type == WorkflowType.HAIR_STYLING:
            return f"{prompt}, professional hair styling, high detail"
        elif intent.workflow_type == WorkflowType.REFERENCE_STYLING:
            return f"{prompt}, high quality styling, professional photography"
        else:
            return f"{prompt}, high quality, detailed"
    
    async def _fallback_to_existing_system(
        self,
        prompt: str,
        user_id: str,
        working_image_url: Optional[str],
        error: str
    ) -> Dict[str, Any]:
        """
        Fallback to your existing workflow system if AI classification fails
        """
        
        return {
            "success": True,
            "workflow_type": "image_generation",  # Safe default
            "final_prompt": prompt,
            "model_selection": {
                "model_id": "black-forest-labs/flux-1.1-pro",
                "provider": "replicate",
                "reasoning": f"Fallback due to error: {error}"
            },
            "references": [],
            "intent_confidence": 0.5,
            "reasoning": "Fallback to existing system",
            "processing_time": 0.1,
            "estimated_cost": 0.04,
            "estimated_time": 30,
            "fallback_used": True
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            **self.metrics,
            "cache_hit_rate": self.metrics["cache_hits"] / max(self.metrics["classifications"], 1),
            "error_rate": self.metrics["errors"] / max(self.metrics["classifications"], 1)
        }
```

---

# 🏃‍♂️ Sprint 5: Frontend Enhancement & Analytics  
**Duration**: Week 9-10  
**Goal**: Enhanced UI components and comprehensive monitoring  
**Deliverable**: Complete user experience with analytics dashboard

## Sprint 5 Scope
- ✅ Enhanced frontend components with AI classification insights
- ✅ User preference management
- ✅ Real-time analytics and monitoring
- ✅ Performance metrics dashboard
- ✅ A/B testing framework for AI vs existing system

## Frontend Integration (Sprint 5)

### 1. Enhanced API Endpoint

```python
# app/api/routes/enhanced_generation.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
import re
import os
from typing import Optional, Dict, Any
from app.services.enhanced_workflow_service import EnhancedWorkflowService
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/v1/enhanced", tags=["enhanced-generation"])

class EnhancedGenerationRequest(BaseModel):
    prompt: str
    working_image_url: Optional[str] = None
    user_preferences: Optional[Dict[str, str]] = None
    use_ai_classification: bool = True  # Allow fallback to existing system
    
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

enhanced_workflow_service = EnhancedWorkflowService()

@router.post("/process")
async def process_enhanced_request(
    request: EnhancedGenerationRequest,
    user = Depends(get_current_user)
):
    """
    Enhanced request processing with AI intent classification
    """
    
    try:
        if request.use_ai_classification:
            # Use new AI-powered workflow
            result = await enhanced_workflow_service.process_request(
                prompt=request.prompt,
                user_id=user.id,
                working_image_url=request.working_image_url,
                user_preferences=request.user_preferences
            )
        else:
            # Fallback to existing workflow (for comparison/debugging)
            result = await process_with_existing_system(request, user)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_metrics(user = Depends(get_current_user)):
    """Get AI classification metrics"""
    return enhanced_workflow_service.get_metrics()

@router.post("/compare")
async def compare_workflows(
    request: EnhancedGenerationRequest,
    user = Depends(get_current_user)
):
    """
    Compare AI classification vs existing system (for debugging)
    """
    
    # Process with both systems
    ai_result = await enhanced_workflow_service.process_request(
        prompt=request.prompt,
        user_id=user.id,
        working_image_url=request.working_image_url,
        user_preferences=request.user_preferences
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
```

### 2. Frontend Component Updates

```typescript
// frontend/components/EnhancedGenerationForm.tsx
import React, { useState } from 'react';
import { useWorkflowProcessing } from '../hooks/useWorkflowProcessing';

interface EnhancedGenerationFormProps {
  workingImageUrl?: string;
}

interface UserPreferences {
  quality: 'speed' | 'balanced' | 'quality';
  enableAI: boolean;
}

export const EnhancedGenerationForm: React.FC<EnhancedGenerationFormProps> = ({
  workingImageUrl
}) => {
  const [prompt, setPrompt] = useState('');
  const [preferences, setPreferences] = useState<UserPreferences>({
    quality: 'balanced',
    enableAI: true
  });
  
  const { processWorkflow, isProcessing, result, error } = useWorkflowProcessing();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    await processWorkflow({
      prompt,
      working_image_url: workingImageUrl,
      user_preferences: {
        quality: preferences.quality
      },
      use_ai_classification: preferences.enableAI
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Prompt Input */}
      <div>
        <label htmlFor="prompt" className="block text-sm font-medium text-gray-700">
          Describe what you want to create or modify
        </label>
        <textarea
          id="prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g., Change my hair to blonde with bangs, or Create a cinematic video of a sunset"
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          rows={3}
          required
        />
      </div>

      {/* Quality Preference */}
      <div>
        <label className="block text-sm font-medium text-gray-700">Quality vs Speed</label>
        <select
          value={preferences.quality}
          onChange={(e) => setPreferences(prev => ({ 
            ...prev, 
            quality: e.target.value as 'speed' | 'balanced' | 'quality' 
          }))}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        >
          <option value="speed">Fast (Lower cost, quicker results)</option>
          <option value="balanced">Balanced (Good quality, reasonable speed)</option>
          <option value="quality">High Quality (Best results, slower)</option>
        </select>
      </div>

      {/* AI Classification Toggle */}
      <div className="flex items-center">
        <input
          id="enable-ai"
          type="checkbox"
          checked={preferences.enableAI}
          onChange={(e) => setPreferences(prev => ({ 
            ...prev, 
            enableAI: e.target.checked 
          }))}
          className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
        />
        <label htmlFor="enable-ai" className="ml-2 block text-sm text-gray-900">
          Use AI-powered workflow selection (Recommended)
        </label>
      </div>

      {/* Working Image Indicator */}
      {workingImageUrl && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
          <div className="flex">
            <div className="flex-shrink-0">
              <img 
                src={workingImageUrl} 
                alt="Working image" 
                className="h-10 w-10 rounded object-cover"
              />
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-800">
                AI will optimize workflow based on your uploaded image
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isProcessing || !prompt.trim()}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
      >
        {isProcessing ? 'Processing...' : 'Generate'}
      </button>

      {/* Results Display */}
      {result && (
        <div className="mt-6 space-y-4">
          {/* Workflow Info */}
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <h3 className="text-sm font-medium text-green-800">AI Analysis</h3>
            <div className="mt-2 text-sm text-green-700">
              <p><strong>Detected workflow:</strong> {result.workflow_type}</p>
              <p><strong>Selected model:</strong> {result.model_selection.model_id}</p>
              <p><strong>Confidence:</strong> {(result.intent_confidence * 100).toFixed(1)}%</p>
              <p><strong>Reasoning:</strong> {result.reasoning}</p>
              {result.estimated_cost && (
                <p><strong>Estimated cost:</strong> ${result.estimated_cost.toFixed(3)}</p>
              )}
            </div>
          </div>

          {/* Enhanced Prompt Display */}
          {result.final_prompt !== prompt && (
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <h3 className="text-sm font-medium text-blue-800">Enhanced Prompt</h3>
              <p className="mt-2 text-sm text-blue-700">{result.final_prompt}</p>
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
    </form>
  );
};
```

### 3. Custom Hook for Workflow Processing

```typescript
// frontend/hooks/useWorkflowProcessing.ts
import { useState } from 'react';
import { api } from '../utils/api';

interface WorkflowRequest {
  prompt: string;
  working_image_url?: string;
  user_preferences?: {
    quality: 'speed' | 'balanced' | 'quality';
  };
  use_ai_classification?: boolean;
}

interface WorkflowResult {
  success: boolean;
  workflow_type: string;
  final_prompt: string;
  model_selection: {
    model_id: string;
    provider: string;
    reasoning: string;
  };
  references: any[];
  intent_confidence: number;
  reasoning: string;
  processing_time: number;
  estimated_cost?: number;
  estimated_time?: number;
  metadata?: any;
}

export const useWorkflowProcessing = () => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const processWorkflow = async (request: WorkflowRequest) => {
    setIsProcessing(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.post('/enhanced/process', request);
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred');
    } finally {
      setIsProcessing(false);
    }
  };

  const compareWorkflows = async (request: WorkflowRequest) => {
    setIsProcessing(true);
    setError(null);

    try {
      const response = await api.post('/enhanced/compare', request);
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Comparison failed');
      return null;
    } finally {
      setIsProcessing(false);
    }
  };

  return {
    processWorkflow,
    compareWorkflows,
    isProcessing,
    result,
    error,
    clearResult: () => setResult(null),
    clearError: () => setError(null)
  };
};
```

### 4. Integration with Existing Generation Components

```typescript
// frontend/components/GenerationWrapper.tsx
import React, { useState } from 'react';
import { EnhancedGenerationForm } from './EnhancedGenerationForm';
import { LegacyGenerationForm } from './LegacyGenerationForm'; // Your existing form

interface GenerationWrapperProps {
  workingImageUrl?: string;
}

export const GenerationWrapper: React.FC<GenerationWrapperProps> = ({
  workingImageUrl
}) => {
  const [useEnhanced, setUseEnhanced] = useState(true);

  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* Toggle between enhanced and legacy */}
      <div className="mb-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setUseEnhanced(true)}
            className={`px-4 py-2 rounded-md ${
              useEnhanced 
                ? 'bg-indigo-600 text-white' 
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            AI-Powered (Recommended)
          </button>
          <button
            onClick={() => setUseEnhanced(false)}
            className={`px-4 py-2 rounded-md ${
              !useEnhanced 
                ? 'bg-indigo-600 text-white' 
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Classic Mode
          </button>
        </div>
        
        {useEnhanced && (
          <p className="mt-2 text-sm text-gray-600">
            ✨ AI will automatically detect your intent and select the best model
          </p>
        )}
      </div>

      {/* Render appropriate form */}
      {useEnhanced ? (
        <EnhancedGenerationForm workingImageUrl={workingImageUrl} />
      ) : (
        <LegacyGenerationForm workingImageUrl={workingImageUrl} />
      )}
    </div>
  );
};
```

---

# 🏃‍♂️ Sprint 3: Production Infrastructure  
**Duration**: Week 5-6  
**Goal**: Redis cache, rate limiting, and circuit breaker reliability  
**Deliverable**: Production-ready performance and error handling

## Sprint 3 Scope
- ✅ Redis distributed caching system
- ✅ Rate limiting and cost controls
- ✅ Circuit breaker pattern for API reliability
- ✅ Enhanced error handling and monitoring
- ✅ Database schema for analytics

## Core Infrastructure Components (Sprint 3)

### 1. Distributed Cache System

```python
# app/core/cache.py
import redis
import json
import asyncio
from typing import Any, Optional, Dict
from datetime import timedelta

class DistributedCache:
    """Redis-based distributed cache for multi-instance deployment"""
    
    def __init__(self, redis_url: str, prefix: str = "", ttl: int = 3600):
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.prefix = prefix
        self.ttl = ttl
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache"""
        try:
            cached = await asyncio.to_thread(self.redis_client.get, f"{self.prefix}{key}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"[WARNING] Cache get failed: {e}")
        return None
    
    async def set(self, key: str, value: Dict[str, Any]):
        """Set value in cache with TTL"""
        try:
            await asyncio.to_thread(
                self.redis_client.setex,
                f"{self.prefix}{key}",
                self.ttl,
                json.dumps(value)
            )
        except Exception as e:
            print(f"[WARNING] Cache set failed: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache"""
        try:
            await asyncio.to_thread(self.redis_client.delete, f"{self.prefix}{key}")
        except Exception as e:
            print(f"[WARNING] Cache delete failed: {e}")
    
    async def health_check(self) -> bool:
        """Check if Redis is accessible"""
        try:
            await asyncio.to_thread(self.redis_client.ping)
            return True
        except Exception:
            return False
```

### 2. Circuit Breaker Pattern

```python
# app/core/circuit_breaker.py
import asyncio
from typing import Callable, Any
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for external API resilience"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60, name: str = "default"):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
        # Success count for half-open state
        self.success_count = 0
        self.required_successes = 3
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                print(f"[INFO] Circuit breaker {self.name} moving to HALF_OPEN state")
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        return datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout)
    
    async def _on_success(self):
        """Handle successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.required_successes:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                print(f"[INFO] Circuit breaker {self.name} reset to CLOSED state")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            print(f"[WARNING] Circuit breaker {self.name} opened due to {self.failure_count} failures")
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }
```

### 3. Rate Limiter and Cost Controller

```python
# app/core/rate_limiter.py
import redis
import time
from typing import Tuple
from datetime import datetime, timedelta

class RateLimiter:
    """Redis-based rate limiter with cost control"""
    
    def __init__(self, requests_per_minute: int = 100, requests_per_hour: int = 1000, 
                 cost_per_hour_limit: float = 50.0):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.cost_per_hour_limit = cost_per_hour_limit
        
        self.redis_client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True
        )
    
    async def check_limits(self, user_id: str) -> Tuple[bool, int]:
        """
        Check if user can make request within rate limits
        Returns: (can_proceed, wait_time_seconds)
        """
        
        current_time = time.time()
        minute_key = f"rate_limit:minute:{user_id}:{int(current_time // 60)}"
        hour_key = f"rate_limit:hour:{user_id}:{int(current_time // 3600)}"
        cost_key = f"cost_limit:hour:{user_id}:{int(current_time // 3600)}"
        
        try:
            # Check minute limit
            minute_count = await asyncio.to_thread(self.redis_client.get, minute_key)
            if minute_count and int(minute_count) >= self.requests_per_minute:
                return False, 60 - int(current_time % 60)
            
            # Check hour limit
            hour_count = await asyncio.to_thread(self.redis_client.get, hour_key)
            if hour_count and int(hour_count) >= self.requests_per_hour:
                return False, 3600 - int(current_time % 3600)
            
            # Check cost limit
            hour_cost = await asyncio.to_thread(self.redis_client.get, cost_key)
            if hour_cost and float(hour_cost) >= self.cost_per_hour_limit:
                return False, 3600 - int(current_time % 3600)
            
            return True, 0
            
        except Exception as e:
            print(f"[WARNING] Rate limit check failed: {e}")
            return True, 0  # Allow on error
    
    async def track_usage(self, user_id: str, estimated_cost: float = 0.0):
        """Track user's API usage and costs"""
        
        current_time = time.time()
        minute_key = f"rate_limit:minute:{user_id}:{int(current_time // 60)}"
        hour_key = f"rate_limit:hour:{user_id}:{int(current_time // 3600)}"
        cost_key = f"cost_limit:hour:{user_id}:{int(current_time // 3600)}"
        
        try:
            # Increment counters with expiration
            await asyncio.to_thread(self.redis_client.incr, minute_key)
            await asyncio.to_thread(self.redis_client.expire, minute_key, 60)
            
            await asyncio.to_thread(self.redis_client.incr, hour_key)
            await asyncio.to_thread(self.redis_client.expire, hour_key, 3600)
            
            # Track costs
            if estimated_cost > 0:
                await asyncio.to_thread(self.redis_client.incrbyfloat, cost_key, estimated_cost)
                await asyncio.to_thread(self.redis_client.expire, cost_key, 3600)
                
        except Exception as e:
            print(f"[WARNING] Usage tracking failed: {e}")
    
    async def get_usage_stats(self, user_id: str) -> dict:
        """Get current usage statistics for user"""
        
        current_time = time.time()
        minute_key = f"rate_limit:minute:{user_id}:{int(current_time // 60)}"
        hour_key = f"rate_limit:hour:{user_id}:{int(current_time // 3600)}"
        cost_key = f"cost_limit:hour:{user_id}:{int(current_time // 3600)}"
        
        try:
            minute_count = await asyncio.to_thread(self.redis_client.get, minute_key) or "0"
            hour_count = await asyncio.to_thread(self.redis_client.get, hour_key) or "0"
            hour_cost = await asyncio.to_thread(self.redis_client.get, cost_key) or "0.0"
            
            return {
                "requests_this_minute": int(minute_count),
                "requests_this_hour": int(hour_count),
                "cost_this_hour": float(hour_cost),
                "minute_limit": self.requests_per_minute,
                "hour_limit": self.requests_per_hour,
                "cost_limit": self.cost_per_hour_limit
            }
        except Exception as e:
            print(f"[WARNING] Getting usage stats failed: {e}")
            return {}
```

---

# 🏃‍♂️ Sprint 4: Advanced Video Workflows  
**Duration**: Week 7-8  
**Goal**: Granular video generation with optimized model selection  
**Deliverable**: Image-to-video, text-to-video, and premium video workflows

## Sprint 4 Scope
- ✅ Separate video workflows (IMAGE_TO_VIDEO, TEXT_TO_VIDEO, VIDEO_GENERATION)
- ✅ Model optimization for different video types
- ✅ Cost-effective video generation options
- ✅ Enhanced video workflow detection

## Configuration and Environment Setup (Sprint 4)

### 1. Environment Variables

```bash
# .env
OPENAI_API_KEY=your_openai_api_key_here
REPLICATE_API_TOKEN=your_replicate_token_here

# Redis Configuration (Required for production)
REDIS_URL=redis://localhost:6379
# For production with authentication:
# REDIS_URL=redis://username:password@redis-host:6379

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_REQUESTS_PER_HOUR=1000
COST_LIMIT_PER_HOUR=50.0

# Circuit Breaker Configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60

# Optional: Enable debug mode for detailed logging
AI_CLASSIFICATION_DEBUG=true

# Cache settings
INTENT_CACHE_TTL=3600

# Performance settings
MAX_CONCURRENT_CLASSIFICATIONS=10
CLASSIFICATION_TIMEOUT=30
```

### 2. Production Dependencies

```bash
# requirements.txt - Add these dependencies
redis>=4.5.0
redis[hiredis]>=4.5.0  # For better performance
```

### 3. Docker Compose for Development

```yaml
# docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN}
    volumes:
      - .:/app
    restart: unless-stopped

volumes:
  redis_data:
```

### 3. Optimized Database Schema

```sql
-- Optimized AI classification tracking with partitioning
CREATE TABLE IF NOT EXISTS intent_classification_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL, -- Using TEXT for flexibility
    prompt TEXT NOT NULL,
    classified_workflow VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    used_fallback BOOLEAN DEFAULT FALSE,
    cache_hit BOOLEAN DEFAULT FALSE,
    circuit_breaker_state VARCHAR(20),
    rate_limited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for better performance
CREATE TABLE intent_classification_logs_2024_01 PARTITION OF intent_classification_logs
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE intent_classification_logs_2024_02 PARTITION OF intent_classification_logs
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Add more partitions as needed...

-- Optimized indexes for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_intent_logs_user_time 
ON intent_classification_logs (user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_intent_logs_workflow_confidence 
ON intent_classification_logs (classified_workflow, confidence DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_intent_logs_performance 
ON intent_classification_logs (used_fallback, cache_hit, rate_limited);

-- Model selection tracking with cost analysis
CREATE TABLE IF NOT EXISTS model_selection_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    generation_id TEXT,
    workflow_type VARCHAR(50) NOT NULL,
    selected_model VARCHAR(100) NOT NULL,
    fallback_models TEXT[], -- Array of fallback models
    estimated_cost FLOAT,
    actual_cost FLOAT,
    estimated_time INTEGER, -- seconds
    actual_time INTEGER, -- seconds
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_logs_user_time 
ON model_selection_logs (user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_logs_workflow_success 
ON model_selection_logs (workflow_type, success);

-- Materialized view for real-time analytics
CREATE MATERIALIZED VIEW intent_analytics AS
SELECT 
    classified_workflow,
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as total_requests,
    AVG(confidence) as avg_confidence,
    AVG(processing_time_ms) as avg_processing_time,
    COUNT(*) FILTER (WHERE used_fallback) as fallback_count,
    COUNT(*) FILTER (WHERE cache_hit) as cache_hits,
    COUNT(*) FILTER (WHERE rate_limited) as rate_limited_count
FROM intent_classification_logs 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY classified_workflow, DATE_TRUNC('hour', created_at);

-- Create unique index for concurrent refresh
CREATE UNIQUE INDEX ON intent_analytics (classified_workflow, hour);

-- Cost tracking materialized view
CREATE MATERIALIZED VIEW cost_analytics AS
SELECT 
    user_id,
    DATE_TRUNC('day', created_at) as day,
    COUNT(*) as total_generations,
    SUM(actual_cost) as total_cost,
    AVG(actual_cost) as avg_cost_per_generation,
    COUNT(*) FILTER (WHERE success) as successful_generations
FROM model_selection_logs 
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY user_id, DATE_TRUNC('day', created_at);

CREATE UNIQUE INDEX ON cost_analytics (user_id, day);

-- Function to automatically refresh materialized views
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY intent_analytics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cost_analytics;
END;
$$ LANGUAGE plpgsql;

-- Schedule view refreshes every hour (requires pg_cron extension)
-- SELECT cron.schedule('refresh-analytics', '0 * * * *', 'SELECT refresh_analytics_views();');
```

---

# 🧪 Sprint Testing Strategies

## Sprint 1 Testing: Core AI Classification
**Test via existing frontend with comparison endpoint**

```bash
# Test AI vs existing classification
curl -X POST http://localhost:8000/api/v1/enhanced/compare \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "change my hair to blonde with bangs",
    "use_ai_classification": true
  }'
```

**Expected Deliverable**: Side-by-side comparison showing AI classification accuracy

## Sprint 2 Testing: Virtual Try-on & Model Selection
**Test new virtual try-on capabilities**

```bash
# Test virtual try-on workflow
curl -X POST http://localhost:8000/api/v1/enhanced/process \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "put @sarah in this red dress",
    "working_image_url": "https://example.com/person.jpg"
  }'
```

**Expected Deliverable**: Virtual try-on using `flux-kontext-apps/multi-image-kontext-max`

## Sprint 3 Testing: Production Infrastructure
**Test performance and reliability under load**

```bash
# Test rate limiting
for i in {1..50}; do
  curl -X POST http://localhost:8000/api/v1/enhanced/process \
    -H "Content-Type: application/json" \
    -d '{"prompt": "test prompt '${i}'"}' &
done

# Test cache performance
curl http://localhost:8000/api/v1/enhanced/metrics
```

**Expected Deliverable**: Production-ready performance with Redis caching

## Sprint 4 Testing: Video Workflows
**Test different video generation approaches**

```bash
# Test image-to-video
curl -X POST http://localhost:8000/api/v1/enhanced/process \
  -d '{"prompt": "animate this sunset", "working_image_url": "sunset.jpg"}'

# Test text-to-video (cost-effective)
curl -X POST http://localhost:8000/api/v1/enhanced/process \
  -d '{"prompt": "a cat playing in the garden"}'

# Test premium video with audio
curl -X POST http://localhost:8000/api/v1/enhanced/process \
  -d '{"prompt": "cinematic video of waves with ocean sounds"}'
```

**Expected Deliverable**: Optimized video workflows with appropriate model selection

## Sprint 5 Testing: Complete User Experience
**Test enhanced frontend and analytics**

- **Frontend Testing**: Enhanced UI components with AI insights
- **Analytics Testing**: Real-time metrics dashboard
- **A/B Testing**: Compare AI vs existing system performance
- **User Testing**: Complete workflow validation

**Expected Deliverable**: Production-ready system with comprehensive monitoring

## Testing Strategy (Detailed)

### 1. Unit Tests

```python
# tests/test_intent_classifier.py
import pytest
from app.services.intent_classifier import IntentClassifier
from app.models.workflows import WorkflowType

@pytest.fixture
def intent_classifier():
    return IntentClassifier()

class TestIntentClassifier:
    
    @pytest.mark.asyncio
    async def test_hair_styling_classification(self, intent_classifier):
        """Test hair styling intent detection"""
        prompts = [
            "change my hair to blonde",
            "give me curtain bangs",
            "make my hair curly"
        ]
        
        for prompt in prompts:
            result = await intent_classifier.classify_intent(prompt)
            assert result.workflow_type == WorkflowType.HAIR_STYLING
            assert result.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_video_generation_classification(self, intent_classifier):
        """Test video generation intent detection"""
        prompts = [
            "create a video of waves crashing",
            "animate this image",
            "make a movie of a sunset"
        ]
        
        for prompt in prompts:
            result = await intent_classifier.classify_intent(prompt)
            assert result.workflow_type == WorkflowType.VIDEO_GENERATION
    
    @pytest.mark.asyncio
    async def test_fallback_classification(self, intent_classifier):
        """Test fallback classification when AI fails"""
        # Mock AI failure
        intent_classifier.client = None
        
        result = await intent_classifier.classify_intent("change my hair color")
        assert result.workflow_type == WorkflowType.HAIR_STYLING
        assert result.confidence == 0.6  # Fallback confidence
        assert "Fallback" in result.reasoning

    def test_cache_functionality(self, intent_classifier):
        """Test cache hit/miss behavior"""
        # First call should miss cache
        cache_key = intent_classifier._generate_cache_key("test prompt", None)
        assert intent_classifier.cache.get(cache_key) is None
        
        # After classification, should be cached
        # (This would need async testing in real implementation)
```

### 2. Integration Tests

```python
# tests/test_enhanced_workflow.py
import pytest
from app.services.enhanced_workflow_service import EnhancedWorkflowService

@pytest.fixture
def workflow_service():
    return EnhancedWorkflowService()

class TestEnhancedWorkflow:
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing(self, workflow_service):
        """Test complete workflow processing"""
        result = await workflow_service.process_request(
            prompt="change my hair to blonde with bangs",
            user_id="test-user-id"
        )
        
        assert result["success"] is True
        assert result["workflow_type"] == "hair_styling"
        assert "change-haircut" in result["model_selection"]["model_id"]
        assert result["intent_confidence"] > 0.5
    
    @pytest.mark.asyncio
    async def test_fallback_behavior(self, workflow_service):
        """Test graceful fallback when services fail"""
        # This would test with mocked failures
        pass
```

## Deployment Checklist

### 1. Pre-deployment Steps

- [ ] **Environment Variables**: Set all required API keys and configuration
- [ ] **Database Migrations**: Run any new table creation scripts
- [ ] **Model Verification**: Test that all referenced Replicate models are accessible
- [ ] **Cache Setup**: Configure Redis or in-memory cache based on environment
- [ ] **Monitoring**: Set up logging and metrics collection

### 2. Deployment Process

```bash
# 1. Update backend dependencies
pip install openai>=1.0.0 asyncio

# 2. Run database migrations
python -m alembic upgrade head

# 3. Update frontend dependencies
npm install

# 4. Build frontend
npm run build

# 5. Deploy with feature flag
export AI_CLASSIFICATION_ENABLED=true
export AI_CLASSIFICATION_ROLLOUT_PERCENTAGE=10  # Start with 10% of users

# 6. Deploy backend
docker build -t picarcade-enhanced .
docker push your-registry/picarcade-enhanced
kubectl apply -f deployment.yaml

# 7. Deploy frontend
npm run deploy
```

### 3. Post-deployment Monitoring

```python
# app/core/monitoring.py
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

class AIClassificationMonitor:
    """Monitor AI classification performance and issues"""
    
    def __init__(self):
        self.logger = logging.getLogger("ai_classification")
        self.metrics = {
            "total_requests": 0,
            "successful_classifications": 0,
            "fallback_used": 0,
            "errors": 0,
            "avg_processing_time": 0
        }
    
    def log_classification(
        self, 
        prompt: str, 
        result: Dict[str, Any], 
        processing_time: float,
        used_fallback: bool = False
    ):
        """Log classification for monitoring"""
        
        self.metrics["total_requests"] += 1
        
        if result.get("success"):
            self.metrics["successful_classifications"] += 1
        else:
            self.metrics["errors"] += 1
        
        if used_fallback:
            self.metrics["fallback_used"] += 1
        
        # Update average processing time
        current_avg = self.metrics["avg_processing_time"]
        total_requests = self.metrics["total_requests"]
        self.metrics["avg_processing_time"] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )
        
        # Log for external monitoring tools
        self.logger.info(
            "AI Classification",
            extra={
                "prompt_length": len(prompt),
                "workflow_type": result.get("workflow_type"),
                "confidence": result.get("intent_confidence"),
                "processing_time": processing_time,
                "used_fallback": used_fallback,
                "model_selected": result.get("model_selection", {}).get("model_id")
            }
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health metrics"""
        
        success_rate = (
            self.metrics["successful_classifications"] / 
            max(self.metrics["total_requests"], 1)
        )
        
        fallback_rate = (
            self.metrics["fallback_used"] / 
            max(self.metrics["total_requests"], 1)
        )
        
        return {
            "status": "healthy" if success_rate > 0.95 else "degraded",
            "success_rate": success_rate,
            "fallback_rate": fallback_rate,
            "avg_processing_time": self.metrics["avg_processing_time"],
            "total_requests": self.metrics["total_requests"]
        }
```

## Rollout Strategy

### 1. Phased Rollout Plan

**Week 1: Internal Testing**
- Deploy to staging environment
- Test with internal team
- Validate all model integrations
- Check performance metrics

**Week 2: Limited Beta (10% of users)**
- Enable for 10% of users via feature flag
- Monitor error rates and performance
- Collect user feedback
- Compare AI vs existing system results

**Week 3: Expanded Beta (50% of users)**
- Increase rollout to 50% if metrics are good
- Monitor cost impact
- Optimize based on usage patterns
- Address any issues found

**Week 4: Full Rollout (100% of users)**
- Enable for all users
- Keep existing system as fallback
- Monitor long-term performance
- Plan Phase 2 features

### 2. Feature Flags Configuration

```python
# app/core/feature_flags.py
import os
import random

class FeatureFlags:
    """Manage feature flag rollouts"""
    
    @staticmethod
    def is_ai_classification_enabled(user_id: str) -> bool:
        """Check if AI classification is enabled for user"""
        
        # Check environment override
        if os.getenv("AI_CLASSIFICATION_ENABLED") == "false":
            return False
        
        # Check rollout percentage
        rollout_percentage = int(os.getenv("AI_CLASSIFICATION_ROLLOUT_PERCENTAGE", "100"))
        
        # Use user ID hash for consistent experience
        user_hash = hash(user_id) % 100
        return user_hash < rollout_percentage
```

## Success Metrics

### 1. Technical Metrics
- **Classification Accuracy**: >95% based on user feedback
- **Processing Time**: <2 seconds average
- **Cache Hit Rate**: >70%
- **Fallback Rate**: <5%
- **Error Rate**: <1%

### 2. Business Metrics
- **User Satisfaction**: Survey rating >4.5/5
- **Cost Per Generation**: Not to exceed current costs by >20%
- **Model Selection Accuracy**: Reduced regenerations by >15%
- **Feature Adoption**: >80% of users use AI classification

### 3. Monitoring Dashboard

```python
# Create monitoring endpoint
@router.get("/health")
async def get_system_health():
    """System health check for monitoring"""
    
    monitor = AIClassificationMonitor()
    health_status = monitor.get_health_status()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "ai_classification": health_status,
        "model_availability": await check_model_availability(),
        "cache_status": get_cache_status(),
        "overall_status": "healthy" if health_status["status"] == "healthy" else "degraded"
    }
```

---

# 📊 Sprint Summary & Deliverables

## Sprint 1 (Week 1-2): Core AI Classification
✅ **Testable via existing frontend**
- Basic AI intent classifier vs existing system comparison
- Simple model selection
- Immediate value: Better workflow detection accuracy

## Sprint 2 (Week 3-4): Virtual Try-on & Enhanced Models  
✅ **New virtual try-on capabilities**
- `flux-kontext-apps/multi-image-kontext-max` integration
- Web search for celebrity/event styling
- Immediate value: Advanced virtual try-on features

## Sprint 3 (Week 5-6): Production Infrastructure
✅ **Production-ready reliability**
- Redis distributed caching
- Rate limiting and cost controls
- Circuit breaker for API reliability
- Immediate value: Performance and cost optimization

## Sprint 4 (Week 7-8): Advanced Video Workflows
✅ **Granular video generation**
- Image-to-video animation
- Cost-effective text-to-video
- Premium video with audio
- Immediate value: Optimized video model selection

## Sprint 5 (Week 9-10): Complete User Experience
✅ **Enhanced frontend and analytics**
- AI classification insights in UI
- Performance monitoring dashboard
- A/B testing framework
- Immediate value: Complete production system

## Key Benefits Per Sprint

| Sprint | User-Facing Benefit | Business Value | Technical Achievement |
|--------|-------------------|----------------|---------------------|
| **1** | More accurate workflow detection | Better user experience | AI classification foundation |
| **2** | Advanced virtual try-on | New monetizable features | Enhanced model integrations |
| **3** | Faster, more reliable system | Reduced costs, better performance | Production infrastructure |
| **4** | Optimized video generation | Cost-effective video options | Granular workflow control |
| **5** | Polished user experience | Data-driven improvements | Complete monitoring system |

This sprint-based approach ensures each phase delivers immediate, testable value while building toward a comprehensive AI-powered intent classification system that maintains compatibility with your existing frontend infrastructure.