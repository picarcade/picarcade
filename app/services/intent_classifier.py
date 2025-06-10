"""
DEPRECATED: IntentClassifier has been replaced by SimplifiedFlowService

This file remains for backward compatibility but is no longer used in production.
The new simplified flow service provides:
- Better CSV-based decision making
- Integrated Sprint 3 infrastructure (Redis cache, circuit breaker, rate limiting)
- More reliable prompt enhancement
- Simplified architecture

Use app.services.simplified_flow_service.SimplifiedFlowService instead.
"""

import asyncio
import json
import re
import random
import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
import replicate
from app.models.workflows import WorkflowType, IntentClassification
import os

# Sprint 3: Import infrastructure components
from app.core.cache import get_cache, cache_result
from app.core.circuit_breaker import get_circuit_breaker, CircuitConfig, CircuitBreakerOpenError
from app.core.rate_limiter import check_all_rate_limits, RateLimitError
from app.core.database import get_database

logger = logging.getLogger(__name__)

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
    """Sprint 3: Production-ready AI-powered intent classification with infrastructure"""
    
    def __init__(self):
        # Using Claude 3.5 Haiku via Replicate
        self.model = "anthropic/claude-3.5-haiku"
        
        # Sprint 3: Initialize infrastructure components
        self.cache = None  # Will be initialized async
        self.circuit_breaker = None  # Will be initialized async
        self.database = None  # Will be initialized async
        
        # Configuration from environment
        self.cache_ttl = int(os.getenv("INTENT_CACHE_TTL", "3600"))  # 1 hour
        self.max_concurrent = int(os.getenv("MAX_CONCURRENT_CLASSIFICATIONS", "10"))
        self.classification_timeout = int(os.getenv("CLASSIFICATION_TIMEOUT", "30"))
        
        # Sprint 2: Enhanced fallback patterns with better virtual try-on detection
        self.fallback_patterns = {
            WorkflowType.VIDEO_GENERATION: ["video with audio", "video with sound", "music video", "cinematic", "soundtrack"],
            WorkflowType.IMAGE_TO_VIDEO: ["animate", "animate this", "bring to life", "make this move", "motion", "movement"],
            WorkflowType.TEXT_TO_VIDEO: ["video", "movie", "clip", "scene", "footage", "film"],
            WorkflowType.HAIR_STYLING: ["hair", "haircut", "hairstyle", "blonde", "brunette", "bangs", "curly", "straight", "highlights"],
            WorkflowType.REFERENCE_STYLING: [
                # Celebrity styling
                "taylor swift", "celebrity", "like", "style of", "inspired by",
                # Event styling  
                "grammy", "met gala", "oscar", "red carpet", "cannes", "fashion week", "coachella",
                # Virtual try-on patterns
                "put @", "try on", "wear this", "outfit", "dress up", "dress like", "style like",
                "put me in", "put them in", "wearing", "dressed as", "outfit change",
                # Fashion terms
                "fashion", "designer", "runway", "haute couture", "vintage fashion"
            ],
            WorkflowType.IMAGE_EDITING: ["edit", "change", "modify", "adjust", "add", "remove", "make it", "turn it", "convert it", "transform it"],
            WorkflowType.IMAGE_ENHANCEMENT: ["enhance", "improve", "upscale", "sharpen"],
            WorkflowType.STYLE_TRANSFER: ["style", "artistic", "painting", "sketch", "cartoon", "renaissance", "filters"]
        }
        
        # Initialize async (called once)
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure all async components are initialized"""
        if not self._initialized:
            try:
                # Initialize distributed cache
                self.cache = await get_cache()
                
                # Initialize circuit breaker for Replicate API
                circuit_config = CircuitConfig(
                    failure_threshold=int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")),
                    timeout_seconds=int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60")),
                    success_threshold=3
                )
                self.circuit_breaker = get_circuit_breaker("replicate_claude", circuit_config)
                
                # Initialize database for analytics
                self.database = await get_database()
                
                self._initialized = True
                logger.info("IntentClassifier Sprint 3 infrastructure initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize IntentClassifier infrastructure: {e}")
                # Continue with degraded functionality
                self._initialized = False
    
    def _check_replicate_token(self):
        """Check if Replicate token is available"""
        token = os.getenv("REPLICATE_API_TOKEN")
        if not token:
            raise Exception("Replicate API token not found in environment variables")
        return token
    
    async def classify_intent(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> IntentClassification:
        """
        Sprint 3: Production classification with rate limiting, caching, and circuit breaker
        """
        start_time = time.time()
        await self._ensure_initialized()
        
        # Default user_id if not provided
        user_id = user_id or "anonymous"
        
        # Estimate cost for rate limiting (approximate)
        estimated_cost = 0.01  # Small cost for Claude 3.5 Haiku
        
        try:
            # Sprint 3: Check rate limits before processing
            allowed, rate_limit_info = await check_all_rate_limits(
                user_id=user_id,
                api_name="replicate",
                estimated_cost=estimated_cost
            )
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                await self._log_classification(
                    user_id=user_id,
                    prompt=prompt,
                    classified_workflow=WorkflowType.IMAGE_GENERATION.value,
                    confidence=0.3,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    used_fallback=True,
                    cache_hit=False,
                    circuit_breaker_state="closed",
                    rate_limited=True
                )
                
                # Return fallback result with rate limit info
                result = self._fallback_classify(prompt, context, reason="rate_limited")
                result.reasoning += f" (Rate limited: {rate_limit_info['user']['requests']['remaining']} requests remaining)"
                return result
            
            # Generate cache key
            cache_key = self._generate_cache_key(prompt, context, user_id)
            
            # Sprint 3: Check distributed cache
            cached_result = None
            cache_hit = False
            if self.cache:
                try:
                    cached_data = await self.cache.get(cache_key)
                    if cached_data:
                        cached_result = IntentClassification(**cached_data)
                        cache_hit = True
                        logger.info(f"Cache hit for user {user_id}")
                except Exception as e:
                    logger.warning(f"Cache get failed: {e}")
            
            if cached_result:
                # Log cache hit
                await self._log_classification(
                    user_id=user_id,
                    prompt=prompt,
                    classified_workflow=cached_result.workflow_type.value,
                    confidence=cached_result.confidence,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    used_fallback=False,
                    cache_hit=True,
                    circuit_breaker_state=self.circuit_breaker.state.value if self.circuit_breaker else "unknown"
                )
                return cached_result
            
            # Try AI classification with circuit breaker protection
            circuit_breaker_state = "unknown"
            used_fallback = False
            
            try:
                if self.circuit_breaker:
                    circuit_breaker_state = self.circuit_breaker.state.value
                    result = await self.circuit_breaker.call(self._ai_classify, prompt, context)
                else:
                    result = await self._ai_classify(prompt, context)
                
                # Cache successful result
                if self.cache:
                    try:
                        await self.cache.set(cache_key, result.dict(), ttl=self.cache_ttl)
                    except Exception as e:
                        logger.warning(f"Cache set failed: {e}")
                
            except (CircuitBreakerOpenError, Exception) as e:
                logger.warning(f"AI classification failed for user {user_id}: {e}")
                circuit_breaker_state = self.circuit_breaker.state.value if self.circuit_breaker else "unknown"
                used_fallback = True
                result = self._fallback_classify(prompt, context, reason=str(e))
            
            # Log classification
            await self._log_classification(
                user_id=user_id,
                prompt=prompt,
                classified_workflow=result.workflow_type.value,
                confidence=result.confidence,
                processing_time_ms=int((time.time() - start_time) * 1000),
                used_fallback=used_fallback,
                cache_hit=cache_hit,
                circuit_breaker_state=circuit_breaker_state,
                rate_limited=False
            )
            
            return result
            
        except RateLimitError as e:
            logger.error(f"Rate limit error for user {user_id}: {e}")
            # Return fallback with rate limit message
            result = self._fallback_classify(prompt, context, reason="rate_limited")
            result.reasoning += " (Rate limit exceeded)"
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in classification for user {user_id}: {e}")
            
            # Log the failure
            await self._log_classification(
                user_id=user_id,
                prompt=prompt,
                classified_workflow=WorkflowType.IMAGE_GENERATION.value,
                confidence=0.3,
                processing_time_ms=int((time.time() - start_time) * 1000),
                used_fallback=True,
                cache_hit=False,
                circuit_breaker_state="error",
                rate_limited=False
            )
            
            # Return safe fallback
            return self._fallback_classify(prompt, context, reason=f"error: {str(e)}")
    
    @retry_with_exponential_backoff(max_retries=2, base_delay=0.5)
    async def _ai_classify(self, prompt: str, context: Optional[Dict[str, Any]]) -> IntentClassification:
        """AI-powered classification using Claude 3.5 Haiku via Replicate"""
        
        # Check Replicate token
        self._check_replicate_token()
        
        classification_prompt = f"""You are an expert at classifying user intents for creative AI workflows.

