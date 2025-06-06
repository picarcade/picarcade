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