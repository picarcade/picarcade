"""
Sprint 3: Rate Limiter System
Distributed rate limiting for cost control and API protection
"""
import asyncio
import time
import logging
import os
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .cache import get_cache

logger = logging.getLogger(__name__)

class RateLimitScope(Enum):
    """Rate limiting scopes"""
    USER = "user"           # Per user limits
    GLOBAL = "global"       # Global application limits
    ENDPOINT = "endpoint"   # Per endpoint limits
    API_KEY = "api_key"     # Per API key limits

@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests: int           # Number of requests allowed
    window_seconds: int     # Time window in seconds
    scope: RateLimitScope   # Scope of the limit
    cost_limit: Optional[float] = None  # Optional cost limit

class RateLimiter:
    """Distributed rate limiter using Redis"""
    
    def __init__(self, limit_config: RateLimit, identifier: str):
        self.config = limit_config
        self.identifier = identifier
        self.cache = None
        
    async def _get_cache(self):
        """Get cache instance"""
        if self.cache is None:
            self.cache = await get_cache()
        return self.cache
    
    def _get_rate_limit_key(self) -> str:
        """Generate Redis key for rate limiting"""
        timestamp_window = int(time.time() // self.config.window_seconds)
        return f"rate_limit:{self.config.scope.value}:{self.identifier}:{timestamp_window}"
    
    def _get_cost_limit_key(self) -> str:
        """Generate Redis key for cost limiting"""
        timestamp_window = int(time.time() // self.config.window_seconds)
        return f"cost_limit:{self.config.scope.value}:{self.identifier}:{timestamp_window}"
    
    async def check_rate_limit(self, cost: float = 0.0) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits
        Returns: (allowed, limit_info)
        """
        cache = await self._get_cache()
        current_time = time.time()
        
        # Get rate limit key
        rate_key = self._get_rate_limit_key()
        
        try:
            # Check request count limit
            current_count = await cache.increment(
                rate_key, 
                amount=1, 
                ttl=self.config.window_seconds + 10  # Add buffer for cleanup
            )
            
            if current_count is None:
                current_count = 1
            
            # Check cost limit if specified
            cost_exceeded = False
            current_cost = 0.0
            
            if self.config.cost_limit and cost > 0:
                cost_key = self._get_cost_limit_key()
                
                # Get current cost in window
                current_cost_str = await cache.get(cost_key)
                current_cost = float(current_cost_str) if current_cost_str else 0.0
                
                # Check if adding this cost would exceed limit
                if current_cost + cost > self.config.cost_limit:
                    cost_exceeded = True
                else:
                    # Update cost tracking
                    await cache.set(
                        cost_key, 
                        current_cost + cost, 
                        ttl=self.config.window_seconds + 10
                    )
                    current_cost += cost
            
            # Determine if request is allowed
            request_exceeded = current_count > self.config.requests
            allowed = not (request_exceeded or cost_exceeded)
            
            # Prepare limit info
            limit_info = {
                "allowed": allowed,
                "scope": self.config.scope.value,
                "identifier": self.identifier,
                "requests": {
                    "current": current_count,
                    "limit": self.config.requests,
                    "exceeded": request_exceeded,
                    "remaining": max(0, self.config.requests - current_count),
                    "reset_time": current_time + self.config.window_seconds,
                    "window_seconds": self.config.window_seconds
                }
            }
            
            # Add cost info if applicable
            if self.config.cost_limit:
                limit_info["cost"] = {
                    "current": round(current_cost, 4),
                    "limit": self.config.cost_limit,
                    "exceeded": cost_exceeded,
                    "remaining": max(0, self.config.cost_limit - current_cost),
                    "this_request": cost
                }
            
            if not allowed:
                # If not allowed, decrement the counter since we're not processing
                if not request_exceeded:  # Only decrement if it was cost that failed
                    await cache.increment(rate_key, amount=-1, ttl=None)
                
                logger.warning(f"Rate limit exceeded for {self.identifier}: "
                             f"requests={current_count}/{self.config.requests}, "
                             f"cost={current_cost:.4f}/{self.config.cost_limit}")
            
            return allowed, limit_info
            
        except Exception as e:
            logger.error(f"Rate limit check failed for {self.identifier}: {e}")
            # Fail open - allow request but log error
            return True, {
                "allowed": True,
                "error": str(e),
                "scope": self.config.scope.value,
                "identifier": self.identifier
            }
    
    async def get_current_usage(self) -> Dict[str, Any]:
        """Get current usage stats without incrementing"""
        cache = await self._get_cache()
        
        try:
            rate_key = self._get_rate_limit_key()
            current_count_str = await cache.get(rate_key)
            current_count = int(current_count_str) if current_count_str else 0
            
            usage = {
                "scope": self.config.scope.value,
                "identifier": self.identifier,
                "requests": {
                    "current": current_count,
                    "limit": self.config.requests,
                    "remaining": max(0, self.config.requests - current_count)
                }
            }
            
            if self.config.cost_limit:
                cost_key = self._get_cost_limit_key()
                current_cost_str = await cache.get(cost_key)
                current_cost = float(current_cost_str) if current_cost_str else 0.0
                
                usage["cost"] = {
                    "current": round(current_cost, 4),
                    "limit": self.config.cost_limit,
                    "remaining": max(0, self.config.cost_limit - current_cost)
                }
            
            return usage
            
        except Exception as e:
            logger.error(f"Failed to get usage for {self.identifier}: {e}")
            return {"error": str(e)}


class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str, limit_info: Dict[str, Any]):
        super().__init__(message)
        self.limit_info = limit_info


# Predefined rate limiters from environment
def get_user_rate_limiter(user_id: str) -> RateLimiter:
    """Get rate limiter for a specific user"""
    requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100"))
    requests_per_hour = int(os.getenv("RATE_LIMIT_REQUESTS_PER_HOUR", "1000"))
    cost_per_hour = float(os.getenv("COST_LIMIT_PER_HOUR", "50.0"))
    
    # Use the more restrictive hourly limit for now
    limit_config = RateLimit(
        requests=requests_per_hour,
        window_seconds=3600,  # 1 hour
        scope=RateLimitScope.USER,
        cost_limit=cost_per_hour
    )
    
    return RateLimiter(limit_config, user_id)

def get_global_rate_limiter() -> RateLimiter:
    """Get global application rate limiter"""
    # Global limits are higher than per-user limits
    limit_config = RateLimit(
        requests=10000,  # 10k requests per hour globally
        window_seconds=3600,
        scope=RateLimitScope.GLOBAL,
        cost_limit=500.0  # $500/hour global cost limit
    )
    
    return RateLimiter(limit_config, "application")

def get_api_rate_limiter(api_name: str) -> RateLimiter:
    """Get rate limiter for specific API endpoints"""
    # API-specific limits
    api_limits = {
        "openai": RateLimit(
            requests=1000,
            window_seconds=3600,
            scope=RateLimitScope.API_KEY,
            cost_limit=100.0
        ),
        "runway": RateLimit(
            requests=500,
            window_seconds=3600,
            scope=RateLimitScope.API_KEY,
            cost_limit=200.0
        ),
        "replicate": RateLimit(
            requests=800,
            window_seconds=3600,
            scope=RateLimitScope.API_KEY,
            cost_limit=150.0
        )
    }
    
    limit_config = api_limits.get(api_name, RateLimit(
        requests=100,
        window_seconds=3600,
        scope=RateLimitScope.API_KEY,
        cost_limit=50.0
    ))
    
    return RateLimiter(limit_config, api_name)


async def check_all_rate_limits(user_id: str, api_name: str, estimated_cost: float = 0.0) -> Tuple[bool, Dict[str, Any]]:
    """
    Check multiple rate limits and return comprehensive result
    Returns: (allowed, combined_limit_info)
    """
    results = {}
    overall_allowed = True
    
    # Check user rate limit
    user_limiter = get_user_rate_limiter(user_id)
    user_allowed, user_info = await user_limiter.check_rate_limit(estimated_cost)
    results["user"] = user_info
    overall_allowed = overall_allowed and user_allowed
    
    # Check global rate limit
    global_limiter = get_global_rate_limiter()
    global_allowed, global_info = await global_limiter.check_rate_limit(estimated_cost)
    results["global"] = global_info
    overall_allowed = overall_allowed and global_allowed
    
    # Check API-specific rate limit
    if api_name:
        api_limiter = get_api_rate_limiter(api_name)
        api_allowed, api_info = await api_limiter.check_rate_limit(estimated_cost)
        results[f"api_{api_name}"] = api_info
        overall_allowed = overall_allowed and api_allowed
    
    combined_result = {
        "overall_allowed": overall_allowed,
        "limits": results,
        "user_id": user_id,
        "api_name": api_name,
        "estimated_cost": estimated_cost,
        "checked_at": time.time()
    }
    
    return overall_allowed, combined_result


def rate_limit(user_id_getter: callable = None, api_name: str = None, cost_estimator: callable = None):
    """
    Decorator for automatic rate limiting
    
    Args:
        user_id_getter: Function to extract user_id from request
        api_name: Name of the API being called
        cost_estimator: Function to estimate cost of the operation
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user ID
            if user_id_getter:
                user_id = user_id_getter(*args, **kwargs)
            else:
                user_id = kwargs.get("user_id", "anonymous")
            
            # Estimate cost
            estimated_cost = 0.0
            if cost_estimator:
                estimated_cost = cost_estimator(*args, **kwargs)
            
            # Check rate limits
            allowed, limit_info = await check_all_rate_limits(user_id, api_name, estimated_cost)
            
            if not allowed:
                raise RateLimitError(
                    f"Rate limit exceeded for user {user_id}",
                    limit_info
                )
            
            # Execute original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator 