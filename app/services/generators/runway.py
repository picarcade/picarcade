import aiohttp
import asyncio
from typing import Dict, Any
from app.services.generators.base import BaseGenerator
from app.models.generation import GenerationResponse
from app.core.config import settings

class RunwayGenerator(BaseGenerator):
    """Runway ML generator implementation"""
    
    def __init__(self):
        super().__init__(settings.runway_api_key)
        self.base_url = "https://api.runwayml.com/v1"
    
    @BaseGenerator._measure_time
    async def generate(self, 
                      prompt: str, 
                      parameters: Dict[str, Any],
                      generation_id: str = None) -> GenerationResponse:
        """Generate using Runway API"""
        
        # Use provided generation_id or create new one
        if not generation_id:
            generation_id = self._create_generation_id()
        
        model_name = "runway_gen4_turbo"
        
        try:
            if parameters.get("type") == "video":
                result = await self._generate_video(prompt, parameters)
            else:
                result = await self._generate_image(prompt, parameters)
            
            # Log successful attempt
            self._log_generation_attempt(
                generation_id=generation_id,
                model_used=model_name,
                parameters=parameters,
                success=True,
                execution_time=getattr(self, '_last_execution_time', 0)
            )
            
            return GenerationResponse(
                success=True,
                generation_id=generation_id,
                output_url=result.get("output_url"),
                model_used=model_name,
                metadata=result.get("metadata", {})
            )
            
        except Exception as e:
            error_msg = str(e)
            
            # Log failed attempt
            self._log_generation_attempt(
                generation_id=generation_id,
                model_used=model_name,
                parameters=parameters,
                success=False,
                execution_time=getattr(self, '_last_execution_time', 0),
                error_message=error_msg
            )
            
            return GenerationResponse(
                success=False,
                generation_id=generation_id,
                error_message=error_msg,
                model_used=model_name
            )
    
    async def _generate_image(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image using Runway"""
        
        # Note: This is pseudo-code - actual Runway API might differ
        payload = {
            "prompt_text": prompt,
            "ratio": parameters.get("ratio", "1280:720"),
            "model": "gen4_image"
        }
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Start generation
            async with session.post(
                f"{self.base_url}/text_to_image",
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"Runway API error: {await response.text()}")
                
                task = await response.json()
                task_id = task.get("id")
            
            # Poll for completion
            while True:
                async with session.get(
                    f"{self.base_url}/tasks/{task_id}",
                    headers=headers
                ) as status_response:
                    status_data = await status_response.json()
                    
                    if status_data.get("status") == "SUCCEEDED":
                        return {
                            "output_url": status_data.get("output", [None])[0],
                            "metadata": {"task_id": task_id}
                        }
                    elif status_data.get("status") == "FAILED":
                        raise Exception(f"Generation failed: {status_data.get('error')}")
                
                await asyncio.sleep(2)  # Poll every 2 seconds
    
    async def _generate_video(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate video using Runway"""
        
        payload = {
            "prompt_text": prompt,
            "duration": parameters.get("duration", 5),
            "ratio": parameters.get("ratio", "1280:720"),
            "model": "gen4_turbo"
        }
        
        # Similar implementation to image generation but for video
        # This would follow the same pattern as _generate_image
        
        # For now, return mock response
        await asyncio.sleep(5)  # Simulate generation time
        return {
            "output_url": "https://mock-video-url.com/video.mp4",
            "metadata": {"duration": parameters.get("duration", 5)}
        } 