Available workflow types:
- image_generation: Create new images from text
- video_generation: Create videos with audio support (premium, uses Veo 3)
- image_to_video: Animate existing images into video (most efficient for image animation)
- text_to_video: Create videos from text without audio (cost-effective option)
- image_editing: Modify existing images (INCLUDES adding clothing, changing pose, background changes, object additions/removals)
- image_enhancement: Improve image quality (upscale, sharpen, etc.)
- reference_styling: ONLY for virtual try-on WITH REFERENCE IMAGES (requires @references or uploaded style images), celebrity styling, event fashion
- hair_styling: Change hair color, cut, or style
- style_transfer: Apply artistic styles to images

CRITICAL DISTINCTIONS:
- Basic clothing changes ("put a tshirt on", "add a hat") = image_editing (NOT reference_styling)
- Pose changes ("face the camera", "turn around") = image_editing (NOT reference_styling)
- Background changes ("change background to beach") = image_editing (NOT reference_styling)
- Reference styling ONLY when: @references mentioned OR specific celebrity/event styling OR uploaded reference images for virtual try-on

Context clues:
- If user has uploaded/working images and wants video → image_to_video
- Audio/music video requests → video_generation
- Basic video requests without audio → text_to_video
- Celebrity names + events → reference_styling (requires_web_search=true)
- Virtual try-on WITH @references or uploaded images → reference_styling
- Face swap phrases like "replace face", "swap face", "change face", "update face with", "put this face on" → reference_styling
- Hair-related terms → hair_styling
- Art/style terms → style_transfer

