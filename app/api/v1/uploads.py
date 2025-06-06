from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
import logging

from app.services.storage import storage_service
from app.core.logging import api_logger

router = APIRouter()

@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    resize_max: Optional[int] = Form(2048)
):
    """
    Upload an image to Supabase Storage
    
    Args:
        file: The image file to upload
        user_id: Optional user ID for organizing files
        resize_max: Maximum dimension for auto-resizing (default: 2048px)
    
    Returns:
        Upload result with file URL and metadata
    """
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (JPEG, PNG, WebP, or GIF)"
        )
    
    # Validate file size (50MB limit)
    max_size = 50 * 1024 * 1024  # 50MB
    if hasattr(file, 'size') and file.size > max_size:
        raise HTTPException(
            status_code=400,
            detail="File size must be less than 50MB"
        )
    
    try:
        # Upload the image
        success, file_path, public_url = await storage_service.upload_image(
            file=file,
            user_id=user_id,
            resize_max=resize_max
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {public_url}"  # public_url contains error message on failure
            )
        
        # Log successful upload
        api_logger.logger.info(f"Image uploaded successfully: {file_path}")
        
        return {
            "success": True,
            "file_path": file_path,
            "public_url": public_url,
            "filename": file.filename,
            "content_type": file.content_type,
            "message": "Image uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.logger.error(f"Error uploading image: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during upload"
        )

@router.delete("/image/{file_path:path}")
async def delete_image(file_path: str):
    """
    Delete an image from storage
    
    Args:
        file_path: The path of the file to delete
    """
    
    try:
        success = await storage_service.delete_image(file_path)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="File not found or could not be deleted"
            )
        
        return {
            "success": True,
            "message": "Image deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.logger.error(f"Error deleting image: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during deletion"
        ) 