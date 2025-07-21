# app/services/generators/google_ai.py
import asyncio
import time
import logging
import os
from typing import Dict, Any, Optional, List
from app.services.generators.base import BaseGenerator
from app.models.generation import GenerationResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

class VertexAIGenerator(BaseGenerator):
    """Vertex AI generator implementation for VEO3 video generation using google-genai SDK"""
    
    def __init__(self):
        super().__init__(None)  # No API key needed for Vertex AI
        
        # Configure environment variables for google-genai SDK
        if not settings.google_cloud_project:
            raise ValueError("Google Cloud project not configured")
        
        # AVOID setting global environment variables that interfere with Replicate
        # Store configuration locally instead
        self.google_project = settings.google_cloud_project
        self.google_location = settings.google_cloud_location or "us-central1"
        
        # Initialize the client (will be done in async context)
        self.client = None
        self.model_name = "veo-3.0-generate-preview"
    
    def _ensure_client(self):
        """Initialize the google-genai client if not already done"""
        if self.client is None:
            try:
                from google import genai
                
                # Create client with explicit configuration instead of environment variables
                self.client = genai.Client(
                    vertexai=True,
                    project=self.google_project,
                    location=self.google_location
                )
                logger.info("Google GenAI client initialized successfully with explicit config")
            except ImportError:
                raise ImportError("google-genai package not installed. Run: pip install --upgrade google-genai")
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI client: {e}")
                raise
        return self.client
    
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available models from Google GenAI"""
        def sync_call():
            try:
                client = self._ensure_client()
                # For now, return VEO-3 as the primary model
                return [{
                    "name": self.model_name,
                    "display_name": "VEO 3.0 Generate Preview",
                    "description": "Video generation with audio support",
                    "model_type": "video_generation"
                }]
            except Exception as e:
                logger.error(f"Error listing models: {e}")
                return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_call)
    
    async def find_veo_models(self) -> List[Dict[str, Any]]:
        """Find all VEO-related models"""
        return await self.list_available_models()

    @BaseGenerator._measure_time
    async def generate(self, 
                      prompt: str, 
                      parameters: Dict[str, Any],
                      generation_id: str = None) -> GenerationResponse:
        """Generate video using VEO3 with google-genai SDK"""
        try:
            logger.info(f"Starting VEO3 generation with prompt: {prompt[:100]}...")
            
            # Generate video using google-genai SDK
            result = await self._generate_veo3_video(prompt, parameters)
            
            # Extract output URL for compatibility
            output_url = result.get("output_url")
            if not output_url and result.get("videos"):
                output_url = result["videos"][0].get("gcs_uri")
            
            return GenerationResponse(
                success=True,
                generation_id=generation_id,
                output_url=output_url,
                model_used=self.model_name,
                execution_time=result.get("generation_time", 0),
                metadata={
                    "generator": "google_genai",
                    "model": self.model_name,
                    "total_videos": result.get("total_videos", 0),
                    "videos": result.get("videos", []),
                    "operation_name": result.get("operation_name"),
                    "parameters": parameters
                }
            )
            
        except Exception as e:
            logger.error(f"VEO3 generation failed: {e}")
            return GenerationResponse(
                success=False,
                generation_id=generation_id,
                error_message=str(e),
                model_used=self.model_name,
                execution_time=0,
                metadata={
                    "generator": "google_genai",
                    "model": self.model_name,
                    "error_type": type(e).__name__
                }
            )

    async def _generate_veo3_video(self, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate video using VEO3 with google-genai SDK"""
        
        def sync_call():
            try:
                from google import genai
                from google.genai.types import GenerateVideosConfig, Image
                
                # Initialize client
                client = self._ensure_client()
                start_time = time.time()
                
                logger.info(f"Starting VEO3 video generation with prompt: {prompt[:100]}...")
                
                # Build the generation config
                config_params = {}
                
                # Aspect ratio (default 16:9)
                aspect_ratio = parameters.get("aspect_ratio", "16:9")
                if aspect_ratio in ["16:9", "9:16"]:
                    config_params["aspect_ratio"] = aspect_ratio
                
                # Output GCS URI - use a default bucket if not provided
                output_gcs_uri = parameters.get("output_gcs_uri")
                if not output_gcs_uri:
                    # Check for custom bucket name from environment
                    custom_bucket = os.environ.get("VEO3_OUTPUT_BUCKET")
                    skip_bucket_check = settings.veo3_skip_bucket_check
                    
                    if custom_bucket:
                        bucket_name = custom_bucket
                        logger.info(f"Using custom output bucket from environment: {bucket_name}")
                    else:
                        bucket_name = f"{settings.google_cloud_project}-veo3-output"
                    
                    # Only check bucket existence if not skipping checks
                    if not skip_bucket_check:
                        self._ensure_gcs_bucket_exists(bucket_name)
                    else:
                        logger.info(f"Skipping bucket existence check for: {bucket_name}")
                    
                    timestamp = str(int(time.time()))
                    output_gcs_uri = f"gs://{bucket_name}/videos/{timestamp}/"
                    logger.info(f"Using output GCS URI: {output_gcs_uri}")
                
                config_params["output_gcs_uri"] = output_gcs_uri
                
                # Create config object
                config = GenerateVideosConfig(**config_params)
                
                # Prepare generation parameters
                generation_params = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "config": config
                }
                
                # Handle image-to-video if image provided
                image_url = parameters.get("image")
                if image_url:
                    logger.info(f"Adding image input for image-to-video: {image_url}")
                    
                    # Determine mime type from URL
                    mime_type = "image/jpeg"  # default
                    if image_url.lower().endswith('.png'):
                        mime_type = "image/png"
                    elif image_url.lower().endswith('.webp'):
                        mime_type = "image/webp"
                    
                    # For google-genai, image should be a GCS URI
                    if image_url.startswith('gs://'):
                        # Already a GCS URI
                        generation_params["image"] = Image(
                            gcs_uri=image_url,
                            mime_type=mime_type
                        )
                    else:
                        # External URL - upload to GCS first
                        logger.info(f"Uploading external image to GCS: {image_url}")
                        gcs_uri = self._upload_image_to_gcs(image_url, mime_type)
                        generation_params["image"] = Image(
                            gcs_uri=gcs_uri,
                            mime_type=mime_type
                        )
                
                # Start the generation operation
                logger.info(f"Starting VEO3 generation operation...")
                operation = client.models.generate_videos(**generation_params)
                
                logger.info(f"VEO3 operation started: {operation.name if hasattr(operation, 'name') else 'unknown'}")
                
                # Poll for completion (like in Google's example)
                max_wait_time = 300  # 5 minutes
                poll_interval = 15   # 15 seconds
                elapsed_time = 0
                
                while not operation.done and elapsed_time < max_wait_time:
                    logger.info(f"VEO3 generation in progress... (elapsed: {elapsed_time}s)")
                    time.sleep(poll_interval)
                    elapsed_time += poll_interval
                    
                    # Refresh operation status
                    operation = client.operations.get(operation)
                
                if not operation.done:
                    raise TimeoutError(f"VEO3 generation timed out after {max_wait_time} seconds")
                
                if operation.error:
                    raise Exception(f"VEO3 generation failed: {operation.error}")
                
                # Extract results
                videos = []
                if operation.response and hasattr(operation.result, 'generated_videos'):
                    for video in operation.result.generated_videos:
                        video_uri = video.video.uri if hasattr(video, 'video') and hasattr(video.video, 'uri') else None
                        if video_uri:
                            videos.append({
                                "gcs_uri": video_uri,
                                "mime_type": "video/mp4",
                                "output_url": video_uri  # For compatibility
                            })
                            logger.info(f"Generated video URI: {video_uri}")
                
                total_time = time.time() - start_time
                logger.info(f"VEO3 generation completed in {total_time:.2f} seconds")
                
                return {
                    "videos": videos,
                    "output_url": videos[0]["gcs_uri"] if videos else None,
                    "generation_time": total_time,
                    "total_videos": len(videos),
                    "operation_name": operation.name if hasattr(operation, 'name') else 'unknown'
                }
                
            except ImportError as e:
                logger.error(f"Google GenAI SDK not available: {e}")
                raise Exception("google-genai package not installed. Run: pip install --upgrade google-genai")
            except Exception as e:
                logger.error(f"VEO3 generation error: {e}")
                raise e
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_call)
    
    def _ensure_gcs_bucket_exists(self, bucket_name: str) -> None:
        """Ensure a GCS bucket exists, create it if it doesn't"""
        from google.cloud import storage
        
        try:
            storage_client = storage.Client(project=settings.google_cloud_project)
            bucket = storage_client.bucket(bucket_name)
            
            if not bucket.exists():
                logger.info(f"Creating GCS bucket: {bucket_name}")
                try:
                    bucket = storage_client.create_bucket(bucket_name, location="us-central1")
                    logger.info(f"Successfully created bucket: {bucket_name}")
                except Exception as create_error:
                    if "does not have storage.buckets.create access" in str(create_error):
                        error_msg = f"""
❌ BUCKET CREATION FAILED - PERMISSION DENIED ❌

The service account 'vertexairunner@directed-smoke-388109.iam.gserviceaccount.com' 
does not have permission to create GCS buckets.

🔧 SOLUTIONS:

Option 1: Grant permissions (Recommended)
Run this command in Google Cloud Console:
gcloud projects add-iam-policy-binding directed-smoke-388109 \\
  --member="serviceAccount:vertexairunner@directed-smoke-388109.iam.gserviceaccount.com" \\
  --role="roles/storage.admin"

Option 2: Pre-create buckets manually
Create these buckets in Google Cloud Console:
• {settings.google_cloud_project}-veo3-output
• {settings.google_cloud_project}-veo3-images

Option 3: Use existing bucket
Set environment variable: VEO3_OUTPUT_BUCKET=your-existing-bucket-name

                        """
                        logger.error(error_msg)
                        raise ValueError(f"Bucket creation permission denied: {bucket_name}. Please see logs for solutions.")
                    else:
                        raise create_error
            else:
                logger.debug(f"Bucket already exists: {bucket_name}")
                
        except Exception as e:
            logger.error(f"Failed to create/access bucket {bucket_name}: {e}")
            raise ValueError(f"Could not ensure bucket exists: {bucket_name} - {e}")

    def _upload_image_to_gcs(self, image_url: str, mime_type: str) -> str:
        """Upload an external image to GCS and return the GCS URI"""
        import requests
        from google.cloud import storage
        import tempfile
        import uuid
        
        try:
            # Create GCS client
            storage_client = storage.Client(project=settings.google_cloud_project)
            
            # Define bucket name
            bucket_name = f"{settings.google_cloud_project}-veo3-images"
            
            # Check if we should skip bucket existence checks
            skip_bucket_check = settings.veo3_skip_bucket_check
            
            # Only check bucket existence if not skipping checks
            if not skip_bucket_check:
                self._ensure_gcs_bucket_exists(bucket_name)
            else:
                logger.info(f"Skipping bucket existence check for: {bucket_name}")
            
            bucket = storage_client.bucket(bucket_name)
            
            # Download image from URL
            logger.info(f"Downloading image from: {image_url}")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Generate unique filename
            file_extension = ".jpg"
            if mime_type == "image/png":
                file_extension = ".png"
            elif mime_type == "image/webp":
                file_extension = ".webp"
                
            filename = f"images/{uuid.uuid4().hex}{file_extension}"
            
            # Upload to GCS
            blob = bucket.blob(filename)
            blob.upload_from_string(response.content, content_type=mime_type)
            
            gcs_uri = f"gs://{bucket_name}/{filename}"
            logger.info(f"Successfully uploaded image to GCS: {gcs_uri}")
            
            return gcs_uri
            
        except Exception as e:
            logger.error(f"Failed to upload image to GCS: {e}")
            raise ValueError(f"Could not upload image to GCS: {e}")

    def _create_generation_id(self) -> str:
        """Create a unique generation ID"""
        import uuid
        return str(uuid.uuid4())

    @property
    def generator_name(self) -> str:
        return "vertex_ai" 