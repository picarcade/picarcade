"""
Simplified Product Flow Service - Sprint 3 Enhanced

Based on CSV rules with Sprint 3 infrastructure:
1. User Prompts
2. App determines Active Image, Uploaded Image, Referenced Image boolean values 
3. LLM classifies intent and enhances prompt based on CSV rules (with caching & circuit breaker)
4. Routes to appropriate model per CSV

Sprint 3 Infrastructure Integration:
- Distributed Redis Cache
- Circuit Breaker Protection  
- Rate Limiting & Cost Control
- Analytics & Performance Monitoring
"""

import asyncio
import json
import logging
import time
import os
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
import replicate

# Sprint 3: Import infrastructure components
from app.core.cache import get_cache, cache_result
from app.core.circuit_breaker import get_circuit_breaker, CircuitConfig, CircuitBreakerOpenError
from app.core.rate_limiter import check_all_rate_limits, RateLimitError
from app.core.database import get_database
from app.core.model_config import model_config

logger = logging.getLogger(__name__)


class PromptType(Enum):
    CREATE_NEW_IMAGE = "NEW_IMAGE"
    NEW_IMAGE_REF = "NEW_IMAGE_REF"
    EDIT_IMAGE = "EDIT_IMAGE" 
    EDIT_IMAGE_REF = "EDIT_IMAGE_REF"
    EDIT_IMAGE_ADD_NEW = "EDIT_IMAGE_ADD_NEW"  # New: Adding elements to scenes (Replicate)
    # New video generation flows from CSV
    NEW_VIDEO = "NEW_VIDEO"
    NEW_VIDEO_WITH_AUDIO = "NEW_VIDEO_WITH_AUDIO"  # New: Text-to-video with audio (Veo 3) - no working image
    IMAGE_TO_VIDEO = "IMAGE_TO_VIDEO"
    IMAGE_TO_VIDEO_WITH_AUDIO = "IMAGE_TO_VIDEO_WITH_AUDIO"  # Image-to-video with audio using Veo 3 Fast
    EDIT_IMAGE_REF_TO_VIDEO = "EDIT_IMAGE_REF_TO_VIDEO"
    # New video editing flows for gen4_aleph
    VIDEO_EDIT = "VIDEO_EDIT"  # Edit working video with prompt
    VIDEO_EDIT_REF = "VIDEO_EDIT_REF"  # Edit working video with reference images/videos


class SimplifiedFlowResult:
    """Result from the simplified flow containing all necessary routing information"""
    
    def __init__(
        self,
        prompt_type: PromptType,
        enhanced_prompt: str,
        model_to_use: str,
        original_prompt: str,
        reasoning: str,
        active_image: bool,
        uploaded_image: bool,
        referenced_image: bool,
        cache_hit: bool = False,
        processing_time_ms: int = 0,
        witty_messages: Optional[List[str]] = None
    ):
        self.prompt_type = prompt_type
        self.enhanced_prompt = enhanced_prompt
        self.model_to_use = model_to_use
        self.original_prompt = original_prompt
        self.reasoning = reasoning
        self.active_image = active_image
        self.uploaded_image = uploaded_image
        self.referenced_image = referenced_image
        self.cache_hit = cache_hit
        self.processing_time_ms = processing_time_ms
        self.witty_messages = witty_messages or []


