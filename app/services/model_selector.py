from typing import Dict, List, Optional
from app.models.workflows import WorkflowType, ModelSelection, IntentClassification

class ModelSelector:
    """Sprint 2: Enhanced model selection with virtual try-on and improved video workflows"""
    
    def __init__(self):
        # Enhanced model mappings with Sprint 2 improvements
        self.image_models = {
            WorkflowType.HAIR_STYLING: {
                "primary": "flux-kontext-apps/multi-image-list",  # Use multi-image-list when reference images provided
                "primary_no_references": "black-forest-labs/flux-kontext-max",  # Use kontext-max for text-only descriptions
                "fallback": ["black-forest-labs/flux-kontext-max", "black-forest-labs/flux-1.1-pro"],
                "cost_per_generation": 0.05,
                "specializations": ["hair_color", "hair_cut", "hair_style"],
                "supports_multiple_images": True,
                "conditional_selection": True  # Indicates model depends on context
            },
            WorkflowType.REFERENCE_STYLING: {
                "primary": "runway_gen4_image",  # Use Runway references for virtual try-on and styling
                "fallback": ["black-forest-labs/flux-kontext-max", "black-forest-labs/flux-1.1-pro"],
                "cost_per_generation": 0.06,
                "specializations": ["virtual_tryon", "celebrity_styling", "event_fashion", "outfit_swapping"],
                "supports_multiple_images": True,
                "max_images": 4,
                "requires_references": True
            },
            WorkflowType.IMAGE_ENHANCEMENT: {
                "primary": "black-forest-labs/flux-kontext-max",  # Use kontext-max for image enhancement
                "fallback": ["black-forest-labs/flux-1.1-pro-ultra", "black-forest-labs/flux-1.1-pro"],
                "cost_per_generation": 0.04,
                "specializations": ["upscaling", "restoration", "quality_improvement"],
                "supports_multiple_images": False
            },
            WorkflowType.IMAGE_EDITING: {
                "primary": "black-forest-labs/flux-kontext-max",  # Use official Flux Kontext Max
                "fallback": ["zsxkib/flux-kontext-pro", "black-forest-labs/flux-1.1-pro"],
                "cost_per_generation": 0.03,
                "specializations": ["object_modification", "scene_editing", "color_adjustment", "text_editing", "style_transfer"],
                "supports_multiple_images": False
            },
            WorkflowType.STYLE_TRANSFER: {
                "primary": "black-forest-labs/flux-kontext-max",  # Use official Flux Kontext Max for style transfer
                "fallback": ["black-forest-labs/flux-1.1-pro", "zsxkib/flux-kontext-pro"],
                "cost_per_generation": 0.04,
                "specializations": ["artistic_styles", "style_transfer", "painting_effects"],
                "supports_multiple_images": False
            },
            WorkflowType.IMAGE_GENERATION: {
                "primary": "black-forest-labs/flux-1.1-pro",
                "fallback": ["black-forest-labs/flux-schnell", "black-forest-labs/flux-1.1-pro-ultra"],
                "cost_per_generation": 0.04,
                "specializations": ["text_to_image", "creative_generation"],
                "supports_multiple_images": False
            }
        }
        
        # Sprint 2: Enhanced video models with granular workflows
        self.video_models = {
            WorkflowType.VIDEO_GENERATION: {
                "primary": "google/veo-3",  # Premium text-to-video with audio support only
                "fallback": ["minimax/video-01"],
                "cost_per_second": 0.75,
                "max_duration": 10,
                "features": ["audio_support", "high_quality", "cinematic", "text_to_video_only"],
                "recommended_for": ["music_videos", "cinematic_scenes", "premium_content"]
            },
            WorkflowType.IMAGE_TO_VIDEO: {
                "primary": "minimax/video-01",  # MiniMax supports image-to-video with first_frame_image
                "fallback": ["lightricks/ltx-video", "wavespeedai/wan-2.1-i2v-720p"],
                "cost_per_second": 0.40,
                "max_duration": 6,
                "features": ["image_animation", "first_frame_support", "subject_reference", "cost_effective"],
                "recommended_for": ["photo_animation", "still_to_motion", "social_media", "image_to_video"]
            },
            WorkflowType.TEXT_TO_VIDEO: {
                "primary": "minimax/video-01",  # Cost-effective text-to-video
                "fallback": ["lightricks/ltx-video", "kwaivgi/kling-v1.6-standard"],
                "cost_per_second": 0.40,
                "max_duration": 6,  # Minimax limitation
                "features": ["text_based", "affordable", "quick_generation"],
                "recommended_for": ["simple_videos", "concept_visualization", "budget_friendly"]
            }
        }
        
        # Sprint 2: Model performance profiles for optimization
        self.performance_profiles = {
            "speed": {
                "image_primary": "black-forest-labs/flux-schnell",
                "video_primary": "lightricks/ltx-video",
                "cost_multiplier": 0.5,
                "time_multiplier": 0.4
            },
            "balanced": {
                "image_primary": "black-forest-labs/flux-1.1-pro",
                "video_primary": "minimax/video-01",
                "cost_multiplier": 1.0,
                "time_multiplier": 1.0
            },
            "quality": {
                "image_primary": "black-forest-labs/flux-1.1-pro-ultra",
                "video_primary": "google/veo-3",  # For audio-required videos only, otherwise minimax
                "cost_multiplier": 1.8,
                "time_multiplier": 1.5
            }
        }
    
    def select_model(
        self, 
        intent: IntentClassification,
        user_preferences: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, any]] = None
    ) -> ModelSelection:
        """
        Sprint 2: Enhanced model selection with virtual try-on optimization
        """
        
        workflow_type = intent.workflow_type
        
        # Get user preference profile
        quality_pref = user_preferences.get("quality", "balanced") if user_preferences else "balanced"
        performance_profile = self.performance_profiles.get(quality_pref, self.performance_profiles["balanced"])
        
        # Select model based on workflow type
        if workflow_type in [WorkflowType.VIDEO_GENERATION, WorkflowType.IMAGE_TO_VIDEO, WorkflowType.TEXT_TO_VIDEO]:
            return self._select_video_model(workflow_type, intent, performance_profile, context)
        else:
            return self._select_image_model(workflow_type, intent, performance_profile, context)
    
    def _select_image_model(
        self, 
        workflow_type: WorkflowType, 
        intent: IntentClassification,
        performance_profile: Dict[str, any],
        context: Optional[Dict[str, any]]
    ) -> ModelSelection:
        """Enhanced image model selection with person identity preservation"""
        
        # Get base model configuration
        model_config = self.image_models.get(workflow_type, self.image_models[WorkflowType.IMAGE_GENERATION])
        
        # Handle specialized workflows first before general identity preservation
        
        # Handle virtual try-on specifically
        if workflow_type == WorkflowType.REFERENCE_STYLING:
            return self._select_virtual_tryon_model(model_config, intent, context, performance_profile)
        
        # Handle hair styling with conditional model selection
        if workflow_type == WorkflowType.HAIR_STYLING:
            return self._select_hair_styling_model(model_config, intent, context, performance_profile)
        
        # Sprint 2: Check if this involves a person with working image for other workflows
        involves_person = self._involves_person_modification(intent.workflow_type, intent.reasoning, context)
        has_working_image = context and (context.get("working_images") or context.get("has_working_image"))
        
        # Use identity-preserving model for person modifications (but not hair/virtual try-on which are handled above)
        if involves_person and has_working_image:
            print(f"[DEBUG] ModelSelector: Person modification detected, using identity-preserving model")
            return self._select_identity_preserving_model(workflow_type, intent, performance_profile, context)
        
        # Standard model selection for other workflows
        selected_model = model_config["primary"]
        
        # Apply performance profile adjustments
        if workflow_type == WorkflowType.IMAGE_GENERATION:
            if performance_profile.get("image_primary"):
                selected_model = performance_profile["image_primary"]
        
        # Calculate costs and time
        base_cost = model_config["cost_per_generation"]
        cost_estimate = base_cost * performance_profile["cost_multiplier"]
        time_estimate = 30 * performance_profile["time_multiplier"]
        
        reasoning = f"Selected {selected_model} for {workflow_type.value}"
        if intent.confidence < 0.8:
            reasoning += f" (confidence: {intent.confidence:.2f})"
        
        # Add specialization info
        if model_config.get("specializations"):
            specializations = ", ".join(model_config["specializations"][:2])
            reasoning += f" - optimized for {specializations}"
        
        return ModelSelection(
            model_id=selected_model,
            provider="replicate",
            reasoning=reasoning,
            fallback_models=model_config["fallback"],
            estimated_cost=cost_estimate,
            estimated_time=int(time_estimate)
        )
    
    def _involves_person_modification(
        self, 
        workflow_type: WorkflowType, 
        reasoning: str, 
        context: Optional[Dict[str, any]]
    ) -> bool:
        """Check if the task involves modifying a person and should preserve identity"""
        
        # Always true for styling workflows
        if workflow_type in [WorkflowType.REFERENCE_STYLING, WorkflowType.HAIR_STYLING]:
            return True
        
        # Check for person-related keywords in reasoning or prompt context
        person_keywords = [
            "person", "man", "woman", "face", "facial", "body", "pose", "position",
            "him", "her", "guy", "girl", "human", "people", "portrait", "character"
        ]
        
        reasoning_lower = reasoning.lower() if reasoning else ""
        
        # Check if reasoning contains person-related terms
        if any(keyword in reasoning_lower for keyword in person_keywords):
            print(f"[DEBUG] Person modification detected in reasoning: '{reasoning}'")
            return True
        
        return False
    
    def _select_identity_preserving_model(
        self,
        workflow_type: WorkflowType, 
        intent: IntentClassification,
        performance_profile: Dict[str, any],
        context: Optional[Dict[str, any]]
    ) -> ModelSelection:
        """Select identity-preserving model for person modifications"""
        
        # Use official Flux Kontext Max for identity preservation and all image edits
        selected_model = "black-forest-labs/flux-kontext-max"
        
        # Calculate cost - identity preservation is slightly more expensive
        base_cost = 0.06  # Same as reference styling
        cost_estimate = base_cost * performance_profile["cost_multiplier"]
        time_estimate = int(35 * performance_profile["time_multiplier"])
        
        reasoning = f"Selected {selected_model} for {workflow_type.value} with identity preservation and advanced editing capabilities"
        if intent.confidence < 0.8:
            reasoning += f" (confidence: {intent.confidence:.2f})"
        
        print(f"[DEBUG] ModelSelector: Using official Flux Kontext Max for person modification")
        print(f"[DEBUG] ModelSelector: Original workflow: {workflow_type.value}")
        print(f"[DEBUG] ModelSelector: Selected model: {selected_model}")
        
        return ModelSelection(
            model_id=selected_model,
            provider="replicate",
            reasoning=reasoning,
            fallback_models=["zsxkib/flux-kontext-pro", "black-forest-labs/flux-1.1-pro"],
            estimated_cost=cost_estimate,
            estimated_time=time_estimate
        )
    
    def _select_virtual_tryon_model(
        self,
        model_config: Dict[str, any],
        intent: IntentClassification,
        context: Optional[Dict[str, any]],
        performance_profile: Dict[str, any]
    ) -> ModelSelection:
        """Sprint 2: Specialized virtual try-on model selection"""
        
        # Check if reference images are available
        has_reference_images = False
        reference_count = 0
        
        if context:
            # Check for working images and uploaded images (clothing references)
            working_images = context.get("working_images", [])
            uploaded_images = context.get("uploaded_images", [])
            has_working_image = context.get("has_working_image", False)
            
            # Count all available reference images
            total_working = len(working_images) if working_images else (1 if has_working_image else 0)
            total_uploaded = len(uploaded_images) if uploaded_images else 0
            reference_count = total_working + total_uploaded
            has_reference_images = reference_count > 0
        
                # Select model based on reference availability  
        if has_reference_images:
            # Use Runway references when reference images are provided
            selected_model = "runway_gen4_image"
            reasoning = f"Selected {selected_model} for virtual try-on with {reference_count} reference image(s)"
            time_estimate = 45 + (reference_count - 1) * 5  # Extra time for multi-image processing
        else:
            # Use kontext-max for text-only virtual try-on descriptions
            selected_model = "black-forest-labs/flux-kontext-max" 
            reasoning = f"Selected {selected_model} for text-only virtual try-on description"
            time_estimate = 35
        
        # Calculate cost based on complexity
        base_cost = model_config["cost_per_generation"]
        if has_reference_images:
            # Multi-image processing is more expensive
            cost_multiplier = 1.2 + (reference_count - 1) * 0.1
            cost_estimate = base_cost * cost_multiplier * performance_profile["cost_multiplier"]
        else:
            cost_estimate = base_cost * performance_profile["cost_multiplier"]
        
        time_estimate = int(time_estimate * performance_profile["time_multiplier"])
        
        # Add web search and confidence notes
        if intent.requires_web_search:
            reasoning += " with web search enhancement"
        
        if intent.confidence < 0.8:
            reasoning += f" (confidence: {intent.confidence:.2f})"
        
        print(f"[DEBUG] Virtual Try-On Model Selection:")
        print(f"[DEBUG]   has_reference_images: {has_reference_images}")
        print(f"[DEBUG]   reference_count: {reference_count}")
        if context:
            print(f"[DEBUG]   working_images: {len(context.get('working_images', []))}")
            print(f"[DEBUG]   uploaded_images: {len(context.get('uploaded_images', []))}")
            print(f"[DEBUG]   has_working_image: {context.get('has_working_image', False)}")
        print(f"[DEBUG]   selected_model: {selected_model}")
        print(f"[DEBUG]   reasoning: {reasoning}")
        
        return ModelSelection(
            model_id=selected_model,
            provider="replicate",
            reasoning=reasoning,
            fallback_models=model_config["fallback"],
            estimated_cost=cost_estimate,
            estimated_time=time_estimate
        )
    
    def _select_hair_styling_model(
        self,
        model_config: Dict[str, any],
        intent: IntentClassification,
        context: Optional[Dict[str, any]],
        performance_profile: Dict[str, any]
    ) -> ModelSelection:
        """Select appropriate model for hair styling based on whether reference images are provided"""
        
        # Check if reference images are available
        has_reference_images = False
        reference_count = 0
        
        print(f"[DEBUG] Hair Styling Context Analysis:")
        print(f"[DEBUG]   context: {context}")
        
        if context:
            # Check for working images and uploaded images (hair references)
            working_images = context.get("working_images", [])
            uploaded_images = context.get("uploaded_images", [])
            reference_images = context.get("reference_images", [])  # References from @mentions in prompt
            has_working_image = context.get("has_working_image", False)
            
            print(f"[DEBUG]   working_images: {working_images}")
            print(f"[DEBUG]   uploaded_images: {uploaded_images}")
            print(f"[DEBUG]   reference_images: {reference_images}")
            print(f"[DEBUG]   has_working_image: {has_working_image}")
            
            # For hair styling, count ALL reference images (uploaded + prompt references) as hair style references
            # Working images are the images being edited, not style references
            total_working = len(working_images) if working_images else (1 if has_working_image else 0)
            total_uploaded = len(uploaded_images) if uploaded_images else 0
            total_references = len(reference_images) if reference_images else 0
            reference_count = total_uploaded + total_references  # Count both uploaded and @reference images
            has_reference_images = reference_count > 0
            
            print(f"[DEBUG]   total_working: {total_working}")
            print(f"[DEBUG]   total_uploaded: {total_uploaded}")
            print(f"[DEBUG]   total_references: {total_references}")
            print(f"[DEBUG]   reference_count: {reference_count}")
            print(f"[DEBUG]   has_reference_images: {has_reference_images}")
        
        # Select model based on reference availability
        if has_reference_images:
            # Use Runway references when reference images are provided
            selected_model = "runway_gen4_image"
            reasoning = f"Selected {selected_model} for hair styling with {reference_count} reference image(s)"
            time_estimate = 45 + (reference_count - 1) * 5  # Extra time for multi-image processing
        else:
            # Use kontext-max for text-only hair descriptions
            selected_model = model_config.get("primary_no_references", "black-forest-labs/flux-kontext-max")
            reasoning = f"Selected {selected_model} for text-only hair styling description"
            time_estimate = 35
        
        # Calculate cost
        base_cost = model_config["cost_per_generation"]
        if has_reference_images:
            # Multi-image processing is slightly more expensive
            cost_multiplier = 1.2 + (reference_count - 1) * 0.1
            cost_estimate = base_cost * cost_multiplier * performance_profile["cost_multiplier"]
        else:
            cost_estimate = base_cost * performance_profile["cost_multiplier"]
        
        time_estimate = int(time_estimate * performance_profile["time_multiplier"])
        
        # Add confidence note if needed
        if intent.confidence < 0.8:
            reasoning += f" (confidence: {intent.confidence:.2f})"
        
        print(f"[DEBUG] Hair Styling Model Selection:")
        print(f"[DEBUG]   has_reference_images: {has_reference_images}")
        print(f"[DEBUG]   reference_count: {reference_count}")
        if context:
            print(f"[DEBUG]   working_images: {len(context.get('working_images', []))}")
            print(f"[DEBUG]   uploaded_images: {len(context.get('uploaded_images', []))}")
            print(f"[DEBUG]   has_working_image: {context.get('has_working_image', False)}")
        print(f"[DEBUG]   selected_model: {selected_model}")
        print(f"[DEBUG]   reasoning: {reasoning}")
        
        return ModelSelection(
            model_id=selected_model,
            provider="replicate",
            reasoning=reasoning,
            fallback_models=model_config["fallback"],
            estimated_cost=cost_estimate,
            estimated_time=time_estimate
        )
    
    def _select_video_model(
        self, 
        workflow_type: WorkflowType, 
        intent: IntentClassification,
        performance_profile: Dict[str, any],
        context: Optional[Dict[str, any]]
    ) -> ModelSelection:
        """Sprint 2: Enhanced video model selection with granular workflows"""
        
        model_config = self.video_models[workflow_type]
        
        # Override with performance profile for video
        selected_model = model_config["primary"]
        if performance_profile.get("video_primary") and workflow_type == WorkflowType.TEXT_TO_VIDEO:
            # Allow performance override for text-to-video
            selected_model = performance_profile["video_primary"]
        
        # Calculate video costs
        duration = model_config["max_duration"]
        
        # Sprint 2: Optimize duration based on workflow
        if workflow_type == WorkflowType.IMAGE_TO_VIDEO:
            # Image-to-video typically shorter
            duration = min(8, duration)
        elif workflow_type == WorkflowType.TEXT_TO_VIDEO and "minimax" in selected_model:
            # Minimax limitation
            duration = 6
        
        cost_estimate = model_config["cost_per_second"] * duration * performance_profile["cost_multiplier"]
        
        # Time estimation based on model and complexity
        if workflow_type == WorkflowType.IMAGE_TO_VIDEO:
            time_estimate = 60 + duration * 5  # Faster processing for image-to-video
        else:
            time_estimate = 90 + duration * 8  # Standard video generation time
        
        time_estimate = int(time_estimate * performance_profile["time_multiplier"])
        
        # Build comprehensive reasoning
        reasoning = f"Selected {selected_model} for {workflow_type.value} ({duration}s)"
        
        # Add workflow-specific reasoning
        features = model_config.get("features", [])
        if features:
            key_features = ", ".join(features[:2])
            reasoning += f" - {key_features}"
        
        recommended_for = model_config.get("recommended_for", [])
        if recommended_for:
            reasoning += f" (ideal for {recommended_for[0]})"
        
        if intent.confidence < 0.8:
            reasoning += f" (confidence: {intent.confidence:.2f})"
        
        return ModelSelection(
            model_id=selected_model,
            provider="replicate",
            reasoning=reasoning,
            fallback_models=model_config["fallback"],
            estimated_cost=cost_estimate,
            estimated_time=time_estimate
        )
    
    def get_model_capabilities(self, workflow_type: WorkflowType) -> Dict[str, any]:
        """Get detailed model capabilities for a workflow type"""
        
        if workflow_type in self.video_models:
            model_config = self.video_models[workflow_type]
            return {
                "type": "video",
                "primary_model": model_config["primary"],
                "max_duration": model_config["max_duration"],
                "features": model_config.get("features", []),
                "recommended_for": model_config.get("recommended_for", []),
                "cost_per_second": model_config["cost_per_second"]
            }
        else:
            model_config = self.image_models.get(workflow_type, self.image_models[WorkflowType.IMAGE_GENERATION])
            return {
                "type": "image",
                "primary_model": model_config["primary"],
                "specializations": model_config.get("specializations", []),
                "supports_multiple_images": model_config.get("supports_multiple_images", False),
                "max_images": model_config.get("max_images", 1),
                "cost_per_generation": model_config["cost_per_generation"]
            }
    
    def estimate_cost_range(self, workflow_type: WorkflowType, context: Optional[Dict[str, any]] = None) -> Dict[str, float]:
        """Provide cost estimates for different quality levels"""
        
        cost_estimates = {}
        
        for profile_name, profile in self.performance_profiles.items():
            if workflow_type in self.video_models:
                model_config = self.video_models[workflow_type]
                duration = model_config["max_duration"]
                base_cost = model_config["cost_per_second"] * duration
            else:
                model_config = self.image_models.get(workflow_type, self.image_models[WorkflowType.IMAGE_GENERATION])
                base_cost = model_config["cost_per_generation"]
            
            cost_estimates[profile_name] = base_cost * profile["cost_multiplier"]
        
        return cost_estimates 