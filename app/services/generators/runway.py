import asyncio
import aiohttp
from typing import Dict, Any
from runwayml import RunwayML
from app.services.generators.base import BaseGenerator
from app.models.generation import GenerationResponse, ReferenceImage
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
        
        # Determine model name based on type
        if parameters.get("type") == "text_to_image_with_references":
            model_name = "runway_gen4_image"
        else:
            model_name = "runway_gen4_turbo"
        
        try:
            if parameters.get("type") == "text_to_image_with_references":
                result = await self._generate_image_with_references(prompt, parameters)
            elif parameters.get("type") == "video":
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
            
            response = GenerationResponse(
                success=True,
                generation_id=generation_id,
                output_url=result.get("output_url"),
                model_used=model_name,
                metadata=result.get("metadata", {})
            )
            
            # Add reference information to response
            if parameters.get("reference_images"):
                response.references_used = [
                    ReferenceImage(uri=ref["uri"], tag=ref["tag"])
                    for ref in parameters["reference_images"]
                ]
            
            return response
            
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
    
    async def _generate_image_with_references(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image using Runway gen4_image with reference images"""
        
        if not self.client:
            raise Exception("Runway API key not configured")
        
        print(f"[DEBUG] Runway SDK: Generating image with references, prompt: {prompt}")
        
        # Extract reference images from parameters
        reference_images = parameters.get("reference_images", [])
        if not reference_images:
            raise Exception("No reference images provided for reference generation")
        
        print(f"[DEBUG] Runway SDK: Reference images count: {len(reference_images)}")
        
        # Validate and log each reference image
        for ref in reference_images:
            print(f"[DEBUG] Runway SDK: Reference - tag: @{ref['tag']}, uri: {ref['uri']}")
            
            # Check for potential issues with the URI
            uri = ref['uri']
            if not uri.startswith(('http://', 'https://')):
                print(f"[WARNING] Reference URI may not be valid HTTP(S) URL: {uri}")
            
            # Check for query parameters that might cause issues
            if '?' in uri and 'supabase' in uri:
                print(f"[INFO] Supabase URL detected with query params - should be accessible")
            elif '?' in uri:
                print(f"[INFO] URL has query parameters: {uri.split('?')[1]}")
                
            # Log URL domain for debugging
            from urllib.parse import urlparse
            parsed = urlparse(uri)
            print(f"[DEBUG] - Domain: {parsed.netloc}")
            print(f"[DEBUG] - Path: {parsed.path}")
            
        # Additional validation check
        if len(reference_images) > 5:  # Runway might have limits
            print(f"[WARNING] Using {len(reference_images)} reference images - Runway may have limits")
        
        try:
            # Create text-to-image task with references using SDK
            task = self.client.text_to_image.create(
                model="gen4_image",
                prompt_text=prompt,
                ratio=parameters.get("ratio", "1920:1080"),
                reference_images=reference_images
            )
            
            task_id = task.id
            print(f"[DEBUG] Runway SDK: Created reference generation task {task_id}")
            
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
                        print(f"[DEBUG] Runway SDK: Reference generation completed: {output_url}")
                        
                        return {
                            "output_url": output_url,
                            "metadata": {
                                "reference_images_used": reference_images,
                                "generation_type": "text_to_image_with_references",
                                "task_id": task_id,
                                "ratio": parameters.get("ratio", "1920:1080")
                            }
                        }
                    else:
                        raise Exception("No output URL returned from successful reference generation")
                        
                elif task.status == "FAILED":
                    # Get detailed error information from multiple possible fields
                    error_msg = getattr(task, 'error', None)
                    failure_msg = getattr(task, 'failure', None)
                    failure_code = getattr(task, 'failure_code', None)
                    error_details = getattr(task, 'error_details', None)
                    failure_reason = getattr(task, 'failure_reason', None)
                    
                    # Use the most specific error message available
                    primary_error = failure_msg or error_msg or 'Unknown error'
                    
                    # Log detailed error info for debugging
                    print(f"[ERROR] Runway task failed with detailed info:")
                    print(f"[ERROR] - Task ID: {task_id}")
                    print(f"[ERROR] - Error: {error_msg}")
                    print(f"[ERROR] - Failure: {failure_msg}")
                    print(f"[ERROR] - Failure Code: {failure_code}")
                    print(f"[ERROR] - Error Details: {error_details}")
                    print(f"[ERROR] - Failure Reason: {failure_reason}")
                    
                    # Check for specific error types using all error fields
                    all_error_text = ' '.join(filter(None, [str(primary_error), str(failure_code), str(error_details)]))
                    
                    if any(keyword in all_error_text.lower() for keyword in ["content moderation", "public figure", "safety"]):
                        raise Exception(f"Content policy violation: {primary_error}")
                    elif any(keyword in all_error_text.lower() for keyword in ["invalid image", "url", "format"]):
                        raise Exception(f"Invalid image format or URL: {primary_error}")
                    elif any(keyword in all_error_text.lower() for keyword in ["quota", "limit", "rate"]):
                        raise Exception(f"API quota/limit exceeded: {primary_error}")
                    else:
                        detailed_error = f"Runway reference generation failed: {primary_error}"
                        if failure_code:
                            detailed_error += f" (Code: {failure_code})"
                        if error_details:
                            detailed_error += f" (Details: {error_details})"
                        raise Exception(detailed_error)
                    
                # Continue polling if status is RUNNING or PENDING
                
            # Timeout
            raise Exception(f"Runway reference generation timed out after {max_attempts * 2} seconds")
            
        except Exception as e:
            print(f"[ERROR] Runway reference generation failed: {str(e)}")
            
            # Check if this is a recoverable error where we might try a fallback
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["content policy", "safety", "invalid image", "url"]):
                # For image/URL issues, we could try a fallback approach
                print(f"[INFO] Attempting fallback: trying with fewer references or different approach")
                
                # Try with just the working image reference (exclude user references that might have bad URLs)
                working_refs = [ref for ref in reference_images if 'working' in ref['tag'].lower()]
                if len(working_refs) > 0 and len(working_refs) < len(reference_images):
                    print(f"[INFO] Retrying with {len(working_refs)} working image references only")
                    try:
                        # Recursive call with just working image references
                        fallback_params = parameters.copy()
                        fallback_params["reference_images"] = working_refs
                        return await self._generate_image_with_references(prompt, fallback_params)
                    except Exception as fallback_error:
                        print(f"[ERROR] Fallback also failed: {fallback_error}")
                        
            if "Runway" in str(e) or "timeout" in str(e):
                raise  # Re-raise our custom exceptions
            else:
                raise Exception(f"Runway SDK reference generation error: {str(e)}")
    
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