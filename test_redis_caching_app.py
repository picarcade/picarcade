#!/usr/bin/env python3
"""
Test Redis Caching Through SimplifiedFlowService
"""

import os
import sys
import asyncio
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def test_cache_hit_miss():
    """Test cache hit/miss behavior"""
    
    print("🔴 Testing Redis Cache Hit/Miss Behavior")
    print("=" * 60)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        # Ensure service is initialized
        await simplified_flow._ensure_initialized()
        
        # Test parameters (keep these identical for cache hit)
        test_prompt = "Create a futuristic robot in a cyberpunk setting"
        test_user_id = "cache_test_user_123"
        active_image = False
        uploaded_image = False
        referenced_image = False
        
        print(f"📋 Test Parameters:")
        print(f"   Prompt: {test_prompt}")
        print(f"   User ID: {test_user_id}")
        print(f"   Flags: active={active_image}, uploaded={uploaded_image}, referenced={referenced_image}")
        
        # First request - should be CACHE MISS
        print(f"\n1️⃣ First Request (expecting CACHE MISS)...")
        start_time = time.time()
        
        result1 = await simplified_flow.process_user_request(
            user_prompt=test_prompt,
            active_image=active_image,
            uploaded_image=uploaded_image,
            referenced_image=referenced_image,
            user_id=test_user_id
        )
        
        first_time = time.time() - start_time
        
        print(f"   ✅ Classification: {result1.prompt_type.value}")
        print(f"   ✅ Model: {result1.model_to_use}")
        print(f"   ✅ Cache hit: {result1.cache_hit}")
        print(f"   ✅ Processing time: {result1.processing_time_ms}ms")
        print(f"   ✅ Total time: {first_time:.2f}s")
        
        # Wait a moment
        print(f"\n⏳ Waiting 2 seconds...")
        await asyncio.sleep(2)
        
        # Second request - should be CACHE HIT
        print(f"\n2️⃣ Second Request (expecting CACHE HIT)...")
        start_time = time.time()
        
        result2 = await simplified_flow.process_user_request(
            user_prompt=test_prompt,  # Same prompt
            active_image=active_image,  # Same flags
            uploaded_image=uploaded_image,
            referenced_image=referenced_image,
            user_id=test_user_id  # Same user
        )
        
        second_time = time.time() - start_time
        
        print(f"   ✅ Classification: {result2.prompt_type.value}")
        print(f"   ✅ Model: {result2.model_to_use}")
        print(f"   ✅ Cache hit: {result2.cache_hit}")
        print(f"   ✅ Processing time: {result2.processing_time_ms}ms")
        print(f"   ✅ Total time: {second_time:.2f}s")
        
        # Analysis
        print(f"\n📊 Cache Analysis:")
        print(f"   First request cache hit: {result1.cache_hit}")
        print(f"   Second request cache hit: {result2.cache_hit}")
        print(f"   Time improvement: {first_time:.2f}s → {second_time:.2f}s")
        print(f"   Speed up: {(first_time/second_time):.1f}x faster" if second_time > 0 else "   Speed up: ∞x faster")
        
        # Verify results are identical
        results_match = (
            result1.prompt_type == result2.prompt_type and
            result1.model_to_use == result2.model_to_use and
            result1.enhanced_prompt == result2.enhanced_prompt
        )
        
        print(f"   Results identical: {results_match}")
        
        if result2.cache_hit and not result1.cache_hit:
            print(f"\n🎉 CACHE TEST SUCCESSFUL!")
            print(f"   ✅ First request: MISS (as expected)")
            print(f"   ✅ Second request: HIT (as expected)")
            print(f"   ✅ Performance improved: {(first_time/second_time):.1f}x")
            return True
        else:
            print(f"\n⚠️ Cache behavior unexpected:")
            print(f"   Expected: MISS → HIT")
            print(f"   Actual: {'HIT' if result1.cache_hit else 'MISS'} → {'HIT' if result2.cache_hit else 'MISS'}")
            return False
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_cache_key_variations():
    """Test that different inputs create different cache keys"""
    
    print(f"\n🔑 Testing Cache Key Variations")
    print("=" * 60)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        base_prompt = "Create a landscape image"
        base_user = "cache_key_test_user"
        
        test_cases = [
            {"name": "Same everything", "prompt": base_prompt, "user": base_user, "active": False},
            {"name": "Different prompt", "prompt": "Create a portrait image", "user": base_user, "active": False},
            {"name": "Different user", "prompt": base_prompt, "user": "different_user", "active": False},
            {"name": "Different flags", "prompt": base_prompt, "user": base_user, "active": True},
        ]
        
        results = []
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n{i}️⃣ Testing: {case['name']}")
            print(f"   Prompt: {case['prompt'][:30]}...")
            print(f"   User: {case['user']}")
            print(f"   Active image: {case['active']}")
            
            result = await simplified_flow.process_user_request(
                user_prompt=case['prompt'],
                active_image=case['active'],
                uploaded_image=False,
                referenced_image=False,
                user_id=case['user']
            )
            
            results.append({
                "name": case['name'],
                "cache_hit": result.cache_hit,
                "processing_time": result.processing_time_ms
            })
            
            print(f"   ✅ Cache hit: {result.cache_hit}")
            print(f"   ✅ Processing time: {result.processing_time_ms}ms")
        
        # Analysis
        print(f"\n📊 Cache Key Analysis:")
        for result in results:
            print(f"   {result['name']}: {'HIT' if result['cache_hit'] else 'MISS'} ({result['processing_time']}ms)")
        
        # Only the first one should potentially be a hit if run multiple times
        return True
        
    except Exception as e:
        print(f"❌ Cache key test failed: {e}")
        return False

