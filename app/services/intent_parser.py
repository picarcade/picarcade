import re
from typing import Dict, Any
from app.models.generation import CreativeIntent, IntentAnalysis
from app.core.logging import intent_logger

"""
Intent Decision Logic (Fixed Priority Order):

Priority 1: Explicit Content Type Requests
- Video keywords ("video", "animation", "movie") → GENERATE_VIDEO (confidence: 0.9)
- Overrides session continuity to handle explicit requests correctly

Priority 2: Image Upload Detection  
- If user uploads new images → EDIT_IMAGE intent (confidence: 0.95)
- Uses flux-kontext model for image editing
- Uploaded image becomes the new working image

Priority 3: Session Continuity with Explicit Edit Intent
- Working image + explicit edit keywords → EDIT_IMAGE (confidence: 0.95)
- Examples: "edit it", "modify this", "change the color"

Priority 4: Session Continuity with Contextual Edit Intent
- Working image + contextual editing phrases → EDIT_IMAGE (confidence: 0.85)
- Examples: "make it blue", "add a hat", "turn it into"

Priority 5: General Keyword Detection
- Edit keywords without context → EDIT_IMAGE (confidence: 0.7)
- Enhance keywords → ENHANCE_IMAGE (confidence: 0.9)

Priority 6: Default Behavior
- No clear intent → GENERATE_IMAGE (confidence: 0.6)
- Even with working image, if no editing context is detected

Example conversation flow:
1. "Create a horse" → GENERATE_IMAGE
2. "Make a video of it galloping" → GENERATE_VIDEO (NOT edit, despite working image)
3. "Add a saddle to it" → EDIT_IMAGE (contextual editing)
4. "Make it blue" → EDIT_IMAGE (contextual editing)
"""

