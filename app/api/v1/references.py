from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.reference_service import ReferenceService
from pydantic import BaseModel, validator

router = APIRouter()

class ReferenceCreateRequest(BaseModel):
    tag: str
    image_url: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: str = "general"
    thumbnail_url: Optional[str] = None
    
    @validator('tag')
    def validate_tag(cls, v):
        if len(v) < 3:
            raise ValueError('Tag must be at least 3 characters long')
        return v.lower().replace(' ', '').replace('-', '')

class ReferenceUpdateRequest(BaseModel):
    new_tag: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    
    @validator('new_tag')
    def validate_new_tag(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError('Tag must be at least 3 characters long')
        return v.lower().replace(' ', '').replace('-', '') if v else None

class ReferenceResponse(BaseModel):
    id: str
    user_id: str
    tag: str
    display_name: Optional[str]
    image_url: str
    description: Optional[str]
    category: str
    source_type: str
    created_at: str
    updated_at: str

@router.post("/", response_model=dict)
async def create_reference(
    reference: ReferenceCreateRequest, 
    user_id: str = Query(..., description="User ID")
):
    """Create a new reference"""
    try:
        result = await ReferenceService.create_reference(
            user_id=user_id,
            tag=reference.tag,
            image_url=reference.image_url,
            display_name=reference.display_name,
            description=reference.description,
            category=reference.category,
            thumbnail_url=reference.thumbnail_url
        )
        
        if result:
            return {"success": True, "reference": result}
        else:
            raise HTTPException(status_code=400, detail="Failed to create reference")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{tag}")
async def update_reference(
    tag: str,
    reference: ReferenceUpdateRequest,
    user_id: str = Query(..., description="User ID")
):
    """Update an existing reference"""
    try:
        result = await ReferenceService.update_reference(
            user_id=user_id,
            old_tag=tag,
            new_tag=reference.new_tag,
            display_name=reference.display_name,
            description=reference.description,
            category=reference.category
        )
        
        if result:
            return {"success": True, "reference": result}
        else:
            raise HTTPException(status_code=404, detail="Reference not found")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[dict])
async def get_user_references(
    user_id: str = Query(..., description="User ID"), 
    category: Optional[str] = Query(None, description="Filter by category")
):
    """Get all references for a user, optionally filtered by category"""
    try:
        references = await ReferenceService.get_user_references(user_id, category)
        return references
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{tag}")
async def delete_reference(
    tag: str, 
    user_id: str = Query(..., description="User ID")
):
    """Delete a reference"""
    try:
        success = await ReferenceService.delete_reference(user_id, tag)
        if success:
            return {"success": True, "message": "Reference deleted"}
        else:
            raise HTTPException(status_code=404, detail="Reference not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/check/{prompt}")
async def check_references_in_prompt(prompt: str):
    """Check if a prompt contains @mentions"""
    has_refs = ReferenceService.has_references(prompt)
    mentions = []
    if has_refs:
        import re
        mentions = re.findall(r'@(\w+)', prompt)
    
    return {
        "has_references": has_refs,
        "mentions": mentions,
        "count": len(mentions)
    } 