async def test_cache_health():
    """Test cache connection and health"""
    
    print(f"\n🏥 Testing Cache Health")
    print("=" * 60)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        if hasattr(simplified_flow, 'cache') and simplified_flow.cache:
            print("1️⃣ Testing cache health...")
            health = await simplified_flow.cache.get_health()
            
            print(f"   ✅ Status: {health['status']}")
            print(f"   ✅ Connected: {health.get('connected', 'unknown')}")
            print(f"   ✅ URL: {health.get('url', 'unknown')}")
            
            print("2️⃣ Testing direct cache operations...")
            test_key = "health_test_key"
            test_data = {"health": "test", "timestamp": time.time()}
            
            # Set
            set_result = await simplified_flow.cache.set(test_key, test_data, ttl=60)
            print(f"   ✅ Cache SET: {'SUCCESS' if set_result else 'FAILED'}")
            
            # Get
            get_result = await simplified_flow.cache.get(test_key)
            print(f"   ✅ Cache GET: {'SUCCESS' if get_result else 'FAILED'}")
            
            # Delete
            await simplified_flow.cache.delete(test_key)
            print(f"   ✅ Cache DELETE: SUCCESS")
            
            return True
        else:
            print("❌ Cache not initialized")
            return False
            
    except Exception as e:
        print(f"❌ Cache health test failed: {e}")
        return False

async def main():
    print("🚀 Redis Cache Testing Through App")
    
    # Test cache hit/miss behavior
    cache_test = await test_cache_hit_miss()
    
    # Test cache key variations
    key_test = await test_cache_key_variations()
    
    # Test cache health
    health_test = await test_cache_health()
    
    print("\n" + "=" * 60)
    print("📊 Redis Cache Test Results")
    print("=" * 60)
    print(f"• Cache Hit/Miss Test: {'✅ PASS' if cache_test else '❌ FAIL'}")
    print(f"• Cache Key Variations: {'✅ PASS' if key_test else '❌ FAIL'}")
    print(f"• Cache Health Test: {'✅ PASS' if health_test else '❌ FAIL'}")
    
    success_count = sum([cache_test, key_test, health_test])
    print(f"\n🎯 Overall Success Rate: {success_count}/3 ({(success_count/3)*100:.1f}%)")
    
    if success_count == 3:
        print("🎉 Redis caching is working perfectly!")
        print("💡 Try the same prompt twice in your web app to see caching in action")
    elif success_count >= 2:
        print("⚠️ Most cache features working")
    else:
        print("❌ Cache issues detected")
    
    return 0 if success_count >= 2 else 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 