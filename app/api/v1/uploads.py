from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request
from typing import Optional
import logging

from app.services.storage import storage_service
from app.core.logging import api_logger

router = APIRouter()

@router.post("/image")
async def upload_image(
    request: Request,
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
    
    # Debug logging
    print(f"[DEBUG] Upload endpoint received:")
    print(f"[DEBUG]   Content-Type: {request.headers.get('content-type', 'None')}")
    print(f"[DEBUG]   file: {file.filename if file else 'None'}")
    print(f"[DEBUG]   file.content_type: {file.content_type if file else 'None'}")
    print(f"[DEBUG]   file.size: {getattr(file, 'size', 'unknown')}")
    print(f"[DEBUG]   user_id: {user_id}")
    print(f"[DEBUG]   resize_max: {resize_max}")
    
    # Check if file is actually received
    if not file:
        print(f"[ERROR] No file received in upload request")
        raise HTTPException(status_code=422, detail="No file provided")
    
    if not file.filename:
        print(f"[ERROR] File received but no filename")
        raise HTTPException(status_code=422, detail="File must have a filename")
    
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
        # Upload the image with thumbnail generation
        success, file_path, public_url, thumbnail_url = await storage_service.upload_image_with_thumbnail(
            file=file,
            user_id=user_id,
            resize_max=resize_max,
            thumbnail_size=256  # Generate 256px thumbnails
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {thumbnail_url}"  # thumbnail_url contains error message on failure
            )
        
        # Log successful upload
        api_logger.logger.info(f"Image uploaded successfully: {file_path}")
        
        return {
            "success": True,
            "file_path": file_path,
            "public_url": public_url,
            "thumbnail_url": thumbnail_url,
            "filename": file.filename,
            "content_type": file.content_type,
            "message": "Image uploaded successfully with thumbnail"
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