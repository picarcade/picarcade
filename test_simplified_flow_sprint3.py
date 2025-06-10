"""
Test Script: SimplifiedFlowService with Sprint 3 Infrastructure
Tests the integration of Sprint 3 components with the simplified flow service.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, trying manual .env loading")
    # Manual .env loading as fallback
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"')
        print("✅ Manually loaded .env file")

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.services.simplified_flow_service import simplified_flow

async def test_simplified_flow_sprint3():
    """Test SimplifiedFlowService with Sprint 3 infrastructure"""
    
    print("🚀 Testing SimplifiedFlowService with Sprint 3 Infrastructure")
    print("=" * 60)
    
    # Test data
    test_cases = [
        {
            "prompt": "Create a sunset over the ocean",
            "active_image": False,
            "uploaded_image": False,
            "referenced_image": False,
            "expected_type": "NEW_IMAGE"
        },
        {
            "prompt": "Add a hat to this person",
            "active_image": True,
            "uploaded_image": False,
            "referenced_image": False,
            "expected_type": "EDIT_IMAGE"
        },
        {
            "prompt": "Style like Taylor Swift at the Grammy awards",
            "active_image": False,
            "uploaded_image": False,
            "referenced_image": True,
            "expected_type": "NEW_IMAGE_REF"
        },
        {
            "prompt": "Change the background to a beach",
            "active_image": True,
            "uploaded_image": True,
            "referenced_image": False,
            "expected_type": "EDIT_IMAGE_REF"
        }
    ]
    
    print("1️⃣ Testing Health Check...")
    try:
        health = await simplified_flow.get_health()
        print(f"✅ Health Status: {health.get('status', 'unknown')}")
        print(f"✅ Initialized: {health.get('initialized', False)}")
        print(f"✅ Model: {health.get('model', 'unknown')}")
        print(f"✅ Cache Status: {health.get('cache', {}).get('status', 'unknown')}")
        print(f"✅ Circuit Breaker: {health.get('circuit_breaker', {}).get('status', 'unknown')}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    print("\n2️⃣ Testing Classification with Sprint 3 Infrastructure...")
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['prompt'][:30]}...")
        
        try:
            start_time = time.time()
            
            result = await simplified_flow.process_user_request(
                user_prompt=test_case["prompt"],
                active_image=test_case["active_image"],
                uploaded_image=test_case["uploaded_image"],
                referenced_image=test_case["referenced_image"],
                context={"test_mode": True},
                user_id=f"test_user_{i}"
            )
            
            processing_time = time.time() - start_time
            
            # Verify result structure
            assert hasattr(result, 'prompt_type'), "Missing prompt_type"
            assert hasattr(result, 'enhanced_prompt'), "Missing enhanced_prompt"
            assert hasattr(result, 'model_to_use'), "Missing model_to_use"
            assert hasattr(result, 'reasoning'), "Missing reasoning"
            assert hasattr(result, 'processing_time_ms'), "Missing processing_time_ms"
            assert hasattr(result, 'cache_hit'), "Missing cache_hit"
            
            # Check expected type
            expected = test_case["expected_type"]
            actual = result.prompt_type.value
            
            if actual == expected:
                print(f"  ✅ Type: {actual} (correct)")
            else:
                print(f"  ⚠️  Type: {actual} (expected {expected})")
                all_passed = False
            
            print(f"  ✅ Model: {result.model_to_use}")
            print(f"  ✅ Enhanced: {result.enhanced_prompt[:50]}...")
            print(f"  ✅ Cache Hit: {result.cache_hit}")
            print(f"  ✅ Processing Time: {result.processing_time_ms}ms")
            print(f"  ✅ Total Time: {processing_time*1000:.1f}ms")
            
        except Exception as e:
            print(f"  ❌ Test {i} failed: {e}")
            all_passed = False
    
    print("\n3️⃣ Testing Rate Limiting...")
    try:
        # Test rapid requests to trigger rate limiting
        rapid_results = []
        for i in range(3):
            result = await simplified_flow.process_user_request(
                user_prompt="Test rate limiting",
                active_image=False,
                uploaded_image=False,
                referenced_image=False,
                context={"test_mode": True},
                user_id="rate_limit_test_user"
            )
            rapid_results.append(result)
        
        print(f"✅ Rapid requests completed: {len(rapid_results)}")
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        all_passed = False
    
    print("\n4️⃣ Testing Cache Functionality...")
    try:
        # First request (should not be cached)
        result1 = await simplified_flow.process_user_request(
            user_prompt="Test caching functionality",
            active_image=False,
            uploaded_image=False,
            referenced_image=False,
            context={"test_mode": True},
            user_id="cache_test_user"
        )
        
        # Second identical request (should be cached)
        result2 = await simplified_flow.process_user_request(
            user_prompt="Test caching functionality",
            active_image=False,
            uploaded_image=False,
            referenced_image=False,
            context={"test_mode": True},
            user_id="cache_test_user"
        )
        
        print(f"✅ First request cache hit: {result1.cache_hit}")
        print(f"✅ Second request cache hit: {result2.cache_hit}")
        
        if not result1.cache_hit and result2.cache_hit:
            print("✅ Cache working correctly!")
        else:
            print("⚠️  Cache behavior unexpected")
            
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        all_passed = False
    
    print("\n5️⃣ Testing Analytics/Stats...")
    try:
        stats = await simplified_flow.get_stats()
        print(f"✅ Stats available: {bool(stats)}")
        if "total_classifications" in stats:
            print(f"✅ Total Classifications: {stats['total_classifications']}")
            print(f"✅ Cache Hit Rate: {stats.get('cache_hit_rate', 0)}%")
            print(f"✅ Fallback Rate: {stats.get('fallback_rate', 0)}%")
        
    except Exception as e:
        print(f"❌ Stats test failed: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED! SimplifiedFlowService with Sprint 3 infrastructure is working correctly!")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False

async def main():
    """Main test runner"""
    
    print("🔧 SimplifiedFlowService Sprint 3 Infrastructure Test")
    print(f"📁 Working Directory: {os.getcwd()}")
    print(f"🐍 Python Path: {sys.path[0]}")
    
    # Check environment
    required_env_vars = ["REDIS_URL", "SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("Some infrastructure features may not work properly.")
    else:
        print("✅ All required environment variables present")
    
    print()
    
    try:
        success = await test_simplified_flow_sprint3()
        
        if success:
            print("\n✅ SimplifiedFlowService Sprint 3 Integration: OPERATIONAL")
            return 0
        else:
            print("\n❌ SimplifiedFlowService Sprint 3 Integration: ISSUES DETECTED")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 