Web search criteria (set requires_web_search=true and provide web_search_query):
- Celebrity styling: "taylor swift grammy outfit" → search "taylor swift grammy fashion style"
- Event fashion: "met gala dress" → search "met gala fashion trends"
- Fashion inspiration: "coachella style" → search "coachella fashion outfit inspiration"

Classify this user request:
"{prompt}"

Context: {self._build_context_string(context)}

Respond in JSON format only:
{{
    "workflow_type": "workflow_name",
    "confidence": 0.95,
    "reasoning": "brief explanation",
    "requires_web_search": false,
    "web_search_query": null,
    "enhancement_needed": false
}}"""
        
        # Run the classification in a thread since replicate is synchronous
        def _run_replicate():
            result_text = ""
            for event in replicate.stream(
                self.model,
                input={"prompt": classification_prompt}
            ):
                result_text += str(event)
            return result_text
        
        # Run in thread pool to not block async event loop
        loop = asyncio.get_event_loop()
        result_text = await loop.run_in_executor(None, _run_replicate)
        
        # Clean up the response
        result_text = result_text.strip()
        
        # Handle potential markdown formatting
        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
        elif result_text.startswith("```"):
            # Find the JSON part
            lines = result_text.split('\n')
            json_start = -1
            json_end = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    json_start = i
                if line.strip().endswith('}') and json_start != -1:
                    json_end = i + 1
                    break
            if json_start != -1 and json_end != -1:
                result_text = '\n'.join(lines[json_start:json_end])
        
        # Extract JSON if there's additional text
        if not result_text.strip().startswith('{'):
            # Try to find JSON in the response
            json_match = re.search(r'\{[^}]*"workflow_type"[^}]*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
            else:
                raise Exception(f"Could not find valid JSON in Claude response: {result_text}")
        
        # Remove any text after the JSON closing brace
        if result_text.strip().startswith('{'):
            brace_count = 0
            json_end_pos = -1
            for i, char in enumerate(result_text):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end_pos = i + 1
                        break
            
            if json_end_pos > 0:
                result_text = result_text[:json_end_pos]
        
        try:
            result_data = json.loads(result_text)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Claude JSON response: {result_text}. Error: {e}")
        
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
        
        # Check context first - fix the key name!
        if context and (context.get("working_images") or context.get("has_working_image")):
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
        
        # Sprint 2: Enhanced web search detection
        requires_search = any(indicator in prompt_lower for indicator in [
            "taylor swift", "celebrity", "grammy", "met gala", "oscar", "red carpet",
            "cannes", "fashion week", "coachella", "like", "style of", "inspired by",
            "designer", "runway", "haute couture", "vintage fashion"
        ])
        
        # Generate web search query if needed
        web_search_query = None
        if requires_search:
            web_search_query = self._generate_fallback_search_query(prompt_lower)
        
        return IntentClassification(
            workflow_type=workflow,
            confidence=0.6,  # Lower confidence for fallback
            reasoning=f"Fallback classification ({reason}) based on keyword patterns",
            requires_web_search=requires_search,
            web_search_query=web_search_query,
            enhancement_needed=len(prompt.split()) < 5
        )
    
    async def _log_classification(
        self,
        user_id: str,
        prompt: str,
        classified_workflow: str,
        confidence: float,
        processing_time_ms: int,
        used_fallback: bool = False,
        cache_hit: bool = False,
        circuit_breaker_state: str = "closed",
        rate_limited: bool = False
    ):
        """Sprint 3: Log classification metrics to Supabase"""
        if not self.database:
            return
        
        try:
            await self.database.execute(
                """
                INSERT INTO intent_classification_logs 
                (user_id, prompt, classified_workflow, confidence, processing_time_ms, 
                 used_fallback, cache_hit, circuit_breaker_state, rate_limited)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                user_id, prompt, classified_workflow, confidence, processing_time_ms,
                used_fallback, cache_hit, circuit_breaker_state, rate_limited
            )
        except Exception as e:
            logger.error(f"Failed to log classification metrics: {e}")
    
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
    
    def _generate_cache_key(self, prompt: str, context: Optional[Dict[str, Any]], user_id: str) -> str:
        """Generate cache key for classification"""
        context_str = ""
        if context:
            has_images = bool(context.get("working_images") or context.get("uploaded_images"))
            context_str = f"_images:{has_images}"
        
        # Include user_id in cache key for user-specific caching
        return f"intent_v3_{hash(prompt.lower())}_{hash(user_id)}{context_str}"
    
    def _generate_fallback_search_query(self, prompt_lower: str) -> str:
        """Sprint 2: Generate web search query for fallback classification"""
        
        # Extract key terms for search
        search_terms = []
        
        # Celebrity names
        celebrities = ["taylor swift", "beyonce", "rihanna", "jennifer lawrence", "emma stone"]
        for celebrity in celebrities:
            if celebrity in prompt_lower:
                search_terms.append(celebrity)
        
        # Events
        events = ["met gala", "grammy", "oscar", "red carpet", "cannes", "fashion week", "coachella"]
        for event in events:
            if event in prompt_lower:
                search_terms.append(event)
        
        # Fashion terms
        if any(term in prompt_lower for term in ["outfit", "dress", "fashion", "style"]):
            search_terms.append("fashion style")
        
        # Build search query
        if search_terms:
            return " ".join(search_terms) + " outfit inspiration"
        else:
            return "fashion style inspiration"
    
    def _build_context_string(self, context: Optional[Dict[str, Any]]) -> str:
        """Build context string for AI"""
        if not context:
            return "No additional context"
        
        parts = []
        if context.get("working_images"):
            parts.append(f"User has {len(context['working_images'])} working images")
        if context.get("has_working_image"):
            parts.append("User has a working image")
        if context.get("uploaded_images"):
            parts.append(f"User uploaded {len(context['uploaded_images'])} new images")
        
        return "; ".join(parts) if parts else "No additional context"
    
    # Sprint 3: Health and monitoring methods
    async def get_health(self) -> Dict[str, Any]:
        """Get classifier health status"""
        await self._ensure_initialized()
        
        health = {
            "classifier": "healthy",
            "initialized": self._initialized,
            "model": self.model
        }
        
        # Check cache health
        if self.cache:
            try:
                cache_health = await self.cache.get_health()
                health["cache"] = cache_health
            except Exception as e:
                health["cache"] = {"status": "error", "error": str(e)}
        else:
            health["cache"] = {"status": "not_initialized"}
        
        # Check circuit breaker health
        if self.circuit_breaker:
            health["circuit_breaker"] = self.circuit_breaker.get_stats()
        else:
            health["circuit_breaker"] = {"status": "not_initialized"}
        
        return health
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get classification statistics"""
        if not self.database:
            return {"error": "Database not available"}
        
        try:
            # Get classification stats from last 24 hours
            stats = await self.database.fetch_one(
                """
                SELECT 
                    COUNT(*) as total_classifications,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time_ms) as avg_processing_time,
                    SUM(CASE WHEN used_fallback THEN 1 ELSE 0 END) as fallback_count,
                    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
                    SUM(CASE WHEN rate_limited THEN 1 ELSE 0 END) as rate_limited_count
                FROM intent_classification_logs 
                WHERE created_at > NOW() - INTERVAL '24 hours'
                """
            )
            
            if stats:
                return {
                    "total_classifications": stats["total_classifications"],
                    "avg_confidence": round(float(stats["avg_confidence"] or 0), 2),
                    "avg_processing_time_ms": round(float(stats["avg_processing_time"] or 0), 2),
                    "fallback_rate": round((stats["fallback_count"] / max(stats["total_classifications"], 1)) * 100, 2),
                    "cache_hit_rate": round((stats["cache_hits"] / max(stats["total_classifications"], 1)) * 100, 2),
                    "rate_limited_rate": round((stats["rate_limited_count"] / max(stats["total_classifications"], 1)) * 100, 2),
                    "period": "24 hours"
                }
            else:
                return {"message": "No classification data available"}
                
        except Exception as e:
            logger.error(f"Failed to get classification stats: {e}")
            return {"error": str(e)} 