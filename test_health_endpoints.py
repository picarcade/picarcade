"""
Test Sprint 3 Health Check Endpoints
"""
import asyncio
import os
from app.api.health import (
    health_check, detailed_health_check, cache_health, 
    readiness_check, liveness_check
)

# Set up environment for testing  
os.environ.setdefault("REDIS_URL", "rediss://default:AbyQAAIjcDE5NDcwNTY3MTc4ODE0NTM1YWQ4YjMzMDA4NDk3N2Y5OXAxMA@apt-kangaroo-48272.upstash.io:6379")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test_key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test_service_key")

async def test_health_endpoints():
    """Test all health check endpoints"""
    print("🏥 Testing Sprint 3 Health Check Endpoints")
    print("=" * 60)
    
    passed = 0
    total = 0
    
    # Test 1: Basic health check
    print("\n🩺 Testing basic health check...")
    try:
        result = await health_check()
        print(f"   ✅ Status: {result.get('status')}")
        print(f"   ✅ Service: {result.get('service')}")
        print(f"   ✅ Version: {result.get('version')}")
        passed += 1
    except Exception as e:
        print(f"   ❌ Basic health check failed: {e}")
    total += 1
    
    # Test 2: Liveness check
    print("\n💓 Testing liveness check...")
    try:
        result = await liveness_check()
        print(f"   ✅ Alive: {result.get('alive')}")
        print(f"   ✅ Status: {result.get('status')}")
        passed += 1
    except Exception as e:
        print(f"   ❌ Liveness check failed: {e}")
    total += 1
    
    # Test 3: Cache health
    print("\n📦 Testing cache health...")
    try:
        result = await cache_health()
        print(f"   ✅ Status: {result.get('status')}")
        print(f"   ✅ Latency: {result.get('latency_ms')}ms")
        print(f"   ✅ Provider: {result.get('provider')}")
        passed += 1
    except Exception as e:
        print(f"   ❌ Cache health check failed: {e}")
    total += 1
    
    # Test 4: Readiness check
    print("\n🚀 Testing readiness check...")
    try:
        result = await readiness_check()
        print(f"   ✅ Ready: {result.get('ready')}")
        print(f"   ✅ Status: {result.get('status')}")
        passed += 1
    except Exception as e:
        print(f"   ❌ Readiness check failed: {e}")
    total += 1
    
    # Test 5: Detailed health check
    print("\n🔍 Testing detailed health check...")
    try:
        result = await detailed_health_check()
        print(f"   ✅ Overall: {result.get('overall')}")
        print(f"   ✅ Health percentage: {result.get('summary', {}).get('health_percentage', 0)}%")
        print(f"   ✅ Healthy components: {result.get('summary', {}).get('healthy_components', 0)}")
        print(f"   ✅ Total components: {result.get('summary', {}).get('total_components', 0)}")
        
        # Show component details
        components = result.get('components', {})
        for name, status in components.items():
            health_status = "✅" if status.get('healthy', False) else "❌"
            print(f"      {health_status} {name}: {status.get('status', 'unknown')}")
        
        passed += 1
    except Exception as e:
        print(f"   ❌ Detailed health check failed: {e}")
    total += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"🏁 Health Endpoint Test Results:")
    print(f"   ✅ Passed: {passed}/{total}")
    print(f"   📊 Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All health check endpoints PASSED!")
        return True
    else:
        print("⚠️  Some health endpoints failed")
        return False

if __name__ == "__main__":
    asyncio.run(test_health_endpoints()) 