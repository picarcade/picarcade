# app/services/generators/replicate.py
import replicate
import os
import asyncio
import time
from typing import Dict, Any
from app.services.generators.base import BaseGenerator
from app.models.generation import GenerationResponse
from app.core.config import settings
from ..prompt_enhancer import prompt_enhancer
import re

class ReplicateGenerator(BaseGenerator):
    """Replicate generator implementation"""
    
    def __init__(self):
        super().__init__(settings.replicate_api_token)
        print("Replicate API Key loaded in generator:", self.api_key)  # DEBUG PRINT
        if self.api_key:
            replicate.api_token = self.api_key
        
        # Set the API token immediately when initializing
        if settings.replicate_api_token:
            replicate.api_token = settings.replicate_api_token
            os.environ["REPLICATE_API_TOKEN"] = settings.replicate_api_token
            print(f"Replicate API Key loaded in generator: {settings.replicate_api_token}")
            
            # Debug: Verify the token is actually set
            print(f"[DEBUG REPLICATE] replicate.api_token after setting: {replicate.api_token}")
            print(f"[DEBUG REPLICATE] os.environ REPLICATE_API_TOKEN: {os.environ.get('REPLICATE_API_TOKEN', 'NOT_SET')}")
            print(f"[DEBUG REPLICATE] settings.replicate_api_token: {settings.replicate_api_token}")
        else:
            print("WARNING: No Replicate API token found in settings")
    
    def _extract_url(self, obj):
        if isinstance(obj, list):
            obj = obj[0]
        return getattr(obj, 'url', obj)
    
    @BaseGenerator._measure_time
    async def generate(self, 
                      prompt: str, 
                      parameters: Dict[str, Any],
                      generation_id: str = None) -> GenerationResponse:
        """Generate using Replicate API"""
        
        # Use provided generation_id or create new one
        if not generation_id:
            generation_id = self._create_generation_id()
        start_time = time.time()
        
        model_name = parameters.get("model", "flux-1.1-pro")
        
        # Double-check token is set before making API call
        if not settings.replicate_api_token:
            error_msg = "Replicate API token not configured"
            execution_time = time.time() - start_time
            
            # Log failed attempt
            self._log_generation_attempt(
                generation_id=generation_id,
                model_used=model_name,
                parameters=parameters,
                success=False,
                execution_time=execution_time,
                error_message=error_msg
            )
            
            return GenerationResponse(
                success=False,
                generation_id=generation_id,
                error_message=error_msg,
                model_used=model_name
            )
        
        try:
            if model_name.startswith("flux-kontext-apps/"):
                # Specialized flux-kontext-apps models (multi-image, change-haircut, etc.)
                result = await self._generate_flux_kontext_apps(prompt, parameters)
            elif model_name == "black-forest-labs/flux-kontext-max":
                # Official Flux Kontext Max model
                result = await self._generate_flux_kontext_max(prompt, parameters)
            elif model_name == "flux-kontext" or "flux-kontext" in model_name:
                # Generic flux-kontext models
                result = await self._generate_flux_kontext_max(prompt, parameters)
            elif "flux" in model_name:
                result = await self._generate_flux(prompt, parameters)
            elif "google/veo" in model_name or "runway" in model_name or "minimax/video" in model_name:
                result = await self._generate_video(prompt, parameters)
            else:
                result = await self._generate_other(prompt, parameters)
            
            execution_time = time.time() - start_time
            
            # Log successful attempt
            self._log_generation_attempt(
                generation_id=generation_id,
                model_used=model_name,
                parameters=parameters,
                success=True,
                execution_time=execution_time
            )
            
            response = GenerationResponse(
                success=True,
                generation_id=generation_id,
                output_url=result.get("output_url"),
                model_used=model_name,
                execution_time=execution_time,
                metadata=result.get("metadata", {})
            )
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            # Log failed attempt
            self._log_generation_attempt(
                generation_id=generation_id,
                model_used=model_name,
                parameters=parameters,
                success=False,
                execution_time=execution_time,
                error_message=error_msg
            )
            
            return GenerationResponse(
                success=False,
                generation_id=generation_id,
                error_message=error_msg,
                model_used=model_name,
                execution_time=execution_time
            )
    
    async def _generate_flux_kontext_max(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image using official Flux Kontext Max for advanced image editing"""
        
        model_version = "black-forest-labs/flux-kontext-max"
        
        # Extract uploaded image from parameters
        image_url = parameters.get("image", parameters.get("uploaded_image"))
        
        print(f"[DEBUG] flux-kontext-max received parameters: {list(parameters.keys())}")
        print(f"[DEBUG] Looking for image in parameters...")
        print(f"[DEBUG] parameters.get('image'): {parameters.get('image')}")
        print(f"[DEBUG] parameters.get('uploaded_image'): {parameters.get('uploaded_image')}")
        print(f"[DEBUG] Final image_url: {image_url}")
        
        if not image_url:
            print(f"[ERROR] flux-kontext-max requires an input image for editing")
            print(f"[ERROR] Available parameters: {parameters}")
            raise ValueError("flux-kontext-max requires an input image for editing")
        
        # Determine edit type from parameters for better enhancement
        edit_type = "image_editing"  # Default
        if "style" in prompt.lower() or "painting" in prompt.lower() or "artistic" in prompt.lower():
            edit_type = "style_transfer"
        elif "wear" in prompt.lower() or "try on" in prompt.lower() or "put" in prompt.lower():
            edit_type = "reference_styling"
        elif parameters.get("enhanced_workflow_type") == "hair_styling" or "hair" in prompt.lower():
            edit_type = "hair_styling"
        
        # Apply AI-powered Flux Kontext Max prompt enhancement
        enhanced_prompt = await prompt_enhancer.enhance_flux_kontext_prompt(
            original_prompt=prompt,
            edit_type=edit_type,
            has_working_image=bool(image_url),
            context=parameters
        )
        
        # For hair styling with kontext-max, ensure feature preservation is explicit
        if edit_type == "hair_styling":
            # Check if there are uploaded images that should be referenced
            uploaded_images = parameters.get("uploaded_images", [])
            if uploaded_images and len(uploaded_images) > 0:
                # Replace generic references with specific reference to uploaded image
                enhanced_prompt = enhanced_prompt.replace("[specific hair style/color]", "the same style as the reference image")
                enhanced_prompt = enhanced_prompt.replace("to [X]", "to the same style as the reference image")
                if "reference image" not in enhanced_prompt.lower():
                    enhanced_prompt = enhanced_prompt.replace("hair to", "hair to the same style as the reference image")
            
            if "maintain all other features" not in enhanced_prompt.lower():
                enhanced_prompt += ". Maintain all other features. Only update the hair style."
        
        def sync_call():
            
            # Use correct parameter names for official API
            inputs = {
                "prompt": enhanced_prompt,
                "input_image": image_url,  # Official API uses 'input_image'
                "output_format": parameters.get("output_format", "jpg")
            }
            
            print(f"[DEBUG] Sending to flux-kontext-max:")
            print(f"[DEBUG]   Original prompt: '{prompt}'")
            print(f"[DEBUG]   Enhanced prompt: '{enhanced_prompt}'")
            print(f"[DEBUG]   Input image: '{image_url}'")
            
            output = replicate.run(model_version, input=inputs)
            return {
                "output_url": self._extract_url(output) if output else None,
                "metadata": {
                    "model_version": model_version, 
                    "inputs": inputs, 
                    "original_prompt": prompt,
                    "enhanced_prompt": enhanced_prompt
                }
            }
        
        return await asyncio.to_thread(sync_call)
    


    async def _generate_flux_kontext_apps(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image using Flux Kontext Apps models on Replicate for specialized tasks"""
        def sync_call():
            # Get the actual model name from parameters, fallback to basic flux-kontext
            model_version = parameters.get("model", "black-forest-labs/flux-kontext-pro")
            
            print(f"[DEBUG] _generate_flux_kontext_apps routing:")
            print(f"[DEBUG]   model_version: '{model_version}'")
            print(f"[DEBUG]   model_version == 'flux-kontext-apps/multi-image-list': {model_version == 'flux-kontext-apps/multi-image-list'}")
            
            # Handle specific flux-kontext-apps models
            if model_version == "flux-kontext-apps/multi-image-list":
                # Multi-image model for virtual try-on and hair styling with references
                print(f"[DEBUG] Routing to _call_multi_image_list")
                return self._call_multi_image_list(prompt, parameters)
            elif model_version == "flux-kontext-apps/multi-image-kontext-max":
                # New model for adding elements to scenes
                print(f"[DEBUG] Routing to _call_multi_image_kontext_max")
                return self._call_multi_image_kontext_max(prompt, parameters)
            elif model_version == "flux-kontext-apps/multi-image-kontext-pro":
                # Legacy model - redirect to multi-image-kontext-max
                print(f"[DEBUG] Routing to _call_multi_image_kontext_max (legacy redirect)")
                return self._call_multi_image_kontext_max(prompt, parameters)
            elif model_version == "flux-kontext-apps/change-haircut":
                # Hair styling model
                print(f"[DEBUG] Routing to _call_change_haircut")
                return self._call_change_haircut(prompt, parameters)
            elif model_version.startswith("flux-kontext-apps/"):
                # Other flux-kontext-apps models
                print(f"[DEBUG] Routing to _call_generic_flux_kontext_app")
                return self._call_generic_flux_kontext_app(prompt, parameters, model_version)
            else:
                # Fallback to original flux-kontext behavior
                print(f"[DEBUG] Routing to _call_basic_flux_kontext")
                return self._call_basic_flux_kontext(prompt, parameters)
        
        return await asyncio.to_thread(sync_call)
    
    def _call_multi_image_list(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call the multi-image-list model for virtual try-on and identity preservation"""
        model_version = "flux-kontext-apps/multi-image-list"
        
        # Extract images from parameters
        primary_image = parameters.get("image", parameters.get("uploaded_image"))
        reference_image = parameters.get("reference_image")  # Clothing reference for virtual try-on
        uploaded_images = parameters.get("uploaded_images", [])  # Additional uploaded images
        
        # For hair styling, the uploaded images are the hair style references
        if parameters.get("enhanced_workflow_type") == "hair_styling" and uploaded_images:
            # Hair styling: working image + uploaded hair reference
            reference_image = uploaded_images[0]  # First uploaded image is the hair reference
        
        # Clean up URLs by removing trailing query parameters if empty
        if primary_image and primary_image.endswith('?'):
            primary_image = primary_image.rstrip('?')
        if reference_image and reference_image.endswith('?'):
            reference_image = reference_image.rstrip('?')
        
        print(f"[DEBUG] multi-image-list received parameters: {list(parameters.keys())}")
        print(f"[DEBUG] Looking for images in parameters...")
        print(f"[DEBUG] parameters.get('image'): {parameters.get('image')}")
        print(f"[DEBUG] parameters.get('uploaded_image'): {parameters.get('uploaded_image')}")
        print(f"[DEBUG] parameters.get('reference_image'): {parameters.get('reference_image')}")
        print(f"[DEBUG] parameters.get('uploaded_images'): {parameters.get('uploaded_images')}")
        print(f"[DEBUG] enhanced_workflow_type: {parameters.get('enhanced_workflow_type')}")
        print(f"[DEBUG] Primary image (person): {primary_image}")
        print(f"[DEBUG] Reference image (styling): {reference_image}")
        
        if not primary_image:
            print(f"[ERROR] multi-image-list requires a primary image (person)")
            print(f"[ERROR] Available parameters: {parameters}")
            raise ValueError("multi-image-list requires a primary image (person)")
        
        # Enhanced prompt based on enhanced AI intent classification (if available) or fallback to keywords
        prompt_lower = prompt.lower()
        
        # Check if this is a virtual try-on scenario (has reference image)
        is_virtual_tryon = bool(reference_image)
        
        # Use enhanced intent if available, otherwise fall back to keyword detection
        enhanced_workflow_type = parameters.get("enhanced_workflow_type")
        enhanced_reasoning = parameters.get("enhanced_reasoning")
        enhanced_confidence = parameters.get("enhanced_confidence")
        
        if enhanced_reasoning and enhanced_workflow_type:
            # Use AI classification reasoning to determine operation type
            reasoning_lower = enhanced_reasoning.lower()
            print(f"[DEBUG] Using enhanced AI intent classification: {enhanced_workflow_type}")
            print(f"[DEBUG] AI reasoning: {enhanced_reasoning}")
            print(f"[DEBUG] AI confidence: {enhanced_confidence}")
            
            # AI-based classification
            is_face_swap = ("face" in reasoning_lower and ("replace" in reasoning_lower or "swap" in reasoning_lower)) or "face swap" in reasoning_lower
            is_pose_change = "pose" in reasoning_lower or "position" in reasoning_lower or "turn" in reasoning_lower
            is_outfit_change = enhanced_workflow_type == "reference_styling" and not is_face_swap
        else:
            # Fallback to keyword detection for backward compatibility
            print(f"[DEBUG] Falling back to keyword-based classification")
            face_swap_keywords = ["replace", "swap", "change face", "face with", "his face", "her face", "replace face"]
            pose_keywords = ["look", "turn", "position", "pose", "angle", "direction", "camera", "face camera", "look at"]
            outfit_keywords = ["wear", "put", "try on", "dress", "outfit", "clothes", "shirt", "pants", "tshirt", "t-shirt", "in this"]
            
            is_face_swap = any(keyword in prompt_lower for keyword in face_swap_keywords)
            is_pose_change = any(keyword in prompt_lower for keyword in pose_keywords) and not is_face_swap
            is_outfit_change = any(keyword in prompt_lower for keyword in outfit_keywords)
        
        if is_virtual_tryon and is_face_swap:
            # Face swap - replace face from reference image
            enhanced_prompt = f"Using the first image as the base person and the second image as the face reference: Replace the face from the first image with the face from the second image. Keep the same body position, clothing, and background from the first image but use the facial features from the second image. Face swap transformation."
        elif is_virtual_tryon and is_outfit_change:
            # Virtual try-on with reference clothing - use prompt format for multi-image-list
            enhanced_prompt = f"Put the person from the first image in the clothing from the second image. Keep the clothing item exactly as it appears in the second image - same color, pattern, style, fit, and details. Do not alter the appearance of the clothing."
        elif is_pose_change and not is_outfit_change:
            # Pose/position modification - emphasize identity preservation
            enhanced_prompt = f"Same person, {prompt}, maintaining exact same facial features, body shape, and physical characteristics"
        elif is_outfit_change:
            # Generic outfit modification - allow more change but preserve person
            enhanced_prompt = f"Person wearing {prompt}, maintaining same facial features and body proportions, same person"
        else:
            # General modification - balanced approach
            enhanced_prompt = f"Same person, {prompt}, maintaining facial features and identity"
        
        # Check if this is hair styling to add feature preservation
        is_hair_styling = parameters.get("enhanced_workflow_type") == "hair_styling"
        
        # For hair styling, enhance the prompt to preserve features
        if is_hair_styling:
            if "maintain all other features" not in enhanced_prompt.lower():
                enhanced_prompt += ". Maintain all other features. Only update the hair style."
        
        # Build inputs based on the multi-image-list model schema
        input_images = [primary_image]  # Always include primary image (person)
        
        # Add reference image if available (for virtual try-on)
        if reference_image:
            input_images.append(reference_image)  # Add clothing reference
        
        inputs = {
            "prompt": enhanced_prompt,
            "input_images": input_images,  # Array of input images for multi-image-list
            "output_format": parameters.get("output_format", "png"),  # Schema default is png
            "aspect_ratio": parameters.get("aspect_ratio", "match_input_image"),  # Match input image aspect ratio
            "safety_tolerance": parameters.get("safety_tolerance", 2)  # Maximum permissive setting
        }
        
        print(f"[DEBUG] Sending to multi-image-list:")
        print(f"[DEBUG]   Original prompt: '{prompt}'")
        print(f"[DEBUG]   Enhanced prompt: '{enhanced_prompt}'")
        print(f"[DEBUG]   Number of input images: {len(input_images)}")
        print(f"[DEBUG]   Input images: {input_images}")
        print(f"[DEBUG]   Classification results:")
        print(f"[DEBUG]     is_face_swap: {is_face_swap}")
        print(f"[DEBUG]     is_pose_change: {is_pose_change}")
        print(f"[DEBUG]     is_outfit_change: {is_outfit_change}")
        print(f"[DEBUG]     enhanced_workflow_type: {enhanced_workflow_type}")
        print(f"[DEBUG]   Aspect ratio: {inputs['aspect_ratio']}")
        print(f"[DEBUG] FULL INPUTS TO REPLICATE MODEL:")
        print(f"[DEBUG]   Model: {model_version}")
        print(f"[DEBUG]   Inputs: {inputs}")
        
        output = replicate.run(model_version, input=inputs)
        return {
            "output_url": self._extract_url(output) if output else None,
            "metadata": {
                "model_version": model_version, 
                "inputs": inputs, 
                "enhanced_prompt": enhanced_prompt,
                "modification_type": "face_swap" if is_face_swap else ("virtual_tryon" if is_virtual_tryon and is_outfit_change else ("pose_change" if is_pose_change else "outfit_change" if is_outfit_change else "general")),
                "has_reference_image": bool(reference_image)
            }
        }
    
    def _call_multi_image_kontext_max(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call the multi-image-kontext-max model for adding elements to scenes"""
        model_version = "flux-kontext-apps/multi-image-kontext-max"
        
        # Extract images from parameters
        scene_image = parameters.get("image", parameters.get("uploaded_image"))  # Scene/environment
        person_image = None
        uploaded_images = parameters.get("uploaded_images", [])
        
        # Get the element to add from reference_images in parameters
        reference_images = parameters.get("reference_images", [])
        
        print(f"[DEBUG] multi-image-kontext-max received parameters: {list(parameters.keys())}")
        print(f"[DEBUG] Scene image (primary): {scene_image}")
        print(f"[DEBUG] Reference images available: {len(reference_images)}")
        
        # Find the person to add (not the working_image)
        for ref in reference_images:
            if isinstance(ref, dict):
                tag = ref.get("tag", "")
                url = ref.get("url", ref.get("uri", ""))
                print(f"[DEBUG] Checking reference: tag='{tag}', url='{url[:50]}...'")
                
                # Skip the working_image reference - we want to add other elements TO the working image
                if tag != "working_image" and url:
                    person_image = url
                    print(f"[DEBUG] Selected person to add: {tag} -> {url}")
                    break
        
        # Fallback: try uploaded images if no reference found
        if not person_image and uploaded_images and len(uploaded_images) > 0:
            person_image = uploaded_images[0]  # Element to add to scene
            print(f"[DEBUG] Using uploaded image as person: {person_image}")
        elif not person_image and parameters.get("reference_image"):
            person_image = parameters.get("reference_image")
            print(f"[DEBUG] Using reference_image parameter: {person_image}")
        
        # Clean up URLs by removing trailing query parameters if empty
        if scene_image and scene_image.endswith('?'):
            scene_image = scene_image.rstrip('?')
        if person_image and person_image.endswith('?'):
            person_image = person_image.rstrip('?')
        
        print(f"[DEBUG] Final scene image: {scene_image}")
        print(f"[DEBUG] Final person image: {person_image}")
        
        if not scene_image:
            print(f"[ERROR] multi-image-kontext-max requires a scene image")
            print(f"[ERROR] Available parameters: {parameters}")
            raise ValueError("multi-image-kontext-max requires a scene image")
        
        if not person_image:
            print(f"[ERROR] multi-image-kontext-max requires a person to add")
            print(f"[ERROR] Available parameters: {parameters}")
            print(f"[ERROR] Reference images found: {reference_images}")
            raise ValueError("multi-image-kontext-max requires a person to add")
        
        # Create a simple, clear prompt following the user's example style
        prompt_lower = prompt.lower()
        
        print(f"[DEBUG] PROMPT PARSING START:")
        print(f"[DEBUG]   Original prompt: '{prompt}'")
        print(f"[DEBUG]   Lowercase prompt: '{prompt_lower}'")
        
        # Extract person identity
        person_name = "the person"
        if "finley" in prompt_lower:
            person_name = "Finley"
        print(f"[DEBUG]   Extracted person_name: '{person_name}'")
        
        # Extract activity/action
        activity = ""
        if "skating" in prompt_lower:
            activity = " skating"
        elif "walking" in prompt_lower:
            activity = " walking"
        elif "running" in prompt_lower:
            activity = " running"
        elif "standing" in prompt_lower:
            activity = " standing"
        print(f"[DEBUG]   Extracted activity: '{activity}'")
        
        # Extract interaction context - fix the regex to find the main subject interaction
        interaction = ""
        
        # Look for key interaction patterns first
        if "cheetah" in prompt_lower:
            if "with" in prompt_lower and "cheetah" in prompt_lower:
                interaction = " with the cheetah"
            elif "alongside" in prompt_lower and "cheetah" in prompt_lower:
                interaction = " with the cheetah"
            else:
                interaction = " with the cheetah"
        elif "with" in prompt_lower:
            # Generic "with" parsing as fallback
            import re
            # Look for "with [something]" but exclude technical terms
            with_match = re.search(r'with (?:a |the )?(?!consistent|natural|lighting|scale|perspective)([^.,\s]+(?:\s+[^.,\s]+)*)', prompt_lower)
            if with_match:
                interaction = f" with {with_match.group(1).strip()}"
        
        print(f"[DEBUG]   Extracted interaction: '{interaction}'")
        
        # Create simple, effective prompt like the user's example
        enhanced_prompt = f"Put {person_name} into the scene{activity}{interaction}"
        
        print(f"[DEBUG] PROMPT PARSING END:")
        print(f"[DEBUG]   Final enhanced prompt: '{enhanced_prompt}'")
        print(f"[DEBUG]   Length check - original: {len(prompt)}, enhanced: {len(enhanced_prompt)}")
        
        # Build inputs for the multi-image-kontext-max model
        # Based on user's example, input_image_1 should be the person, input_image_2 should be the scene
        inputs = {
            "prompt": enhanced_prompt,
            "aspect_ratio": parameters.get("aspect_ratio", "16:9"),  # Better for preserving faces
            "input_image_1": person_image,  # The person (like "woman" in user's example)
            "input_image_2": scene_image,   # The scene (like "white t-shirt" in user's example)
            "output_format": parameters.get("output_format", "png"),
            "safety_tolerance": parameters.get("safety_tolerance", 2)
        }
        
        print(f"[DEBUG] Sending to multi-image-kontext-max:")
        print(f"[DEBUG]   Original prompt: '{prompt}'")
        print(f"[DEBUG]   Enhanced prompt: '{enhanced_prompt}'")
        print(f"[DEBUG]   Person image (input_image_1): '{person_image}'")
        print(f"[DEBUG]   Scene image (input_image_2): '{scene_image}'")
        print(f"[DEBUG] FULL INPUTS TO REPLICATE MODEL:")
        print(f"[DEBUG]   Model: {model_version}")
        print(f"[DEBUG]   Inputs: {inputs}")
        
        output = replicate.run(model_version, input=inputs)
        return {
            "output_url": self._extract_url(output) if output else None,
            "metadata": {
                "model_version": model_version, 
                "inputs": inputs, 
                "enhanced_prompt": enhanced_prompt,
                "modification_type": "add_person_to_scene",
                "person_image": person_image,
                "scene_image": scene_image
            }
        }
    
    def _call_change_haircut(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call the change-haircut model for hair styling"""
        model_version = "flux-kontext-apps/change-haircut"
        
        image_url = parameters.get("image", parameters.get("uploaded_image"))
        
        if not image_url:
            raise ValueError("change-haircut requires an input image")
        
        inputs = {
            "prompt": prompt,
            "image": image_url,
            "output_format": parameters.get("output_format", "jpg")
        }
        
        print(f"[DEBUG] Sending to change-haircut: prompt='{prompt}', input_image='{image_url}'")
        
        output = replicate.run(model_version, input=inputs)
        return {
            "output_url": self._extract_url(output) if output else None,
            "metadata": {"model_version": model_version, "inputs": inputs}
        }
    
    def _call_generic_flux_kontext_app(self, prompt: str, parameters: Dict[str, Any], model_version: str) -> Dict[str, Any]:
        """Call other flux-kontext-apps models with generic parameters"""
        image_url = parameters.get("image", parameters.get("uploaded_image"))
        
        if not image_url:
            raise ValueError(f"{model_version} requires an input image")
        
        inputs = {
            "prompt": prompt,
            "image": image_url,
            "output_format": parameters.get("output_format", "jpg")
        }
        
        print(f"[DEBUG] Sending to {model_version}: prompt='{prompt}', input_image='{image_url}'")
        
        output = replicate.run(model_version, input=inputs)
        return {
            "output_url": self._extract_url(output) if output else None,
            "metadata": {"model_version": model_version, "inputs": inputs}
        }
    
    def _call_basic_flux_kontext(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call basic flux-kontext-pro for backward compatibility"""
        model_version = "black-forest-labs/flux-kontext-pro"
        
        image_url = parameters.get("image", parameters.get("uploaded_image"))
        
        if not image_url:
            raise ValueError("flux-kontext requires an input image for editing")
        
        inputs = {
            "prompt": prompt,
            "input_image": image_url,
            "output_format": parameters.get("output_format", "jpg")
        }
        
        print(f"[DEBUG] Sending to flux-kontext-pro: prompt='{prompt}', input_image='{image_url}'")
        
        output = replicate.run(model_version, input=inputs)
        return {
            "output_url": self._extract_url(output) if output else None,
            "metadata": {"model_version": model_version, "inputs": inputs}
        }

    async def _generate_flux_kontext(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image using Flux Kontext Pro for image editing on Replicate"""
        def sync_call():
            model_version = "black-forest-labs/flux-kontext-pro"
            
            # Extract uploaded image from parameters (should be passed from API)
            image_url = parameters.get("image", parameters.get("uploaded_image"))
            
            print(f"[DEBUG] flux-kontext generator received parameters: {list(parameters.keys())}")
            print(f"[DEBUG] Looking for image in parameters...")
            print(f"[DEBUG] parameters.get('image'): {parameters.get('image')}")
            print(f"[DEBUG] parameters.get('uploaded_image'): {parameters.get('uploaded_image')}")
            print(f"[DEBUG] Final image_url: {image_url}")
            
            if not image_url:
                print(f"[ERROR] flux-kontext requires an input image for editing")
                print(f"[ERROR] Available parameters: {parameters}")
                raise ValueError("flux-kontext requires an input image for editing")
            
            inputs = {
                "prompt": prompt,
                "input_image": image_url,  # The uploaded/working image to edit
                "output_format": parameters.get("output_format", "jpg")
            }
            
            print(f"[DEBUG] Sending to flux-kontext: prompt='{prompt}', input_image='{image_url}'")
            
            output = replicate.run(model_version, input=inputs)
            return {
                "output_url": self._extract_url(output) if output else None,
                "metadata": {"model_version": model_version, "inputs": inputs}
            }
        return await asyncio.to_thread(sync_call)

    async def _generate_virtual_tryon(self, prompt: str, parameters: Dict[str, Any], generation_id: str = None) -> Dict[str, Any]:
        """Generate virtual try-on using specialized models on Replicate"""
        def sync_call():
            model_version = parameters.get("model", "cuuupid/outfit-anyone:38b72dfe69c51c1ab0e42e6b56d94c1cee8c2b4a3ac4da58c86e00ecb006c970")
            
            inputs = {
                "human_img": parameters.get("human_img"),
                "garm_img": parameters.get("garm_img"),
                "garment_des": parameters.get("garment_des", "A clothing item for virtual try-on")
            }
            
            print(f"[DEBUG] Virtual try-on model: {model_version}")
            print(f"[DEBUG] Inputs: {inputs}")
            
            if not inputs["human_img"] or not inputs["garm_img"]:
                raise ValueError("Both human_img and garm_img are required for virtual try-on")
            
            output = replicate.run(model_version, input=inputs)
            return {
                "output_url": self._extract_url(output) if output else None,
                "metadata": {"model_version": model_version, "inputs": inputs}
            }
        return await asyncio.to_thread(sync_call)

    async def _generate_flux(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image using a Flux model on Replicate (official schema)"""
        def sync_call():
            model_version = "black-forest-labs/flux-1.1-pro" if parameters.get("model") == "flux-1.1-pro" else "black-forest-labs/flux-1.1-pro-ultra"
            
            # Debug: Check token status right before API call
            print(f"[DEBUG REPLICATE] About to make API call:")
            print(f"[DEBUG REPLICATE]   replicate.api_token: {replicate.api_token}")
            print(f"[DEBUG REPLICATE]   os.environ REPLICATE_API_TOKEN: {os.environ.get('REPLICATE_API_TOKEN', 'NOT_SET')}")
            print(f"[DEBUG REPLICATE]   model_version: {model_version}")
            
            # Some Flux models only accept jpg/png, not webp
            output_format = parameters.get("output_format", "jpg")
            if output_format not in ["jpg", "png"]:
                output_format = "jpg"  # Default to jpg if unsupported format
                
            inputs = {
                "prompt": prompt,
                "aspect_ratio": parameters.get("aspect_ratio", "1:1"),
                "output_format": output_format,
                "output_quality": parameters.get("output_quality", 80),
                "safety_tolerance": parameters.get("safety_tolerance", 2),
                "prompt_upsampling": parameters.get("prompt_upsampling", True)
            }
            
            print(f"[DEBUG REPLICATE] Making replicate.run() call with inputs: {inputs}")
            
            try:
                output = replicate.run(model_version, input=inputs)
                print(f"[DEBUG REPLICATE] ✅ API call successful, output type: {type(output)}")
            except Exception as e:
                print(f"[DEBUG REPLICATE] ❌ API call failed:")
                print(f"[DEBUG REPLICATE]   Error type: {type(e).__name__}")
                print(f"[DEBUG REPLICATE]   Error message: {str(e)}")
                print(f"[DEBUG REPLICATE]   Token at time of error: {replicate.api_token}")
                print(f"[DEBUG REPLICATE]   ENV token at time of error: {os.environ.get('REPLICATE_API_TOKEN', 'NOT_SET')}")
                raise  # Re-raise the original error
            
            return {
                "output_url": self._extract_url(output) if output else None,
                "metadata": {"model_version": model_version, "inputs": inputs}
            }
        return await asyncio.to_thread(sync_call)
    
    async def _generate_video(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate video using video models on Replicate (google/veo-3, minimax/video-01)"""
        def sync_call():
            model_name = parameters.get("model", "google/veo-3")
            
            # Prepare inputs for video generation
            inputs = {
                "prompt": prompt,
            }
            
            # Add model-specific parameters based on actual API schema
            if "google/veo" in model_name:
                # Google Veo-3 on Replicate: {"prompt": string, "seed": integer (optional)}
                # Only supports text-to-video with audio
                seed = parameters.get("seed")
                if seed is not None:
                    inputs["seed"] = seed
                    
            elif "minimax/hailuo-02" in model_name:
                # MiniMax Hailuo-02: supports prompt, first_frame_image, duration, resolution, prompt_optimizer
                print(f"[DEBUG] Configuring Minimax Hailuo-02 with parameters: {list(parameters.keys())}")
                
                # Always include prompt_optimizer (default True for better results)
                inputs["prompt_optimizer"] = parameters.get("prompt_optimizer", True)
                print(f"[DEBUG] Hailuo-02 prompt_optimizer: {inputs['prompt_optimizer']}")
                
                # Add duration (6 or 10 seconds, default 6)
                duration = parameters.get("duration", 6)
                if duration in [6, 10]:
                    inputs["duration"] = duration
                    print(f"[DEBUG] Hailuo-02 duration: {duration}s")
                
                # Add resolution (768p or 1080p, default 1080p)
                resolution = parameters.get("resolution", "1080p")
                if resolution in ["768p", "1080p"]:
                    inputs["resolution"] = resolution
                    print(f"[DEBUG] Hailuo-02 resolution: {resolution}")
                    
                    # Note: 10 seconds is only available for 768p
                    if duration == 10 and resolution != "768p":
                        inputs["resolution"] = "768p"
                        print(f"[DEBUG] Hailuo-02 forcing 768p for 10s duration")
                
                # Add first frame image if provided (for image-to-video scenarios)
                first_frame = parameters.get("first_frame_image") or parameters.get("image") or parameters.get("uploaded_image")
                if first_frame:
                    inputs["first_frame_image"] = first_frame
                    print(f"[DEBUG] Hailuo-02 first_frame_image: {first_frame[:50] if len(first_frame) > 50 else first_frame}")
                    print(f"[DEBUG] This should trigger IMAGE-TO-VIDEO generation")
                    
            elif "runway" in model_name:
                # Legacy Runway parameters (if still needed)
                inputs.update({
                    "duration": parameters.get("duration", 5),
                    "ratio": parameters.get("ratio", "1280:720"),
                    "motion": parameters.get("motion", 3),
                })
            
            print(f"[DEBUG] Replicate video generation with model: {model_name}")
            print(f"[DEBUG] Video generation inputs: {inputs}")
            
            print(f"[DEBUG] About to call replicate.run() with model: {model_name}")
            print(f"[DEBUG] Replicate API key configured: {bool(self.api_key)}")
            print(f"[DEBUG] Replicate API key length: {len(self.api_key) if self.api_key else 0}")
            
            try:
                import time
                start_time = time.time()
                print(f"[DEBUG] Starting replicate.run() at {start_time}")
                
                # Use the simple replicate.run() approach which handles model names directly
                print(f"[DEBUG] Using replicate.run() for video generation...")
                print(f"[DEBUG] Model: {model_name}")
                print(f"[DEBUG] Inputs: {inputs}")
                
                # Call replicate.run() directly - this handles the async prediction internally
                output = replicate.run(model_name, input=inputs)
                
                end_time = time.time()
                duration = end_time - start_time
                print(f"[DEBUG] replicate.run() completed successfully in {duration:.2f} seconds")
                print(f"[DEBUG] Raw output type: {type(output)}")
                print(f"[DEBUG] Raw output content: {output}")
                    
            except Exception as e:
                print(f"[ERROR] Video generation failed: {str(e)}")
                print(f"[ERROR] Exception type: {type(e)}")
                import traceback
                print(f"[ERROR] Full traceback: {traceback.format_exc()}")
                raise
            
            # Extract the video URL - video models typically return direct URLs or lists
            print(f"[DEBUG] About to extract URL from output...")
            video_url = self._extract_url(output) if output else None
            print(f"[DEBUG] Extracted video URL: {video_url}")
            
            print(f"[DEBUG] Video generation completed successfully")
            
            return {
                "output_url": video_url,
                "metadata": {
                    "model_version": model_name, 
                    "inputs": inputs,
                    "generation_type": "video"
                }
            }
        return await asyncio.to_thread(sync_call)

    async def _generate_other(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate using other models on Replicate (e.g., DALL-E)"""
        def sync_call():
            model_version = parameters.get("model_version", "openai/dall-e-3")
            inputs = {
                "prompt": prompt,
                **{k: v for k, v in parameters.items() if k != "model"}
            }
            output = replicate.run(model_version, input=inputs)
            return {
                "output_url": self._extract_url(output) if output else None,
                "metadata": {"model_version": model_version, "inputs": inputs}
            }
        return await asyncio.to_thread(sync_call)