# app/services/generators/replicate.py
import replicate
import os
import asyncio
import time
from typing import Dict, Any
from app.services.generators.base import BaseGenerator
from app.models.generation import GenerationResponse
from app.core.config import settings

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
            if model_name == "flux-kontext":
                result = await self._generate_flux_kontext(prompt, parameters)
            elif "flux" in model_name:
                result = await self._generate_flux(prompt, parameters)
            elif "google/veo" in model_name or "runway" in model_name:
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
            inputs = {
                "prompt": prompt,
                "aspect_ratio": parameters.get("aspect_ratio", "1:1"),
                "output_format": parameters.get("output_format", "webp"),
                "output_quality": parameters.get("output_quality", 80),
                "safety_tolerance": parameters.get("safety_tolerance", 2),
                "prompt_upsampling": parameters.get("prompt_upsampling", True)
            }
            output = replicate.run(model_version, input=inputs)
            return {
                "output_url": self._extract_url(output) if output else None,
                "metadata": {"model_version": model_version, "inputs": inputs}
            }
        return await asyncio.to_thread(sync_call)
    
    async def _generate_video(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate video using video models on Replicate (e.g., google/veo-3)"""
        def sync_call():
            model_name = parameters.get("model", "google/veo-3")
            
            # Prepare inputs for video generation
            inputs = {
                "prompt": prompt,
            }
            
            # Add model-specific parameters based on actual API schema
            if "google/veo" in model_name:
                # Google Veo-3 on Replicate only supports prompt and seed
                # Based on the actual API schema: {"prompt": string, "seed": integer (optional)}
                seed = parameters.get("seed")
                if seed is not None:
                    inputs["seed"] = seed
                    
            elif "runway" in model_name:
                # Runway specific parameters (if using Replicate endpoint)
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