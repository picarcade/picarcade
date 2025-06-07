from typing import Dict, Any, Optional, List
from app.models.generation import IntentAnalysis, QualityPriority, GenerationRequest, ReferenceImage
from app.core.logging import routing_logger

class ModelRouter:
    """
    Phase 1: Simple model routing based on intent and quality preferences
    Will be enhanced with learning and performance optimization in later phases
    """
    
    def __init__(self):
        self.model_capabilities = {
            # Image generation models
            "flux-1.1-pro": {
                "type": "image",
                "speed": 8,      # 1-10 scale
                "quality": 7,
                "cost": 3,
                "supports": ["generate_image"]
            },
            "flux-1.1-pro-ultra": {
                "type": "image", 
                "speed": 4,
                "quality": 9,
                "cost": 8,
                "supports": ["generate_image"]
            },
            "dall-e-3": {
                "type": "image",
                "speed": 6,
                "quality": 8,
                "cost": 6,
                "supports": ["generate_image"]
            },
            
            # Video generation models
            "runway_gen4_turbo": {
                "type": "video",
                "speed": 5,
                "quality": 9,
                "cost": 9,
                "supports": ["generate_video", "image_to_video"]
            },
            "google/veo-3": {
                "type": "video",
                "speed": 7,
                "quality": 9,
                "cost": 8,
                "supports": ["generate_video", "generate_video_with_audio"]
            },
            
            # Edit models
            "flux-kontext": {
                "type": "image_edit",
                "speed": 7,
                "quality": 8,
                "cost": 5,
                "supports": ["edit_image"]
            },
            
            # Virtual try-on models
            "outfit-anyone": {
                "type": "virtual_tryon",
                "speed": 6,
                "quality": 8,
                "cost": 4,
                "supports": ["virtual_tryon"]
            }
        }
    
    async def route_generation(self, 
                              request: GenerationRequest, 
                              intent_analysis: IntentAnalysis,
                              generation_id: str = None) -> Dict[str, Any]:
        """
        Route generation request to optimal model
        
        Args:
            request: User's generation request
            intent_analysis: Analyzed intent and requirements
            generation_id: Unique generation ID for logging
            
        Returns:
            Routing decision with model and parameters
        """
        
        # Check if references are provided - ALWAYS use Runway if so
        has_references = request.reference_images and len(request.reference_images) > 0
        
        if has_references:
            print(f"[DEBUG] Router: References detected, forcing Runway gen4_image model")
            print(f"[DEBUG] Router: Reference count: {len(request.reference_images)}")
            
            # Override model selection for references
            selected_model = "runway_gen4_image"
            parameters = self._generate_runway_reference_parameters(
                request.reference_images,
                intent_analysis,
                request.quality_priority
            )
            
            result = {
                "model": selected_model,
                "confidence": 1.0,  # High confidence for forced routing
                "parameters": parameters,
                "estimated_time": 30,  # Runway gen4_image typical time
                "routing_reason": f"Forced Runway gen4_image due to {len(request.reference_images)} reference images"
            }
            
            # Log routing decision
            if generation_id:
                routing_logger.log_model_routing(
                    generation_id=generation_id,
                    selected_model=selected_model,
                    routing_confidence=1.0,
                    quality_priority=request.quality_priority.value,
                    estimated_time=30,
                    routing_reason=result["routing_reason"],
                    compatible_models=[selected_model],
                    model_scores={selected_model: 1.0}
                )
            
            return result
        
        # Check if we need image-to-video generation
        # This happens when: video intent + existing image in context
        effective_intent = intent_analysis.detected_intent
        has_input_image = (request.uploaded_images and len(request.uploaded_images) > 0) or request.current_working_image
        
        print(f"[DEBUG] Router: Intent: {intent_analysis.detected_intent}")
        print(f"[DEBUG] Router: Current working image: {request.current_working_image}")
        print(f"[DEBUG] Router: Uploaded images: {request.uploaded_images}")
        print(f"[DEBUG] Router: Has input image: {has_input_image}")
        
        if intent_analysis.detected_intent == "generate_video" and has_input_image:
            effective_intent = "image_to_video"
            print(f"[DEBUG] Router: Detected image-to-video generation (video intent + input image)")
            print(f"[DEBUG] Router: Input image: {request.current_working_image or request.uploaded_images[0] if request.uploaded_images else 'none'}")
        else:
            print(f"[DEBUG] Router: No image-to-video detected. Intent: {intent_analysis.detected_intent}, Has image: {has_input_image}")
        
        # Filter models that support the effective intent
        compatible_models = self._get_compatible_models(effective_intent)
        print(f"[DEBUG] Router: Effective intent: {effective_intent}")
        print(f"[DEBUG] Router: Compatible models: {list(compatible_models.keys())}")
        
        # Score models based on quality priority and requirements
        scored_models = self._score_models(
            compatible_models, 
            request.quality_priority,
            intent_analysis.complexity_level,
            content_type=intent_analysis.content_type
        )
        
        print(f"[DEBUG] Router: Model scores: {scored_models}")
        
        # Select best model
        if not scored_models:
            raise Exception(f"No compatible models found for intent: {effective_intent}")
        
        selected_model = max(scored_models.items(), key=lambda x: x[1])
        print(f"[DEBUG] Router: Selected model: {selected_model[0]} with score: {selected_model[1]}")
        
        # Generate optimized parameters
        parameters = self._generate_parameters(
            selected_model[0], 
            intent_analysis, 
            request.quality_priority,
            effective_intent=effective_intent
        )
        
        # Prepare result
        result = {
            "model": selected_model[0],
            "confidence": selected_model[1],
            "parameters": parameters,
            "estimated_time": self._estimate_generation_time(selected_model[0], intent_analysis),
            "routing_reason": self._explain_routing_decision(selected_model[0], request.quality_priority, effective_intent)
        }
        
        # Log routing decision
        if generation_id:
            routing_logger.log_model_routing(
                generation_id=generation_id,
                selected_model=selected_model[0],
                routing_confidence=selected_model[1],
                quality_priority=request.quality_priority.value,
                estimated_time=result["estimated_time"],
                routing_reason=result["routing_reason"],
                compatible_models=list(compatible_models.keys()),
                model_scores=scored_models
            )
        
        return result
    
    def _get_compatible_models(self, intent: str) -> Dict[str, Dict[str, Any]]:
        """Get models that support the detected intent"""
        
        compatible = {}
        intent_mapping = {
            "generate_image": "generate_image",
            "generate_video": "generate_video",
            "image_to_video": "image_to_video",
            "edit_image": "edit_image",
            "enhance_image": "generate_image",  # Use generation models for enhancement
            "virtual_tryon": "virtual_tryon"
        }
        
        required_capability = intent_mapping.get(intent, "generate_image")
        
        for model_name, capabilities in self.model_capabilities.items():
            if required_capability in capabilities["supports"]:
                compatible[model_name] = capabilities
                
        return compatible
    
    def _score_models(self, 
                     compatible_models: Dict[str, Dict[str, Any]], 
                     quality_priority: QualityPriority,
                     complexity: str,
                     content_type: str = None) -> Dict[str, float]:
        """Score models based on user preferences and requirements"""
        
        scores = {}
        
        for model_name, capabilities in compatible_models.items():
            score = 0.0
            
            # Base scoring based on quality priority
            if quality_priority == QualityPriority.SPEED:
                score += capabilities["speed"] * 0.6
                score += capabilities["quality"] * 0.2
                score += (10 - capabilities["cost"]) * 0.2
                
            elif quality_priority == QualityPriority.QUALITY:
                score += capabilities["quality"] * 0.7
                score += capabilities["speed"] * 0.1
                score += (10 - capabilities["cost"]) * 0.2
                
            else:  # BALANCED
                score += capabilities["quality"] * 0.4
                score += capabilities["speed"] * 0.4
                score += (10 - capabilities["cost"]) * 0.2
            
            # Complexity adjustments
            if complexity == "complex" and capabilities["quality"] >= 8:
                score += 1.0  # Bonus for high-quality models on complex tasks
            elif complexity == "simple" and capabilities["speed"] >= 7:
                score += 0.5  # Bonus for fast models on simple tasks
            
            # Audio capability bonus
            if content_type == "video_with_audio" and "generate_video_with_audio" in capabilities["supports"]:
                score += 2.0  # Strong bonus for audio-capable models when audio is requested
                print(f"[DEBUG] Router: Audio bonus applied to {model_name}, new score: {score}")
            
            scores[model_name] = score
            
        return scores
    
    def _generate_parameters(self, 
                           model: str, 
                           intent_analysis: IntentAnalysis,
                           quality_priority: QualityPriority,
                           effective_intent: str = None) -> Dict[str, Any]:
        """Generate optimized parameters for the selected model"""
        
        base_params = {}
        
        # Model-specific base parameters
        if "flux" in model:
            base_params = {
                "guidance_scale": 7.5,
                "num_inference_steps": 50,
                "width": 1024,
                "height": 1024
            }
            
            # Adjust based on quality priority
            if quality_priority == QualityPriority.QUALITY:
                base_params["num_inference_steps"] = 75
                base_params["width"] = 1536
                base_params["height"] = 1536
            elif quality_priority == QualityPriority.SPEED:
                base_params["num_inference_steps"] = 25
            
            # Special handling for flux-kontext (image editing)
            if model == "flux-kontext":
                base_params["output_format"] = "jpg"  # Required parameter for flux-kontext-pro
                # Remove other parameters that flux-kontext-pro doesn't support
                base_params.pop("guidance_scale", None)
                base_params.pop("num_inference_steps", None)
                base_params.pop("width", None)
                base_params.pop("height", None)
                
        elif "runway" in model:
            base_params = {
                "duration": 5,
                "ratio": "1280:720",
                "motion": 3
            }
            
            # Special handling for image-to-video
            if effective_intent == "image_to_video":
                base_params["type"] = "image_to_video"
                print(f"[DEBUG] Router: Setting image-to-video parameters for Runway")
            else:
                base_params["type"] = "video"
            
            if quality_priority == QualityPriority.QUALITY:
                base_params["duration"] = 10
                base_params["ratio"] = "1920:1080"
                
        elif "dall-e" in model:
            base_params = {
                "size": "1024x1024",
                "quality": "standard"
            }
            
            if quality_priority == QualityPriority.QUALITY:
                base_params["quality"] = "hd"
                base_params["size"] = "1792x1024"
        
        return base_params
    
    def _estimate_generation_time(self, model: str, intent_analysis: IntentAnalysis) -> int:
        """Estimate generation time in seconds"""
        
        base_times = {
            "flux-1.1-pro": 15,
            "flux-1.1-pro-ultra": 45, 
            "dall-e-3": 20,
            "runway_gen4_turbo": 120,
            "google/veo-3": 60,  # Veo 3 is faster than Runway
            "flux-kontext": 25,
            "outfit-anyone": 30
        }
        
        base_time = base_times.get(model, 30)
        
        # Adjust for complexity
        if intent_analysis.complexity_level == "complex":
            base_time *= 1.5
        elif intent_analysis.complexity_level == "simple":
            base_time *= 0.8
            
        return int(base_time)
    
    def _explain_routing_decision(self, model: str, quality_priority: QualityPriority, effective_intent: str = None) -> str:
        """Generate human-readable explanation of routing decision"""
        
        explanations = {
            "flux-1.1-pro": "Selected for balanced speed and quality",
            "flux-1.1-pro-ultra": "Selected for maximum image quality",
            "dall-e-3": "Selected for creative interpretation",
            "runway_gen4_turbo": "Selected for high-quality video generation",
            "google/veo-3": "Selected for advanced video generation with audio support",
            "flux-kontext": "Selected for precise image editing",
            "outfit-anyone": "Selected for virtual clothing try-on"
        }
        
        # Special handling for image-to-video
        if effective_intent == "image_to_video" and "runway" in model:
            base_explanation = "Selected for image-to-video generation"
        else:
            base_explanation = explanations.get(model, f"Selected {model}")
            
        priority_note = f" (optimizing for {quality_priority.value})"
        
        return base_explanation + priority_note
    
    def _generate_runway_reference_parameters(self, 
                                            reference_images: List[ReferenceImage],
                                            intent_analysis: IntentAnalysis,
                                            quality_priority: QualityPriority) -> Dict[str, Any]:
        """Generate parameters for Runway gen4_image with references"""
        
        # Convert our ReferenceImage objects to Runway API format
        runway_references = []
        for ref in reference_images:
            runway_references.append({
                "uri": ref.uri,
                "tag": ref.tag
            })
        
        parameters = {
            "model": "gen4_image",
            "reference_images": runway_references,
            "type": "text_to_image_with_references",
            "ratio": "1920:1080"  # Default high quality
        }
        
        # Adjust based on quality priority
        if quality_priority == QualityPriority.QUALITY:
            parameters["ratio"] = "1920:1080"
        elif quality_priority == QualityPriority.SPEED:
            parameters["ratio"] = "1280:720"
        else:  # BALANCED
            parameters["ratio"] = "1920:1080"
        
        return parameters 