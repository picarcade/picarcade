#!/usr/bin/env python3
"""
Sprint 3: Infrastructure Testing
Tests all core Sprint 3 components: Cache, Circuit Breaker, Rate Limiter
"""
import asyncio
import time
import logging
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_distributed_cache():
    """Test the distributed cache system"""
    print("🔍 Testing Distributed Cache...")
    
    try:
        from app.core.cache import get_cache, cache_result
        
        cache = await get_cache()
        
        # Test basic operations
        test_key = "test:cache:basic"
        test_value = {"message": "Hello Sprint 3!", "timestamp": time.time()}
        
        # Set value
        success = await cache.set(test_key, test_value, ttl=60)
        assert success, "Cache set should succeed"
        
        # Get value
        retrieved = await cache.get(test_key)
        assert retrieved == test_value, "Retrieved value should match"
        
        # Test exists
        exists = await cache.exists(test_key)
        assert exists, "Key should exist"
        
        # Test increment (for rate limiting)
        counter_key = "test:counter"
        count = await cache.increment(counter_key, amount=1, ttl=60)
        assert count == 1, "Counter should start at 1"
        
        count = await cache.increment(counter_key, amount=5, ttl=60)
        assert count == 6, "Counter should increment by 5"
        
        # Test cache decorator
        @cache_result("test:function:{0}", ttl=30)
        async def test_function(param):
            return f"processed_{param}_{time.time()}"
        
        result1 = await test_function("hello")
        result2 = await test_function("hello")  # Should be cached
        assert result1 == result2, "Cached results should be identical"
        
        # Test health
        health = await cache.get_health()
        assert health["healthy"], "Cache should be healthy"
        
        # Cleanup
        await cache.delete(test_key)
        await cache.delete(counter_key)
        await cache.clear_pattern("test:function:*")
        
        return {
            "status": "✅ SUCCESS",
            "latency_ms": health.get("latency_ms", 0),
            "operations": ["set", "get", "exists", "increment", "decorator", "delete", "health"]
        }
        
    except Exception as e:
        return {"status": "❌ FAILED", "error": str(e)}

async def test_circuit_breaker():
    """Test the circuit breaker system"""
    print("🔍 Testing Circuit Breaker...")
    
    try:
        from app.core.circuit_breaker import (
            CircuitBreaker, CircuitConfig, CircuitState, 
            circuit_breaker, get_all_circuit_stats
        )
        
        # Create test circuit breaker with fast config
        config = CircuitConfig(
            failure_threshold=2,    # Open after 2 failures
            timeout_seconds=1,      # Test recovery after 1s
            success_threshold=1     # Close after 1 success
        )
        
        breaker = CircuitBreaker("test_service", config)
        
        # Test successful calls
        async def success_function():
            return "success"
        
        result = await breaker.call(success_function)
        assert result == "success", "Successful call should work"
        assert breaker.state == CircuitState.CLOSED, "Circuit should remain closed"
        
        # Test failing calls
        async def failing_function():
            raise Exception("Simulated failure")
        
        # Trigger failures to open circuit
        for i in range(3):
            try:
                await breaker.call(failing_function)
            except Exception:
                pass  # Expected
        
        assert breaker.state == CircuitState.OPEN, "Circuit should be open after failures"
        
        # Test that circuit blocks calls when open
        try:
            await breaker.call(success_function)
            assert False, "Circuit should block calls when open"
        except Exception as e:
            assert "OPEN" in str(e), "Should get circuit open error"
        
        # Wait for timeout and test half-open
        await asyncio.sleep(1.1)  # Wait for timeout
        
        # Next call should transition to half-open and succeed
        result = await breaker.call(success_function)
        assert result == "success", "Call should succeed in half-open"
        assert breaker.state == CircuitState.CLOSED, "Circuit should close after success"
        
        # Test circuit breaker decorator
        @circuit_breaker("test_decorated", config)
        async def decorated_function(should_fail=False):
            if should_fail:
                raise Exception("Decorated failure")
            return "decorated_success"
        
        result = await decorated_function(False)
        assert result == "decorated_success", "Decorated function should work"
        
        # Test statistics
        stats = breaker.get_stats()
        assert stats["name"] == "test_service", "Stats should have correct name"
        assert stats["total_calls"] > 0, "Should have recorded calls"
        
        # Test global stats
        global_stats = await get_all_circuit_stats()
        assert len(global_stats["circuit_breakers"]) >= 1, "Should have at least one circuit"
        
        return {
            "status": "✅ SUCCESS",
            "circuits_tested": 2,
            "states_tested": ["CLOSED", "OPEN", "HALF_OPEN"],
            "features": ["manual_calls", "decorator", "stats", "transitions"]
        }
        
    except Exception as e:
        return {"status": "❌ FAILED", "error": str(e)}

