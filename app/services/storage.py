import uuid
import io
from typing import Optional, Tuple
from fastapi import UploadFile
from supabase import create_client, Client
from app.core.config import settings
from PIL import Image
import time

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

# Global storage service instance
storage_service = SupabaseStorageService() 