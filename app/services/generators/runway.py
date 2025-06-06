import asyncio
from typing import Dict, Any
from runwayml import RunwayML
from app.services.generators.base import BaseGenerator
from app.models.generation import GenerationResponse
from app.core.config import settings

class RunwayGenerator(BaseGenerator):
    """Runway ML generator implementation"""
    
    def __init__(self):
        super().__init__(settings.runway_api_key)
        self.client = RunwayML(api_key=settings.runway_api_key) if settings.runway_api_key else None
    
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
            elif parameters.get("type") == "image_to_video":
                result = await self._generate_image_to_video(prompt, parameters)
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
        """Generate video using Runway SDK"""
        
        if not self.client:
            raise Exception("Runway API key not configured")
        
        print(f"[DEBUG] Runway SDK: Generating text-to-video with prompt: {prompt}")
        
        try:
            # Create text-to-video task using SDK
            task = self.client.text_to_video.create(
                model="gen4_turbo",
                prompt_text=prompt,
                ratio=parameters.get("ratio", "1280:720"),
                duration=parameters.get("duration", 5)
            )
            
            task_id = task.id
            print(f"[DEBUG] Runway SDK: Created task {task_id}")
            
            # Poll for completion using SDK
            max_attempts = 60  # 2 minutes max wait
            attempt = 0
            
            while attempt < max_attempts:
                await asyncio.sleep(2)  # Wait 2 seconds between polls
                attempt += 1
                
                # Get task status
                task = self.client.tasks.retrieve(task_id)
                print(f"[DEBUG] Runway SDK: Task status: {task.status}")
                
                if task.status == "SUCCEEDED":
                    if task.output and len(task.output) > 0:
                        output_url = task.output[0]
                        print(f"[DEBUG] Runway SDK: Generation completed: {output_url}")
                        
                        return {
                            "output_url": output_url,
                            "metadata": {
                                "duration": parameters.get("duration", 5),
                                "generation_type": "text_to_video",
                                "task_id": task_id
                            }
                        }
                    else:
                        raise Exception("No output URL returned from successful generation")
                        
                elif task.status == "FAILED":
                    error_msg = getattr(task, 'error', 'Unknown error')
                    raise Exception(f"Runway generation failed: {error_msg}")
                    
                # Continue polling if status is RUNNING or PENDING
                
            # Timeout
            raise Exception(f"Runway generation timed out after {max_attempts * 2} seconds")
            
        except Exception as e:
            if "Runway generation" in str(e) or "timeout" in str(e):
                raise  # Re-raise our custom exceptions
            else:
                raise Exception(f"Runway SDK error: {str(e)}")
    
    async def _generate_image_to_video(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate video from image using Runway SDK"""
        
        if not self.client:
            raise Exception("Runway API key not configured")
        
        print(f"[DEBUG] Runway SDK: Generating image-to-video with prompt: {prompt}")
        print(f"[DEBUG] Runway SDK: Parameters: {parameters}")
        
        # Get the input image URL
        input_image = parameters.get("image") or parameters.get("uploaded_image")
        if not input_image:
            raise Exception("No input image provided for image-to-video generation")
            
        print(f"[DEBUG] Runway SDK: Input image: {input_image}")
        
        try:
            # Create image-to-video task using SDK
            task = self.client.image_to_video.create(
                model="gen4_turbo",
                prompt_image=input_image,
                prompt_text=prompt,
                ratio=parameters.get("ratio", "1280:720"),
                duration=parameters.get("duration", 5)
            )
            
            task_id = task.id
            print(f"[DEBUG] Runway SDK: Created task {task_id}")
            
            # Poll for completion using SDK
            max_attempts = 60  # 2 minutes max wait
            attempt = 0
            
            while attempt < max_attempts:
                await asyncio.sleep(2)  # Wait 2 seconds between polls
                attempt += 1
                
                # Get task status
                task = self.client.tasks.retrieve(task_id)
                print(f"[DEBUG] Runway SDK: Task status: {task.status}")
                
                if task.status == "SUCCEEDED":
                    if task.output and len(task.output) > 0:
                        output_url = task.output[0]
                        print(f"[DEBUG] Runway SDK: Generation completed: {output_url}")
                        
                        return {
                            "output_url": output_url,
                            "metadata": {
                                "duration": parameters.get("duration", 5),
                                "input_image": input_image,
                                "generation_type": "image_to_video",
                                "task_id": task_id
                            }
                        }
                    else:
                        raise Exception("No output URL returned from successful generation")
                        
                elif task.status == "FAILED":
                    error_msg = getattr(task, 'error', 'Unknown error')
                    raise Exception(f"Runway generation failed: {error_msg}")
                    
                # Continue polling if status is RUNNING or PENDING
                
            # Timeout
            raise Exception(f"Runway generation timed out after {max_attempts * 2} seconds")
            
        except Exception as e:
            if "Runway generation" in str(e) or "timeout" in str(e):
                raise  # Re-raise our custom exceptions
            else:
                raise Exception(f"Runway SDK error: {str(e)}") 