async def test_rate_limiter():
    """Test the rate limiter system"""
    print("🔍 Testing Rate Limiter...")
    
    try:
        from app.core.rate_limiter import (
            RateLimiter, RateLimit, RateLimitScope,
            get_user_rate_limiter, check_all_rate_limits,
            rate_limit
        )
        
        # Test basic rate limiter
        test_config = RateLimit(
            requests=3,
            window_seconds=60,
            scope=RateLimitScope.USER,
            cost_limit=10.0
        )
        
        limiter = RateLimiter(test_config, f"test_user_{int(time.time())}")
        
        # Test allowed requests
        for i in range(3):
            allowed, info = await limiter.check_rate_limit(cost=1.0)
            assert allowed, f"Request {i+1} should be allowed"
            assert info["requests"]["current"] == i + 1, f"Counter should be {i+1}, got {info['requests']['current']}"
            assert info["cost"]["current"] == i + 1, f"Cost should be {i+1}, got {info['cost']['current']}"
        
        # Test rate limit exceeded
        allowed, info = await limiter.check_rate_limit(cost=1.0)
        assert not allowed, "4th request should be blocked"
        assert info["requests"]["exceeded"], "Should indicate request limit exceeded"
        
        # Test cost limit
        cost_limiter = RateLimiter(
            RateLimit(requests=100, window_seconds=60, scope=RateLimitScope.USER, cost_limit=5.0),
            f"test_cost_user_{int(time.time())}"
        )
        
        # Allowed within cost limit
        allowed, info = await cost_limiter.check_rate_limit(cost=3.0)
        assert allowed, "Request within cost limit should be allowed"
        
        # Blocked by cost limit
        allowed, info = await cost_limiter.check_rate_limit(cost=5.0)
        assert not allowed, "Request exceeding cost limit should be blocked"
        assert info["cost"]["exceeded"], "Should indicate cost limit exceeded"
        
        # Test user rate limiter
        user_limiter = get_user_rate_limiter("test_user_123")
        usage = await user_limiter.get_current_usage()
        assert "requests" in usage, "Should have request usage info"
        assert "cost" in usage, "Should have cost usage info"
        
        # Test comprehensive rate limiting
        allowed, combined = await check_all_rate_limits("test_user_456", "openai", 0.01)
        assert allowed, "Low-cost request should be allowed"
        assert "user" in combined["limits"], "Should check user limits"
        assert "global" in combined["limits"], "Should check global limits"
        assert "api_openai" in combined["limits"], "Should check API limits"
        
        # Test rate limit decorator
        @rate_limit(
            user_id_getter=lambda *args, **kwargs: kwargs.get("user_id", "test"),
            api_name="test_api",
            cost_estimator=lambda *args, **kwargs: 0.01
        )
        async def limited_function(user_id=None):
            return f"success for {user_id}"
        
        result = await limited_function(user_id="test_decorator_user")
        assert "success" in result, "Decorated function should work"
        
        return {
            "status": "✅ SUCCESS",
            "limiters_tested": ["basic", "cost", "user", "global", "api"],
            "features": ["request_limiting", "cost_limiting", "multi_scope", "decorator"]
        }
        
    except Exception as e:
        return {"status": "❌ FAILED", "error": str(e)}

async def test_integration():
    """Test integration between components"""
    print("🔍 Testing Component Integration...")
    
    try:
        from app.core.cache import get_cache
        from app.core.circuit_breaker import get_circuit_breaker, CircuitConfig
        from app.core.rate_limiter import get_user_rate_limiter
        
        # Test that cache is shared between components
        cache = await get_cache()
        
        # Test circuit breaker with cached results
        circuit = get_circuit_breaker("integration_test", CircuitConfig(failure_threshold=2))
        
        async def cached_api_call():
            # Simulate API call that could be cached
            cache_key = "integration:api_result"
            cached = await cache.get(cache_key)
            if cached:
                return cached
            
            result = {"data": "api_response", "timestamp": time.time()}
            await cache.set(cache_key, result, ttl=60)
            return result
        
        # Call through circuit breaker
        result1 = await circuit.call(cached_api_call)
        result2 = await circuit.call(cached_api_call)  # Should use cache
        
        assert result1 == result2, "Results should be identical (cached)"
        
        # Test rate limiter with circuit breaker stats
        limiter = get_user_rate_limiter("integration_user")
        usage = await limiter.get_current_usage()
        
        circuit_stats = circuit.get_stats()
        
        # Verify both systems are working
        assert usage["requests"]["limit"] > 0, "Rate limiter should have limits"
        assert circuit_stats["total_calls"] > 0, "Circuit should have recorded calls"
        
        return {
            "status": "✅ SUCCESS", 
            "integration_points": ["cache_circuit", "cache_rate_limiter", "shared_redis"]
        }
        
    except Exception as e:
        return {"status": "❌ FAILED", "error": str(e)}

async def main():
    """Run all Sprint 3 infrastructure tests"""
    print("🚀 Sprint 3 Infrastructure Testing")
    print("=" * 50)
    
    tests = [
        ("Distributed Cache", test_distributed_cache),
        ("Circuit Breaker", test_circuit_breaker),
        ("Rate Limiter", test_rate_limiter),
        ("Component Integration", test_integration)
    ]
    
    results = {}
    
    for name, test_func in tests:
        print(f"\n🧪 Testing {name}...")
        try:
            result = await test_func()
            results[name] = result
            print(f"   {result['status']}")
        except Exception as e:
            results[name] = {"status": "❌ FAILED", "error": str(e)}
            print(f"   ❌ FAILED: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SPRINT 3 INFRASTRUCTURE TEST RESULTS")
    print("=" * 50)
    
    passed = sum(1 for r in results.values() if "SUCCESS" in r["status"])
    total = len(results)
    
    for name, result in results.items():
        status = result["status"]
        print(f"{name:<25} {status}")
        if "error" in result:
            print(f"{'':25} Error: {result['error']}")
    
    print(f"\n🎯 OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All Sprint 3 infrastructure components are working!")
        print("🚀 Ready to update IntentClassifier and add health endpoints")
    else:
        print("❌ Some components need attention before proceeding")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 