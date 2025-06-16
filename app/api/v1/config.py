"""
Configuration Management API Endpoints

Provides endpoints to view and update model routing configuration without
restarting the application.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import yaml
import os
from datetime import datetime

from app.core.model_config import model_config, reload_model_config
from app.api.v1.auth import get_current_user

router = APIRouter()

class ModelConfigResponse(BaseModel):
    """Response model for configuration info"""
    config_file: str
    last_loaded: Optional[str]
    version: str
    description: str
    total_image_models: int
    total_video_models: int
    routing_rules_enabled: int

class ModelUpdateRequest(BaseModel):
    """Request model for updating a single model"""
    prompt_type: str
    model: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

class KeywordUpdateRequest(BaseModel):
    """Request model for updating keywords"""
    keyword_type: str  # "video", "audio", "edit"
    keywords: List[str]

@router.get("/config/info", response_model=ModelConfigResponse)
async def get_config_info():
    """Get information about current model configuration"""
    try:
        info = model_config.get_config_info()
        return ModelConfigResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config info: {str(e)}")

@router.get("/config/models")
async def get_all_models():
    """Get all model configurations"""
    try:
        models = model_config.config.get("model_routing", {}).get("models", {})
        return {
            "image_models": models.get("image_generation", {}),
            "video_models": models.get("video_generation", {}),
            "routing_rules": model_config.config.get("model_routing", {}).get("routing_rules", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

@router.get("/config/model/{prompt_type}")
async def get_model_config(prompt_type: str):
    """Get configuration for a specific prompt type"""
    try:
        image_models = model_config.config.get("model_routing", {}).get("models", {}).get("image_generation", {})
        video_models = model_config.config.get("model_routing", {}).get("models", {}).get("video_generation", {})
        
        all_models = {**image_models, **video_models}
        
        if prompt_type not in all_models:
            raise HTTPException(status_code=404, detail=f"Prompt type '{prompt_type}' not found")
        
        return {
            "prompt_type": prompt_type,
            "config": all_models[prompt_type],
            "current_model": model_config.get_model_for_type(prompt_type),
            "parameters": model_config.get_model_parameters(prompt_type, all_models[prompt_type].get("model", ""))
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model config: {str(e)}")

@router.put("/config/model")
async def update_model_config(
    request: ModelUpdateRequest,
    user = Depends(get_current_user)
):
    """Update model configuration for a specific prompt type"""
    try:
        # Get current config
        current_config = model_config.config
        models = current_config.get("model_routing", {}).get("models", {})
        
        # Find which category the prompt type belongs to
        image_models = models.get("image_generation", {})
        video_models = models.get("video_generation", {})
        
        if request.prompt_type in image_models:
            target_models = image_models
            category = "image_generation"
        elif request.prompt_type in video_models:
            target_models = video_models
            category = "video_generation"
        else:
            raise HTTPException(status_code=404, detail=f"Prompt type '{request.prompt_type}' not found")
        
        # Update the model configuration
        if request.prompt_type not in target_models:
            target_models[request.prompt_type] = {}
        
        target_models[request.prompt_type]["model"] = request.model
        
        if request.description:
            target_models[request.prompt_type]["description"] = request.description
        
        if request.parameters:
            target_models[request.prompt_type]["parameters"] = request.parameters
        
        # Update last modified timestamp
        current_config["model_routing"]["last_updated"] = datetime.now().isoformat()
        
        # Save the updated configuration
        config_path = model_config.config_path
        with open(config_path, 'w') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                yaml.dump(current_config, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(current_config, f, indent=2)
        
        # Reload the configuration
        reload_model_config()
        
        return {
            "message": f"Model for {request.prompt_type} updated to {request.model}",
            "prompt_type": request.prompt_type,
            "old_model": target_models[request.prompt_type].get("model", "unknown"),
            "new_model": request.model,
            "config_file": config_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update model config: {str(e)}")

@router.put("/config/keywords")
async def update_keywords(
    request: KeywordUpdateRequest,
    user = Depends(get_current_user)
):
    """Update detection keywords"""
    try:
        valid_types = ["video", "audio", "edit"]
        if request.keyword_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid keyword type. Must be one of: {valid_types}")
        
        # Get current config
        current_config = model_config.config
        routing_rules = current_config.get("model_routing", {}).get("routing_rules", {})
        
        # Update the appropriate keyword list
        if request.keyword_type == "video":
            if "video_detection" not in routing_rules:
                routing_rules["video_detection"] = {}
            routing_rules["video_detection"]["video_keywords"] = request.keywords
        elif request.keyword_type == "audio":
            if "audio_detection" not in routing_rules:
                routing_rules["audio_detection"] = {}
            routing_rules["audio_detection"]["audio_keywords"] = request.keywords
        elif request.keyword_type == "edit":
            if "edit_detection" not in routing_rules:
                routing_rules["edit_detection"] = {}
            routing_rules["edit_detection"]["edit_keywords"] = request.keywords
        
        # Update last modified timestamp
        current_config["model_routing"]["last_updated"] = datetime.now().isoformat()
        
        # Save the updated configuration
        config_path = model_config.config_path
        with open(config_path, 'w') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                yaml.dump(current_config, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(current_config, f, indent=2)
        
        # Reload the configuration
        reload_model_config()
        
        return {
            "message": f"{request.keyword_type.title()} keywords updated successfully",
            "keyword_type": request.keyword_type,
            "keywords": request.keywords,
            "config_file": config_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update keywords: {str(e)}")

@router.post("/config/reload")
async def reload_configuration(user = Depends(get_current_user)):
    """Reload configuration from file"""
    try:
        old_version = model_config.config.get("model_routing", {}).get("version", "unknown")
        reload_model_config()
        new_version = model_config.config.get("model_routing", {}).get("version", "unknown")
        
        return {
            "message": "Configuration reloaded successfully",
            "config_file": model_config.config_path,
            "old_version": old_version,
            "new_version": new_version,
            "reloaded_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload config: {str(e)}")

@router.get("/config/test/{prompt_type}")
async def test_model_routing(
    prompt_type: str,
    prompt: str = "test prompt",
    total_references: int = 0
):
    """Test model routing for a given prompt type and reference count"""
    try:
        model = model_config.get_model_for_type(prompt_type, total_references)
        parameters = model_config.get_model_parameters(prompt_type, model)
        
        return {
            "prompt_type": prompt_type,
            "prompt": prompt,
            "total_references": total_references,
            "selected_model": model,
            "parameters": parameters,
            "routing_info": {
                "config_file": model_config.config_path,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test routing: {str(e)}")

@router.get("/config/export")
async def export_configuration(format: str = "yaml"):
    """Export current configuration"""
    try:
        if format.lower() not in ["yaml", "json"]:
            raise HTTPException(status_code=400, detail="Format must be 'yaml' or 'json'")
        
        config = model_config.config
        
        if format.lower() == "yaml":
            return {
                "format": "yaml",
                "content": yaml.dump(config, default_flow_style=False, sort_keys=False),
                "filename": f"model_config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            }
        else:
            return {
                "format": "json",
                "content": json.dumps(config, indent=2),
                "filename": f"model_config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export config: {str(e)}")