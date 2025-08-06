import asyncio
import aiohttp
import time
from typing import Dict, Any
import json
import logging
import httpx
from runwayml import RunwayML
from app.services.generators.base import BaseGenerator
from app.models.generation import GenerationResponse, ReferenceImage
from app.core.config import settings

logger = logging.getLogger(__name__)

# Enable detailed HTTP logging for Runway requests
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)

class RunwayGenerator(BaseGenerator):
    """
    DEPRECATED: Runway ML generator implementation
    
    This generator is deprecated. Runway models are now handled via Replicate.
    Use ReplicateGenerator with runway model names instead:
    - "runwayml/gen4-turbo" for image-to-video
    - "runwayml/gen4-aleph" for video editing
    
    This class remains for backward compatibility but will be removed in a future version.
    """
    
    def __init__(self):
        super().__init__(settings.runway_api_key)
        
        # DEPRECATION WARNING
        import warnings
        warnings.warn(
            "RunwayGenerator is deprecated. Runway models are now handled via ReplicateGenerator. "
            "Use 'runwayml/gen4-turbo' or 'runwayml/gen4-aleph' with ReplicateGenerator instead.",
            DeprecationWarning,
            stacklevel=2
        )
        print("⚠️  WARNING: RunwayGenerator is DEPRECATED! Use ReplicateGenerator with runway models instead.")
        logger.warning("RunwayGenerator is deprecated. Use ReplicateGenerator with runway model names instead.")
        
        # VERY OBVIOUS LOG TO CONFIRM WHEN GENERATOR IS INSTANTIATED
        print("🔥🔥🔥 RUNWAY GENERATOR __INIT__ CALLED - NEW INSTANCE CREATED! 🔥🔥🔥")
        logger.info("🔥🔥🔥 RUNWAY GENERATOR __INIT__ CALLED - NEW INSTANCE CREATED! 🔥🔥🔥")
        
        print(f"🔑 DEBUG: Runway API Key present: {bool(settings.runway_api_key)}")
        print(f"🔑 DEBUG: Runway API Key length: {len(settings.runway_api_key) if settings.runway_api_key else 0}")
        
        if settings.runway_api_key:
            try:
                print("🔧 DEBUG: Starting RunwayML client initialization...")
                # Create custom HTTP client with detailed logging
                import httpx
                from runwayml import DefaultHttpxClient
                
                # Custom transport with detailed logging
                class LoggingTransport(httpx.HTTPTransport):
                    def handle_request(self, request):
                        # Log the complete request
                        logger.info("🌐 HTTPX REQUEST TO RUNWAY:")
                        logger.info(f"   Method: {request.method}")
                        logger.info(f"   URL: {request.url}")
                        logger.info(f"   Headers: {dict(request.headers)}")
                        if request.content:
                            try:
                                content_str = request.content.decode('utf-8')
                                logger.info(f"   Body: {content_str}")
                            except:
                                logger.info(f"   Body: {len(request.content)} bytes (binary)")
                        
                        # Make the actual request
                        response = super().handle_request(request)
                        
                        # Log the response
                        logger.info("🌐 HTTPX RESPONSE FROM RUNWAY:")
                        logger.info(f"   Status: {response.status_code}")
                        logger.info(f"   Headers: {dict(response.headers)}")
                        try:
                            # Read response content first to avoid streaming issues
                            content = response.read()
                            response_text = content.decode('utf-8')
                            logger.info(f"   Body: {response_text}")
                        except Exception as e:
                            logger.info(f"   Body: Unable to read response ({e})")
                        
                        return response
                
                http_client = DefaultHttpxClient(
                    transport=LoggingTransport()
                )
                
                self.client = RunwayML(
                    api_key=settings.runway_api_key,
                    default_headers={
                        "X-Runway-Version": "2024-11-06"
                    },
                    http_client=http_client
                )
                print("✅ DEBUG: RunwayML client initialized successfully with detailed logging")
                print(f"🔍 DEBUG: Client attributes: {[attr for attr in dir(self.client) if not attr.startswith('_')]}")
                logger.info(f"RunwayML client initialized with API version 2024-11-06 and detailed logging")
            except Exception as e:
                print(f"❌ DEBUG: Failed to initialize RunwayML client with logging: {e}")
                logger.warning(f"Could not initialize RunwayML client with logging: {e}")
                try:
                    # Fallback to basic client - exactly as shown in Runway docs
                    print("🔄 DEBUG: Trying fallback basic client...")
                    # Match the docs: just RunwayML() with env var RUNWAYML_API_SECRET
                    import os
                    if not os.environ.get('RUNWAYML_API_SECRET'):
                        os.environ['RUNWAYML_API_SECRET'] = settings.runway_api_key
                        print("🔑 DEBUG: Set RUNWAYML_API_SECRET environment variable")
                    
                    self.client = RunwayML()  # Let it use env var as per docs
                    print("✅ DEBUG: Basic RunwayML client initialized successfully")
                    print(f"🔍 DEBUG: Fallback client attributes: {[attr for attr in dir(self.client) if not attr.startswith('_')]}")
                    logger.info("Fallback basic RunwayML client initialized successfully")
                except Exception as fallback_error:
                    print(f"❌ DEBUG: Fallback client also failed: {fallback_error}")
                    logger.error(f"Both advanced and fallback RunwayML client initialization failed: {fallback_error}")
                    self.client = None
        else:
            print("❌ DEBUG: No Runway API key found, setting client to None")
            self.client = None
            
        print(f"🔄 DEBUG: Final client state: {self.client is not None}")
    
    @BaseGenerator._measure_time
    async def generate(self, 
                      prompt: str, 
                      parameters: Dict[str, Any],
                      generation_id: str = None) -> GenerationResponse:
        """Generate using Runway API"""
        
        if not generation_id:
            generation_id = self._create_generation_id()
        
        # Determine model name based on type
        if parameters.get("type") == "text_to_image_with_references":
            model_name = "runway_gen4_image"
        elif parameters.get("type") == "video_edit":
            model_name = "gen4_aleph"
        else:
            model_name = "runway_gen4_turbo"
        
        try:
            # VERY OBVIOUS DEBUG LOG TO CONFIRM CODE RELOAD
            print("🚨🚨🚨 RUNWAY GENERATOR CALLED - CODE RELOADED! 🚨🚨🚨")
            print(f"*** RUNWAY GENERATOR: Starting generation with type='{parameters.get('type')}' ***")
            logger.info("🚨🚨🚨 RUNWAY GENERATOR CALLED - CODE RELOADED! 🚨🚨🚨")
            logger.info(f"*** RUNWAY GENERATOR: Starting generation with type='{parameters.get('type')}' ***")
            
            if parameters.get("type") == "text_to_image_with_references":
                logger.info("*** RUNWAY GENERATOR: Taking text_to_image_with_references path ***")
                result = await self._generate_image_with_references(prompt, parameters)
            elif parameters.get("type") == "video_edit":
                logger.info("*** RUNWAY GENERATOR: Taking video_edit path with gen4_aleph ***")
                result = await self._generate_video_edit(prompt, parameters)
            elif parameters.get("type") == "video":
                logger.info("*** RUNWAY GENERATOR: Taking video path ***")
                result = await self._generate_video(prompt, parameters)
            elif parameters.get("type") == "image_to_video":
                logger.info("*** RUNWAY GENERATOR: Taking image_to_video path ***")
                result = await self._generate_image_to_video(prompt, parameters)
            else:
                logger.info("*** RUNWAY GENERATOR: Taking basic image path ***")
                result = await self._generate_image(prompt, parameters)
            
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
            
            # Check for reference images in both camelCase and snake_case for response metadata
            ref_images = parameters.get("referenceImages", parameters.get("reference_images", []))
            if ref_images:
                response.references_used = [
                    ReferenceImage(uri=ref["uri"], tag=ref["tag"])
                    for ref in ref_images
                ]
            
            # Enhanced logging for successful video edit 
            if parameters.get("type") == "video_edit":
                logger.info(f"💰 gen4_aleph VIDEO_EDIT completed for generation {generation_id}")
                logger.info(f"💰 VIDEO_EDIT cost impact: 300 XP (~$0.50) charged for successful video editing")
            
            return response
            
        except Exception as e:
            error_msg = str(e)
            
            # Enhanced logging for video edit failures 
            if parameters.get("type") == "video_edit":
                logger.error(f"💰 gen4_aleph VIDEO_EDIT failed for generation {generation_id}: {e}")
                logger.error(f"💰 VIDEO_EDIT cost impact: 300 XP (~$0.50) failed request")
            
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
        """Generate image using Runway SDK"""
        
        if not self.client:
            raise Exception("Runway API key not configured")
        
        # Use promptText from parameters if available (correct camelCase from simplified flow)
        prompt_text = parameters.get("promptText", prompt)
        ratio = parameters.get("ratio", "1280:720")
        
        # Log the complete, definitive SDK call (Python SDK uses snake_case, converts to camelCase internally)
        complete_api_request = {
            "sdk_method": "client.text_to_image.create", 
            "python_sdk_parameters": {
                "model": "gen4_image",
                "prompt_text": prompt_text,  # ✅ Python SDK snake_case
                "ratio": ratio
            },
            "converted_to_http_api": {
                "model": "gen4_image", 
                "promptText": prompt_text,  # ✅ HTTP API camelCase
                "ratio": ratio
            }
        }
        logger.debug(f"🚀 Runway text_to_image call: {complete_api_request['sdk_method']}")
        
        try:
            task = self.client.text_to_image.create(
                model="gen4_image",
                prompt_text=prompt_text,  # ✅ Python SDK uses snake_case
                ratio=ratio
            )
            
            task_id = task.id
            logger.info(f"Runway task created: {task_id}")
            
            # Poll for completion
            max_attempts = 60
            attempt = 0
            
            while attempt < max_attempts:
                await asyncio.sleep(2)
                attempt += 1
                
                task = self.client.tasks.retrieve(task_id)
                
                if task.status == "SUCCEEDED":
                    if task.output and len(task.output) > 0:
                        output_url = task.output[0]
                        logger.info(f"Runway task {task_id} completed: {output_url}")
                        
                        return {
                            "output_url": output_url,
                            "metadata": {
                                "generation_type": "text_to_image",
                                "task_id": task_id
                            }
                        }
                    else:
                        raise Exception("No output URL returned from successful generation")
                        
                elif task.status == "FAILED":
                    error_msg = getattr(task, 'error', 'Unknown error')
                    raise Exception(f"Runway generation failed: {error_msg}")
                    
            raise Exception(f"Runway generation timed out after {max_attempts * 2} seconds")
            
        except Exception as e:
            if "Runway generation" in str(e) or "timeout" in str(e):
                raise
            else:
                raise Exception(f"Runway SDK error: {str(e)}")
    
    async def _generate_video(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate video using Runway SDK"""
        
        if not self.client:
            raise Exception("Runway API key not configured")
        
        # Use camelCase parameters from simplified flow service
        prompt_text = parameters.get("promptText", prompt)
        ratio = parameters.get("ratio", "1280:720")
        duration = parameters.get("duration", 5)
        
        # Log the complete, definitive API request being sent to Runway
        complete_api_request = {
            "sdk_method": "client.text_to_video.create",
            "parameters": {
                "model": "gen4_turbo",
                "promptText": prompt_text,  # ✅ Use camelCase
                "ratio": ratio,
                "duration": duration
            }
        }
        logger.debug(f"🚀 Runway text_to_video call: {complete_api_request['sdk_method']}")
        
        try:
            task = self.client.text_to_video.create(
                model="gen4_turbo",
                prompt_text=prompt_text,  # ✅ Python SDK uses snake_case
                ratio=ratio,
                duration=duration
            )
            
            task_id = task.id
            logger.info(f"Runway task created: {task_id}")
            
            # Poll for completion
            max_attempts = 60
            attempt = 0
            
            while attempt < max_attempts:
                await asyncio.sleep(2)
                attempt += 1
                
                task = self.client.tasks.retrieve(task_id)
                
                if task.status == "SUCCEEDED":
                    if task.output and len(task.output) > 0:
                        output_url = task.output[0]
                        logger.info(f"Runway task {task_id} completed: {output_url}")
                        
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
                    
            raise Exception(f"Runway generation timed out after {max_attempts * 2} seconds")
            
        except Exception as e:
            if "Runway generation" in str(e) or "timeout" in str(e):
                raise
            else:
                raise Exception(f"Runway SDK error: {str(e)}")
    
    async def _generate_image_with_references(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image using Runway gen4_image with reference images"""
        
        print("*** RUNWAY GENERATOR: _generate_image_with_references called ***")
        logger.info("*** RUNWAY GENERATOR: _generate_image_with_references called ***")
        
        if not self.client:
            raise Exception("Runway API key not configured")
        
        # Check for reference images in both camelCase (from simplified flow) and snake_case (from generation.py)
        # Merge both sources to ensure working image and other references are included
        reference_images_camel = parameters.get("referenceImages", [])
        reference_images_snake = parameters.get("reference_images", [])
        
        # Combine and deduplicate reference images
        all_references = []
        seen_uris = set()
        
        # Add from both sources, avoiding duplicates based on URI
        for ref_list in [reference_images_camel, reference_images_snake]:
            for ref in ref_list:
                if ref["uri"] not in seen_uris:
                    all_references.append(ref)
                    seen_uris.add(ref["uri"])
        
        reference_images = all_references
        
        print(f"📸 REFERENCE IMAGES COUNT: {len(reference_images)}")
        for i, ref in enumerate(reference_images):
            print(f"  📸 Reference {i+1}: tag='{ref['tag']}', uri='{ref['uri'][:100]}...'")
        if not reference_images:
            raise Exception("No reference images provided for reference generation")
        
        # Validate and fix reference image aspect ratios for Runway requirements
        # Runway requires aspect ratio between 0.5 and 2.0 (width/height)
        validated_references = []
        for ref in reference_images:
            try:
                validated_ref = await self._validate_reference_image_aspect_ratio(ref)
                validated_references.append(validated_ref)
                print(f"✅ Validated reference: {ref['tag']}")
            except Exception as e:
                print(f"❌ Failed to validate reference {ref['tag']}: {e}")
                # For now, skip invalid images rather than failing the whole request
                logger.warning(f"Skipping invalid reference image {ref['tag']}: {e}")
                continue
        
        if not validated_references:
            raise Exception("No valid reference images after aspect ratio validation")
        
        reference_images = validated_references
        
        # Optimize prompt for different styling scenarios
        is_hair_styling = parameters.get("enhanced_workflow_type") == "hair_styling"
        
        if is_hair_styling and len(reference_images) >= 2:
            # Hair styling optimization - be very specific about only changing hair
            working_tag = None
            hair_ref_tag = None
            
            # First, try to find structured tags
            for ref in reference_images:
                if "working" in ref["tag"]:
                    working_tag = ref["tag"]
                elif "hair_reference" in ref["tag"]:
                    hair_ref_tag = ref["tag"]
            
            # If structured tags not found, analyze the original prompt to determine roles
            if not working_tag or not hair_ref_tag:
                # Parse the original prompt to understand which reference is for hair style
                prompt_lower = prompt.lower()
                
                # Look for patterns that indicate hair source
                # e.g., "hair style to the same as @charlie", "hair the style of @blonde", etc.
                hair_indicators = [
                    "hair style to the same as @", "hairstyle from @", "hair to the same as @", "hair like @",
                    "hair the style of @", "hair style of @", "hairstyle of @", "hairstyle like @",
                    "hair style to @", "hair style from @", "style of @", "hair to look like @"
                ]
                base_indicators = ["with @", "use the composition", "setting from @"]
                
                detected_hair_ref = None
                detected_base_ref = None
                
                for indicator in hair_indicators:
                    if indicator in prompt_lower:
                        # Extract the reference name after the indicator
                        start_idx = prompt_lower.find(indicator) + len(indicator)
                        end_idx = prompt_lower.find(" ", start_idx)
                        if end_idx == -1:
                            end_idx = len(prompt_lower)
                        detected_hair_ref = prompt_lower[start_idx:end_idx].strip()
                        
                        # Clean up the reference name (remove punctuation, extra spaces)
                        detected_hair_ref = detected_hair_ref.replace(".", "").replace(",", "").strip()
                        
                        print(f"   🎯 Found hair indicator: '{indicator}' -> extracted: '{detected_hair_ref}'")
                        break
                
                for indicator in base_indicators:
                    if indicator in prompt_lower:
                        start_idx = prompt_lower.find(indicator) + len(indicator)
                        end_idx = prompt_lower.find(" ", start_idx)
                        if end_idx == -1:
                            end_idx = prompt_lower.find(".", start_idx)
                        if end_idx == -1:
                            end_idx = len(prompt_lower)
                        detected_base_ref = prompt_lower[start_idx:end_idx].strip()
                        break
                
                # Map detected references to actual tags
                print(f"🔍 Hair styling prompt analysis:")
                print(f"   detected_hair_ref: '{detected_hair_ref}'")
                print(f"   detected_base_ref: '{detected_base_ref}'")
                
                if detected_hair_ref:
                    # Try to find matching reference by tag name
                    for ref in reference_images:
                        ref_tag_lower = ref["tag"].lower()
                        if ref_tag_lower == detected_hair_ref or detected_hair_ref in ref_tag_lower:
                            hair_ref_tag = ref["tag"]
                            print(f"   ✅ Mapped hair reference: '{detected_hair_ref}' -> '{hair_ref_tag}'")
                            break
                
                if detected_base_ref:
                    for ref in reference_images:
                        if ref["tag"].lower() == detected_base_ref:
                            working_tag = ref["tag"]
                            print(f"   ✅ Mapped base reference: {detected_base_ref} -> {working_tag}")
                            break
                
                # Final fallback: intelligently assign based on context
                if not working_tag or not hair_ref_tag:
                    # Look for working image indicators (these are usually the base person)
                    working_indicators = ["working", "man_", "woman_", "girl_", "boy_", "person_"]
                    
                    for ref in reference_images:
                        ref_tag_lower = ref["tag"].lower()
                        
                        # If this looks like a working image, it's the base person
                        if any(indicator in ref_tag_lower for indicator in working_indicators) and not working_tag:
                            working_tag = ref["tag"]
                            print(f"   🎯 Auto-detected base person: '{working_tag}' (working image pattern)")
                        # Otherwise, it's likely the hair reference
                        elif not hair_ref_tag and ref["tag"] != working_tag:
                            hair_ref_tag = ref["tag"]
                            print(f"   🎯 Auto-detected hair reference: '{hair_ref_tag}' (non-working image)")
                    
                    # Ultimate fallback if still not set
                    if not working_tag:
                        working_tag = reference_images[0]["tag"]
                        print(f"   ⚠️ Fallback: Using first image as base person: '{working_tag}'")
                    if not hair_ref_tag:
                        hair_ref_tag = reference_images[1]["tag"] if len(reference_images) > 1 else reference_images[0]["tag"]
                        print(f"   ⚠️ Fallback: Using second image as hair reference: '{hair_ref_tag}'")
            
            # Create a direct, simple prompt that works better with Runway - include feature preservation
            optimized_prompt = f"@{working_tag} with the hairstyle from @{hair_ref_tag}. Maintain all other features. Only update the hair style."
            logger.info(f"Hair styling optimization: '{prompt}' -> '{optimized_prompt}'")
            prompt = optimized_prompt
            
            # Update parameters so the enhanced prompt gets logged correctly
            parameters["prompt"] = optimized_prompt
        
        # Use camelCase parameters from simplified flow service
        prompt_text = parameters.get("promptText", prompt)
        ratio = parameters.get("ratio", "1920:1080")
        # Use the merged reference_images that contains both @finley AND working_image
        reference_images_param = reference_images
        
        # Log clean summary without image data
        ref_summary = [{"tag": ref.get("tag", "unknown"), "uri_preview": ref.get("uri", "")[:50] + "..."} for ref in reference_images_param]
        
        logger.debug(f"🚀 Runway SDK call: text_to_image.create(model='gen4_image', prompt='{prompt_text}', ratio='{ratio}', reference_images={len(reference_images_param)})")
        logger.debug(f"📋 Reference images: {ref_summary}")
        
        try:
            print(f"🌟 CALLING: self.client.text_to_image.create(model='gen4_image', prompt_text='{prompt_text}', ratio='{ratio}', reference_images={len(reference_images_param)} images)")
            task = self.client.text_to_image.create(
                model="gen4_image",
                prompt_text=prompt_text,  # ✅ Python SDK uses snake_case
                ratio=ratio,
                reference_images=reference_images_param  # ✅ Python SDK uses snake_case
            )
            
            task_id = task.id
            print(f"✅ RUNWAY TASK CREATED: {task_id}")
            logger.info(f"Runway reference task created: {task_id}")
            
            # Log clean task creation summary
            logger.info(f"📋 Task created: {task.id} (status: {getattr(task, 'status', 'pending')})")
            
            # Poll for completion
            max_attempts = 60
            attempt = 0
            
            while attempt < max_attempts:
                await asyncio.sleep(2)
                attempt += 1
                
                task = self.client.tasks.retrieve(task_id)
                
                if task.status == "SUCCEEDED":
                    if task.output and len(task.output) > 0:
                        output_url = task.output[0]
                        logger.info(f"Runway reference task {task_id} completed: {output_url}")
                        
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
                    error_msg = getattr(task, 'error', None)
                    failure_msg = getattr(task, 'failure', None)
                    failure_code = getattr(task, 'failure_code', None)
                    
                    primary_error = failure_msg or error_msg or 'Unknown error'
                    
                    logger.error(f"Runway task {task_id} failed: {primary_error}")
                    if failure_code:
                        logger.error(f"Failure code: {failure_code}")
                    
                    all_error_text = ' '.join(filter(None, [str(primary_error), str(failure_code)]))
                    
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
                        raise Exception(detailed_error)
                    
            raise Exception(f"Runway reference generation timed out after {max_attempts * 2} seconds")
            
        except Exception as e:
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["content policy", "safety", "invalid image", "url"]):
                working_refs = [ref for ref in reference_images if 'working' in ref['tag'].lower()]
                if len(working_refs) > 0 and len(working_refs) < len(reference_images):
                    logger.info(f"Retrying with {len(working_refs)} working image references only")
                    try:
                        fallback_params = parameters.copy()
                        fallback_params["reference_images"] = working_refs
                        return await self._generate_image_with_references(prompt, fallback_params)
                    except Exception as fallback_error:
                        logger.error(f"Fallback also failed: {fallback_error}")
                        
            if "Runway" in str(e) or "timeout" in str(e):
                raise
            else:
                raise Exception(f"Runway SDK reference generation error: {str(e)}")
    
    async def _validate_reference_image_aspect_ratio(self, reference_image: Dict[str, str]) -> Dict[str, str]:
        """Validate and potentially modify reference image to meet Runway's aspect ratio requirements"""
        
        try:
            from PIL import Image
            import io
            import tempfile
            import os
            
            uri = reference_image["uri"]
            tag = reference_image["tag"]
            
            print(f"🔍 Checking aspect ratio for reference: {tag}")
            
            # Download and check the image dimensions
            async with aiohttp.ClientSession() as session:
                async with session.get(uri) as response:
                    if response.status != 200:
                        raise Exception(f"Could not download image: HTTP {response.status}")
                    
                    image_data = await response.read()
                    
            # Open image with PIL to get dimensions
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            aspect_ratio = width / height
            
            print(f"📐 Image dimensions: {width}x{height}, aspect ratio: {aspect_ratio:.3f}")
            
            # Runway requires aspect ratio between 0.5 and 2.0
            if 0.5 <= aspect_ratio <= 2.0:
                print(f"✅ Aspect ratio {aspect_ratio:.3f} is valid for Runway")
                return reference_image  # No changes needed
            
            print(f"⚠️ Aspect ratio {aspect_ratio:.3f} is outside Runway's range (0.5-2.0), cropping...")
            
            # Crop the image to fit within acceptable aspect ratio
            if aspect_ratio > 2.0:
                # Image is too wide, crop width
                target_aspect_ratio = 2.0
                new_width = int(height * target_aspect_ratio)
                left = (width - new_width) // 2
                right = left + new_width
                cropped_image = image.crop((left, 0, right, height))
                print(f"🔧 Cropped wide image from {width}x{height} to {new_width}x{height}")
            else:
                # Image is too tall, crop height  
                target_aspect_ratio = 0.5
                new_height = int(width / target_aspect_ratio)
                top = (height - new_height) // 2
                bottom = top + new_height
                cropped_image = image.crop((0, top, width, bottom))
                print(f"🔧 Cropped tall image from {width}x{height} to {width}x{new_height}")
            
            # Save cropped image to temporary file and upload
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                # Convert to RGB if necessary (for JPEG compatibility)
                if cropped_image.mode in ('RGBA', 'LA', 'P'):
                    cropped_image = cropped_image.convert('RGB')
                
                cropped_image.save(temp_file.name, format='JPEG', quality=95)
                temp_file_path = temp_file.name
            
            try:
                # For now, convert to base64 data URI as a simple solution
                # This avoids needing to re-upload the image
                import base64
                
                with open(temp_file_path, 'rb') as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    data_uri = f"data:image/jpeg;base64,{base64_data}"
                
                print(f"✅ Created data URI for cropped image (size: {len(base64_data)} chars)")
                
                # Clean up temp file
                os.unlink(temp_file_path)
                
                # Return modified reference with data URI
                return {
                    "uri": data_uri,
                    "tag": tag
                }
                
            except Exception as conversion_error:
                # Clean up temp file on error
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                raise Exception(f"Failed to convert cropped image: {conversion_error}")
                
        except Exception as e:
            raise Exception(f"Aspect ratio validation failed for {tag}: {e}")
    
    async def _generate_image_to_video(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate video from image using Runway SDK"""
        
        if not self.client:
            raise Exception("Runway API key not configured")
        
        # Check multiple possible image parameter names
        input_image = (parameters.get("prompt_image") or 
                      parameters.get("first_frame_image") or 
                      parameters.get("image") or 
                      parameters.get("uploaded_image"))
        
        print(f"🔍 DEBUG: Checking for input image in parameters:")
        print(f"   prompt_image: {parameters.get('prompt_image', 'NOT_FOUND')}")
        print(f"   first_frame_image: {parameters.get('first_frame_image', 'NOT_FOUND')}")
        print(f"   image: {parameters.get('image', 'NOT_FOUND')}")
        print(f"   uploaded_image: {parameters.get('uploaded_image', 'NOT_FOUND')}")
        print(f"   final input_image: {input_image}")
        
        if not input_image:
            raise Exception("No input image provided for image-to-video generation")
        
        # Use parameters from the request
        prompt_text = parameters.get("promptText", prompt)
        ratio = parameters.get("ratio", "1280:720")
        duration = parameters.get("duration", 5)
        model = parameters.get("model", "gen4_turbo")
        
        print(f"🎬 RUNWAY IMAGE-TO-VIDEO REQUEST:")
        print(f"   📹 Model: {model}")
        print(f"   🖼️  Input Image: {input_image[:50]}...")
        print(f"   📝 Prompt: {prompt_text}")
        print(f"   📐 Ratio: {ratio}")
        print(f"   ⏱️  Duration: {duration}s")
        
        # Log the complete, definitive API request being sent to Runway
        complete_api_request = {
            "sdk_method": "client.image_to_video.create",
            "parameters": {
                "model": model,
                "prompt_image": input_image,
                "prompt_text": prompt_text,
                "ratio": ratio,
                "duration": duration
            }
        }
        logger.info(f"🚀 Runway image_to_video API call: {complete_api_request}")
        
        try:
            print(f"🚀 CALLING: client.image_to_video.create(model='{model}', prompt_image='{input_image[:50]}...', prompt_text='{prompt_text}', ratio='{ratio}', duration={duration})")
            
            # Create the task
            task_response = self.client.image_to_video.create(
                model=model,
                prompt_image=input_image,
                prompt_text=prompt_text,
                ratio=ratio,
                duration=duration
            )
            
            task_id = task_response.id
            print(f"✅ RUNWAY TASK CREATED: {task_id}")
            logger.info(f"Runway image-to-video task created: {task_id}")
            
            # Poll for completion manually
            print(f"⏳ Polling task {task_id} for completion...")
            max_attempts = 120  # 4 minutes max wait time  
            attempt = 0
            
            while attempt < max_attempts:
                await asyncio.sleep(2)  # Wait 2 seconds between polls
                attempt += 1
                
                try:
                    task = self.client.tasks.retrieve(task_id)
                    print(f"📊 Task {task_id} status: {task.status} (attempt {attempt}/{max_attempts})")
                    
                    if task.status == "SUCCEEDED":
                        if task.output and len(task.output) > 0:
                            output_url = task.output[0]
                            print(f"✅ RUNWAY TASK COMPLETED: {output_url}")
                            logger.info(f"Runway task {task_id} completed: {output_url}")
                            
                            return {
                                "output_url": output_url,
                                "metadata": {
                                    "duration": duration,
                                    "input_image": input_image,
                                    "generation_type": "image_to_video",
                                    "task_id": task_id,
                                    "model": model,
                                    "ratio": ratio,
                                    "attempts": attempt
                                }
                            }
                        else:
                            raise Exception(f"Task {task_id} succeeded but no output URL returned")
                    
                    elif task.status == "FAILED":
                        error_msg = getattr(task, 'error', {})
                        failure_code = getattr(task, 'failure_code', 'Unknown')
                        raise Exception(f"Runway task {task_id} failed: {error_msg} (Code: {failure_code})")
                    
                    elif task.status in ["PENDING", "RUNNING"]:
                        # Continue polling
                        continue
                        
                    else:
                        print(f"⚠️  Unknown task status: {task.status}")
                        continue
                        
                except Exception as poll_error:
                    if "failed" in str(poll_error) or "error" in str(poll_error).lower():
                        raise poll_error
                    else:
                        print(f"⚠️  Poll attempt {attempt} failed: {poll_error}")
                        continue
            
            # If we get here, we've exceeded max attempts
            raise Exception(f"Runway task {task_id} timed out after {max_attempts * 2} seconds")
            
        except Exception as e:
            print(f"❌ RUNWAY SDK ERROR: {e}")
            if "Runway" in str(e):
                raise
            else:
                raise Exception(f"Runway SDK error: {str(e)}")
    
    async def _generate_face_swap(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate face swap using Runway with temporary reference creation"""
        
        if not self.client:
            raise Exception("Runway API key not configured")
        
        base_image = parameters.get("face_swap_base_image")
        source_image = parameters.get("face_swap_source_image")
        
        if not base_image or not source_image:
            raise Exception("Face swap requires both base image and source image")
        
        from app.services.reference_service import ReferenceService
        import time
        
        try:
            time_suffix = str(int(time.time()))[-6:]
            temp_tag = f"face{time_suffix}"
            base_temp_tag = f"body{time_suffix}"
            
            logger.info(f"Creating temporary references: @{temp_tag}, @{base_temp_tag}")
            
            # Create references
            await ReferenceService.create_reference(
                user_id="temp_user",
                tag=temp_tag,
                image_url=source_image,
                display_name=f"Face Source {temp_tag[-8:]}",
                description="Temporary reference for face swap operation",
                category="temporary",
                source_type="temporary_face_swap"
            )
            
            await ReferenceService.create_reference(
                user_id="temp_user",
                tag=base_temp_tag,
                image_url=base_image,
                display_name=f"Body Source {base_temp_tag[-8:]}",
                description="Temporary reference for face swap base image",
                category="temporary",
                source_type="temporary_face_swap"
            )
            
            reference_images = [
                {"uri": base_image, "tag": base_temp_tag},
                {"uri": source_image, "tag": temp_tag}
            ]
            
            face_swap_prompt = f"Update the face of @{base_temp_tag} with @{temp_tag}"
            
            # Use camelCase parameters from simplified flow service
            ratio = parameters.get("ratio", "1920:1080")
            
            # Log the complete, definitive API request being sent to Runway
            complete_api_request = {
                "sdk_method": "client.text_to_image.create",
                "operation": "face_swap",
                "parameters": {
                    "model": "gen4_image",
                    "promptText": face_swap_prompt,  # ✅ Use camelCase
                    "ratio": ratio,
                    "referenceImages": reference_images  # ✅ Use camelCase
                }
            }
            logger.debug(f"🚀 Runway face_swap call: {complete_api_request['sdk_method']}")
            
            task = self.client.text_to_image.create(
                model="gen4_image",
                prompt_text=face_swap_prompt,  # ✅ Python SDK uses snake_case
                ratio=ratio,
                reference_images=reference_images  # ✅ Python SDK uses snake_case
            )
            
            task_id = task.id
            logger.info(f"Runway face swap task created: {task_id}")
            
            # Poll for completion
            max_attempts = 60
            attempt = 0
            
            while attempt < max_attempts:
                await asyncio.sleep(2)
                attempt += 1
                
                task = self.client.tasks.retrieve(task_id)
                
                if task.status == "SUCCEEDED":
                    if task.output and len(task.output) > 0:
                        output_url = task.output[0]
                        logger.info(f"Runway face swap task {task_id} completed: {output_url}")
                        
                        # Clean up temporary references
                        try:
                            await ReferenceService.delete_reference("temp_user", temp_tag)
                            await ReferenceService.delete_reference("temp_user", base_temp_tag)
                            logger.info(f"Cleaned up temporary references")
                        except Exception as cleanup_error:
                            logger.warning(f"Could not clean up temporary references: {cleanup_error}")
                        
                        return {
                            "output_url": output_url,
                            "metadata": {
                                "face_swap": True,
                                "base_image": base_image,
                                "source_image": source_image,
                                "temp_reference_tags": [temp_tag, base_temp_tag],
                                "generation_type": "face_swap",
                                "task_id": task_id,
                                "ratio": parameters.get("ratio", "1920:1080")
                            }
                        }
                    else:
                        raise Exception("No output URL returned from successful face swap")
                        
                elif task.status == "FAILED":
                    error_msg = getattr(task, 'error', None) or getattr(task, 'failure', 'Unknown error')
                    try:
                        await ReferenceService.delete_reference("temp_user", temp_tag)
                        await ReferenceService.delete_reference("temp_user", base_temp_tag)
                    except:
                        pass
                    raise Exception(f"Runway face swap failed: {error_msg}")
                    
            # Timeout cleanup
            try:
                await ReferenceService.delete_reference("temp_user", temp_tag)
                await ReferenceService.delete_reference("temp_user", base_temp_tag)
            except:
                pass
            raise Exception(f"Runway face swap timed out after {max_attempts * 2} seconds")
            
        except Exception as e:
            if "Runway" in str(e) or "timeout" in str(e) or "face swap" in str(e):
                raise
            else:
                raise Exception(f"Runway face swap error: {str(e)}")
    
    async def _generate_video_edit(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate video edit using Runway gen4_aleph (video_to_video)"""
        
        if not self.client:
            raise Exception("Runway API key not configured")
        
        logger.info(f"🎬 Starting gen4_aleph video edit - Cost: 300 XP (~$0.50)")
        
        # Extract working video URI
        video_uri = parameters.get("videoUri") or parameters.get("video_uri") or parameters.get("current_working_video")
        if not video_uri:
            raise Exception("VIDEO_EDIT requires a working video (videoUri parameter)")
        
        # Validate video URI format
        logger.info(f"🎬 Raw video URI received: {video_uri}")
        
        # Check if it's a valid HTTPS URL
        if not isinstance(video_uri, str) or not video_uri.startswith('https://'):
            raise Exception(f"Invalid video URI format: {video_uri}. Must be HTTPS URL.")
        
        # Check if the URL looks like a Runway URL and may have an expired JWT
        if 'dnznrvs05pmza.cloudfront.net' in video_uri and '_jwt=' in video_uri:
            logger.warning(f"🎬 Video URI appears to be a Runway URL with JWT token - may be expired")
            # Extract JWT and check expiration
            try:
                import jwt
                import time
                jwt_token = video_uri.split('_jwt=')[1]
                decoded = jwt.decode(jwt_token, options={"verify_signature": False})
                exp_time = decoded.get('exp', 0)
                current_time = time.time()
                if exp_time < current_time:
                    logger.error(f"🎬 JWT token in video URL has expired! Exp: {exp_time}, Current: {current_time}")
                    raise Exception(f"Video URL has expired JWT token. Please generate a fresh video.")
                else:
                    logger.info(f"🎬 JWT token is valid. Expires at: {exp_time}")
            except Exception as jwt_error:
                logger.warning(f"🎬 Could not validate JWT in video URL: {jwt_error}")
        
        # Ensure video URI is properly encoded
        video_uri = video_uri.strip()
        
        # Use promptText from parameters if available
        prompt_text = parameters.get("promptText", prompt)
        
        # Build request parameters exactly as shown in Runway docs
        # The error shows "videoUri" so Runway expects camelCase, not snake_case
        request_params = {
            "model": "gen4_aleph", 
            "videoUri": video_uri,  # camelCase as expected by API
            "promptText": prompt_text,  # camelCase as expected by API
            "ratio": parameters.get("ratio", "1280:720")  # Default to 16:9
        }
        
        # Log the video URI to debug
        logger.info(f"🎬 Video URI being sent: {video_uri}")
        logger.info(f"🎬 Video URI type: {type(video_uri)}")
        logger.info(f"🎬 Video URI length: {len(str(video_uri)) if video_uri else 'None'}")
        
        # Add optional parameters
        if "seed" in parameters:
            request_params["seed"] = parameters["seed"]
            
        # Add references if provided (maintain exact structure from docs)
        references = parameters.get("references", [])
        if references:
            request_params["references"] = references
            logger.info(f"🎬 VIDEO_EDIT with {len(references)} reference(s)")
        
        logger.info(f"🎬 VIDEO_EDIT Request: {request_params}")
        
        try:
            # Use RunwayML SDK video_to_video method (available in v3.9.0+)
            logger.info("🎬 Using RunwayML SDK client.video_to_video.create()...")
            logger.info(f"🎬 Request parameters: {request_params}")
            
            # Convert camelCase params to snake_case for SDK (it may expect different naming)
            sdk_params = {
                "model": "gen4_aleph",
                "video_uri": video_uri,  # SDK may expect snake_case
                "prompt_text": prompt_text,  # SDK may expect snake_case  
                "ratio": parameters.get("ratio", "1280:720")
            }
            
            # Add optional parameters
            if "seed" in parameters:
                sdk_params["seed"] = parameters["seed"]
                
            if references:
                sdk_params["references"] = references
                logger.info(f"🎬 VIDEO_EDIT with {len(references)} reference(s)")
            
            logger.info(f"🎬 SDK parameters: {sdk_params}")
            
            # Create task using SDK and wait for completion in one call
            print(f"⏳ Creating video edit task and waiting for completion...")
            logger.info(f"🎬 Calling client.video_to_video.create().wait_for_task_output()...")
            
            task = self.client.video_to_video.create(**sdk_params).wait_for_task_output()
            
            logger.info(f"🎬 SDK task completed: {task}")
            print(f"✅ VIDEO EDIT TASK COMPLETED via SDK")
            
            # Extract output URL from task response
            if hasattr(task, 'output') and task.output and len(task.output) > 0:
                output_url = task.output[0]
                logger.info(f"🎬 Video edit completed: {output_url}")
                
                return {
                    "output_url": output_url,
                    "metadata": {
                        "video_uri": video_uri,
                        "prompt_text": prompt_text,
                        "generation_type": "video_edit",
                        "task_id": getattr(task, 'id', 'unknown'),
                        "model": "gen4_aleph",
                        "ratio": sdk_params.get("ratio"),
                        "references": references,
                        "sdk_version": "3.9.0+"
                    }
                }
            else:
                # Fallback: task might be just an ID, poll manually
                task_id = getattr(task, 'id', None) or str(task)
                logger.warning(f"🎬 SDK returned unexpected format, falling back to manual polling: {task_id}")
                
                # Manual polling fallback
                max_attempts = 120
                attempt = 0
                
                while attempt < max_attempts:
                    await asyncio.sleep(2)
                    attempt += 1
                    
                    try:
                        task_status = self.client.tasks.retrieve(task_id)
                        print(f"📊 Video edit task {task_id} status: {task_status.status} (attempt {attempt}/{max_attempts})")
                        
                        if task_status.status == "SUCCEEDED":
                            if task_status.output and len(task_status.output) > 0:
                                output_url = task_status.output[0]
                                print(f"✅ VIDEO EDIT TASK COMPLETED: {output_url}")
                                
                                return {
                                    "output_url": output_url,
                                    "metadata": {
                                        "video_uri": video_uri,
                                        "prompt_text": prompt_text,
                                        "generation_type": "video_edit",
                                        "task_id": task_id,
                                        "model": "gen4_aleph",
                                        "ratio": sdk_params.get("ratio"),
                                        "attempts": attempt,
                                        "references": references,
                                        "sdk_version": "3.9.0+_fallback"
                                    }
                                }
                            else:
                                raise Exception(f"Video edit task {task_id} succeeded but no output URL returned")
                        
                        elif task_status.status == "FAILED":
                            error_msg = getattr(task_status, 'error', {})
                            failure_code = getattr(task_status, 'failure_code', 'Unknown')
                            raise Exception(f"Runway video edit task {task_id} failed: {error_msg} (Code: {failure_code})")
                        
                        elif task_status.status in ["PENDING", "RUNNING"]:
                            continue
                        else:
                            logger.warning(f"🎬 Unknown task status: {task_status.status}")
                            continue
                            
                    except Exception as poll_error:
                        logger.error(f"🎬 Error polling task {task_id}: {poll_error}")
                        if attempt >= max_attempts - 1:
                            raise Exception(f"Failed to poll video edit task {task_id}: {poll_error}")
                        continue
                
                raise Exception(f"Video edit task {task_id} timed out after {max_attempts * 2} seconds")
            
        except Exception as e:
            logger.error(f"🎬 VIDEO_EDIT error: {e}")
            raise 