import asyncio
import time
import uuid
from typing import Dict, Any, Optional
from app.services.intent_classifier import IntentClassifier
from app.services.model_selector import ModelSelector
from app.services.reference_service import ReferenceService
from app.services.model_router import ModelRouter
from app.services.generators.replicate import ReplicateGenerator
from app.services.session_manager import session_manager
from app.services.web_search_service import WebSearchService
from app.models.workflows import WorkflowType, IntentClassification, ModelSelection
from app.models.generation import GenerationRequest, GenerationResponse

class EnhancedWorkflowService:
    """Sprint 2: Enhanced orchestration service with web search and virtual try-on"""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.model_selector = ModelSelector()
        self.reference_service = ReferenceService()
        self.model_router = ModelRouter()
        self.replicate_generator = ReplicateGenerator()
        self.web_search_service = WebSearchService()  # Sprint 2: Web search integration
        
        # Performance tracking
        self.metrics = {
            "classifications": 0,
            "cache_hits": 0,
            "fallbacks": 0,
            "errors": 0,
            "web_searches": 0  # Sprint 2: Track web searches
        }
    
    async def process_request(
        self,
        prompt: str,
        user_id: str,
        working_image_url: Optional[str] = None,
        user_preferences: Optional[Dict[str, str]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing user requests with AI intent classification
        """
        
        start_time = time.time()
        generation_id = f"gen_{uuid.uuid4().hex[:12]}"
        
        try:
            # Step 1: Build context
            context = await self._build_context(user_id, working_image_url)
            
            # Step 2: Classify intent using AI with rate limiting
            intent = await self.intent_classifier.classify_intent(prompt, context, user_id)
            self.metrics["classifications"] += 1
            
            # Step 3: Check for web search requirements (Sprint 2)
            styling_data = None
            if intent.requires_web_search and intent.web_search_query:
                styling_data = await self._perform_web_search(intent.web_search_query)
            
            # Step 4: Select optimal model
            model_selection = self.model_selector.select_model(intent, user_preferences, context)
            
            # Step 5: Process with existing reference system
            final_prompt, references = await self._integrate_with_references(
                prompt, user_id, working_image_url, intent
            )
            
            # Step 6: Apply web search styling enhancement (Sprint 2)
            if styling_data:
                final_prompt = self.web_search_service.enhance_prompt_with_styling_context(
                    final_prompt, styling_data
                )
            
            # Step 7: Apply quick prompt enhancement if needed
            if intent.enhancement_needed:
                final_prompt = self._quick_enhance_prompt(final_prompt, intent)
            
            # Step 8: Actually generate the content
            generation_result = await self._execute_generation(
                final_prompt, user_id, working_image_url, model_selection, 
                intent, generation_id, session_id
            )
            
            processing_time = time.time() - start_time
            
            # Return comprehensive result including actual generation
            return {
                "success": True,
                "generation_id": generation_id,
                "workflow_type": intent.workflow_type.value,
                "final_prompt": final_prompt,
                "model_selection": model_selection.dict(),
                "references": references,
                "intent_confidence": intent.confidence,
                "reasoning": f"{intent.reasoning} | {model_selection.reasoning}",
                "processing_time": processing_time,
                "estimated_cost": model_selection.estimated_cost,
                "estimated_time": model_selection.estimated_time,
                "generation_result": generation_result,
                "metadata": {
                    "requires_web_search": intent.requires_web_search,
                    "web_search_query": intent.web_search_query,
                    "enhancement_applied": intent.enhancement_needed,
                    "styling_data": styling_data,  # Sprint 2: Include styling data
                    "workflow_specializations": model_selection.dict().get("specializations", [])
                }
            }
            
        except Exception as e:
            self.metrics["errors"] += 1
            print(f"[ERROR] Enhanced workflow processing failed: {e}")
            
            # Graceful fallback to existing system
            return await self._fallback_to_existing_system(
                prompt, user_id, working_image_url, str(e)
            )
    
    async def _build_context(self, user_id: str, working_image_url: Optional[str]) -> Dict[str, Any]:
        """Build context for intent classification and model selection"""
        
        context = {"user_id": user_id}
        
        if working_image_url:
            context["working_images"] = [working_image_url]
            context["has_working_image"] = True
        
        # Add any other relevant context from your existing system
        return context
    
    async def _integrate_with_references(
        self,
        prompt: str,
        user_id: str,
        working_image_url: Optional[str],
        intent: IntentClassification
    ) -> tuple[str, list]:
        """
        Integrate with your existing reference system
        """
        
        try:
            if working_image_url:
                # Use your existing reference enhancement
                enhanced_prompt, references = await self.reference_service.enhance_prompt_with_working_image(
                    prompt, user_id, working_image_url
                )
                return enhanced_prompt, references
            else:
                # Parse reference mentions
                references, missing_tags = await self.reference_service.parse_reference_mentions(
                    prompt, user_id
                )
                return prompt, references
        except Exception as e:
            print(f"[WARNING] Reference integration failed: {e}")
            return prompt, []
    
    def _quick_enhance_prompt(self, prompt: str, intent: IntentClassification) -> str:
        """
        Quick rule-based prompt enhancement (no AI call for performance)
        """
        
        word_count = len(prompt.split())
        
        # Only enhance very short prompts
        if word_count >= 8:
            return prompt
        
        # Add basic quality descriptors based on workflow type
        if intent.workflow_type == WorkflowType.IMAGE_GENERATION:
            return f"{prompt}, high quality, detailed, professional"
        elif intent.workflow_type == WorkflowType.HAIR_STYLING:
            return f"{prompt}, professional hair styling, high detail"
        elif intent.workflow_type == WorkflowType.REFERENCE_STYLING:
            return f"{prompt}, high quality styling, professional photography"
        else:
            return f"{prompt}, high quality, detailed"
    
    async def _execute_generation(
        self,
        prompt: str,
        user_id: str,
        working_image_url: Optional[str],
        model_selection: ModelSelection,
        intent: IntentClassification,
        generation_id: str,
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Execute the actual content generation using the selected model
        """
        
        try:
            # Create a GenerationRequest object compatible with existing system
            generation_request = GenerationRequest(
                prompt=prompt,
                user_id=user_id,
                session_id=session_id or f"enhanced_session_{user_id}",
                uploaded_images=[working_image_url] if working_image_url else [],
                preferences={}
            )
            
            # Set the current working image on the request
            generation_request.current_working_image = working_image_url
            
            print(f"[DEBUG] Enhanced: Executing generation with model {model_selection.model_id}")
            print(f"[DEBUG] Enhanced: Working image: {working_image_url}")
            print(f"[DEBUG] Enhanced: Workflow type: {intent.workflow_type}")
            
            # For image editing workflows, ensure we have the required image parameter
            if intent.workflow_type in [WorkflowType.IMAGE_EDITING, WorkflowType.IMAGE_ENHANCEMENT, 
                                       WorkflowType.HAIR_STYLING, WorkflowType.REFERENCE_STYLING]:
                if not working_image_url:
                    return {
                        "success": False,
                        "error": f"Working image required for {intent.workflow_type.value} but none provided",
                        "output_url": None
                    }
            
            # Prepare parameters for the selected model
            parameters = {
                "prompt": prompt,
                "output_format": "jpg",
                "model": model_selection.model_id
            }
            
            # Add image parameters for image editing workflows
            if working_image_url and intent.workflow_type in [
                WorkflowType.IMAGE_EDITING, WorkflowType.IMAGE_ENHANCEMENT,
                WorkflowType.HAIR_STYLING, WorkflowType.REFERENCE_STYLING
            ]:
                parameters["image"] = working_image_url
                parameters["uploaded_image"] = working_image_url
                print(f"[DEBUG] Enhanced: Added image parameters for editing workflow")
            
            # Execute generation using the appropriate generator
            if model_selection.provider == "replicate":
                print(f"[DEBUG] Enhanced: Using Replicate generator")
                result = await self.replicate_generator.generate(
                    prompt=prompt,
                    parameters=parameters,
                    generation_id=generation_id
                )
            else:
                # Fallback to model router for other providers
                print(f"[DEBUG] Enhanced: Using model router fallback")
                routing_decision = await self.model_router.route_generation(
                    generation_request,
                    intent_analysis=None,  # We already have our classification
                    generation_id=generation_id
                )
                
                # Override the model with our AI-selected one
                routing_decision["model"] = model_selection.model_id
                routing_decision["parameters"].update(parameters)
                
                result = await self.replicate_generator.generate(
                    prompt=prompt,
                    parameters=routing_decision["parameters"],
                    generation_id=generation_id
                )
            
            # Convert GenerationResponse to dict for consistent handling
            if hasattr(result, 'dict'):
                result_dict = result.dict()
            else:
                result_dict = result
            
            # Update session with new working image if generation was successful
            if result_dict.get("success") and result_dict.get("output_url") and session_id:
                print(f"[DEBUG] Enhanced: Setting new working image in session: {result_dict['output_url']}")
                await session_manager.set_current_working_image(
                    session_id=session_id,
                    image_url=result_dict["output_url"],
                    user_id=user_id
                )
            
            return result_dict
            
        except Exception as e:
            print(f"[ERROR] Enhanced generation execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "output_url": None
            }
    
    async def _fallback_to_existing_system(
        self,
        prompt: str,
        user_id: str,
        working_image_url: Optional[str],
        error: str
    ) -> Dict[str, Any]:
        """
        Fallback to your existing workflow system if AI classification fails
        """
        
        return {
            "success": True,
            "workflow_type": "image_generation",  # Safe default
            "final_prompt": prompt,
            "model_selection": {
                "model_id": "black-forest-labs/flux-1.1-pro",
                "provider": "replicate",
                "reasoning": f"Fallback due to error: {error}"
            },
            "references": [],
            "intent_confidence": 0.5,
            "reasoning": "Fallback to existing system",
            "processing_time": 0.1,
            "estimated_cost": 0.04,
            "estimated_time": 30,
            "fallback_used": True
        }
    
    async def _perform_web_search(self, search_query: str) -> Optional[Dict[str, Any]]:
        """Sprint 2: Perform web search for styling references"""
        
        try:
            print(f"[DEBUG] Performing web search for: {search_query}")
            
            styling_data = await self.web_search_service.search_for_styling_references(search_query)
            self.metrics["web_searches"] += 1
            
            return styling_data
            
        except Exception as e:
            print(f"[ERROR] Web search failed: {e}")
            return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics including Sprint 2 web search stats"""
        total_requests = max(self.metrics["classifications"], 1)
        
        return {
            **self.metrics,
            "cache_hit_rate": self.metrics["cache_hits"] / total_requests,
            "error_rate": self.metrics["errors"] / total_requests,
            "web_search_rate": self.metrics["web_searches"] / total_requests,  # Sprint 2
            "web_search_cache_stats": self.web_search_service.get_cache_stats()  # Sprint 2
        } 