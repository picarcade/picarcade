"""
Model Configuration Management System

This module handles loading and managing model routing configurations from external files.
Supports both JSON and YAML configuration formats for flexibility.
"""

import json
import yaml
import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ModelConfigManager:
    """Manages model routing configuration from external files"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self.config: Dict[str, Any] = {}
        self.last_loaded: Optional[datetime] = None
        self.load_config()
    
    def _find_config_file(self) -> str:
        """Find the model configuration file"""
        base_dir = Path(__file__).parent.parent.parent  # Go up to project root
        
        # Check for YAML first, then JSON
        yaml_path = base_dir / "config" / "model_routing.yaml"
        json_path = base_dir / "config" / "model_routing.json"
        
        if yaml_path.exists():
            return str(yaml_path)
        elif json_path.exists():
            return str(json_path)
        else:
            # Create config directory if it doesn't exist
            config_dir = base_dir / "config"
            config_dir.mkdir(exist_ok=True)
            
            # Return YAML path as default (will be created with defaults)
            return str(yaml_path)
    
    def load_config(self) -> None:
        """Load configuration from file"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found at {self.config_path}, using defaults")
                self.config = self._get_default_config()
                self._save_default_config()
                return
            
            with open(self.config_path, 'r') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    self.config = yaml.safe_load(f)
                else:
                    self.config = json.load(f)
            
            self.last_loaded = datetime.now()
            logger.info(f"Model configuration loaded from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model config from {self.config_path}: {e}")
            logger.info("Using default configuration")
            self.config = self._get_default_config()
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        logger.info("Reloading model configuration...")
        self.load_config()
    
    def get_model_for_type(self, prompt_type: str, total_references: int = 0) -> str:
        """Get the model to use for a specific prompt type"""
        try:
            # Get base model mapping
            image_models = self.config.get("model_routing", {}).get("models", {}).get("image_generation", {})
            video_models = self.config.get("model_routing", {}).get("models", {}).get("video_generation", {})
            
            all_models = {**image_models, **video_models}
            
            if prompt_type not in all_models:
                logger.warning(f"Unknown prompt type: {prompt_type}, using default")
                return self._get_default_model(prompt_type)
            
            model_config = all_models[prompt_type]
            base_model = model_config.get("model", "black-forest-labs/flux-1.1-pro")
            
            # Check special routing rules
            routing_rules = self.config.get("model_routing", {}).get("routing_rules", {})
            
            # Multi-reference routing rule
            multi_ref_config = routing_rules.get("multi_reference_routing", {})
            if (multi_ref_config.get("enabled", True) and 
                total_references >= multi_ref_config.get("threshold", 2) and
                prompt_type in multi_ref_config.get("applies_to", [])):
                
                override_model = multi_ref_config.get("target_model", "runway_gen4_image")
                logger.debug(f"Multi-reference routing: {total_references} refs -> {override_model}")
                return override_model
            
            return base_model
            
        except Exception as e:
            logger.error(f"Error getting model for type {prompt_type}: {e}")
            return self._get_default_model(prompt_type)
    
    def get_model_parameters(self, prompt_type: str, model: str) -> Dict[str, Any]:
        """Get model parameters for a specific prompt type and model"""
        try:
            # Get base model mapping
            image_models = self.config.get("model_routing", {}).get("models", {}).get("image_generation", {})
            video_models = self.config.get("model_routing", {}).get("models", {}).get("video_generation", {})
            
            all_models = {**image_models, **video_models}
            
            if prompt_type in all_models:
                model_config = all_models[prompt_type]
                return model_config.get("parameters", {})
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting model parameters for {prompt_type}: {e}")
            return {}
    
    def get_generator_for_type(self, prompt_type: str) -> str:
        """Get the generator to use for a specific prompt type"""
        try:
            # Get base model mapping
            image_models = self.config.get("model_routing", {}).get("models", {}).get("image_generation", {})
            video_models = self.config.get("model_routing", {}).get("models", {}).get("video_generation", {})
            
            all_models = {**image_models, **video_models}
            
            if prompt_type not in all_models:
                logger.warning(f"Unknown prompt type: {prompt_type}, using default generator")
                return "replicate"  # Default generator
            
            model_config = all_models[prompt_type]
            generator = model_config.get("generator", "replicate")  # Default to replicate
            
            return generator
            
        except Exception as e:
            logger.error(f"Error getting generator for type {prompt_type}: {e}")
            return "replicate"  # Default generator
    
    def get_audio_keywords(self) -> List[str]:
        """Get audio detection keywords"""
        try:
            routing_rules = self.config.get("model_routing", {}).get("routing_rules", {})
            audio_config = routing_rules.get("audio_detection", {})
            return audio_config.get("audio_keywords", [])
        except Exception as e:
            logger.error(f"Error getting audio keywords: {e}")
            return []
    
    def get_video_keywords(self) -> List[str]:
        """Get video detection keywords"""
        try:
            routing_rules = self.config.get("model_routing", {}).get("routing_rules", {})
            video_config = routing_rules.get("video_detection", {})
            return video_config.get("video_keywords", [])
        except Exception as e:
            logger.error(f"Error getting video keywords: {e}")
            return []
    
    def get_edit_keywords(self) -> List[str]:
        """Get edit detection keywords"""
        try:
            routing_rules = self.config.get("model_routing", {}).get("routing_rules", {})
            edit_config = routing_rules.get("edit_detection", {})
            return edit_config.get("edit_keywords", [])
        except Exception as e:
            logger.error(f"Error getting edit keywords: {e}")
            return []
    
    def get_fallback_model(self, prompt_type: str) -> str:
        """Get fallback model for a prompt type"""
        try:
            image_models = self.config.get("model_routing", {}).get("models", {}).get("image_generation", {})
            video_models = self.config.get("model_routing", {}).get("models", {}).get("video_generation", {})
            
            all_models = {**image_models, **video_models}
            
            if prompt_type in all_models:
                return all_models[prompt_type].get("fallback_model", self._get_default_model(prompt_type))
            
            return self._get_default_model(prompt_type)
            
        except Exception as e:
            logger.error(f"Error getting fallback model for {prompt_type}: {e}")
            return self._get_default_model(prompt_type)
    
    def _get_default_model(self, prompt_type: str) -> str:
        """Get default model based on prompt type"""
        if "VIDEO" in prompt_type:
            return "minimax/video-01"
        elif "EDIT" in prompt_type and "REF" not in prompt_type:
            return "black-forest-labs/flux-kontext-max"
        elif "REF" in prompt_type:
            return "runway_gen4_image"
        else:
            return "black-forest-labs/flux-1.1-pro"
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when no config file exists"""
        return {
            "model_routing": {
                "description": "Default model routing configuration",
                "version": "1.0.0",
                "models": {
                    "image_generation": {
                        "NEW_IMAGE": {"model": "black-forest-labs/flux-1.1-pro"},
                        "NEW_IMAGE_REF": {"model": "runway_gen4_image"},
                        "EDIT_IMAGE": {"model": "black-forest-labs/flux-kontext-max"},
                        "EDIT_IMAGE_REF": {"model": "runway_gen4_image"},
                        "EDIT_IMAGE_ADD_NEW": {"model": "runway_gen4_image"},
                        "EDIT_IMAGE_REMOVE": {"model": "runway_gen4_image"},
                        "EDIT_STYLE": {"model": "runway_gen4_image"},
                        "EDIT_STYLE_REF": {"model": "runway_gen4_image"},
                        "EDIT_FACE_SWAP": {"model": "runway_gen4_image"},
                        "VIRTUAL_TRYON": {"model": "runway_gen4_image"}
                    },
                    "video_generation": {
                        "NEW_VIDEO": {"model": "veo-3.0-generate-preview", "generator": "google_ai"},
                        "NEW_VIDEO_REF": {"model": "veo-3.0-generate-preview", "generator": "google_ai"},
                        "IMAGE_TO_VIDEO": {"model": "veo-3.0-generate-preview", "generator": "google_ai"},
                        "IMAGE_TO_VIDEO_WITH_AUDIO": {"model": "veo-3.0-generate-preview", "generator": "google_ai"},
                        "EDIT_IMAGE_REF_TO_VIDEO": {"model": "veo-3.0-generate-preview", "generator": "google_ai"},
                        "EDIT_VIDEO": {"model": "runway_gen4_video"},
                        "EDIT_VIDEO_REF": {"model": "runway_gen4_video"}
                    }
                },
                "routing_rules": {
                    "multi_reference_routing": {
                        "enabled": True,
                        "threshold": 2,
                        "target_model": "runway_gen4_image",
                        "applies_to": ["NEW_IMAGE_REF", "EDIT_IMAGE_REF"]
                    }
                }
            }
        }
    
    def _save_default_config(self) -> None:
        """Save default configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
                else:
                    json.dump(self.config, f, indent=2)
            
            logger.info(f"Default configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save default config: {e}")
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get information about the current configuration"""
        model_routing = self.config.get("model_routing", {})
        
        return {
            "config_file": self.config_path,
            "last_loaded": self.last_loaded.isoformat() if self.last_loaded else None,
            "version": model_routing.get("version", "unknown"),
            "description": model_routing.get("description", ""),
            "total_image_models": len(model_routing.get("models", {}).get("image_generation", {})),
            "total_video_models": len(model_routing.get("models", {}).get("video_generation", {})),
            "routing_rules_enabled": len([
                rule for rule in model_routing.get("routing_rules", {}).values()
                if isinstance(rule, dict) and rule.get("enabled", False)
            ])
        }

# Global configuration manager instance
model_config = ModelConfigManager()

def reload_model_config():
    """Reload the global model configuration"""
    global model_config
    model_config.reload_config()

def get_model_for_type(prompt_type: str, total_references: int = 0) -> str:
    """Get model for prompt type using global config"""
    return model_config.get_model_for_type(prompt_type, total_references)

def get_model_parameters(prompt_type: str, model: str) -> Dict[str, Any]:
    """Get model parameters using global config"""
    return model_config.get_model_parameters(prompt_type, model)