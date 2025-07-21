"""
AI-powered prompt enhancement service using Claude through Replicate.
Optimizes prompts specifically for Flux Kontext Max following best practices.
"""

import asyncio
import logging
import hashlib
from typing import Dict, Any, Optional
import replicate

logger = logging.getLogger(__name__)

class PromptEnhancer:
    """AI-powered prompt enhancement for image generation models"""
    
    def __init__(self):
        self.model = "anthropic/claude-3.5-haiku"
        self.cache = None  # Will be initialized on first use
        
    async def _get_cache(self):
        """Get Redis cache instance (lazy initialization)"""
        if not self.cache:
            try:
                from app.core.cache import get_cache
                self.cache = await get_cache()
            except Exception as e:
                logger.warning(f"Cache not available for prompt enhancement: {e}")
                self.cache = None
        return self.cache
        
    def _generate_cache_key(self, original_prompt: str, edit_type: str, has_working_image: bool) -> str:
        """Generate cache key for prompt enhancement"""
        # Create key from prompt content and context
        key_data = f"prompt_enhance:{original_prompt}:{edit_type}:{has_working_image}"
        return f"prompt_enhance:{hashlib.md5(key_data.encode()).hexdigest()}"
        
    async def enhance_flux_kontext_prompt(
        self, 
        original_prompt: str, 
        edit_type: str = "image_editing",
        has_working_image: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Enhance a prompt for Flux Kontext Max using Claude AI (with caching)
        
        Args:
            original_prompt: The user's original prompt
            edit_type: Type of edit (image_editing, style_transfer, reference_styling, etc.)
            has_working_image: Whether there's a working image to edit
            context: Additional context about the request
            
        Returns:
            Enhanced prompt optimized for Flux Kontext Max
        """
        
        # Quick check - if prompt is already detailed (>15 words), return as-is
        if len(original_prompt.split()) > 15:
            logger.info(f"Prompt already detailed ({len(original_prompt.split())} words), skipping enhancement")
            return original_prompt
            
        # Check cache first
        cache = await self._get_cache()
        cache_key = self._generate_cache_key(original_prompt, edit_type, has_working_image)
        
        if cache:
            try:
                cached_enhancement = await cache.get(cache_key)
                if cached_enhancement:
                    logger.info(f"Cache HIT for prompt enhancement: '{original_prompt}' → '{cached_enhancement}'")
                    return cached_enhancement
            except Exception as e:
                logger.warning(f"Cache get failed for prompt enhancement: {e}")
            
        try:
            enhancement_prompt = self._build_enhancement_prompt(
                original_prompt, edit_type, has_working_image, context
            )
            
            enhanced = await self._call_claude(enhancement_prompt)
            
            # Validate enhancement isn't worse than original
            if len(enhanced.split()) < len(original_prompt.split()):
                logger.warning(f"Enhanced prompt shorter than original, using original")
                return original_prompt
                
            # Cache the result (24 hour TTL)
            if cache and enhanced != original_prompt:
                try:
                    await cache.set(cache_key, enhanced, ttl=86400)  # 24 hours
                    logger.info(f"Cached prompt enhancement: '{original_prompt}' → '{enhanced}'")
                except Exception as e:
                    logger.warning(f"Cache set failed for prompt enhancement: {e}")
                    
            logger.info(f"Enhanced prompt: '{original_prompt}' → '{enhanced}'")
            return enhanced
            
        except Exception as e:
            logger.error(f"Prompt enhancement failed: {e}")
            # Fallback to original prompt
            return original_prompt
    
    def _build_enhancement_prompt(
        self, 
        original_prompt: str, 
        edit_type: str,
        has_working_image: bool,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build the system prompt for Claude to enhance the user prompt"""
        
        flux_guidelines = """
Flux Kontext Max Best Practices:
1. Be SPECIFIC: Use clear, detailed language with exact colors and descriptions
2. Avoid vague terms like "make it better" or "improve"
3. Name subjects directly: "the woman with short black hair" vs. "she"
4. For identity preservation: Specify "while keeping the same facial features"
5. For backgrounds: "Change the background to [X] while keeping the person in exact same position"
6. For text editing: Use quotation marks around text to replace
7. For style transfer: Be specific about artistic styles (impressionist, Renaissance, etc.)
8. Preserve intentionally: Always specify what should stay the same
9. For hair styling: CRITICAL - emphasize maintaining all facial features and only changing hair
"""
        
        context_info = ""
        if has_working_image:
            context_info = "\nCONTEXT: This prompt will edit an existing image."
            
        if edit_type == "reference_styling":
            context_info += "\nThis is a virtual try-on request - identity preservation is critical."
        elif edit_type == "style_transfer":
            context_info += "\nThis is a style transfer request - be specific about artistic style."
        elif edit_type == "hair_styling":
            context_info += "\nThis is a hair styling request - MUST preserve all other features and only update hair."
        elif edit_type == "image_editing":
            context_info += "\nThis is an image editing request - be specific about what changes."
            
        hair_styling_requirements = ""
        if edit_type == "hair_styling" or (context and context.get("enhanced_workflow_type") == "hair_styling"):
            hair_styling_requirements = """
CRITICAL HAIR STYLING REQUIREMENTS:
- MUST include "Maintain all other features. Only update the hair style."
- Preserve face, eyes, nose, mouth, skin tone, facial structure
- Keep clothing, background, and pose exactly the same
- Only modify hair color, cut, length, or texture
"""
            
        return f"""You are an expert at optimizing prompts for Flux Kontext Max image editing.

{flux_guidelines}

TASK: Enhance this user prompt to follow Flux Kontext Max best practices.

Original prompt: "{original_prompt}"
Edit type: {edit_type}{context_info}{hair_styling_requirements}

REQUIREMENTS:
- Make the prompt more specific and detailed
- Follow Flux Kontext Max guidelines above
- Keep the core intent unchanged
- Add clarity without changing meaning
- Be concise but descriptive
- If editing a person, emphasize identity preservation
- For hair styling: MUST include feature preservation instructions

Return ONLY the enhanced prompt, nothing else."""

    async def _call_claude(self, prompt: str) -> str:
        """Call Claude through Replicate (using correct API format)"""
        
        def sync_call():
            try:
                result_text = ""
                for event in replicate.stream(
                    self.model,
                    input={
                        "prompt": prompt
                    }
                ):
                    result_text += str(event)
                
                # Clean up common Claude response patterns
                result = result_text.strip().replace('"', '').strip()
                
                return result
                
            except Exception as e:
                logger.error(f"Claude API call failed: {e}")
                raise
        
        return await asyncio.to_thread(sync_call)

# Global instance
prompt_enhancer = PromptEnhancer() 