class BasicIntentParser:
    """
    Phase 1: Simple rule-based intent detection
    Will be replaced with AI-powered analysis in later phases
    """
    
    def __init__(self):
        self.video_keywords = [
            "video", "animation", "movie", "film", "motion", "animate", 
            "moving", "sequence", "clip", "footage"
        ]
        
        self.edit_keywords = [
            "edit", "modify", "change", "alter", "adjust", "fix", 
            "improve", "update", "remove", "add to", "put", "place",
            "add a", "add the", "give it", "make it", "turn it",
            "on it", "to it", "with", "without"
        ]
        
        self.enhance_keywords = [
            "enhance", "upscale", "improve quality", "make better", 
            "higher resolution", "sharper", "cleaner"
        ]
        
        self.audio_keywords = [
            "audio", "sound", "music", "voice", "narration", "speaking", 
            "talking", "dialogue", "soundtrack", "song", "singing",
            "tell us", "says", "excitedly telling", "shouts", "speaks",
            "announces", "whispers", "screams", "breaking news"
        ]
    
    async def analyze_intent(self, prompt: str, user_context: Dict[str, Any] = None, generation_id: str = None, uploaded_images: list = None, current_working_image: str = None) -> IntentAnalysis:
        """
        Analyze user prompt to determine creative intent
        
        Args:
            prompt: User's input prompt
            user_context: Additional context (future: from Mem0)
            generation_id: Unique generation ID for logging
            uploaded_images: List of uploaded image URLs (if any)
            current_working_image: URL of current working image in session (if any)
            
        Returns:
            IntentAnalysis with detected intent and metadata
        """
        
        prompt_lower = prompt.lower()
        
        # Priority 1: Explicit content type requests (video, animation, etc.) - these override session continuity
        if any(keyword in prompt_lower for keyword in self.video_keywords):
            intent = CreativeIntent.GENERATE_VIDEO
            # Check if audio is also requested
            has_audio_request = any(keyword in prompt_lower for keyword in self.audio_keywords)
            content_type = "video_with_audio" if has_audio_request else "video"
            confidence = 0.9  # High confidence for explicit video requests
            
        # Priority 2: If user has uploaded new images, assume they want to edit/adjust them
        elif uploaded_images and len(uploaded_images) > 0:
            intent = CreativeIntent.EDIT_IMAGE
            content_type = "image_edit"
            confidence = 0.95  # High confidence since images were uploaded
            
        # Priority 3: Session continuity - if there's a working image AND the prompt suggests editing
        elif current_working_image and any(keyword in prompt_lower for keyword in self.edit_keywords):
            intent = CreativeIntent.EDIT_IMAGE
            content_type = "image_edit"
            confidence = 0.95  # High confidence for explicit editing of working image
            
        # Priority 4: Session continuity - working image with ambiguous prompts that could be editing
        elif current_working_image and self._suggests_editing_context(prompt_lower):
            intent = CreativeIntent.EDIT_IMAGE
            content_type = "image_edit"
            confidence = 0.85  # Lower confidence for ambiguous cases
            
        # Priority 5: Other keyword-based detection
        elif any(keyword in prompt_lower for keyword in self.edit_keywords):
            intent = CreativeIntent.EDIT_IMAGE
            content_type = "image_edit"
            confidence = 0.7
            
        elif any(keyword in prompt_lower for keyword in self.enhance_keywords):
            intent = CreativeIntent.ENHANCE_IMAGE
            content_type = "image_enhancement" 
            confidence = 0.9
            
        else:
            # Default to image generation (even if there's a working image, if no editing context is detected)
            intent = CreativeIntent.GENERATE_IMAGE
            content_type = self._detect_image_type(prompt_lower)
            confidence = 0.6
        
        # Analyze complexity
        complexity = self._analyze_complexity(prompt)
        
        # Create result
        result = IntentAnalysis(
            detected_intent=intent,
            confidence=confidence,
            content_type=content_type,
            complexity_level=complexity,
            suggested_model=self._suggest_initial_model(intent, complexity)
        )
        
        # Log intent decision
        if generation_id:
            intent_logger.log_intent_decision(
                generation_id=generation_id,
                prompt=prompt,
                detected_intent=intent.value,
                confidence=confidence,
                content_type=content_type,
                complexity_level=complexity,
                suggested_model=result.suggested_model,
                has_uploaded_images=bool(uploaded_images and len(uploaded_images) > 0),
                uploaded_images_count=len(uploaded_images) if uploaded_images else 0,
                has_current_working_image=bool(current_working_image),
                current_working_image_url=current_working_image
            )
        
        return result
    
    def _detect_image_type(self, prompt_lower: str) -> str:
        """Detect what type of image user wants"""
        
        if any(word in prompt_lower for word in ["photo", "photograph", "realistic", "portrait"]):
            return "photograph"
        elif any(word in prompt_lower for word in ["art", "painting", "drawing", "illustration"]):
            return "artwork"
        elif any(word in prompt_lower for word in ["logo", "design", "graphic"]):
            return "design"
        else:
            return "general_image"
    
    def _analyze_complexity(self, prompt: str) -> str:
        """Basic complexity analysis based on prompt characteristics"""
        
        word_count = len(prompt.split())
        
        # Check for complex elements
        complex_indicators = [
            "multiple", "several", "many", "complex", "detailed", 
            "intricate", "elaborate", "sophisticated"
        ]
        
        has_complex_elements = any(indicator in prompt.lower() for indicator in complex_indicators)
        
        if word_count > 30 or has_complex_elements:
            return "complex"
        elif word_count > 15:
            return "moderate" 
        else:
            return "simple"
    
    def _suggests_editing_context(self, prompt_lower: str) -> bool:
        """
        Check if prompt suggests editing the current working image
        This catches conversational editing phrases that don't use explicit edit keywords
        """
        
        # Contextual editing phrases that suggest working with current image
        contextual_edit_indicators = [
            "make it", "turn it", "change it", "paint it", "color it",
            "add a", "add some", "add the", "put a", "put some", "put the",
            "give it", "give them", "give this", "remove the", "take away",
            "make this", "make that", "turn this", "turn that",
            "it should", "it needs", "this should", "this needs",
            "instead of", "but with", "but make", "except",
            "more", "less", "bigger", "smaller", "brighter", "darker",
            "different color", "another color", "new color"
        ]
        
        # Handle "and X" pattern - very common for adding items to existing images
        if prompt_lower.startswith("and "):
            return True
            
        # Handle "with X" pattern - another common way to add elements
        if prompt_lower.startswith("with "):
            return True
            
        # Handle other common conversational addition patterns
        addition_patterns = [
            "but ", "plus ", "also ", "wearing ", "holding ", "now with "
        ]
        if any(prompt_lower.startswith(pattern) for pattern in addition_patterns):
            return True
        
        # Pronouns and references that suggest working with existing content
        contextual_references = [
            "it ", "this ", "that ", "them ", "these ", "those ",
            "the image", "the picture", "the photo"
        ]
        
        # Check for contextual editing indicators
        if any(indicator in prompt_lower for indicator in contextual_edit_indicators):
            return True
            
        # Check for references to existing content combined with modification verbs
        modification_verbs = ["make", "change", "turn", "paint", "color", "add", "remove"]
        if any(ref in prompt_lower for ref in contextual_references):
            if any(verb in prompt_lower for verb in modification_verbs):
                return True
        
        return False

    def _suggest_initial_model(self, intent: CreativeIntent, complexity: str) -> str:
        """Basic model suggestion logic"""
        
        if intent == CreativeIntent.GENERATE_VIDEO:
            return "runway_gen4_turbo"
        elif intent == CreativeIntent.GENERATE_IMAGE:
            if complexity == "complex":
                return "flux-1.1-pro-ultra"
            else:
                return "flux-1.1-pro"
        elif intent == CreativeIntent.EDIT_IMAGE:
            return "flux-kontext"
        else:
            return "flux-1.1-pro" 