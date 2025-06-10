"""
Sprint 3: Distributed Cache System
Replaces in-memory cache with Redis for multi-instance deployment
"""
import redis
import json
import asyncio
import os
import logging
from typing import Any, Optional, Dict, Union
from datetime import timedelta
from functools import wraps

logger = logging.getLogger(__name__)

class DistributedCache:
    """Redis-based distributed cache for multi-instance deployment"""
    
    def __init__(self, redis_url: str = None, prefix: str = "picarcade:", ttl: int = 3600):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.prefix = prefix
        self.default_ttl = ttl
        self.client = None
        self._connection_healthy = False
        
    async def connect(self) -> bool:
        """Establish Redis connection with error handling"""
        try:
            if not self.redis_url:
                logger.error("No Redis URL provided")
                return False
                
            # Parse SSL requirement from URL
            ssl_required = self.redis_url.startswith("rediss://")
            
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                ssl_cert_reqs="required" if ssl_required else None,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.ping
            )
            
            self._connection_healthy = True
            logger.info("Redis connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connection_healthy = False
            return False
    
    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key"""
        return f"{self.prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with JSON deserialization"""
        if not self._connection_healthy:
            return None
            
        try:
            redis_key = self._make_key(key)
            value = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get, redis_key
            )
            
            if value is None:
                return None
                
            # Try to deserialize JSON, fallback to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with JSON serialization"""
        if not self._connection_healthy:
            return False
            
        try:
            redis_key = self._make_key(key)
            ttl = ttl or self.default_ttl
            
            # Serialize value to JSON if possible, fallback to string
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)
            
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.client.setex, redis_key, ttl, serialized_value
            )
            
            return bool(success)
            
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._connection_healthy:
            return False
            
        try:
            redis_key = self._make_key(key)
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.client.delete, redis_key
            )
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._connection_healthy:
            return False
            
        try:
            redis_key = self._make_key(key)
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.client.exists, redis_key
            )
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Cache exists check failed for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        """Increment counter in cache (for rate limiting)"""
        if not self._connection_healthy:
            return None
            
        try:
            redis_key = self._make_key(key)
            
            # Use pipeline for atomic operations
            pipe = self.client.pipeline()
            pipe.incr(redis_key, amount)
            if ttl:
                pipe.expire(redis_key, ttl)
            
            results = await asyncio.get_event_loop().run_in_executor(
                None, pipe.execute
            )
            
            return int(results[0]) if results else None
            
        except Exception as e:
            logger.warning(f"Cache increment failed for key {key}: {e}")
            return None
    
    async def get_health(self) -> Dict[str, Any]:
        """Get cache health metrics"""
        try:
            if not self.client:
                return {"status": "disconnected", "healthy": False}
            
            # Test ping
            start_time = asyncio.get_event_loop().time()
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.ping
            )
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Get Redis info
            info = await asyncio.get_event_loop().run_in_executor(
                None, self.client.info
            )
            
            return {
                "status": "connected",
                "healthy": True,
                "latency_ms": round(latency, 2),
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            self._connection_healthy = False
            return {"status": "error", "healthy": False, "error": str(e)}
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern (use carefully!)"""
        if not self._connection_healthy:
            return 0
            
        try:
            redis_pattern = self._make_key(pattern)
            keys = await asyncio.get_event_loop().run_in_executor(
                None, self.client.keys, redis_pattern
            )
            
            if keys:
                deleted = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.delete, *keys
                )
                return int(deleted)
            
            return 0
            
        except Exception as e:
            logger.warning(f"Cache pattern clear failed for {pattern}: {e}")
            return 0


# Global cache instance
_cache_instance = None

async def get_cache() -> DistributedCache:
    """Get or create global cache instance"""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = DistributedCache()
        await _cache_instance.connect()
    
    return _cache_instance


def cache_result(key_template: str, ttl: int = 3600):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from template and args
            cache_key = key_template.format(*args, **kwargs)
            
            cache = await get_cache()
            
            # Try to get from cache first
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator 