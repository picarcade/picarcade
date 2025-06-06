# app/services/generators/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import uuid
import time
import functools
import asyncio
from app.models.generation import GenerationResponse
from app.core.logging import generation_logger

class BaseGenerator(ABC):
    """Base class for all generation providers"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    @abstractmethod
    async def generate(self, 
                      prompt: str, 
                      parameters: Dict[str, Any]) -> GenerationResponse:
        """Generate content based on prompt and parameters"""
        pass
    
    def _create_generation_id(self) -> str:
        """Create unique generation ID"""
        return f"gen_{uuid.uuid4().hex[:12]}"
    
    def _log_generation_attempt(self,
                               generation_id: str,
                               model_used: str,
                               parameters: Dict[str, Any],
                               success: bool,
                               execution_time: float,
                               error_message: str = None):
        """Log generation attempt with details"""
        generation_logger.log_model_generation(
            generation_id=generation_id,
            model_used=model_used,
            generator_type=self.__class__.__name__,
            parameters=parameters,
            success=success,
            execution_time=execution_time,
            error_message=error_message
        )
    
    @staticmethod
    def _measure_time(func):
        """Decorator to measure execution time"""
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(self, *args, **kwargs):
                start_time = time.time()
                result = await func(self, *args, **kwargs)
                end_time = time.time()
                
                if hasattr(result, 'execution_time'):
                    result.execution_time = end_time - start_time
                
                return result
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(self, *args, **kwargs):
                start_time = time.time()
                result = func(self, *args, **kwargs)
                end_time = time.time()
                
                if hasattr(result, 'execution_time'):
                    result.execution_time = end_time - start_time
                
                return result
            return sync_wrapper