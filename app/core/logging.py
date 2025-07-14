import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    """Structured logger for tracking intent decisions and model usage"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Create console handler with custom formatter
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            
            # Custom formatter for structured logging
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_intent_decision(self, 
                           generation_id: str,
                           prompt: str, 
                           detected_intent: str,
                           confidence: float,
                           content_type: str,
                           complexity_level: str,
                           suggested_model: str,
                           has_uploaded_images: bool = False,
                           uploaded_images_count: int = 0,
                           has_current_working_image: bool = False,
                           current_working_image_url: str = None):
        """Log intent analysis decision"""
        
        log_data = {
            "event_type": "intent_decision",
            "generation_id": generation_id,
            "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "detected_intent": detected_intent,
            "confidence": confidence,
            "content_type": content_type,
            "complexity_level": complexity_level,
            "suggested_model": suggested_model,
            "has_uploaded_images": has_uploaded_images,
            "uploaded_images_count": uploaded_images_count,
            "has_current_working_image": has_current_working_image,
            "current_working_image_url": current_working_image_url,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"INTENT_DECISION: {json.dumps(log_data, indent=2)}")
    
    def log_model_routing(self,
                         generation_id: str,
                         selected_model: str,
                         routing_confidence: float,
                         quality_priority: str,
                         estimated_time: int,
                         routing_reason: str,
                         compatible_models: list,
                         model_scores: Dict[str, float]):
        """Log model routing decision"""
        
        log_data = {
            "event_type": "model_routing",
            "generation_id": generation_id,
            "selected_model": selected_model,
            "routing_confidence": routing_confidence,
            "quality_priority": quality_priority,
            "estimated_time_seconds": estimated_time,
            "routing_reason": routing_reason,
            "compatible_models": compatible_models,
            "model_scores": model_scores,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"MODEL_ROUTING: {json.dumps(log_data, indent=2)}")
    
    def log_model_generation(self,
                            generation_id: str,
                            model_used: str,
                            generator_type: str,
                            parameters: Dict[str, Any],
                            success: bool,
                            execution_time: float,
                            error_message: str = None):
        """Log actual model generation execution"""
        
        # Sanitize parameters to avoid logging sensitive and large data
        safe_parameters = {}
        for k, v in parameters.items():
            if k in ['api_token', 'api_key', 'secret']:
                continue
            elif k in ['image', 'images', 'uploaded_image', 'uploaded_images']:
                # Log image presence but not data
                if isinstance(v, list):
                    safe_parameters[k] = f"[{len(v)} images]"
                elif v:
                    safe_parameters[k] = "[image data]"
            elif k == 'referenceImages' and isinstance(v, list):
                # Log reference image summary without URIs
                safe_parameters[k] = [{"tag": img.get("tag", "unknown")} for img in v if isinstance(img, dict)]
            else:
                safe_parameters[k] = v
        
        log_data = {
            "event_type": "model_generation",
            "generation_id": generation_id,
            "model_used": model_used,
            "generator_type": generator_type,
            "parameters": safe_parameters,
            "success": success,
            "execution_time_seconds": round(execution_time, 2) if execution_time else None,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"MODEL_GENERATION: {json.dumps(log_data, indent=2)}")
    
    def log_generation_summary(self,
                              generation_id: str,
                              prompt: str,
                              intent: str,
                              model_used: str,
                              success: bool,
                              total_time: float,
                              output_url: str = None):
        """Log complete generation summary"""
        
        log_data = {
            "event_type": "generation_summary",
            "generation_id": generation_id,
            "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "final_intent": intent,
            "final_model": model_used,
            "success": success,
            "total_time_seconds": round(total_time, 2),
            "has_output": bool(output_url),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"GENERATION_SUMMARY: {json.dumps(log_data, indent=2)}")
    
    def debug(self, message: str, extra: Dict[str, Any] = None):
        """Debug level logging with optional extra data"""
        if extra:
            formatted_message = f"{message} | {json.dumps(extra)}"
        else:
            formatted_message = message
        self.logger.debug(formatted_message)
    
    def info(self, message: str, extra: Dict[str, Any] = None):
        """Info level logging with optional extra data"""
        if extra:
            formatted_message = f"{message} | {json.dumps(extra)}"
        else:
            formatted_message = message
        self.logger.info(formatted_message)
    
    def warning(self, message: str, extra: Dict[str, Any] = None):
        """Warning level logging with optional extra data"""
        if extra:
            formatted_message = f"{message} | {json.dumps(extra)}"
        else:
            formatted_message = message
        self.logger.warning(formatted_message)
    
    def error(self, message: str, extra: Dict[str, Any] = None):
        """Error level logging with optional extra data"""
        if extra:
            formatted_message = f"{message} | {json.dumps(extra)}"
        else:
            formatted_message = message
        self.logger.error(formatted_message)

# Create loggers for different components
intent_logger = StructuredLogger("intent_parser")
routing_logger = StructuredLogger("model_router") 
generation_logger = StructuredLogger("generators")
api_logger = StructuredLogger("api") 