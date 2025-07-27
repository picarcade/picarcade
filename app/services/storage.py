import uuid
import io
from typing import Optional, Tuple
from fastapi import UploadFile
from supabase import create_client, Client
from app.core.config import settings
from PIL import Image
import time
import aiohttp

class SupabaseStorageService:
    """Service for handling file uploads to Supabase Storage"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        self.bucket_name = "images"
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists"""
        try:
            # Try to get bucket info - if it fails, the bucket doesn't exist
            self.supabase.storage.get_bucket(self.bucket_name)
        except Exception:
            # Create bucket if it doesn't exist
            try:
                self.supabase.storage.create_bucket(self.bucket_name, options={
                    "public": True,  # Make bucket public for easy access
                    "file_size_limit": 50 * 1024 * 1024,  # 50MB limit
                    "allowed_mime_types": ["image/jpeg", "image/png", "image/webp", "image/gif"]
                })
                print(f"Created storage bucket: {self.bucket_name}")
            except Exception as e:
                print(f"Error creating bucket: {e}")
    
    async def upload_image(self, 
                          file: UploadFile, 
                          user_id: str = None,
                          resize_max: Optional[int] = 2048) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload an image to Supabase Storage
        
        Args:
            file: The uploaded file
            user_id: Optional user ID for organizing files
            resize_max: Maximum dimension for resizing (None to skip resize)
            
        Returns:
            Tuple of (success, file_path, public_url)
        """
        
        try:
            # Generate unique filename
            file_extension = file.filename.split('.')[-1].lower() if file.filename else 'jpg'
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Create folder structure
            timestamp = int(time.time())
            folder_path = f"uploads/{timestamp // 86400}"  # Group by day
            if user_id:
                folder_path = f"uploads/{user_id}/{timestamp // 86400}"
            
            file_path = f"{folder_path}/{unique_filename}"
            
            # Read and process the image
            content = await file.read()
            
            # Validate file type
            if not self._is_valid_image(content):
                return False, None, "Invalid image format"
            
            # Resize image if needed
            if resize_max:
                content = self._resize_image(content, resize_max)
            
            # Upload to Supabase Storage
            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=content,
                file_options={
                    "content-type": file.content_type or f"image/{file_extension}",
                    "cache-control": "3600",
                    "upsert": "true"  # Overwrite if exists
                }
            )
            
            if result:
                # Get public URL
                public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
                return True, file_path, public_url
            else:
                return False, None, "Upload failed"
                
        except Exception as e:
            print(f"Error uploading image: {e}")
            return False, None, str(e)

    async def upload_image_with_thumbnail(self, 
                                         file: UploadFile, 
                                         user_id: str = None,
                                         resize_max: Optional[int] = 2048,
                                         thumbnail_size: int = 256) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Upload an image with automatic thumbnail generation
        
        Args:
            file: The uploaded file
            user_id: Optional user ID for organizing files
            resize_max: Maximum dimension for main image resizing
            thumbnail_size: Maximum dimension for thumbnail (default 256px)
            
        Returns:
            Tuple of (success, file_path, public_url, thumbnail_url)
        """
        
        try:
            # Generate unique filename
            file_extension = file.filename.split('.')[-1].lower() if file.filename else 'jpg'
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Create folder structure
            timestamp = int(time.time())
            folder_path = f"uploads/{timestamp // 86400}"  # Group by day
            if user_id:
                folder_path = f"uploads/{user_id}/{timestamp // 86400}"
            
            file_path = f"{folder_path}/{unique_filename}"
            thumbnail_path = f"{folder_path}/thumbs/{unique_filename}"
            
            # Read and process the image
            content = await file.read()
            
            # Validate file type
            if not self._is_valid_image(content):
                return False, None, None, "Invalid image format"
            
            # Resize main image if needed
            if resize_max:
                content = self._resize_image(content, resize_max)
            
            # Generate thumbnail
            thumbnail_content = self._generate_thumbnail(content, thumbnail_size)
            
            # Upload main image
            main_result = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=content,
                file_options={
                    "content-type": file.content_type or f"image/{file_extension}",
                    "cache-control": "3600",
                    "upsert": "true"
                }
            )
            
            # Upload thumbnail
            thumb_result = self.supabase.storage.from_(self.bucket_name).upload(
                path=thumbnail_path,
                file=thumbnail_content,
                file_options={
                    "content-type": "image/jpeg",
                    "cache-control": "3600",
                    "upsert": "true"
                }
            )
            
            if main_result and thumb_result:
                # Get public URLs
                public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
                thumbnail_url = self.supabase.storage.from_(self.bucket_name).get_public_url(thumbnail_path)
                return True, file_path, public_url, thumbnail_url
            else:
                return False, None, None, "Upload failed"
                
        except Exception as e:
            print(f"Error uploading image with thumbnail: {e}")
            return False, None, None, str(e)

    async def download_and_store_image(self, 
                                     image_url: str, 
                                     user_id: str = None,
                                     resize_max: Optional[int] = 2048,
                                     thumbnail_size: int = 256) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Download an image or video from external URL and store it permanently with thumbnail
        
        Args:
            image_url: External image/video URL to download
            user_id: Optional user ID for organizing files
            resize_max: Maximum dimension for main image resizing (videos are stored as-is)
            thumbnail_size: Maximum dimension for thumbnail (videos get a placeholder)
            
        Returns:
            Tuple of (success, file_path, public_url, thumbnail_url)
        """
        
        try:
            # Download the file
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        print(f"Failed to download file: HTTP {response.status}")
                        return False, None, None, None
                    
                    content = await response.read()
                    content_type = response.headers.get('content-type', 'application/octet-stream')
            
            # Determine if it's a video or image
            is_video = any(vid_type in content_type.lower() or image_url.lower().endswith(ext) 
                          for vid_type in ['video/', 'mp4', 'webm', 'mov', 'avi']
                          for ext in ['.mp4', '.webm', '.mov', '.avi'])
            
            # Generate appropriate filename
            if is_video:
                file_extension = 'mp4'
                if '.webm' in image_url.lower() or 'webm' in content_type:
                    file_extension = 'webm'
                elif '.mov' in image_url.lower() or 'quicktime' in content_type:
                    file_extension = 'mov'
                content_type = f'video/{file_extension}'
            else:
                # Validate image content
                if not self._is_valid_image(content):
                    print("Downloaded content is not a valid image")
                    return False, None, None, None
                
                file_extension = 'jpg'
                if 'png' in content_type:
                    file_extension = 'png'
                elif 'webp' in content_type:
                    file_extension = 'webp'
            
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Create folder structure
            timestamp = int(time.time())
            folder_path = f"uploads/{timestamp // 86400}"  # Group by day
            if user_id:
                folder_path = f"uploads/{user_id}/{timestamp // 86400}"
            
            file_path = f"{folder_path}/{unique_filename}"
            thumbnail_path = f"{folder_path}/thumbs/{unique_filename}"
            
            # Process content based on type
            if is_video:
                # Store video as-is, create a placeholder thumbnail
                thumbnail_content = self._create_video_placeholder_thumbnail(thumbnail_size)
            else:
                # Resize main image if needed
                if resize_max:
                    content = self._resize_image(content, resize_max)
                # Generate thumbnail
                thumbnail_content = self._generate_thumbnail(content, thumbnail_size)
            
            # Upload main file
            main_result = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=content,
                file_options={
                    "content-type": content_type,
                    "cache-control": "3600",
                    "upsert": "true"
                }
            )
            
            # Upload thumbnail
            thumb_result = self.supabase.storage.from_(self.bucket_name).upload(
                path=thumbnail_path,
                file=thumbnail_content,
                file_options={
                    "content-type": "image/jpeg",
                    "cache-control": "3600",
                    "upsert": "true"
                }
            )
            
            if main_result and thumb_result:
                # Get public URLs
                public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
                thumbnail_url = self.supabase.storage.from_(self.bucket_name).get_public_url(thumbnail_path)
                print(f"Successfully stored {'video' if is_video else 'image'}: {public_url}")
                print(f"Generated thumbnail: {thumbnail_url}")
                return True, file_path, public_url, thumbnail_url
            else:
                print("Failed to upload file or thumbnail")
                return False, None, None, None
                
        except Exception as e:
            print(f"Error downloading and storing file: {e}")
            return False, None, None, None

    def _generate_thumbnail(self, content: bytes, max_dimension: int) -> bytes:
        """Generate thumbnail from image content"""
        try:
            with Image.open(io.BytesIO(content)) as img:
                # Convert to RGB if necessary (for JPEG)
                if img.mode in ('RGBA', 'P'):
                    # Create white background for transparent images
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calculate thumbnail dimensions maintaining aspect ratio
                width, height = img.size
                if width <= max_dimension and height <= max_dimension:
                    # Image is already small enough
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=85, optimize=True)
                    return output.getvalue()
                
                # Resize maintaining aspect ratio
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * max_dimension / width)
                else:
                    new_height = max_dimension
                    new_width = int(width * max_dimension / height)
                
                thumbnail = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save as JPEG with high quality for thumbnails
                output = io.BytesIO()
                thumbnail.save(output, format='JPEG', quality=85, optimize=True)
                return output.getvalue()
                
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            # Return original content as fallback
            return content
    
    def _is_valid_image(self, content: bytes) -> bool:
        """Check if the file content is a valid image"""
        try:
            with Image.open(io.BytesIO(content)) as img:
                img.verify()
            return True
        except Exception:
            return False
    
    def _resize_image(self, content: bytes, max_dimension: int) -> bytes:
        """Resize image while maintaining aspect ratio"""
        try:
            with Image.open(io.BytesIO(content)) as img:
                # Convert to RGB if necessary (for JPEG)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Calculate new dimensions
                width, height = img.size
                if width <= max_dimension and height <= max_dimension:
                    # No resize needed
                    return content
                
                # Resize maintaining aspect ratio
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * max_dimension / width)
                else:
                    new_height = max_dimension
                    new_width = int(width * max_dimension / height)
                
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save to bytes
                output = io.BytesIO()
                resized_img.save(output, format='JPEG', quality=85, optimize=True)
                return output.getvalue()
                
        except Exception as e:
            print(f"Error resizing image: {e}")
            return content  # Return original if resize fails
    
    async def delete_image(self, file_path: str) -> bool:
        """Delete an image from storage"""
        try:
            self.supabase.storage.from_(self.bucket_name).remove([file_path])
            return True
        except Exception as e:
            print(f"Error deleting image: {e}")
            return False
    
    def get_public_url(self, file_path: str) -> str:
        """Get public URL for a stored image"""
        return self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)

    def _create_video_placeholder_thumbnail(self, max_dimension: int) -> bytes:
        """Create a placeholder thumbnail for video files"""
        try:
            # Create a simple placeholder image with a play icon
            placeholder = Image.new('RGB', (max_dimension, max_dimension), (64, 64, 64))
            
            # Add a simple play triangle in the center
            from PIL import ImageDraw
            draw = ImageDraw.Draw(placeholder)
            
            # Calculate triangle points for play icon
            center_x, center_y = max_dimension // 2, max_dimension // 2
            triangle_size = max_dimension // 4
            
            triangle_points = [
                (center_x - triangle_size // 2, center_y - triangle_size // 2),
                (center_x - triangle_size // 2, center_y + triangle_size // 2),
                (center_x + triangle_size // 2, center_y)
            ]
            
            draw.polygon(triangle_points, fill=(255, 255, 255))
            
            # Save as JPEG
            output = io.BytesIO()
            placeholder.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            print(f"Error creating video placeholder: {e}")
            # Return a simple gray square as fallback
            fallback = Image.new('RGB', (max_dimension, max_dimension), (128, 128, 128))
            output = io.BytesIO()
            fallback.save(output, format='JPEG', quality=85)
            return output.getvalue()

# Global storage service instance
storage_service = SupabaseStorageService() 