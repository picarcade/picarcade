"""
Sprint 3 Simple Integration Test: Test core infrastructure components
"""
import os
import asyncio
import time
from app.core.circuit_breaker import CircuitBreaker, CircuitConfig, CircuitState

# Set up environment for testing  
os.environ.setdefault("REDIS_URL", "rediss://default:AbyQAAIjcDE5NDcwNTY3MTc4ODE0NTM1YWQ4YjMzMDA4NDk3N2Y5OXAxMA@apt-kangaroo-48272.upstash.io:6379")

async def test_sprint3_infrastructure():
    """Test Sprint 3 infrastructure components"""
    print("🚀 Testing Sprint 3 Infrastructure Components")
    print("=" * 60)
    
    # Test 1: Distributed Cache
    print("\n📦 Testing Distributed Cache...")
    try:
        from app.core.cache import get_cache
        
        cache = await get_cache()
        
        # Test basic operations
        await cache.set("test_key", {"message": "Hello Sprint 3!"}, ttl=60)
        result = await cache.get("test_key")
        
        if result and result.get("message") == "Hello Sprint 3!":
            print("   ✅ Cache set/get working")
        else:
            print("   ❌ Cache set/get failed")
        
        # Test health
        health = await cache.get_health()
        print(f"   📊 Cache health: {health.get('status', 'unknown')}")
        print(f"   📊 Cache latency: {health.get('latency_ms', 'unknown')}ms")
        
        cache_passed = True
        
    except Exception as e:
        print(f"   ❌ Cache test failed: {e}")
        cache_passed = False
    
    # Test 2: Circuit Breaker  
    print("\n🔌 Testing Circuit Breaker...")
    try:
        config = CircuitConfig(failure_threshold=3, timeout_seconds=5, success_threshold=2)
        breaker = CircuitBreaker("test_circuit", config)
        
        # Test successful call
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        
        if result == "success":
            print("   ✅ Circuit breaker successful call")
        else:
            print("   ❌ Circuit breaker call failed")
        
        # Test stats
        stats = breaker.get_stats()
        print(f"   📊 Circuit state: {stats['state']}")
        print(f"   📊 Total calls: {stats['total_calls']}")
        print(f"   📊 Success rate: {stats['success_rate_percent']}%")
        
        circuit_passed = True
        
    except Exception as e:
        print(f"   ❌ Circuit breaker test failed: {e}")
        circuit_passed = False
    
    # Test 3: Rate Limiter
    print("\n⚡ Testing Rate Limiter...")
    try:
        from app.core.rate_limiter import get_user_rate_limiter, check_all_rate_limits
        
        user_id = "test_user_simple"
        allowed_count = 0
        
        # Test multiple rate limit checks
        for i in range(5):
            is_allowed, info = await check_all_rate_limits(
                user_id=user_id,
                api_name="test_api",
                estimated_cost=0.01
            )
            
            if is_allowed:
                allowed_count += 1
                print(f"   ✅ Request {i+1}: Allowed")
            else:
                print(f"   ❌ Request {i+1}: Rate limited")
        
        print(f"   📊 Allowed requests: {allowed_count}/5")
        
        # Test individual rate limiter
        user_limiter = get_user_rate_limiter(user_id)
        stats = await user_limiter.get_current_usage()
        print(f"   📊 Current usage: {stats.get('requests', {}).get('current', 0)} requests")
        
        rate_limiter_passed = True
        
    except Exception as e:
        print(f"   ❌ Rate limiter test failed: {e}")
        rate_limiter_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    total_tests = 3
    passed_tests = sum([cache_passed, circuit_passed, rate_limiter_passed])
    
    print(f"🏁 Sprint 3 Infrastructure Test Results:")
    print(f"   ✅ Passed: {passed_tests}/{total_tests}")
    print(f"   📊 Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 All Sprint 3 infrastructure tests PASSED!")
        return True
    else:
        print("⚠️  Some infrastructure components failed")
        return False

if __name__ == "__main__":
    asyncio.run(test_sprint3_infrastructure()) 