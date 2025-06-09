"""
Simplified Product Flow Service

Based on CSV rules:
1. User Prompts
2. App determines Active Image, Uploaded Image, Referenced Image boolean values 
3. LLM classifies intent and enhances prompt based on CSV rules
4. Routes to appropriate model per CSV

All prompt writing logic is in the LLM prompt itself.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import replicate

logger = logging.getLogger(__name__)


class PromptType(Enum):
    CREATE_NEW_IMAGE = "NEW_IMAGE"
    NEW_IMAGE_REF = "NEW_IMAGE_REF"
    EDIT_IMAGE = "EDIT_IMAGE" 
    EDIT_IMAGE_REF = "EDIT_IMAGE_REF"


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
        referenced_image: bool
    ):
        self.prompt_type = prompt_type
        self.enhanced_prompt = enhanced_prompt
        self.model_to_use = model_to_use
        self.original_prompt = original_prompt
        self.reasoning = reasoning
        self.active_image = active_image
        self.uploaded_image = uploaded_image
        self.referenced_image = referenced_image


class SimplifiedFlowService:
    """
    Simplified flow service that implements CSV logic in a single LLM call
    """
    
    def __init__(self):
        # Use Anthropic Claude 3.7 Sonnet via Replicate for prompt processing
        self.model = "anthropic/claude-3.7-sonnet"
        
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
    
    async def process_user_request(
        self, 
        user_prompt: str,
        active_image: bool = False,
        uploaded_image: bool = False, 
        referenced_image: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> SimplifiedFlowResult:
        """
        Process user request through simplified flow:
        1. Determine boolean flags (passed in)
        2. Use LLM to classify intent and enhance prompt based on CSV rules
        3. Route to appropriate model (with special rule for 2+ references → Runway)
        """
        
        try:
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
            
            # Determine prompt type based on CSV logic
            prompt_type, enhanced_prompt, reasoning = await self._classify_and_enhance(
                user_prompt, active_image, uploaded_image, referenced_image, context
            )
            
            # Map to model based on CSV (with special rule for 2+ references)
            model_to_use = self._get_model_for_type(prompt_type, total_references)
            
            return SimplifiedFlowResult(
                prompt_type=PromptType(prompt_type),
                enhanced_prompt=enhanced_prompt,
                model_to_use=model_to_use,
                original_prompt=user_prompt,
                reasoning=reasoning,
                active_image=active_image,
                uploaded_image=uploaded_image,
                referenced_image=referenced_image
            )
            
        except Exception as e:
            logger.error(f"Simplified flow processing failed: {e}")
            # Fallback to basic new image generation
            return SimplifiedFlowResult(
                prompt_type=PromptType.CREATE_NEW_IMAGE,
                enhanced_prompt=user_prompt,
                model_to_use="Flux 1.1 Pro",
                original_prompt=user_prompt,
                reasoning=f"Fallback due to error: {str(e)}",
                active_image=active_image,
                uploaded_image=uploaded_image,
                referenced_image=referenced_image
            )
    
    async def _classify_and_enhance(
        self, 
        user_prompt: str,
        active_image: bool,
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
2. uploaded_image: {uploaded_image} 
3. referenced_image: {referenced_image}

DO NOT try to detect images from the prompt - these flags tell you exactly what images are available!

CLASSIFICATION RULES (from CSV) - FOLLOW THESE EXACTLY:
1. If Active Image=NO, Uploaded Image=NO, Referenced Image=NO → Type: NEW_IMAGE, Model: Flux 1.1 Pro
2. If Active Image=YES, Uploaded Image=NO, Referenced Image=NO → Type: NEW_IMAGE, Model: Flux 1.1 Pro (no edit intent) or EDIT_IMAGE, Model: Kontext (edit intent)
3. If Active Image=NO, Uploaded Image=NO, Referenced Image=YES → Type: NEW_IMAGE_REF, Model: Kontext
4. If Active Image=NO, Uploaded Image=YES, Referenced Image=NO → Type: NEW_IMAGE_REF, Model: Kontext
5. If Active Image=YES, Uploaded Image=YES, Referenced Image=NO → Type: EDIT_IMAGE_REF, Model: Runway
6. If Active Image=YES, Uploaded Image=NO, Referenced Image=YES → Type: EDIT_IMAGE_REF, Model: Runway  
7. If Active Image=YES, Uploaded Image=YES, Referenced Image=YES → Type: EDIT_IMAGE_REF, Model: Runway

CRITICAL: When both Active Image=TRUE AND (Uploaded Image=TRUE OR Referenced Image=TRUE), it is ALWAYS EDIT_IMAGE_REF, regardless of edit keywords!

SPECIFIC EXAMPLE:
- If active_image=True, uploaded_image=True, referenced_image=False → ALWAYS classify as EDIT_IMAGE_REF
- User prompt: "Update hair style to this" with these flags → Type: EDIT_IMAGE_REF

EDIT INTENT KEYWORDS:
- "edit", "change", "modify", "adjust", "add", "remove", "make it", "turn it", "convert it", "transform it"
- "put on", "wear", "dress up", "style", "hair", "background", "color", "enhance", "improve"

PROMPT ENHANCEMENT RULES (from CSV):
1. NEW_IMAGE: No enhancement needed - use original prompt
2. NEW_IMAGE_REF: Understand intent and make minor edits to improve clarity. Add: "Maintain all other aspects of the original image."
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
   - Examples:
     * "Update the hair to @blonde" (with working image) → "@working_image with the hairstyle from @blonde. Maintain all other features. Only update the hair style."
     * "Change hair to desired style" (with working image + uploaded hair image) → "@working_image with the hairstyle from @reference_1. Maintain all other features. Only update the hair style."
     * "Put @dress on person" (with working image) → "Add clothing from @dress to @working_image"
     * "Change outfit" (with working image + uploaded clothing image) → "Add clothing from @reference_1 to @working_image"

Based on the CSV decision matrix - APPLY THESE RULES IN ORDER:
1. If active_image=True AND (uploaded_image=True OR referenced_image=True): prompt_type="EDIT_IMAGE_REF" 
2. If no images (all False): prompt_type="NEW_IMAGE"
3. If only uploaded_image=True OR only referenced_image=True: prompt_type="NEW_IMAGE_REF"
4. If only active_image=True: determine if user wants to edit (prompt_type="EDIT_IMAGE") or create new (prompt_type="NEW_IMAGE")

For prompt enhancement:
- NEW_IMAGE: Return original prompt unchanged
- NEW_IMAGE_REF, EDIT_IMAGE: Make minor clarity improvements and add "Maintain all other aspects of the original image."
- EDIT_IMAGE_REF: COMPLETELY REWRITE the prompt following the structured format - do not just enhance the original!

**CRITICAL FOR EDIT_IMAGE_REF: You must identify the TARGET and SOURCE from context and rewrite the prompt completely. Never just append or enhance - always restructure to the SIMPLE format: "Add [CHANGE] from @[SOURCE] to @[TARGET]"**

Return your analysis as JSON:
{{"prompt_type": "NEW_IMAGE|NEW_IMAGE_REF|EDIT_IMAGE|EDIT_IMAGE_REF", "enhanced_prompt": "the appropriately enhanced or rewritten prompt"}}

USER PROMPT TO ANALYZE: "{user_prompt}"

REFERENCE TAG RULES:
- active_image=True: Working image becomes @working_image
- uploaded_image=True: First uploaded image becomes @reference_1, second becomes @reference_2, etc.
- referenced_image=True: Named references in prompt keep their original names (e.g., @blonde, @dress)

CONTEXT FOR EDIT_IMAGE_REF:
- When active_image=True, there is a WORKING IMAGE that is the main subject being edited (this becomes @working_image)
- When referenced_image=True, there are @reference images mentioned in the prompt that provide styles/features to copy
- When uploaded_image=True, there are uploaded images that should be referenced as @reference_1, @reference_2, etc.
- For EDIT_IMAGE_REF: The WORKING IMAGE is the TARGET (what gets edited), @references are the SOURCE (what to copy from)
- Example: "Update hair to @blonde" with working image = TARGET is @working_image, SOURCE is @blonde reference
- CRITICAL: For uploaded images (not named references), always use @reference_1, @reference_2, etc. - NEVER use generic @reference
- NEVER use the @reference as both TARGET and SOURCE - always use @working_image as TARGET

TASK:
1. Classify the intent type based on the rules above
2. Enhance the prompt according to the enhancement rules
3. For EDIT_IMAGE_REF: Carefully analyze which @reference is the TARGET (subject being changed) vs SOURCE (providing the style/feature)
4. Provide reasoning for your classification and enhancement decisions

IMPORTANT FOR EDIT_IMAGE_REF:
- Always identify the main subject (TARGET) that is being edited
- Clearly specify what aspect is being changed (hair, clothing, pose, etc.)
- Structure the enhanced prompt to be unambiguous about what changes and what stays the same
- Use the SIMPLE format: "Add [aspect] from @[source] to @[target]"
- CRITICAL: If uploaded_image=True, use @reference_1 for the first uploaded image, @reference_2 for second, etc.
- NEVER use generic @reference - always use the specific numbered reference tags

Respond with ONLY valid JSON and no additional text:
{{
    "type": "NEW_IMAGE|NEW_IMAGE_REF|EDIT_IMAGE|EDIT_IMAGE_REF",
    "enhanced_prompt": "enhanced version of user prompt following CSV rules",
    "reasoning": "brief explanation of classification and enhancement decisions"
}}

IMPORTANT: Return ONLY the JSON object above. Do not add any extra analysis, explanations, or text after the JSON."""

        # Call Claude via Replicate
        def sync_call():
            try:
                result_text = ""
                for event in replicate.stream(
                    self.model,
                    input={
                        "prompt": classification_prompt,
                        "max_tokens": 1024,  # Claude 3.7 Sonnet requires minimum 1024 tokens
                        "temperature": 0.2  # Low temperature for consistent classification
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
            
            llm_type = result.get("type", "NEW_IMAGE")
            enhanced_prompt = result.get("enhanced_prompt", user_prompt)
            reasoning = result.get("reasoning", "LLM classification completed")
            
            # Safety check: Enforce CSV rules even if LLM gets it wrong
            correct_type = self._enforce_csv_rules(active_image, uploaded_image, referenced_image)
            if llm_type != correct_type:
                print(f"[WARNING] SIMPLIFIED: LLM classified as {llm_type} but CSV rules require {correct_type}. Correcting.")
                llm_type = correct_type
                reasoning += f" (Corrected from {result.get('type')} to {correct_type})"
                
                # If we corrected to EDIT_IMAGE_REF, ensure proper prompt format
                if correct_type == "EDIT_IMAGE_REF":
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
        
        # Simple rule-based classification following updated CSV
        if not active_image and not uploaded_image and not referenced_image:
            return ("NEW_IMAGE", user_prompt, "Fallback: No images detected")
        
        # New scenarios: NEW_IMAGE_REF for creating new images with references/uploads but no active image
        if not active_image and (uploaded_image or referenced_image):
            enhanced_prompt = user_prompt + ". Maintain all other aspects of the original image."
            return ("NEW_IMAGE_REF", enhanced_prompt, "Fallback: New image with references/uploads")
            
        # Check for edit keywords when active image is present
        edit_keywords = ["edit", "change", "modify", "adjust", "add", "remove", "make it", "turn it", "put on", "wear"]
        has_edit_intent = any(keyword in user_prompt.lower() for keyword in edit_keywords)
        
        if active_image and not uploaded_image and not referenced_image:
            if has_edit_intent:
                enhanced_prompt = user_prompt + ". Maintain all other aspects of the original image."
                return ("EDIT_IMAGE", enhanced_prompt, "Fallback: Edit intent detected")
            else:
                return ("NEW_IMAGE", user_prompt, "Fallback: New image intent")
        
        # Any reference images with active image = reference editing
        if active_image and (uploaded_image or referenced_image):
            # Use simple structured rewriting for EDIT_IMAGE_REF fallback
            if "hair" in user_prompt.lower():
                enhanced_prompt = f"@working_image with the hairstyle from @reference_1. Maintain all other features. Only update the hair style."
            elif "clothing" in user_prompt.lower() or "dress" in user_prompt.lower() or "wear" in user_prompt.lower() or "outfit" in user_prompt.lower():
                enhanced_prompt = f"Add clothing from @reference_1 to @working_image"
            elif "face" in user_prompt.lower():
                enhanced_prompt = f"Add face from @reference_1 to @working_image"
            else:
                enhanced_prompt = f"Add style from @reference_1 to @working_image"
            return ("EDIT_IMAGE_REF", enhanced_prompt, "Fallback: Reference editing with active image")
        
        return ("NEW_IMAGE", user_prompt, "Fallback: Default to new image")
    
    def _enforce_csv_rules(self, active_image: bool, uploaded_image: bool, referenced_image: bool) -> str:
        """
        Enforce CSV rules to determine the correct classification
        """
        # CSV rules in order:
        if not active_image and not uploaded_image and not referenced_image:
            return "NEW_IMAGE"
        if active_image and not uploaded_image and not referenced_image:
            return "EDIT_IMAGE"  # Default to edit for active image alone
        if not active_image and not uploaded_image and referenced_image:
            return "NEW_IMAGE_REF"
        if not active_image and uploaded_image and not referenced_image:
            return "NEW_IMAGE_REF"
        if active_image and uploaded_image and not referenced_image:
            return "EDIT_IMAGE_REF"
        if active_image and not uploaded_image and referenced_image:
            return "EDIT_IMAGE_REF"  # This should be our case!
        if active_image and uploaded_image and referenced_image:
            return "EDIT_IMAGE_REF"
        
        return "NEW_IMAGE"  # Default fallback
    
    def _get_model_for_type(self, prompt_type: str, total_references: int = 0) -> str:
        """
        Map prompt type to model based on CSV
        Special rule: 2+ reference images → Runway (regardless of original CSV mapping)
        """
        model_mapping = {
            "NEW_IMAGE": "black-forest-labs/flux-1.1-pro",
            "NEW_IMAGE_REF": "black-forest-labs/flux-kontext-max",  # New: Kontext for new images with references
            "EDIT_IMAGE": "black-forest-labs/flux-kontext-max", 
            "EDIT_IMAGE_REF": "runway_gen4_image"
        }
        
        # Special rule: 2+ reference images always go to Runway
        if total_references >= 2:
            print(f"[DEBUG] SIMPLIFIED: {total_references} reference images detected - routing to Runway instead of {model_mapping.get(prompt_type)}")
            return "runway_gen4_image"
        
        return model_mapping.get(prompt_type, "black-forest-labs/flux-1.1-pro")
    
    def get_model_parameters(self, result: SimplifiedFlowResult) -> Dict[str, Any]:
        """
        Get model-specific parameters based on the result
        """
        base_params = {
            "prompt": result.enhanced_prompt,
            "model": result.model_to_use
        }
        
        # Add model-specific parameters
        if result.model_to_use == "black-forest-labs/flux-kontext-max":
            base_params.update({
                "guidance_scale": 3.5,
                "num_inference_steps": 28,
                "safety_tolerance": 2
            })
        elif result.model_to_use == "black-forest-labs/flux-1.1-pro":
            base_params.update({
                "guidance_scale": 3.5,
                "num_inference_steps": 25,
                "safety_tolerance": 2
            })
        elif result.model_to_use == "runway_gen4_image":
            base_params.update({
                "guidance_scale": 7.5,
                "num_inference_steps": 50
            })
        
        return base_params


# Global instance
simplified_flow = SimplifiedFlowService() 