class SimplifiedFlowService:
    """
    Sprint 3: Simplified flow service with production infrastructure
    """
    
    def __init__(self):
        # Use Anthropic Claude 4 Sonnet via Replicate for prompt processing
        self.model = "anthropic/claude-4-sonnet"
        
        # Sprint 3: Infrastructure components (initialized async)
        self.cache = None
        self.circuit_breaker = None
        self.database = None
        self._initialized = False
        
        # Configuration from environment
        self.cache_ttl = int(os.getenv("INTENT_CACHE_TTL", "3600"))  # 1 hour
        self.max_concurrent = int(os.getenv("MAX_CONCURRENT_CLASSIFICATIONS", "10"))
        self.classification_timeout = int(os.getenv("CLASSIFICATION_TIMEOUT", "30"))
        
        # CSV-based decision matrix (updated with new scenarios)
        self.decision_matrix = {
            # (active_image, uploaded_image, referenced_image) -> (type, model)
            (False, False, False): ("NEW_IMAGE", "Flux 1.1 Pro"),
            (True, False, False): ("NEW_IMAGE", "Flux 1.1 Pro"), 
            (False, False, True): ("NEW_IMAGE_REF", "Kontext"),  # New: Create new image with references
            (False, True, False): ("NEW_IMAGE_REF", "Kontext"),  # New: Create new image with uploads
            (True, False, False): ("EDIT_IMAGE", "Kontext"),  # Edit case
            (True, True, False): ("EDIT_IMAGE_REF", "Runway"),
            (True, False, True): ("EDIT_IMAGE_REF", "Runway"),
            (True, True, True): ("EDIT_IMAGE_REF", "Runway"),
        }
    
    async def _ensure_initialized(self):
        """Sprint 3: Ensure all async infrastructure components are initialized"""
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
                logger.info("SimplifiedFlowService Sprint 3 infrastructure initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize SimplifiedFlowService infrastructure: {e}")
                # Continue with degraded functionality
                self._initialized = False
    
    async def process_user_request(
        self, 
        user_prompt: str,
        active_image: bool = False,
        active_video: bool = False,
        uploaded_image: bool = False, 
        referenced_image: bool = False,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> SimplifiedFlowResult:
        """
        Sprint 3: Process user request through simplified flow with infrastructure:
        1. Rate limiting check
        2. Cache lookup
        3. LLM classification with circuit breaker
        4. Analytics logging
        5. Cache storage
        """
        
        start_time = time.time()
        await self._ensure_initialized()
        
        # Default user_id if not provided
        user_id = user_id or "anonymous"
        
        try:
            # Sprint 3: Check rate limits before processing
            estimated_cost = 0.03  # Claude 4 Sonnet cost estimate (slightly higher than 3.7)
            
            try:
                allowed, rate_limit_info = await check_all_rate_limits(
                    user_id=user_id,
                    api_name="replicate",
                    estimated_cost=estimated_cost
                )
                
                if not allowed:
                    logger.warning(f"Rate limit exceeded for user {user_id}")
                    # Return fallback result
                    result = self._create_fallback_result(
                        user_prompt, active_image, uploaded_image, referenced_image,
                        reason="rate_limited"
                    )
                    
                    await self._log_classification(
                        user_id=user_id,
                        prompt=user_prompt,
                        result=result,
                        used_fallback=True,
                        rate_limited=True,
                        circuit_breaker_state="closed"
                    )
                    
                    return result
                    
            except RateLimitError as e:
                logger.error(f"Rate limit error for user {user_id}: {e}")
                result = self._create_fallback_result(
                    user_prompt, active_image, uploaded_image, referenced_image,
                    reason="rate_limited"
                )
                result.reasoning += " (Rate limit exceeded)"
                return result
            
            # Generate cache key
            cache_key = self._generate_cache_key(user_prompt, active_image, active_video, uploaded_image, referenced_image, user_id)
            
            # Sprint 3: Check distributed cache
            cached_result = None
            cache_hit = False
            if self.cache:
                try:
                    cached_data = await self.cache.get(cache_key)
                    if cached_data:
                        cached_result = self._result_from_cache_data(cached_data)
                        cache_hit = True
                        logger.info(f"Cache hit for user {user_id}")
                except Exception as e:
                    logger.warning(f"Cache get failed: {e}")
            
            if cached_result:
                # Update processing time for cache hit
                cached_result.cache_hit = True
                cached_result.processing_time_ms = int((time.time() - start_time) * 1000)
                
                # Log cache hit
                await self._log_classification(
                    user_id=user_id,
                    prompt=user_prompt,
                    result=cached_result,
                    used_fallback=False,
                    rate_limited=False,
                    circuit_breaker_state=self.circuit_breaker.state.value if self.circuit_breaker else "unknown"
                )
                
                return cached_result
            
            # Count total reference images from context
            total_references = 0
            if context:
                # Count uploaded images
                uploaded_images = context.get("uploaded_images", [])
                total_references += len(uploaded_images) if uploaded_images else 0
                
                # Count @references in prompt
                import re
                prompt_references = re.findall(r'@\w+', user_prompt)
                total_references += len(prompt_references)
                
                print(f"[DEBUG] SIMPLIFIED: Reference count - uploaded: {len(uploaded_images) if uploaded_images else 0}, prompt refs: {len(prompt_references)}, total: {total_references}")
            
            # Try AI classification with circuit breaker protection
            circuit_breaker_state = "unknown"
            used_fallback = False
            
            try:
                if self.circuit_breaker:
                    circuit_breaker_state = self.circuit_breaker.state.value
                    prompt_type, enhanced_prompt, reasoning = await self.circuit_breaker.call(
                        self._classify_and_enhance,
                        user_prompt, active_image, active_video, uploaded_image, referenced_image, context
                    )
                else:
                    prompt_type, enhanced_prompt, reasoning = await self._classify_and_enhance(
                        user_prompt, active_image, active_video, uploaded_image, referenced_image, context
                    )
                
                # Map to model based on CSV (with special rule for 2+ references)
                model_to_use = self._get_model_for_type(prompt_type, total_references)
                
                # Generate witty messages for user engagement
                witty_messages = []
                try:
                    from app.services.witty_message_service import witty_message_service
                    
                    # Build context for witty message generation
                    witty_context = {
                        "is_edit": "EDIT" in prompt_type,
                        "has_references": referenced_image or (context and context.get("uploaded_images")),
                        "is_video": "VIDEO" in prompt_type,
                        "total_references": total_references,
                        "working_image": context.get("working_image") if context else None,
                        "working_video": context.get("working_video") if context else None,
                        "uploaded_images": context.get("uploaded_images") if context else [],
                        "user_id": user_id,
                        "session_id": context.get("session_id") if context else None
                    }
                    
                    # Estimate generation time based on model and type
                    estimated_time = self._estimate_generation_time(prompt_type, model_to_use)
                    
                    witty_messages = await witty_message_service.generate_witty_messages(
                        user_prompt=user_prompt,
                        prompt_type=prompt_type,
                        estimated_time=estimated_time,
                        context=witty_context
                    )
                    
                    logger.info(f"Generated {len(witty_messages)} witty messages for user {user_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to generate witty messages: {e}")
                    # Use fallback messages
                    witty_messages = self._get_fallback_witty_messages(prompt_type)
                    logger.info(f"WITTY MESSAGES FALLBACK: Using {len(witty_messages)} fallback messages")
                
                # Create successful result
                result = SimplifiedFlowResult(
                    prompt_type=PromptType(prompt_type),
                    enhanced_prompt=enhanced_prompt,
                    model_to_use=model_to_use,
                    original_prompt=user_prompt,
                    reasoning=reasoning,
                    active_image=active_image,
                    uploaded_image=uploaded_image,
                    referenced_image=referenced_image,
                    cache_hit=False,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    witty_messages=witty_messages
                )
                
                # Cache successful result
                if self.cache:
                    try:
                        cache_data = self._result_to_cache_data(result)
                        await self.cache.set(cache_key, cache_data, ttl=self.cache_ttl)
                    except Exception as e:
                        logger.warning(f"Cache set failed: {e}")
                
            except (CircuitBreakerOpenError, Exception) as e:
                logger.warning(f"AI classification failed for user {user_id}: {e}")
                circuit_breaker_state = self.circuit_breaker.state.value if self.circuit_breaker else "unknown"
                used_fallback = True
                
                # Create fallback result
                result = self._create_fallback_result(
                    user_prompt, active_image, active_video, uploaded_image, referenced_image,
                    reason=str(e), total_references=total_references
                )
                result.processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Log classification
            await self._log_classification(
                user_id=user_id,
                prompt=user_prompt,
                result=result,
                used_fallback=used_fallback,
                rate_limited=False,
                circuit_breaker_state=circuit_breaker_state
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in simplified flow for user {user_id}: {e}")
            
            # Create error fallback
            result = self._create_fallback_result(
                user_prompt, active_image, uploaded_image, referenced_image,
                reason=f"error: {str(e)}"
            )
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Log the failure
            await self._log_classification(
                user_id=user_id,
                prompt=user_prompt,
                result=result,
                used_fallback=True,
                rate_limited=False,
                circuit_breaker_state="error"
            )
            
            return result
    
    async def _classify_and_enhance(
        self, 
        user_prompt: str,
        active_image: bool,
        active_video: bool,
        uploaded_image: bool, 
        referenced_image: bool,
        context: Optional[Dict[str, Any]]
    ) -> Tuple[str, str, str]:
        """
        Use LLM to classify intent and enhance prompt based on CSV rules
        """
        
        # Build comprehensive prompt with all CSV logic embedded
        classification_prompt = f"""You are an AI assistant that classifies user intents and enhances prompts based on specific rules.

ANALYSIS:
You are given these EXACT boolean flags - USE THESE VALUES ONLY:
1. active_image: {active_image}
2. active_video: {active_video}
3. uploaded_image: {uploaded_image} 
4. referenced_image: {referenced_image}

DO NOT try to detect images or videos from the prompt - these flags tell you exactly what content is available!

🚨 CRITICAL RULE: If active_video=TRUE and the prompt contains ANY editing keywords (change, modify, edit, adjust, update, make it, turn it, transform, alter, add, remove, apply style, change colors, change weather, etc.), you MUST classify as VIDEO_EDIT or VIDEO_EDIT_REF, NOT as EDIT_IMAGE. This takes absolute priority over all other rules!

🚨 ENHANCED PROMPT INDICATOR: If your enhanced prompt contains @working_video, this is a STRONG INDICATOR that you should classify as VIDEO_EDIT or VIDEO_EDIT_REF, never as EDIT_IMAGE variants!

VIDEO DETECTION - FIRST PRIORITY:
Check if the user wants VIDEO generation or editing (not image). Video keywords include:
- "create video", "make video", "generate video", "video of", "animate", "animation"
- "make it move", "bring to life", "turn into video", "video version"
- "moving", "motion", "animated", "video clip", "movie", "film"

VIDEO EDITING DETECTION - HIGHEST PRIORITY:
If active_video=TRUE AND user wants to edit/modify the working video:
- "edit video", "change video", "modify video", "adjust video", "update video"
- "make the video", "turn the video", "transform the video", "alter the video"
- "change the weather", "make it sunny", "add rain", "change lighting", "change style"
- "make it look", "apply style", "change colors", "add object", "remove background"
- Style transfers: "change style to", "make it look like", "apply style from"
- Weather/environment: "change weather", "make it sunny", "add rain", "change lighting"
- Content modification: "add object", "remove background", "change colors"

IF VIDEO INTENT DETECTED:
CRITICAL: Veo 3 is ONLY used for pure text-to-video with audio when NO working image exists!

First check for AUDIO INTENT - Audio is required for:
A) EXPLICIT AUDIO: singing, song, music, audio, sound, voice, speak, talk, lyrics, melody, vocal, narration, dialogue, conversation
B) CONVERSATIONAL SCENARIOS: interview, interviewing, reporter, news report, press conference, Q&A, asking questions, discussion, debate, meeting, presentation, lecture, speech, announcement
C) INTERACTIVE CONTENT: characters talking to each other, people having conversations, phone calls, video calls, broadcasting, podcasting, storytelling

CRITICAL: If the video involves people communicating, conversing, or any scenario where dialogue/speech is the main content, it REQUIRES AUDIO even if not explicitly mentioned.

1. Active Image=NO, Uploaded Image=NO, Referenced Image=NO WITH AUDIO INTENT → Type: NEW_VIDEO_WITH_AUDIO, Model: Veo 3 (text-to-video with audio)
2. Active Image=NO, Uploaded Image=NO, Referenced Image=NO WITHOUT AUDIO INTENT → Type: NEW_VIDEO, Model: MiniMax (text-to-video)
3. Active Image=YES, Uploaded Image=NO, Referenced Image=NO WITH AUDIO INTENT → Type: IMAGE_TO_VIDEO_WITH_AUDIO, Model: Veo 3 Fast (image-to-video with audio)
4. Active Image=YES, Uploaded Image=NO, Referenced Image=NO WITHOUT AUDIO INTENT → Type: IMAGE_TO_VIDEO, Model: MiniMax (image-to-video)
5. Active Image=YES AND (Uploaded Image=YES OR Referenced Image=YES) → Type: EDIT_IMAGE_REF_TO_VIDEO, Model: Runway (reference-based video)
6. Active Image=NO AND (Uploaded Image=YES OR Referenced Image=YES) → Type: EDIT_IMAGE_REF_TO_VIDEO, Model: Runway (reference-based video)

🚨🚨🚨 VIDEO EDITING CLASSIFICATION (ABSOLUTE HIGHEST PRIORITY - check FIRST before ANY other classification):
If user has WORKING VIDEO context (active_video=TRUE):

MANDATORY DECISION TREE - FOLLOW EXACTLY:
- If active_video=TRUE AND prompt contains edit keywords → MUST be VIDEO_EDIT or VIDEO_EDIT_REF
- Edit keywords: "change", "modify", "edit", "adjust", "update", "make it", "turn it", "transform", "alter", "add", "remove", "apply style", "change colors", "change weather"
- If your enhanced prompt uses @working_video → MUST be VIDEO_EDIT or VIDEO_EDIT_REF

1. Working Video=YES, No edit intent → Type: NEW_VIDEO (creating new video, ignore working video)
2. Working Video=YES, Edit intent, No references → Type: VIDEO_EDIT, Model: gen4_aleph (basic video editing)
3. Working Video=YES, Edit intent, With references → Type: VIDEO_EDIT_REF, Model: gen4_aleph (reference-based video editing)

🚨 EXAMPLES: 
- "change the horse to be red" with active_video=TRUE → Type: VIDEO_EDIT (NOT EDIT_IMAGE!)
- "add @pig walking behind" with active_video=TRUE + referenced_image=TRUE → Type: VIDEO_EDIT_REF (NOT EDIT_IMAGE_ADD_NEW!)

IMAGE CLASSIFICATION RULES (if NO video intent):
1. If Active Image=NO, Uploaded Image=NO, Referenced Image=NO → Type: NEW_IMAGE, Model: Flux 1.1 Pro
2. If Active Image=YES, Uploaded Image=NO, Referenced Image=NO → Type: NEW_IMAGE, Model: Flux 1.1 Pro (no edit intent) or EDIT_IMAGE, Model: Kontext (edit intent)
3. If Active Image=NO, Uploaded Image=NO, Referenced Image=YES → Type: NEW_IMAGE_REF, Model: Runway
4. If Active Image=NO, Uploaded Image=YES, Referenced Image=NO → Type: NEW_IMAGE_REF, Model: Runway
5. If Active Image=YES, Uploaded Image=YES, Referenced Image=NO → Type: EDIT_IMAGE_REF or EDIT_IMAGE_ADD_NEW, Model: Runway or Replicate
6. If Active Image=YES, Uploaded Image=NO, Referenced Image=YES → Type: EDIT_IMAGE_REF or EDIT_IMAGE_ADD_NEW, Model: Runway or Replicate  
7. If Active Image=YES, Uploaded Image=YES, Referenced Image=YES → Type: EDIT_IMAGE_REF or EDIT_IMAGE_ADD_NEW, Model: Runway or Replicate

CRITICAL NEW DISTINCTION FOR EDIT_IMAGE_REF vs EDIT_IMAGE_ADD_NEW:
When both Active Image=TRUE AND (Uploaded Image=TRUE OR Referenced Image=TRUE), analyze the intent:

EDIT_IMAGE_REF (Use Runway) - Face/Hair/Dress Transfers:
- Face swapping/replacement: "replace face", "swap face", "change face to"
- Hair styling/transfer: "change hair", "hair style", "hairstyle from", "hair like"
- Clothing/dress transfer: "wear this", "put on", "dress in", "outfit from", "clothing from"
- Pose/position changes: "turn to face", "look like this", "same pose as"
- Style transfers from person to person: "make them look like", "style like this person"
- Key indicators: transferring specific features/attributes FROM one person TO another

EDIT_IMAGE_ADD_NEW (Use Replicate) - Adding New Elements:
- Adding people to scenes: "add person", "put woman next to", "place person in"
- Adding objects to environments: "add car to street", "put tree in background"
- Placing elements in new contexts: "put the woman next to the house"
- Combining separate elements: "merge these images", "combine person and scene"
- Environmental additions: "add mountains", "place building", "insert animal"
- Key indicators: adding NEW elements to scenes where they don't already exist
- Enhancement should maintain the photographic style and composition of the original image

CRITICAL: When both Active Image=TRUE AND (Uploaded Image=TRUE OR Referenced Image=TRUE), it is ALWAYS one of these reference types, but you must distinguish which one!

SPECIFIC EXAMPLE:
- "Change hair to @blonde" with working image → EDIT_IMAGE_REF (hair transfer)
- "Put the woman next to the house" with working image → EDIT_IMAGE_ADD_NEW (adding to scene)

EDIT INTENT KEYWORDS:
- "edit", "change", "modify", "adjust", "add", "remove", "make it", "turn it", "convert it", "transform it"
- "put on", "wear", "dress up", "style", "hair", "background", "color", "enhance", "improve"

PROMPT ENHANCEMENT RULES (from CSV):

VIDEO ENHANCEMENT RULES:
1. NEW_VIDEO: Transform user prompt to cover these elements:
   - Scene description: Overall description of the scene - what's happening, who's involved, atmosphere
   - Visual style: Overall look and feel - cinematic, realistic, animated, stylized, surreal
   - Camera movement: How camera should move - slow pan, static shot, tracking shot, aerial zoom (avoid slang terms)
   - Main subject: Primary person/character/object that should be the focus
   - Background setting: Specific location or environment - city street at night, forest during sunrise, futuristic lab
   - Lighting/mood: Type of lighting and emotional tone - soft natural light with warm tone, harsh dramatic lighting
   - Audio cue (optional): Specific sound or music - song when character dances, ambient sounds like rain/footsteps
   - Color palette: Dominant colors or tones - bold and bright, pastel, muted earth tones, monochrome
   - Dialog/Background Noise (optional): What characters should say and when, environmental sounds
   - Subtitles and Language: Whether to include subtitles, language preferences affect cultural context

2. IMAGE_TO_VIDEO: No specific enhancement - use original prompt for image animation (MiniMax - no audio)
3. IMAGE_TO_VIDEO_WITH_AUDIO: No specific enhancement - use original prompt for image animation with audio (Veo 3 Fast - audio enabled)
4. EDIT_IMAGE_REF_TO_VIDEO: Use Kontext to update the image first, then send to Runway for video generation

IMAGE ENHANCEMENT RULES:
1. NEW_IMAGE: No enhancement needed - use original prompt
2. NEW_IMAGE_REF: Understand intent and make minor edits to improve clarity. Add: "Preserve all facial features, likeness, and identity of referenced people exactly. Maintain all other aspects of the original image."
3. EDIT_IMAGE: Understand intent and make minor edits to improve clarity. Add: "Maintain all other aspects of the original image."
4. EDIT_IMAGE_REF: 
   - DO NOT just append to the original prompt - COMPLETELY REWRITE IT
   - Analyze the user intent and available references to determine:
     * TARGET: The main subject being edited (often from working image or primary @reference)
     * CHANGE: What the user wants to modify (hair, clothing, style, etc.)
     * SOURCE: Which @reference provides the new style
   - REWRITE the prompt using SIMPLE, DIRECT language: "Add [CHANGE] from @[SOURCE] to @[TARGET]"
   - For EDIT_IMAGE_REF: TARGET = working image (the subject being edited), SOURCE = @reference from prompt
   - Keep prompts short and clear - Runway works better with simple instructions
   - For face replacement: Use format "@working_image with only the face changed to match @[source]'s face exactly. Keep everything else identical: same body, pose, clothing, background, lighting, and style" rather than "replace face"
   - Examples:
     * "Update the hair to @blonde" (with working image) → "@working_image with the hairstyle from @blonde. Maintain all other features. Only update the hair style."
     * "Change hair to desired style" (with working image + uploaded hair image) → "@working_image with the hairstyle from @reference_1. Maintain all other features. Only update the hair style."
     * "Put @dress on person" (with working image) → "Add clothing from @dress to @working_image"
     * "Change outfit" (with working image + uploaded clothing image) → "Add clothing from @reference_1 to @working_image"
     * "Update face to @finley" (with working image) → "@working_image with only the face changed to match @finley's face exactly. Keep everything else identical: same body, pose, clothing, background, lighting, and style."
     * "Replace face with @person" (with working image) → "@working_image with only the face changed to match @person's face exactly. Keep everything else identical: same body, pose, clothing, background, lighting, and style."

5. EDIT_IMAGE_ADD_NEW:
   - For adding new elements to scenes, use descriptive language that clearly explains placement
   - Focus on spatial relationships and natural integration
   - ALWAYS include both @reference and @working_image tags explicitly in the enhanced prompt
   - Examples:
     * "Put the woman next to the house" → "Place the woman from @reference_1 next to the house in @working_image, ensuring natural lighting and perspective"
     * "Add person to background" → "Add the person from @reference_1 to the background of @working_image, maintaining consistent lighting and scale"
     * "Add @finley skating with cheetah" → "Place @finley skating alongside the cheetah in @working_image, ensuring natural integration"

Based on the CSV decision matrix - APPLY THESE RULES IN ORDER:
1. If active_image=True AND (uploaded_image=True OR referenced_image=True): Determine if EDIT_IMAGE_REF (transfers) or EDIT_IMAGE_ADD_NEW (adding referenced elements)
2. If no images (all False): prompt_type="NEW_IMAGE"
3. If only uploaded_image=True OR only referenced_image=True: prompt_type="NEW_IMAGE_REF"  
4. If only active_image=True: prompt_type="EDIT_IMAGE" (basic image editing without references)

For prompt enhancement:
- NEW_IMAGE: Return original prompt unchanged
- NEW_IMAGE_REF: Make minor clarity improvements and add "Preserve all facial features, likeness, and identity of referenced people exactly. Maintain all other aspects of the original image."
- EDIT_IMAGE: Make minor clarity improvements and add "Maintain all other aspects of the original image."
- EDIT_IMAGE_REF: COMPLETELY REWRITE the prompt following the structured format - do not just enhance the original!
- EDIT_IMAGE_ADD_NEW: Focus on placing/adding new elements to scenes with clear spatial instructions, natural integration, and maintaining the photographic style and composition of the original image. ALWAYS explicitly include both @reference and @working_image tags in the enhanced prompt

**CRITICAL FOR EDIT_IMAGE_REF: You must identify the TARGET and SOURCE from context and rewrite the prompt completely. Never just append or enhance - always restructure to the SIMPLE format: "Add [CHANGE] from @[SOURCE] to @[TARGET]"**

**CRITICAL FOR EDIT_IMAGE_ADD_NEW: Focus on placing/adding new elements to scenes with clear spatial instructions, natural integration, and maintaining the photographic style and composition of the original image. ALWAYS explicitly include both @reference and @working_image tags in the enhanced prompt.**

Return your analysis as JSON:
{{"prompt_type": "NEW_IMAGE|NEW_IMAGE_REF|EDIT_IMAGE|EDIT_IMAGE_REF|EDIT_IMAGE_ADD_NEW|NEW_VIDEO|NEW_VIDEO_WITH_AUDIO|IMAGE_TO_VIDEO|IMAGE_TO_VIDEO_WITH_AUDIO|EDIT_IMAGE_REF_TO_VIDEO|VIDEO_EDIT|VIDEO_EDIT_REF", "enhanced_prompt": "the appropriately enhanced or rewritten prompt"}}

USER PROMPT TO ANALYZE: "{user_prompt}"

REFERENCE TAG RULES:
- active_image=True: Working image becomes @working_image
- active_video=True: Working video becomes @working_video
- uploaded_image=True: First uploaded image becomes @reference_1, second becomes @reference_2, etc.
- referenced_image=True: Named references in prompt keep their original names (e.g., @blonde, @dress)

🚨 CRITICAL VIDEO EDITING RULE: If active_video=TRUE, you MUST use @working_video in enhanced prompts, NOT @working_image!

VIDEO EDITING ENHANCEMENT RULES (when active_video=TRUE):
- VIDEO_EDIT: "Change the weather in @working_video to be sunny" 
- VIDEO_EDIT_REF: "Add @pig walking behind the boy in @working_video" (when referenced_image=TRUE)
- ALWAYS use @working_video as the target for video editing, never @working_image
- For VIDEO_EDIT_REF: Include both @working_video and @reference tags in enhanced prompt
- Examples:
  * "change the horse to be red" → "Change the horse in @working_video to be red"
  * "add @pig walking behind" → "Add @pig walking behind the boy in @working_video"

CONTEXT FOR EDIT_IMAGE_REF vs EDIT_IMAGE_ADD_NEW:
- When active_image=True, there is a WORKING IMAGE that is the main subject being edited (this becomes @working_image)
- When referenced_image=True, there are @reference images mentioned in the prompt that provide styles/features to copy
- When uploaded_image=True, there are uploaded images that should be referenced as @reference_1, @reference_2, etc.

**CRITICAL DISTINCTION:**
- EDIT_IMAGE_REF: TRANSFERRING features/styles FROM one subject TO another (face swaps, hair styling, clothing changes)
  - Examples: "Change hair to @blonde", "Put on @dress", "Replace face with @person", "Style like @celebrity"
  - The @reference provides a FEATURE/STYLE to transfer
  - The @working_image is the TARGET that receives the feature/style

- EDIT_IMAGE_ADD_NEW: ADDING/PLACING REFERENCED people/objects INTO a scene (REQUIRES referenced_image=True OR uploaded_image=True)
  - Examples: "Add @person to the scene", "Put @finley walking with tiger", "Place @woman next to house"
  - The @reference is a COMPLETE ELEMENT to add to the scene
  - The @working_image is the SCENE/ENVIRONMENT to add to
  - **CRITICAL: ONLY use EDIT_IMAGE_ADD_NEW when you have actual reference images to add. If no references, use EDIT_IMAGE instead.**

**KEY INDICATORS FOR EDIT_IMAGE_ADD_NEW:**
- Phrases like "Add @person", "Put @name", "Place @character" (WITH actual @references)
- Actions involving the referenced person: "walking", "sitting", "standing", "playing"
- Spatial relationships: "next to", "in front of", "behind", "with"
- Scene integration: "to the scene", "in the background", "in the image"
- **CRITICAL: ONLY use EDIT_IMAGE_ADD_NEW when uploaded_image=True OR referenced_image=True**
- **WARNING: Do NOT use EDIT_IMAGE_ADD_NEW for generic "add a bear", "add a car", "add nats" etc. without actual reference images. These are EDIT_IMAGE.**

**KEY INDICATORS FOR EDIT_IMAGE_REF:**
- Style/feature transfers: "hair like", "dress like", "face from", "style of"
- Clothing changes: "wear this", "put on", "in this outfit"
- Appearance modifications: "make look like", "change to look like"
- Face replacement: "update face", "replace face", "change face", "face to", "face swap", "look like @person"

- For EDIT_IMAGE_REF: The WORKING IMAGE is the TARGET (what gets edited), @references are the SOURCE (what to copy from)
- For EDIT_IMAGE_ADD_NEW: The WORKING IMAGE is the scene/environment, @references are elements to ADD to the scene
- For EDIT_IMAGE: The WORKING IMAGE is edited/modified without external references
- Example: "Update hair to @blonde" with working image = TARGET is @working_image, SOURCE is @blonde reference (EDIT_IMAGE_REF)
- Example: "Put the woman next to the house" with working image + uploaded woman image = SCENE is @working_image, ELEMENT TO ADD is @reference_1 (EDIT_IMAGE_ADD_NEW)  
- Example: "Add @finley walking the cheetah" with @finley reference = SCENE is @working_image, ELEMENT TO ADD is @finley (EDIT_IMAGE_ADD_NEW)
- Example: "Make him riding a bear" with only working image = basic image editing (EDIT_IMAGE)
- CRITICAL: For uploaded images (not named references), always use @reference_1, @reference_2, etc. - NEVER use generic @reference
- NEVER use the @reference as both TARGET and SOURCE - always use @working_image as TARGET for EDIT_IMAGE_REF or as SCENE for EDIT_IMAGE_ADD_NEW

TASK:
1. Classify the intent type based on the rules above
2. Enhance the prompt according to the enhancement rules
3. For EDIT_IMAGE_REF: Carefully analyze which @reference is the TARGET (subject being changed) vs SOURCE (providing the style/feature)
4. For EDIT_IMAGE_ADD_NEW: Focus on spatial placement and natural integration of new elements  
5. **CRITICAL: If only active_image=True (no uploads/references), ALWAYS use EDIT_IMAGE for any editing request, even if it mentions "adding" things like "add nats", "add a car", etc.**
6. **EDIT_IMAGE_ADD_NEW requires uploaded_image=True OR referenced_image=True - never use it when both are False**
7. Provide reasoning for your classification and enhancement decisions

IMPORTANT FOR EDIT_IMAGE_REF vs EDIT_IMAGE_ADD_NEW:
- EDIT_IMAGE_REF: Always identify the main subject (TARGET) that is being edited
- EDIT_IMAGE_REF: Clearly specify what aspect is being changed (hair, clothing, pose, etc.)
- EDIT_IMAGE_REF: Structure the enhanced prompt to be unambiguous about what changes and what stays the same
- EDIT_IMAGE_REF: Use the SIMPLE format: "Add [aspect] from @[source] to @[target]"
- EDIT_IMAGE_REF: For face replacement, use format "@working_image with only the face changed to match @[source]'s face exactly. Keep everything else identical: same body, pose, clothing, background, lighting, and style"
- EDIT_IMAGE_ADD_NEW: Focus on adding new elements to scenes with clear spatial instructions while maintaining the photographic style and composition of the original image. ALWAYS explicitly include both @reference and @working_image tags in the enhanced prompt
- EDIT_IMAGE_ADD_NEW: Use descriptive language for placement: "Place @[element] [spatial relationship] in @working_image"
- CRITICAL: If uploaded_image=True, use @reference_1 for the first uploaded image, @reference_2 for second, etc.
- NEVER use generic @reference - always use the specific numbered reference tags

Respond with ONLY valid JSON and no additional text:
{{
    "type": "NEW_IMAGE|NEW_IMAGE_REF|EDIT_IMAGE|EDIT_IMAGE_REF|EDIT_IMAGE_ADD_NEW|NEW_VIDEO|NEW_VIDEO_WITH_AUDIO|IMAGE_TO_VIDEO|IMAGE_TO_VIDEO_WITH_AUDIO|EDIT_IMAGE_REF_TO_VIDEO",
    "enhanced_prompt": "enhanced version of user prompt following CSV rules",
    "reasoning": "brief explanation of classification and enhancement decisions"
}}

IMPORTANT: Return ONLY the JSON object above. Do not add any extra analysis, explanations, or text after the JSON."""

        # Call Claude via Replicate (using correct API format)
        def sync_call():
            try:
                result_text = ""
                for event in replicate.stream(
                    self.model,
                    input={
                        "prompt": classification_prompt,
                        "system_prompt": "You are an AI assistant that classifies user intents and enhances prompts based on specific rules. Always return valid JSON."
                    }
                ):
                    result_text += str(event)
                return result_text.strip()
            except Exception as e:
                logger.error(f"Claude API call failed: {e}")
                raise

        result_text = await asyncio.to_thread(sync_call)
        
        # Debug: Log the raw LLM response
        print(f"[DEBUG] SIMPLIFIED: Raw LLM response: {result_text}")
        
        # Parse JSON response
        try:
            # Clean up potential markdown formatting
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                lines = result_text.split('\n')
                for i, line in enumerate(lines):
                    if line.strip().startswith('{'):
                        result_text = '\n'.join(lines[i:])
                        break
                if result_text.endswith("```"):
                    result_text = result_text[:-3].strip()
            
            # Clean up control characters that break JSON parsing
            import re
            result_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', result_text)  # Remove control characters
            result_text = re.sub(r'\s+', ' ', result_text)  # Normalize whitespace
            
            result = json.loads(result_text)
            
            # Handle both "type" and "prompt_type" field names for compatibility
            llm_type = result.get("type") or result.get("prompt_type", "NEW_IMAGE")
            enhanced_prompt = result.get("enhanced_prompt", user_prompt)
            reasoning = result.get("reasoning", "LLM classification completed")
            
            # Trust the LLM classification - only use CSV rules as fallback for edge cases
            print(f"[DEBUG] SIMPLIFIED: LLM classified as {llm_type} with reasoning: {reasoning}")
            
            # Only override LLM if it makes an obviously invalid classification
            # (For now, trust the LLM - we can add specific validation rules later if needed)
            valid_types = ["NEW_IMAGE", "NEW_IMAGE_REF", "EDIT_IMAGE", "EDIT_IMAGE_REF", "EDIT_IMAGE_ADD_NEW", 
                          "NEW_VIDEO", "NEW_VIDEO_WITH_AUDIO", "IMAGE_TO_VIDEO", "IMAGE_TO_VIDEO_WITH_AUDIO", "EDIT_IMAGE_REF_TO_VIDEO",
                          "VIDEO_EDIT", "VIDEO_EDIT_REF"]
            
            if llm_type not in valid_types:
                print(f"[WARNING] SIMPLIFIED: LLM returned invalid type '{llm_type}', falling back to CSV rules")
                correct_type = self._enforce_csv_rules(active_image, uploaded_image, referenced_image, user_prompt)
                llm_type = correct_type
                reasoning += f" (Corrected from invalid '{result.get('type')}' to {correct_type} via CSV fallback)"
            else:
                print(f"[DEBUG] SIMPLIFIED: Trusting LLM classification: {llm_type}")
                
                # VEO-3-Fast now supports image inputs, so no correction needed
                # Note: Previously VEO-3-Fast couldn't accept image inputs, but this has been updated
                
                # CSV rules are NOT enforced - LLM decision is trusted
                
                # If we did a CSV fallback to EDIT_IMAGE_REF, ensure proper prompt format
                if llm_type == "EDIT_IMAGE_REF" and "CSV fallback" in reasoning:
                    if "hair" in user_prompt.lower():
                        if referenced_image and not uploaded_image:
                            # Use the named reference from the prompt
                            import re
                            refs = re.findall(r'@(\w+)', user_prompt)
                            if refs:
                                ref_name = refs[0]
                                enhanced_prompt = f"@working_image with the hairstyle from @{ref_name}. Maintain all other features. Only update the hair style."
                            else:
                                enhanced_prompt = f"@working_image with the hairstyle from @reference_1. Maintain all other features. Only update the hair style."
                        else:
                            enhanced_prompt = f"@working_image with the hairstyle from @reference_1. Maintain all other features. Only update the hair style."
                    elif "clothing" in user_prompt.lower():
                        enhanced_prompt = f"Add clothing from @reference_1 to @working_image"
                    elif "face" in user_prompt.lower():
                        enhanced_prompt = f"Add face from @reference_1 to @working_image"
                    else:
                        enhanced_prompt = f"Add style from @reference_1 to @working_image"
            
            return (llm_type, enhanced_prompt, reasoning)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Raw response: {result_text}")
            
            # Fallback classification based on simple rules
            return self._fallback_classify_and_enhance(
                user_prompt, active_image, uploaded_image, referenced_image
            )
    
    def _fallback_classify_and_enhance(
        self,
        user_prompt: str,
        active_image: bool,
        uploaded_image: bool,
        referenced_image: bool
    ) -> Tuple[str, str, str]:
        """
        Fallback classification when LLM fails
        """
        
        # Get video keywords from configuration
        try:
            video_keywords = model_config.get_video_keywords()
            # Add any additional transform keywords from config
            routing_rules = model_config.config.get("model_routing", {}).get("routing_rules", {})
            video_config = routing_rules.get("video_detection", {})
            transform_keywords = video_config.get("transform_keywords", [])
            motion_keywords = video_config.get("motion_keywords", [])
            motion_context = video_config.get("motion_context_required", [])
            motion_exclusions = video_config.get("motion_exclusions", [])
        except Exception as e:
            logger.warning(f"Error loading video keywords from config: {e}, using defaults")
            video_keywords = ["create video", "make video", "generate video", "video of", "animate", "animation"]
            transform_keywords = ["transform this image into a video", "transform into video"]
            motion_keywords = ["move"]
            motion_context = ["image", "this"]
            motion_exclusions = ["remove"]
        
        # Check for video intent with configuration-based detection
        has_basic_video_intent = any(keyword in user_prompt.lower() for keyword in video_keywords)
        has_transform_intent = any(keyword in user_prompt.lower() for keyword in transform_keywords)
        
        # Check motion keywords with context and exclusions
        has_motion_intent = False
        if motion_keywords:
            for motion_word in motion_keywords:
                if (motion_word in user_prompt.lower() and
                    any(context_word in user_prompt.lower() for context_word in motion_context) and
                    not any(exclusion in user_prompt.lower() for exclusion in motion_exclusions)):
                    has_motion_intent = True
                    break
        
        has_video_intent = has_basic_video_intent or has_transform_intent or has_motion_intent
        
        if has_video_intent:
            # Video flow fallback logic
            if not active_image and not uploaded_image and not referenced_image:
                # Check for audio intent using configuration
                try:
                    audio_keywords = model_config.get_audio_keywords()
                except Exception as e:
                    logger.warning(f"Error loading audio keywords: {e}, using defaults")
                    audio_keywords = ["singing", "song", "music", "audio", "sound", "voice", "speak", "talk", 
                                     "lyrics", "melody", "chorus", "verse", "tune", "rhythm", "beat", "vocal", "microphone",
                                     "saying", "says", "said", "tells", "telling", "announces", "whispers", "shouts", "screams"]
                has_audio_intent = any(keyword in user_prompt.lower() for keyword in audio_keywords)
                
                if has_audio_intent:
                    # Veo 3 for text-to-video with audio
                    enhanced_prompt = self._enhance_veo3_prompt_fallback(user_prompt)
                    return ("NEW_VIDEO_WITH_AUDIO", enhanced_prompt, "Fallback: Text-to-video with audio (Veo 3)")
                else:
                    # MiniMax for text-to-video without audio
                    return ("NEW_VIDEO", user_prompt, "Fallback: Text-to-video (MiniMax)")
            elif active_image and not uploaded_image and not referenced_image:
                # Check for audio intent using configuration
                try:
                    audio_keywords = model_config.get_audio_keywords()
                except Exception as e:
                    logger.warning(f"Error loading audio keywords: {e}, using defaults")
                    audio_keywords = ["singing", "song", "music", "audio", "sound", "voice", "speak", "talk", 
                                     "lyrics", "melody", "chorus", "verse", "tune", "rhythm", "beat", "vocal", "microphone",
                                     "saying", "says", "said", "tells", "telling", "announces", "whispers", "shouts", "screams"]
                # Check for audio intent to decide between models
                has_audio_intent = any(keyword in user_prompt.lower() for keyword in audio_keywords)
                if has_audio_intent:
                    return ("IMAGE_TO_VIDEO_WITH_AUDIO", user_prompt, "Fallback: Image to video conversion with audio (Veo 3 Fast)")
                else:
                    return ("IMAGE_TO_VIDEO", user_prompt, "Fallback: Image to video conversion (MiniMax)")
            else:
                # Any combination with references = EDIT_IMAGE_REF_TO_VIDEO
                return ("EDIT_IMAGE_REF_TO_VIDEO", user_prompt, "Fallback: Video generation with image references")
        
        # Image flow fallback logic (existing)
        if not active_image and not uploaded_image and not referenced_image:
            prompt_type = "NEW_IMAGE"
            enhanced_prompt = user_prompt
        elif not active_image and (uploaded_image or referenced_image):
            prompt_type = "NEW_IMAGE_REF"
            enhanced_prompt = user_prompt + ". Preserve all facial features, likeness, and identity of referenced people exactly. Maintain all other aspects of the original image."
        elif active_image and not uploaded_image and not referenced_image:
            # Only working image - this is always EDIT_IMAGE (basic image editing)
            # Even if prompt contains "add" keywords, without reference images it's just editing
            prompt_type = "EDIT_IMAGE"
            enhanced_prompt = user_prompt + ". Maintain all other aspects of the original image."
        else:
            # active_image + (uploaded_image or referenced_image)
            # CRITICAL: Only use ADD_NEW/REF when we actually have reference images
            # Check for ADD_NEW vs REF scenarios
            add_keywords = ["add", "place", "put", "include", "insert", "bring", "introduce"]
            has_add_intent = any(keyword in user_prompt.lower() for keyword in add_keywords)
            
            if has_add_intent and (uploaded_image or referenced_image):
                # Adding new elements to existing scene (only with actual references)
                prompt_type = "EDIT_IMAGE_ADD_NEW"
                enhanced_prompt = user_prompt
            elif uploaded_image or referenced_image:
                # Transferring features/styles between images
                prompt_type = "EDIT_IMAGE_REF"
                enhanced_prompt = user_prompt
            else:
                # Fallback to basic edit if no references found
                prompt_type = "EDIT_IMAGE"
                enhanced_prompt = user_prompt + ". Maintain all other aspects of the original image."
        
        # Get model for type
        model_to_use = self._get_model_for_type(prompt_type, 0)
        
        return SimplifiedFlowResult(
            prompt_type=PromptType(prompt_type),
            enhanced_prompt=enhanced_prompt,
            model_to_use=model_to_use,
            original_prompt=user_prompt,
            reasoning="Fallback classification based on CSV rules",
            active_image=active_image,
            uploaded_image=uploaded_image,
            referenced_image=referenced_image,
            cache_hit=False,
            processing_time_ms=0
        )
    
    def _enhance_veo3_prompt_fallback(self, user_prompt: str) -> str:
        """
        Basic Veo 3 prompt enhancement for fallback scenarios
        """
        # Simple enhancement that adds some video-specific structure
        enhanced = f"Scene: {user_prompt}. "
        enhanced += "Visual style: cinematic and realistic. "
        enhanced += "Camera movement: smooth and steady. "
        enhanced += "Lighting: natural and well-balanced. "
        enhanced += "Duration: 5-10 seconds."
        return enhanced
    
    def _enforce_csv_rules(self, active_image: bool, uploaded_image: bool, referenced_image: bool, user_prompt: str = "") -> str:
        """
        Enforce CSV rules to determine the correct classification
        IMPORTANT: Check for video intent FIRST before applying image rules
        """
        
        # FIRST: Check for video intent in the prompt  
        video_keywords = ["create video", "make video", "generate video", "video of", "animate", "animation", 
                         "make it move", "bring to life", "turn into video", "video version", 
                         "moving", "motion", "animated", "video clip", "movie", "film", "make a video", "flow naturally",
                         "create a video"]
        transform_keywords = ["transform this image into a video", "transform into video"]
        
        # Avoid false positives like "remove" triggering on "move"
        has_video_intent = (any(keyword in user_prompt.lower() for keyword in video_keywords) or
                           any(keyword in user_prompt.lower() for keyword in transform_keywords) or
                           ("move" in user_prompt.lower() and ("image" in user_prompt.lower() or "this" in user_prompt.lower()) and "remove" not in user_prompt.lower()))
        
        # Debug video intent detection
        print(f"[DEBUG] CSV Rules: user_prompt='{user_prompt}'")
        print(f"[DEBUG] CSV Rules: user_prompt.lower()='{user_prompt.lower()}'")
        print(f"[DEBUG] CSV Rules: video_keywords={video_keywords}")
        print(f"[DEBUG] CSV Rules: has_video_intent={has_video_intent}")
        if has_video_intent:
            matching_keywords = [kw for kw in video_keywords if kw in user_prompt.lower()]
            print(f"[DEBUG] CSV Rules: matching video keywords={matching_keywords}")
        print(f"[DEBUG] CSV Rules: flags - active_image={active_image}, uploaded_image={uploaded_image}, referenced_image={referenced_image}")
        
        if has_video_intent:
            # Check for audio intent in video requests
            audio_keywords = ["singing", "sing", "song", "music", "audio", "sound", "voice", "speak", "talk", 
                             "lyrics", "melody", "chorus", "verse", "tune", "rhythm", "beat", "vocal", "microphone",
                             "saying", "says", "said", "tells", "telling", "announces", "whispers", "shouts", "screams"]
            has_audio_intent = any(keyword in user_prompt.lower() for keyword in audio_keywords)
            
            # VIDEO CSV RULES:
            if not active_image and not uploaded_image and not referenced_image:
                # No working image - check for audio intent
                if has_audio_intent:
                    return "NEW_VIDEO_WITH_AUDIO"  # Veo 3 (text-to-video with audio)
                else:
                    return "NEW_VIDEO"  # MiniMax (text-to-video)
            elif active_image and not uploaded_image and not referenced_image:
                # Has working image - choose model based on audio intent
                if has_audio_intent:
                    return "IMAGE_TO_VIDEO_WITH_AUDIO"  # Veo 3 Fast (image-to-video with audio)
                else:
                    return "IMAGE_TO_VIDEO"  # MiniMax (image-to-video)
            else:
                # Any combination with references = EDIT_IMAGE_REF_TO_VIDEO
                return "EDIT_IMAGE_REF_TO_VIDEO"  # MiniMax (reference-based video)
        
        # IMAGE CSV RULES (only if no video intent):
        if not active_image and not uploaded_image and not referenced_image:
            return "NEW_IMAGE"
        if active_image and not uploaded_image and not referenced_image:
            return "EDIT_IMAGE"  # Basic image editing with only working image
        if not active_image and not uploaded_image and referenced_image:
            return "NEW_IMAGE_REF"
        if not active_image and uploaded_image and not referenced_image:
            return "NEW_IMAGE_REF"
        if active_image and uploaded_image and not referenced_image:
            return "EDIT_IMAGE_REF"
        if active_image and not uploaded_image and referenced_image:
            return "EDIT_IMAGE_REF"  # Could be EDIT_IMAGE_ADD_NEW but default to REF for fallback
        if active_image and uploaded_image and referenced_image:
            return "EDIT_IMAGE_REF"  # Could be EDIT_IMAGE_ADD_NEW but default to REF for fallback
        
        return "NEW_IMAGE"  # Default fallback
    
    def _get_model_for_type(self, prompt_type: str, total_references: int = 0) -> str:
        """
        Map prompt type to model using centralized configuration
        Special rules are handled by the model config system
        """
        try:
            # Use centralized model configuration
            model = model_config.get_model_for_type(prompt_type, total_references)
            
            # Log special routing decisions
            if total_references >= 2:
                routing_rules = model_config.config.get("model_routing", {}).get("routing_rules", {})
                multi_ref_config = routing_rules.get("multi_reference_routing", {})
                if (multi_ref_config.get("enabled", True) and 
                    prompt_type in multi_ref_config.get("applies_to", [])):
                    print(f"[DEBUG] SIMPLIFIED: {total_references} reference images detected - routing to {model} via config rule")
            
            return model
            
        except Exception as e:
            logger.error(f"Error getting model from config for {prompt_type}: {e}")
            # Fallback to hardcoded mapping
            fallback_mapping = {
                "NEW_IMAGE": "black-forest-labs/flux-1.1-pro",
                "NEW_IMAGE_REF": "runway_gen4_image",
                "EDIT_IMAGE": "black-forest-labs/flux-kontext-max", 
                "EDIT_IMAGE_REF": "runway_gen4_image",
                "EDIT_IMAGE_ADD_NEW": "runway_gen4_image",
                "NEW_VIDEO": "minimax/video-01",
                "NEW_VIDEO_WITH_AUDIO": "google/veo-3",
                "IMAGE_TO_VIDEO": "minimax/video-01",
                "IMAGE_TO_VIDEO_WITH_AUDIO": "google/veo-3-fast",
                "EDIT_IMAGE_REF_TO_VIDEO": "minimax/video-01"
            }
            return fallback_mapping.get(prompt_type, "black-forest-labs/flux-1.1-pro")
    
    async def get_model_parameters(self, result: SimplifiedFlowResult, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get model-specific parameters based on flow result (with caching)"""
        
        # Generate cache key for model parameters
        cache_key = f"model_params:{result.model_to_use}:{result.prompt_type.value}"
        
        # Ensure service is initialized
        await self._ensure_initialized()
        
        # Skip cache for Runway models to ensure proper reference image handling
        use_cache = result.model_to_use != "runway_gen4_image"
        
        # Try to get from cache first (except for Runway models)
        if self.cache and use_cache:
            try:
                cached_params = await self.cache.get(cache_key)
                if cached_params:
                    # Add dynamic prompt to cached base parameters
                    cached_params["prompt"] = result.enhanced_prompt
                    logger.info(f"Cache HIT for model parameters: {result.model_to_use}")
                    return cached_params
            except Exception as e:
                logger.warning(f"Cache get failed for model parameters: {e}")
        
        # Generate parameters if not cached
        base_params = {
            "prompt": result.enhanced_prompt,
            "model": result.model_to_use
        }
        
        # Model-specific parameters
        if result.model_to_use == "black-forest-labs/flux-1.1-pro":
            base_params.update({
                "width": 1024,
                "height": 1024,
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "num_outputs": 1,
                "output_format": "jpg",
                "output_quality": 90
            })
        elif result.model_to_use == "black-forest-labs/flux-kontext-max":
            base_params.update({
                "guidance_scale": 3.5,
                "num_inference_steps": 28,
                "safety_tolerance": 2
            })
        elif result.model_to_use == "flux-kontext-apps/multi-image-kontext-max":
            # For EDIT_IMAGE_ADD_NEW flow with multi-image-kontext-max
            base_params.update({
                "guidance_scale": 7.5,
                "num_inference_steps": 20,
                "output_format": "png",
                "aspect_ratio": "16:9",
                "safety_tolerance": 2
            })
            
            # Add reference images for EDIT_IMAGE_ADD_NEW
            if context and result.prompt_type.value == "EDIT_IMAGE_ADD_NEW":
                reference_images = []
                
                print(f"[DEBUG] SIMPLIFIED: Setting up reference images for EDIT_IMAGE_ADD_NEW")
                print(f"[DEBUG] SIMPLIFIED: Context received: {context}")
                
                # For EDIT_IMAGE_ADD_NEW, add working image as @working_image reference first
                if "working_image" in context:
                    working_image_url = context["working_image"]
                    reference_images.append({
                        "url": working_image_url,
                        "uri": working_image_url,  # Both formats for compatibility
                        "tag": "working_image"
                    })
                    print(f"[DEBUG] SIMPLIFIED: Added working image reference: @working_image -> {working_image_url}")
                
                # Get reference images from context
                if "reference_images" in context:
                    print(f"[DEBUG] SIMPLIFIED: Found {len(context['reference_images'])} reference images in context")
                    for ref_image in context["reference_images"]:
                        if isinstance(ref_image, dict) and "url" in ref_image and "tag" in ref_image:
                            reference_images.append({
                                "url": ref_image["url"],
                                "uri": ref_image["url"],  # Both formats for compatibility
                                "tag": ref_image["tag"]
                            })
                            print(f"[DEBUG] SIMPLIFIED: Added reference: @{ref_image['tag']} -> {ref_image['url']}")
                
                # Add uploaded images as references
                if "uploaded_images" in context and context["uploaded_images"]:
                    print(f"[DEBUG] SIMPLIFIED: Found {len(context['uploaded_images'])} uploaded images in context")
                    for i, uploaded_url in enumerate(context["uploaded_images"]):
                        reference_images.append({
                            "url": uploaded_url,
                            "uri": uploaded_url,  # Both formats for compatibility
                            "tag": f"reference_{i+1}"
                        })
                        print(f"[DEBUG] SIMPLIFIED: Added uploaded reference: reference_{i+1} -> {uploaded_url}")
                
                if reference_images:
                    base_params["reference_images"] = reference_images
                    print(f"[DEBUG] SIMPLIFIED: Added {len(reference_images)} reference images for multi-image-kontext-max")
                else:
                    print(f"[DEBUG] SIMPLIFIED: No reference images found for EDIT_IMAGE_ADD_NEW")
        elif result.model_to_use == "runway_gen4_image":
            print(f"[DEBUG] SIMPLIFIED: Setting up Runway image parameters for replicate runwayml/gen4-image")
            print(f"[DEBUG] SIMPLIFIED: Context received: {context}")
            
            # For replicate runway, use different parameter names
            base_params.update({
                "prompt": result.enhanced_prompt,  # Use 'prompt' instead of 'promptText'
                "aspect_ratio": "4:3",  # Use 'aspect_ratio' instead of 'ratio'
                "model": "runway_gen4_image"  # Keep original model name for routing
            })
            
            print(f"[DEBUG] SIMPLIFIED: Base Runway image params for replicate: {base_params}")
            
            # Add reference images if they exist in context
            if context and result.prompt_type.value in ["NEW_IMAGE_REF", "EDIT_IMAGE_REF", "EDIT_IMAGE_ADD_NEW"]:
                # Set type to route to correct generator path
                base_params["type"] = "text_to_image_with_references"
                print(f"[DEBUG] SIMPLIFIED: Set type=text_to_image_with_references for reference flow")
                
                reference_images = []
                
                print(f"[DEBUG] SIMPLIFIED: Checking for reference images in context...")
                
                # For EDIT_IMAGE_ADD_NEW, add working image as @working_image reference first
                if result.prompt_type.value == "EDIT_IMAGE_ADD_NEW" and "working_image" in context:
                    working_image_url = context["working_image"]
                    reference_images.append({
                        "uri": working_image_url,
                        "tag": "working_image"
                    })
                    print(f"[DEBUG] SIMPLIFIED: Added working image reference: @working_image -> {working_image_url}")
                
                # Get reference images from context
                if "reference_images" in context:
                    print(f"[DEBUG] SIMPLIFIED: Found {len(context['reference_images'])} reference images in context")
                    for ref_image in context["reference_images"]:
                        if isinstance(ref_image, dict) and "url" in ref_image and "tag" in ref_image:
                            reference_images.append({
                                "uri": ref_image["url"],
                                "tag": ref_image["tag"]
                            })
                            print(f"[DEBUG] SIMPLIFIED: Added reference: @{ref_image['tag']} -> {ref_image['url']}")
                
                # Add uploaded images as references
                if "uploaded_images" in context and context["uploaded_images"]:
                    print(f"[DEBUG] SIMPLIFIED: Found {len(context['uploaded_images'])} uploaded images in context")
                    for i, uploaded_url in enumerate(context["uploaded_images"]):
                        reference_images.append({
                            "uri": uploaded_url,
                            "tag": f"reference_{i+1}"
                        })
                        print(f"[DEBUG] SIMPLIFIED: Added uploaded reference: reference_{i+1} -> {uploaded_url}")
                
                if reference_images:
                    # For replicate runway, keep both formats for compatibility
                    base_params["referenceImages"] = reference_images  # camelCase for legacy
                    base_params["reference_images"] = reference_images  # snake_case for replicate
                    print(f"[DEBUG] SIMPLIFIED: Final Runway image params with {len(reference_images)} reference images: {base_params}")
                else:
                    print(f"[DEBUG] SIMPLIFIED: No reference images found - generator will work without references")
        # Video model parameters
        elif result.model_to_use == "veo-3.0-generate-preview":
            # VEO3 supports text-to-video and image-to-video with native audio generation
            base_params.update({
                "duration_seconds": 8,  # 8 seconds for VEO3
                "fps": 24,
                "enhance_prompt": True,
                "generate_audio": True  # VEO3 native audio generation
            })
            
            # Add image input for image-to-video scenarios
            if result.prompt_type.value in ["IMAGE_TO_VIDEO", "IMAGE_TO_VIDEO_WITH_AUDIO", "EDIT_IMAGE_REF_TO_VIDEO"]:
                # These will be populated with actual image URLs by the API layer
                base_params["requires_image_input"] = True
        elif result.model_to_use in ["google/veo-3", "google/veo-3-fast"]:
            # VEO-3 and VEO-3-Fast support text-to-video and image-to-video with native audio generation
            base_params.update({
                "duration_seconds": 8,  # 8 seconds for VEO models
                "fps": 24,
                "enhance_prompt": True,
                "generate_audio": True  # VEO native audio generation
            })
            
            # Add image input for image-to-video scenarios
            if result.prompt_type.value in ["IMAGE_TO_VIDEO", "IMAGE_TO_VIDEO_WITH_AUDIO", "EDIT_IMAGE_REF_TO_VIDEO"]:
                # These will be populated with actual image URLs by the API layer
                base_params["requires_image_input"] = True
        elif result.model_to_use == "minimax/video-01":
            # MiniMax supports all video scenarios (text-to-video and image-to-video)
            base_params.update({
                "prompt_optimizer": True
            })
            
            # Add first_frame_image for image-to-video scenarios
            if result.prompt_type.value in ["IMAGE_TO_VIDEO", "IMAGE_TO_VIDEO_WITH_AUDIO", "EDIT_IMAGE_REF_TO_VIDEO"]:
                # These will be populated with actual image URLs by the API layer
                base_params["requires_first_frame_image"] = True
                
            # Add subject_reference for reference-based scenarios  
            if result.prompt_type.value == "EDIT_IMAGE_REF_TO_VIDEO":
                base_params["requires_subject_reference"] = True
        else:
            # Default parameters for unknown models
            base_params.update({
                "guidance_scale": 7.5,
                "num_inference_steps": 20
            })
        
        # Cache the base parameters (without prompt) for 1 hour (except Runway models)
        if self.cache and use_cache:
            try:
                cache_params = {k: v for k, v in base_params.items() if k not in ["prompt", "promptText", "referenceImages"]}
                await self.cache.set(cache_key, cache_params, ttl=3600)
                logger.info(f"Cached model parameters for: {result.model_to_use}")
            except Exception as e:
                logger.warning(f"Cache set failed for model parameters: {e}")
        
        return base_params
    
    # Sprint 3: Infrastructure helper methods
    
    def _create_fallback_result(
        self,
        user_prompt: str,
        active_image: bool,
        active_video: bool,
        uploaded_image: bool,
        referenced_image: bool,
        reason: str,
        total_references: int = 0
    ) -> SimplifiedFlowResult:
        """Create fallback result when AI classification fails"""
        
        # HIGHEST PRIORITY: Check for video editing (working video + edit intent)
        if active_video:
            edit_keywords = ["edit", "change", "modify", "adjust", "update", "make the", "turn the", "transform", 
                           "alter", "change weather", "make it sunny", "add rain", "change lighting", "change style",
                           "make it look", "apply style", "change colors", "add object", "remove background"]
            has_edit_intent = any(keyword in user_prompt.lower() for keyword in edit_keywords)
            
            if has_edit_intent:
                if referenced_image:
                    prompt_type = "VIDEO_EDIT_REF"
                    enhanced_prompt = user_prompt
                else:
                    prompt_type = "VIDEO_EDIT"
                    enhanced_prompt = user_prompt
            else:
                # No edit intent with working video - create new video
                prompt_type = "NEW_VIDEO"
                enhanced_prompt = user_prompt
        
        # Check for general video intent
        else:
            video_keywords = ["create video", "make video", "generate video", "video of", "animate", "animation", 
                             "make it move", "bring to life", "turn into video", "video version", 
                             "moving", "motion", "animated", "video clip", "movie", "film", "move", "transform"]
            has_video_intent = any(keyword in user_prompt.lower() for keyword in video_keywords)
        
        if has_video_intent:
            # Video flow fallback logic
            if not active_image and not uploaded_image and not referenced_image:
                # Check for audio intent
                audio_keywords = ["singing", "sing", "song", "music", "audio", "sound", "voice", "speak", "talk", 
                                 "lyrics", "melody", "chorus", "verse", "tune", "rhythm", "beat", "vocal", "microphone",
                                 "saying", "says", "said", "tells", "telling", "announces", "whispers", "shouts", "screams"]
                has_audio_intent = any(keyword in user_prompt.lower() for keyword in audio_keywords)
                
                if has_audio_intent:
                    prompt_type = "NEW_VIDEO_WITH_AUDIO"
                    enhanced_prompt = self._enhance_veo3_prompt_fallback(user_prompt)
                else:
                    prompt_type = "NEW_VIDEO"
                    enhanced_prompt = user_prompt
            elif active_image and not uploaded_image and not referenced_image:
                # Check for audio intent in fallback result creation
                audio_keywords = ["singing", "sing", "song", "music", "audio", "sound", "voice", "speak", "talk", 
                                 "lyrics", "melody", "chorus", "verse", "tune", "rhythm", "beat", "vocal", "microphone",
                                 "saying", "says", "said", "tells", "telling", "announces", "whispers", "shouts", "screams"]
                has_audio_intent = any(keyword in user_prompt.lower() for keyword in audio_keywords)
                
                if has_audio_intent:
                    prompt_type = "IMAGE_TO_VIDEO_WITH_AUDIO"
                    enhanced_prompt = user_prompt
                else:
                    prompt_type = "IMAGE_TO_VIDEO"
                    enhanced_prompt = user_prompt
            else:
                # Any combination with references = EDIT_IMAGE_REF_TO_VIDEO
                prompt_type = "EDIT_IMAGE_REF_TO_VIDEO"
                enhanced_prompt = user_prompt
        else:
            # Image flow fallback logic (existing)
            if not active_image and not uploaded_image and not referenced_image:
                prompt_type = "NEW_IMAGE"
                enhanced_prompt = user_prompt
            elif not active_image and (uploaded_image or referenced_image):
                prompt_type = "NEW_IMAGE_REF"
                enhanced_prompt = user_prompt + ". Preserve all facial features, likeness, and identity of referenced people exactly. Maintain all other aspects of the original image."
            elif active_image and not uploaded_image and not referenced_image:
                # Check for edit intent
                edit_keywords = ["edit", "change", "modify", "adjust", "add", "remove", "make it", "turn it", "improve", "enhance", "fix", "update", "make the", "make this"]
                has_edit_intent = any(keyword in user_prompt.lower() for keyword in edit_keywords)
                if has_edit_intent:
                    prompt_type = "EDIT_IMAGE"
                    enhanced_prompt = user_prompt + ". Maintain all other aspects of the original image."
                else:
                    prompt_type = "NEW_IMAGE"
                    enhanced_prompt = user_prompt
            else:
                # active_image + (uploaded_image or referenced_image)
                # Check for ADD_NEW vs REF scenarios
                add_keywords = ["add", "place", "put", "include", "insert", "bring", "introduce"]
                has_add_intent = any(keyword in user_prompt.lower() for keyword in add_keywords)
                
                if has_add_intent:
                    # Adding new elements to existing scene
                    prompt_type = "EDIT_IMAGE_ADD_NEW"
                    enhanced_prompt = user_prompt
                else:
                    # Transferring features/styles between images
                    prompt_type = "EDIT_IMAGE_REF"
                    enhanced_prompt = user_prompt
        
        # Get model for type
        model_to_use = self._get_model_for_type(prompt_type, total_references)
        
        # Generate fallback witty messages
        witty_messages = self._get_fallback_witty_messages(prompt_type)

        
        return SimplifiedFlowResult(
            prompt_type=PromptType(prompt_type),
            enhanced_prompt=enhanced_prompt,
            model_to_use=model_to_use,
            original_prompt=user_prompt,
            reasoning="Fallback classification based on CSV rules",
            active_image=active_image,
            uploaded_image=uploaded_image,
            referenced_image=referenced_image,
            cache_hit=False,
            processing_time_ms=0,
            witty_messages=witty_messages
        )
    
    def _generate_cache_key(
        self, 
        prompt: str, 
        active_image: bool, 
        active_video: bool,
        uploaded_image: bool, 
        referenced_image: bool,
        user_id: str
    ) -> str:
        """Generate cache key for classification"""
        flags_str = f"a:{active_image}_v:{active_video}_u:{uploaded_image}_r:{referenced_image}"
        return f"simplified_flow_v3_{hash(prompt.lower())}_{hash(user_id)}_{flags_str}"
    
    def _result_to_cache_data(self, result: SimplifiedFlowResult) -> Dict[str, Any]:
        """Convert result to cache-friendly data"""
        return {
            "prompt_type": result.prompt_type.value,
            "enhanced_prompt": result.enhanced_prompt,
            "model_to_use": result.model_to_use,
            "original_prompt": result.original_prompt,
            "reasoning": result.reasoning,
            "active_image": result.active_image,
            "uploaded_image": result.uploaded_image,
            "referenced_image": result.referenced_image,
            "witty_messages": result.witty_messages
        }
    
    def _result_from_cache_data(self, cache_data: Dict[str, Any]) -> SimplifiedFlowResult:
        """Convert cache data back to result"""
        return SimplifiedFlowResult(
            prompt_type=PromptType(cache_data["prompt_type"]),
            enhanced_prompt=cache_data["enhanced_prompt"],
            model_to_use=cache_data["model_to_use"],
            original_prompt=cache_data["original_prompt"],
            reasoning=cache_data["reasoning"],
            active_image=cache_data["active_image"],
            uploaded_image=cache_data["uploaded_image"],
            referenced_image=cache_data["referenced_image"],
            cache_hit=True,
            processing_time_ms=0,  # Will be updated
            witty_messages=cache_data.get("witty_messages", [])
        )
    
    async def _log_classification(
        self,
        user_id: str,
        prompt: str,
        result: SimplifiedFlowResult,
        used_fallback: bool = False,
        rate_limited: bool = False,
        circuit_breaker_state: str = "closed"
    ):
        """Sprint 3: Log classification metrics to Supabase (graceful error handling)"""
        try:
            # Use Supabase client for analytics logging (more reliable)
            from app.core.database import db_manager
            
            # Create minimal log data that should work with any schema
            log_data = {
                "user_id": user_id,
                "user_prompt": prompt,  # Fixed: database expects "user_prompt" not "prompt"
                "classified_workflow": result.prompt_type.value,
                "processing_time_ms": result.processing_time_ms,
                "used_fallback": used_fallback,
                "cache_hit": result.cache_hit,
                "circuit_breaker_state": circuit_breaker_state,
                "rate_limited": rate_limited
            }
            
            # Try to add confidence if the column exists
            try:
                log_data["confidence"] = 0.95 if not used_fallback else 0.6
            except:
                pass  # Skip confidence if column doesn't exist
            
            await db_manager.log_intent_classification(log_data)
            
        except Exception as e:
            # Log error but don't fail the request
            logger.warning(f"Failed to log classification metrics (non-critical): {e}")
            # Continue processing - logging failures shouldn't break the main flow
    
    # Sprint 3: Health and monitoring methods
    async def get_health(self) -> Dict[str, Any]:
        """Get simplified flow service health status"""
        await self._ensure_initialized()
        
        health = {
            "service": "simplified_flow",
            "status": "healthy",
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
    
    def _estimate_generation_time(self, prompt_type: str, model_to_use: str) -> int:
        """Estimate generation time in seconds based on prompt type and model"""
        
        # Base times for different types
        base_times = {
            "NEW_IMAGE": 25,
            "NEW_IMAGE_REF": 30,
            "EDIT_IMAGE": 30,
            "EDIT_IMAGE_REF": 35,
            "EDIT_IMAGE_ADD_NEW": 35,
            "NEW_VIDEO": 45,
            "NEW_VIDEO_WITH_AUDIO": 50,
            "IMAGE_TO_VIDEO": 40,
            "IMAGE_TO_VIDEO_WITH_AUDIO": 45,
            "EDIT_IMAGE_REF_TO_VIDEO": 45,
            "VIDEO_EDIT": 60,
            "VIDEO_EDIT_REF": 65
        }
        
        # Get base time for prompt type
        base_time = base_times.get(prompt_type, 30)
        
        # Adjust based on model complexity
        model_adjustments = {
            "Flux 1.1 Pro": 0,  # Standard
            "Kontext": 5,       # Slightly slower
            "Runway": 10,       # Slower for complex operations
            "gen4_aleph": 15,   # Video editing is slower
            "Veo 3": 20,        # Video generation is slower
            "MiniMax": 15       # Video generation is slower
        }
        
        adjustment = model_adjustments.get(model_to_use, 0)
        estimated_time = base_time + adjustment
        
        # Ensure reasonable bounds
        return max(20, min(90, estimated_time))
    
    def _get_fallback_witty_messages(self, prompt_type: str) -> List[str]:
        """Get fallback witty messages if generation fails"""
        
        base_messages = [
            "Creating something amazing for you... ✨",
            "This might take around 30 seconds, but it'll be worth the wait",
            "Your creative vision is coming to life... 🎨",
            "Working some AI magic here... 🔮",
            "Almost there! Your masterpiece is being crafted",
            "Just 30 seconds until your creation is ready",
            "The AI is putting the finishing touches on your request",
            "Something special is being generated just for you",
            "Your imagination is becoming reality... 🌟",
            "The wait will be worth it - this is going to look incredible!"
        ]
        
        # Customize based on prompt type
        if "EDIT" in prompt_type:
            base_messages[0] = "Enhancing your creation with some AI magic... ✨"
            base_messages[2] = "Your improvements are being applied... 🎨"
        elif "VIDEO" in prompt_type:
            base_messages[0] = "Bringing your vision to life with motion... 🎬"
            base_messages[2] = "Your video is being crafted frame by frame... 🎨"
        
        return base_messages
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get simplified flow classification statistics using Supabase client (with caching)"""
        
        # Ensure initialized first
        await self._ensure_initialized()
        
        # Check cache first (5 minute TTL for stats)
        cache_key = "simplified_flow_stats"
        if self.cache:
            try:
                cached_stats = await self.cache.get(cache_key)
                if cached_stats:
                    logger.info("Cache HIT for simplified flow stats")
                    cached_stats["cached"] = True
                    return cached_stats
            except Exception as e:
                logger.warning(f"Cache get failed for stats: {e}")
        
        try:
            # Use Supabase client for stats (more reliable than PostgreSQL)
            from app.core.database import db_manager
            from datetime import datetime, timedelta
            
            # Get stats from last 24 hours
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            
            result = db_manager.supabase.table("intent_classification_logs")\
                .select("*")\
                .gte("created_at", yesterday)\
                .in_("classified_workflow", ["NEW_IMAGE", "NEW_IMAGE_REF", "EDIT_IMAGE", "EDIT_IMAGE_REF"])\
                .execute()
            
            stats_data = None
            if result.data:
                total = len(result.data)
                fallback_count = sum(1 for row in result.data if row.get('used_fallback', False))
                cache_hits = sum(1 for row in result.data if row.get('cache_hit', False))
                rate_limited_count = sum(1 for row in result.data if row.get('rate_limited', False))
                
                # Calculate averages
                total_confidence = sum(row.get('confidence', 0) for row in result.data)
                total_processing_time = sum(row.get('processing_time_ms', 0) for row in result.data)
                
                avg_confidence = total_confidence / total if total > 0 else 0
                avg_processing_time = total_processing_time / total if total > 0 else 0
                
                stats_data = {
                    "total_classifications": total,
                    "avg_confidence": round(avg_confidence, 2),
                    "avg_processing_time_ms": round(avg_processing_time, 2),
                    "fallback_rate": round((fallback_count / max(total, 1)) * 100, 2),
                    "cache_hit_rate": round((cache_hits / max(total, 1)) * 100, 2),
                    "rate_limited_rate": round((rate_limited_count / max(total, 1)) * 100, 2),
                    "period": "24 hours",
                    "service": "simplified_flow",
                    "data_source": "supabase_client",
                    "cached": False
                }
            else:
                stats_data = {
                    "message": "No classification data available", 
                    "service": "simplified_flow",
                    "cached": False
                }
            
            # Cache the result for 5 minutes
            if self.cache and stats_data:
                try:
                    await self.cache.set(cache_key, stats_data, ttl=300)  # 5 minutes
                    logger.info("Cached simplified flow stats")
                except Exception as e:
                    logger.warning(f"Cache set failed for stats: {e}")
            
            return stats_data
                
        except Exception as e:
            logger.error(f"Failed to get simplified flow classification stats: {e}")
            return {"error": str(e), "service": "simplified_flow", "cached": False}


# Global instance
simplified_flow = SimplifiedFlowService() 