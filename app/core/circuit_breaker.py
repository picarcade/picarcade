"""
Sprint 3: Circuit Breaker System
Prevents cascading failures when external APIs are down
"""
import asyncio
import time
import logging
from typing import Any, Callable, Optional, Dict
from enum import Enum
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Blocking calls
    HALF_OPEN = "half_open" # Testing if service recovered

@dataclass
class CircuitConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5      # Failures before opening
    timeout_seconds: int = 60       # Time before testing recovery
    success_threshold: int = 3      # Successes to close circuit
    monitor_window: int = 300       # Time window for failure tracking

class CircuitBreaker:
    """Circuit breaker for external API calls"""
    
    def __init__(self, name: str, config: CircuitConfig = None):
        self.name = name
        self.config = config or CircuitConfig()
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.last_state_change = time.time()
        
        # Monitoring
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.blocked_calls = 0
        
        logger.info(f"Circuit breaker '{name}' initialized in CLOSED state")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        self.total_calls += 1
        
        # Check if circuit should remain open
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time < self.config.timeout_seconds:
                self.blocked_calls += 1
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Retry in {self.config.timeout_seconds - (time.time() - self.last_failure_time):.1f}s"
                )
            else:
                # Transition to HALF_OPEN for testing
                self._transition_to_half_open()
        
        try:
            # Execute the protected function
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Record success
            await self._record_success(execution_time)
            return result
            
        except Exception as e:
            # Record failure
            await self._record_failure(e)
            raise
    
    async def _record_success(self, execution_time: float):
        """Record successful call"""
        self.successful_calls += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(f"Circuit '{self.name}': Success in HALF_OPEN state ({self.success_count}/{self.config.success_threshold})")
            
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)
    
    async def _record_failure(self, error: Exception):
        """Record failed call"""
        self.failed_calls += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        logger.warning(f"Circuit '{self.name}': Failure recorded - {error} (count: {self.failure_count})")
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN immediately opens circuit
            self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition circuit to OPEN state"""
        self.state = CircuitState.OPEN
        self.last_state_change = time.time()
        self.success_count = 0
        
        logger.error(f"Circuit '{self.name}' OPENED after {self.failure_count} failures")
    
    def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = time.time()
        self.success_count = 0
        
        logger.info(f"Circuit '{self.name}' transitioned to HALF_OPEN for testing")
    
    def _transition_to_closed(self):
        """Transition circuit to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()
        self.failure_count = 0
        self.success_count = 0
        
        logger.info(f"Circuit '{self.name}' CLOSED - service recovered")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        uptime = time.time() - self.last_state_change
        success_rate = (self.successful_calls / self.total_calls * 100) if self.total_calls > 0 else 0
        
        return {
            "name": self.name,
            "state": self.state.value,
            "uptime_seconds": round(uptime, 2),
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "blocked_calls": self.blocked_calls,
            "success_rate_percent": round(success_rate, 2),
            "failure_count": self.failure_count,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "timeout_seconds": self.config.timeout_seconds,
                "success_threshold": self.config.success_threshold
            }
        }
    
    def force_open(self):
        """Manually open circuit (for maintenance)"""
        self._transition_to_open()
        logger.warning(f"Circuit '{self.name}' manually opened")
    
    def force_close(self):
        """Manually close circuit (for recovery)"""
        self._transition_to_closed()
        logger.info(f"Circuit '{self.name}' manually closed")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}

def get_circuit_breaker(name: str, config: CircuitConfig = None) -> CircuitBreaker:
    """Get or create circuit breaker instance"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]

def circuit_breaker(name: str, config: CircuitConfig = None):
    """Decorator for circuit breaker protection"""
    def decorator(func):
        breaker = get_circuit_breaker(name, config)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator

async def get_all_circuit_stats() -> Dict[str, Any]:
    """Get statistics for all circuit breakers"""
    return {
        "circuit_breakers": [cb.get_stats() for cb in _circuit_breakers.values()],
        "total_circuits": len(_circuit_breakers),
        "healthy_circuits": sum(1 for cb in _circuit_breakers.values() if cb.state == CircuitState.CLOSED),
        "open_circuits": sum(1 for cb in _circuit_breakers.values() if cb.state == CircuitState.OPEN),
        "half_open_circuits": sum(1 for cb in _circuit_breakers.values() if cb.state == CircuitState.HALF_OPEN)
    }


# Predefined circuit breakers for common services
def get_openai_circuit() -> CircuitBreaker:
    """Get circuit breaker for OpenAI API"""
    config = CircuitConfig(
        failure_threshold=3,    # Open after 3 failures
        timeout_seconds=30,     # Test recovery after 30s
        success_threshold=2     # Close after 2 successes
    )
    return get_circuit_breaker("openai", config)

def get_runway_circuit() -> CircuitBreaker:
    """Get circuit breaker for Runway API"""
    config = CircuitConfig(
        failure_threshold=5,    # Open after 5 failures
        timeout_seconds=60,     # Test recovery after 60s
        success_threshold=3     # Close after 3 successes
    )
    return get_circuit_breaker("runway", config)

def get_replicate_circuit() -> CircuitBreaker:
    """Get circuit breaker for Replicate API"""
    config = CircuitConfig(
        failure_threshold=5,    # Open after 5 failures
        timeout_seconds=45,     # Test recovery after 45s
        success_threshold=2     # Close after 2 successes
    )
    return get_circuit_breaker("replicate", config) 