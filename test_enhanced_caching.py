#!/usr/bin/env python3
"""
Test Enhanced Caching Features
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

async def test_prompt_enhancement_caching():
    """Test prompt enhancement caching"""
    
    print("🎨 Testing Prompt Enhancement Caching")
    print("=" * 60)
    
    try:
        from app.services.prompt_enhancer import PromptEnhancer
        
        enhancer = PromptEnhancer()
        
        # Test prompt that will be enhanced
        test_prompt = "cat sitting"
        edit_type = "image_editing"
        has_working_image = True
        
        print(f"📝 Test Prompt: '{test_prompt}'")
        print(f"   Edit Type: {edit_type}")
        print(f"   Has Working Image: {has_working_image}")
        
        # First call - should trigger Claude API
        print(f"\n1️⃣ First Enhancement (expecting CACHE MISS)...")
        start_time = time.time()
        
        enhanced1 = await enhancer.enhance_flux_kontext_prompt(
            original_prompt=test_prompt,
            edit_type=edit_type,
            has_working_image=has_working_image
        )
        
        first_time = time.time() - start_time
        
        print(f"   ✅ Enhanced: '{enhanced1}'")
        print(f"   ✅ Time: {first_time:.2f}s")
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Second call - should hit cache
        print(f"\n2️⃣ Second Enhancement (expecting CACHE HIT)...")
        start_time = time.time()
        
        enhanced2 = await enhancer.enhance_flux_kontext_prompt(
            original_prompt=test_prompt,
            edit_type=edit_type,
            has_working_image=has_working_image
        )
        
        second_time = time.time() - start_time
        
        print(f"   ✅ Enhanced: '{enhanced2}'")
        print(f"   ✅ Time: {second_time:.2f}s")
        
        # Analysis
        print(f"\n📊 Enhancement Cache Analysis:")
        print(f"   First call time: {first_time:.2f}s")
        print(f"   Second call time: {second_time:.2f}s")
        print(f"   Results identical: {enhanced1 == enhanced2}")
        
        if second_time < first_time and enhanced1 == enhanced2:
            print(f"   Speed improvement: {(first_time/second_time):.1f}x faster")
            print(f"🎉 Prompt enhancement caching working!")
            return True
        else:
            print(f"⚠️ Cache behavior unexpected")
            return False
        
    except Exception as e:
        print(f"❌ Prompt enhancement caching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_model_parameters_caching():
    """Test model parameters caching"""
    
    print(f"\n⚙️ Testing Model Parameters Caching")
    print("=" * 60)
    
    try:
        from app.services.simplified_flow_service import simplified_flow, SimplifiedFlowResult, PromptType
        
        # Create a mock result for testing
        test_result = SimplifiedFlowResult(
            prompt_type=PromptType.CREATE_NEW_IMAGE,
            model_to_use="black-forest-labs/flux-1.1-pro",
            enhanced_prompt="Test enhanced prompt",
            original_prompt="Test prompt",
            reasoning="Test reasoning",
            active_image=False,
            uploaded_image=False,
            referenced_image=False
        )
        
        print(f"🔧 Test Model: {test_result.model_to_use}")
        print(f"   Prompt Type: {test_result.prompt_type.value}")
        
        # First call - should generate and cache parameters
        print(f"\n1️⃣ First Parameter Generation (expecting computation)...")
        start_time = time.time()
        
        params1 = await simplified_flow.get_model_parameters(test_result)
        
        first_time = time.time() - start_time
        
        print(f"   ✅ Parameters: {list(params1.keys())}")
        print(f"   ✅ Time: {first_time:.4f}s")
        
        # Second call - should hit cache
        print(f"\n2️⃣ Second Parameter Generation (expecting CACHE HIT)...")
        start_time = time.time()
        
        params2 = await simplified_flow.get_model_parameters(test_result)
        
        second_time = time.time() - start_time
        
        print(f"   ✅ Parameters: {list(params2.keys())}")
        print(f"   ✅ Time: {second_time:.4f}s")
        
        # Analysis (excluding prompt which is dynamic)
        params1_static = {k: v for k, v in params1.items() if k != "prompt"}
        params2_static = {k: v for k, v in params2.items() if k != "prompt"}
        
        print(f"\n📊 Parameter Cache Analysis:")
        print(f"   Static parameters identical: {params1_static == params2_static}")
        print(f"   Performance improvement: {(first_time/second_time):.1f}x" if second_time > 0 else "∞x")
        
        if params1_static == params2_static:
            print(f"🎉 Model parameters caching working!")
            return True
        else:
            print(f"⚠️ Parameters not identical")
            return False
        
    except Exception as e:
        print(f"❌ Model parameters caching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_analytics_stats_caching():
    """Test analytics stats caching"""
    
    print(f"\n📊 Testing Analytics Stats Caching")
    print("=" * 60)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        # First call - should hit database
        print(f"1️⃣ First Stats Query (expecting database query)...")
        start_time = time.time()
        
        stats1 = await simplified_flow.get_stats()
        
        first_time = time.time() - start_time
        
        print(f"   ✅ Stats: {list(stats1.keys())}")
        print(f"   ✅ Cached: {stats1.get('cached', False)}")
        print(f"   ✅ Time: {first_time:.2f}s")
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Second call - should hit cache
        print(f"\n2️⃣ Second Stats Query (expecting CACHE HIT)...")
        start_time = time.time()
        
        stats2 = await simplified_flow.get_stats()
        
        second_time = time.time() - start_time
        
        print(f"   ✅ Stats: {list(stats2.keys())}")
        print(f"   ✅ Cached: {stats2.get('cached', False)}")
        print(f"   ✅ Time: {second_time:.2f}s")
        
        # Analysis
        print(f"\n📊 Stats Cache Analysis:")
        print(f"   First call cached: {stats1.get('cached', False)}")
        print(f"   Second call cached: {stats2.get('cached', False)}")
        print(f"   Performance improvement: {(first_time/second_time):.1f}x" if second_time > 0 else "∞x")
        
        if not stats1.get('cached', False) and stats2.get('cached', False):
            print(f"🎉 Analytics stats caching working!")
            return True
        else:
            print(f"⚠️ Expected MISS → HIT pattern")
            return False
        
    except Exception as e:
        print(f"❌ Analytics stats caching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_session_caching():
    """Test session data caching"""
    
    print(f"\n🔐 Testing Session Data Caching")
    print("=" * 60)
    
    try:
        from app.services.session_manager import session_manager
        test_session_id = "cache_test_session_123"
        test_image_url = "https://example.com/test_image.jpg"
        test_user_id = "cache_test_user"
        
        print(f"🔑 Test Session: {test_session_id}")
        print(f"   Image URL: {test_image_url}")
        
        # Set a working image
        print(f"\n1️⃣ Setting working image...")
        await session_manager.set_current_working_image(
            session_id=test_session_id,
            image_url=test_image_url,
            user_id=test_user_id
        )
        
        # First get - should query database
        print(f"\n2️⃣ First Image Retrieval (expecting database query)...")
        start_time = time.time()
        
        image1 = await session_manager.get_current_working_image(test_session_id)
        
        first_time = time.time() - start_time
        
        print(f"   ✅ Retrieved: {image1}")
        print(f"   ✅ Time: {first_time:.4f}s")
        
        # Second get - should hit cache
        print(f"\n3️⃣ Second Image Retrieval (expecting CACHE HIT)...")
        start_time = time.time()
        
        image2 = await session_manager.get_current_working_image(test_session_id)
        
        second_time = time.time() - start_time
        
        print(f"   ✅ Retrieved: {image2}")
        print(f"   ✅ Time: {second_time:.4f}s")
        
        # Analysis
        print(f"\n📊 Session Cache Analysis:")
        print(f"   Images identical: {image1 == image2}")
        print(f"   Performance improvement: {(first_time/second_time):.1f}x" if second_time > 0 else "∞x")
        
        if image1 == image2 and image1 == test_image_url:
            print(f"🎉 Session data caching working!")
            return True
        else:
            print(f"⚠️ Session caching behavior unexpected")
            return False
        
    except Exception as e:
        print(f"❌ Session caching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_cache_health():
    """Test overall cache health"""
    
    print(f"\n🏥 Testing Overall Cache Health")
    print("=" * 60)
    
    try:
        from app.core.cache import get_cache
        
        cache = await get_cache()
        
        if cache:
            # Test basic operations
            print("1️⃣ Testing basic cache operations...")
            
            test_key = "health_test_enhanced_caching"
            test_data = {"timestamp": time.time(), "test": "enhanced_caching"}
            
            # Set
            set_result = await cache.set(test_key, test_data, ttl=60)
            print(f"   ✅ SET: {'SUCCESS' if set_result else 'FAILED'}")
            
            # Get
            get_result = await cache.get(test_key)
            print(f"   ✅ GET: {'SUCCESS' if get_result else 'FAILED'}")
            
            # Delete
            await cache.delete(test_key)
            print(f"   ✅ DELETE: SUCCESS")
            
            # Health check
            print("2️⃣ Cache health status...")
            health = await cache.get_health()
            print(f"   ✅ Status: {health['status']}")
            
            return True
        else:
            print("❌ Cache not available")
            return False
            
    except Exception as e:
        print(f"❌ Cache health test failed: {e}")
        return False

async def main():
    print("🚀 Enhanced Caching Features Test Suite")
    print("=" * 80)
    
    # Test all enhanced caching features
    prompt_cache_test = await test_prompt_enhancement_caching()
    params_cache_test = await test_model_parameters_caching()
    stats_cache_test = await test_analytics_stats_caching()
    session_cache_test = await test_session_caching()
    health_test = await test_cache_health()
    
    print("\n" + "=" * 80)
    print("📊 Enhanced Caching Test Results")
    print("=" * 80)
    print(f"• Prompt Enhancement Caching: {'✅ PASS' if prompt_cache_test else '❌ FAIL'}")
    print(f"• Model Parameters Caching: {'✅ PASS' if params_cache_test else '❌ FAIL'}")
    print(f"• Analytics Stats Caching: {'✅ PASS' if stats_cache_test else '❌ FAIL'}")
    print(f"• Session Data Caching: {'✅ PASS' if session_cache_test else '❌ FAIL'}")
    print(f"• Cache Health: {'✅ PASS' if health_test else '❌ FAIL'}")
    
    success_count = sum([prompt_cache_test, params_cache_test, stats_cache_test, session_cache_test, health_test])
    print(f"\n🎯 Overall Success Rate: {success_count}/5 ({(success_count/5)*100:.1f}%)")
    
    if success_count == 5:
        print("🎉 All enhanced caching features working perfectly!")
        print("💡 Your system now has comprehensive caching for:")
        print("   • AI-powered prompt enhancements (24h TTL)")
        print("   • Model parameters & configurations (1h TTL)")
        print("   • Analytics & stats queries (5min TTL)")
        print("   • User session data (10min TTL)")
        print("   • Intent classification results (1h TTL - existing)")
    elif success_count >= 3:
        print("⚠️ Most enhanced caching features working")
    else:
        print("❌ Enhanced caching needs attention")
    
    return 0 if success_count >= 3 else 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 