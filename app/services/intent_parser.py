import re
from typing import Dict, Any
from app.models.generation import CreativeIntent, IntentAnalysis
from app.core.logging import intent_logger

"""
Intent Decision Logic Enhancement:

Priority 1: Session Continuity (NEW!)
- If there's a current working image in the session → EDIT_IMAGE intent (confidence: 0.98)
- Enables conversational editing: "add hat" → "make it blue" → "change color"
- Each generated image becomes the new working image for the session

Priority 2: Image Upload Detection
- If user uploads new images → EDIT_IMAGE intent (confidence: 0.95) 
- Uses flux-kontext model for image editing
- Uploaded image becomes the new working image

Priority 3: Keyword-Based Detection (existing logic)
- Video keywords → GENERATE_VIDEO
- Edit keywords → EDIT_IMAGE  
- Enhance keywords → ENHANCE_IMAGE
- Default → GENERATE_IMAGE

Example conversation flow:
1. User uploads hat.jpg + "add sunglasses" → EDIT_IMAGE (flux-kontext) → outputs hat_with_sunglasses.jpg
2. User says "make it blue" → EDIT_IMAGE (flux-kontext using hat_with_sunglasses.jpg)
3. User says "add a background" → EDIT_IMAGE (flux-kontext using previous result)
4. User uploads new cat.jpg + "edit this" → EDIT_IMAGE (flux-kontext using cat.jpg - new session context)
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
        
        # Priority 1: If there's a current working image in the session, continue editing it
        # This enables conversational image editing (e.g., "add hat" → "make it blue")
        if current_working_image:
            intent = CreativeIntent.EDIT_IMAGE
            content_type = "image_edit"
            confidence = 0.98  # Very high confidence for session continuity
            
        # Priority 2: If user has uploaded new images, assume they want to edit/adjust them
        # This uses the flux-kontext model for image editing
        elif uploaded_images and len(uploaded_images) > 0:
            intent = CreativeIntent.EDIT_IMAGE
            content_type = "image_edit"
            confidence = 0.95  # High confidence since images were uploaded
            
        # Priority 3: Detect intent based on keywords
        elif any(keyword in prompt_lower for keyword in self.video_keywords):
            intent = CreativeIntent.GENERATE_VIDEO
            content_type = "video"
            confidence = 0.8
            
        elif any(keyword in prompt_lower for keyword in self.edit_keywords):
            intent = CreativeIntent.EDIT_IMAGE
            content_type = "image_edit"
            confidence = 0.7
            
        elif any(keyword in prompt_lower for keyword in self.enhance_keywords):
            intent = CreativeIntent.ENHANCE_IMAGE
            content_type = "image_enhancement" 
            confidence = 0.9
            
        else:
            # Default to image generation
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