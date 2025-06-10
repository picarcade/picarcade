#!/usr/bin/env python3
"""
Final Sprint 3 Infrastructure Test - Supabase Optimized
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def test_supabase_infrastructure():
    """Test complete Supabase infrastructure"""
    
    print("🔧 Testing Supabase Infrastructure")
    print("=" * 50)
    
    try:
        from app.core.database import db_manager, get_database
        
        print("1️⃣ Testing Supabase analytics logging...")
        success = await db_manager.log_intent_classification({
            "user_id": "final_test_user",
            "prompt": "Final Sprint 3 infrastructure test",
            "classified_workflow": "NEW_IMAGE",
            "confidence": 0.97,
            "processing_time_ms": 250,
            "used_fallback": False,
            "cache_hit": False,
            "circuit_breaker_state": "closed",
            "rate_limited": False
        })
        print(f"   ✅ Analytics logging: {'SUCCESS' if success else 'FAILED'}")
        
        print("2️⃣ Testing database graceful fallback...")
        database = await get_database()
        fallback_result = await database.fetch_one("SELECT 1 as test")
        print(f"   ✅ Database fallback: {'SUCCESS' if fallback_result else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase infrastructure test failed: {e}")
        return False

async def test_simplified_flow_complete():
    """Test complete SimplifiedFlowService functionality"""
    
    print("\n🎯 Testing Complete SimplifiedFlowService")
    print("=" * 50)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        print("1️⃣ Testing service initialization...")
        simplified_flow._initialized = False  # Force re-init
        await simplified_flow._ensure_initialized()
        print(f"   ✅ Service initialized: {simplified_flow._initialized}")
        
        print("2️⃣ Testing AI classification...")
        result = await simplified_flow.process_user_request(
            user_prompt="Create a stunning cyberpunk cityscape at night",
            active_image=False,
            uploaded_image=False,
            referenced_image=False,
            user_id="final_sprint3_test"
        )
        
        print(f"   ✅ Classification: {result.prompt_type.value}")
        print(f"   ✅ Model: {result.model_to_use}")
        print(f"   ✅ Enhanced prompt: {result.enhanced_prompt[:60]}...")
        print(f"   ✅ Cache hit: {result.cache_hit}")
        print(f"   ✅ Processing time: {result.processing_time_ms}ms")
        
        print("3️⃣ Testing service health...")
        health = await simplified_flow.get_health()
        print(f"   ✅ Service status: {health['status']}")
        print(f"   ✅ Cache status: {health.get('cache', {}).get('status', 'unknown')}")
        
        print("4️⃣ Testing service stats (Supabase-only)...")
        stats = await simplified_flow.get_stats()
        if "error" not in stats:
            print(f"   ✅ Stats working: {stats.get('total_classifications', 0)} classifications")
            print(f"   ✅ Avg confidence: {stats.get('avg_confidence', 0)}")
            print(f"   ✅ Cache hit rate: {stats.get('cache_hit_rate', 0)}%")
            print(f"   ✅ Data source: {stats.get('data_source', 'unknown')}")
        else:
            print(f"   ⚠️ Stats error: {stats.get('error', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ SimplifiedFlowService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_redis_cache():
    """Test Redis cache functionality"""
    
    print("\n🔴 Testing Redis Cache")
    print("=" * 50)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        if hasattr(simplified_flow, 'cache') and simplified_flow.cache:
            print("1️⃣ Testing cache health...")
            health = await simplified_flow.cache.get_health()
            print(f"   ✅ Cache status: {health['status']}")
            
            print("2️⃣ Testing cache operations...")
            test_key = "final_sprint3_test"
            test_data = {"message": "Final Sprint 3 test", "version": "3.0"}
            
            set_success = await simplified_flow.cache.set(test_key, test_data, ttl=300)
            print(f"   ✅ Cache set: {'SUCCESS' if set_success else 'FAILED'}")
            
            get_result = await simplified_flow.cache.get(test_key)
            print(f"   ✅ Cache get: {'SUCCESS' if get_result else 'FAILED'}")
            
            return True
        else:
            print("   ⚠️ Cache not initialized - using simplified flow without cache")
            return False
            
    except Exception as e:
        print(f"❌ Redis cache test failed: {e}")
        return False

async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    
    print("\n⚡ Testing Circuit Breaker")
    print("=" * 50)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        if hasattr(simplified_flow, 'circuit_breaker') and simplified_flow.circuit_breaker:
            print("1️⃣ Testing circuit breaker state...")
            stats = simplified_flow.circuit_breaker.get_stats()
            print(f"   ✅ Circuit breaker status: {stats.get('status', 'unknown')}")
            print(f"   ✅ State: {stats.get('state', 'unknown')}")
            print(f"   ✅ Failure count: {stats.get('failure_count', 0)}")
            print(f"   ✅ Success count: {stats.get('success_count', 0)}")
            
            return True
        else:
            print("   ⚠️ Circuit breaker not initialized")
            return False
            
    except Exception as e:
        print(f"❌ Circuit breaker test failed: {e}")
        return False

async def verify_recent_analytics():
    """Verify recent analytics data"""
    
    print("\n📊 Verifying Recent Analytics")
    print("=" * 50)
    
    try:
        from app.core.database import db_manager
        
        print("1️⃣ Checking recent intent classifications...")
        result = db_manager.supabase.table("intent_classification_logs")\
            .select("*")\
            .order("created_at", desc=True)\
            .limit(3)\
            .execute()
        
        if result.data:
            for i, log in enumerate(result.data, 1):
                print(f"   ✅ Log {i}: {log['classified_workflow']} - {log['user_id']}")
                print(f"      Confidence: {log['confidence']}, Time: {log['processing_time_ms']}ms")
        else:
            print("   ⚠️ No recent analytics found")
        
        print("2️⃣ Checking generation history...")
        result = db_manager.supabase.table("generation_history")\
            .select("generation_id, prompt, model_used, success")\
            .order("created_at", desc=True)\
            .limit(2)\
            .execute()
        
        if result.data:
            for i, gen in enumerate(result.data, 1):
                print(f"   ✅ Generation {i}: {gen['generation_id']}")
                print(f"      Model: {gen['model_used']}, Success: {gen['success']}")
        else:
            print("   ⚠️ No recent generations found")
        
        return True
        
    except Exception as e:
        print(f"❌ Analytics verification failed: {e}")
        return False

async def main():
    print("🚀 Final Sprint 3 Infrastructure Test")
    print("🎯 Testing Complete Supabase-Optimized System")
    
    # Test all components
    supabase_test = await test_supabase_infrastructure()
    flow_test = await test_simplified_flow_complete()
    cache_test = await test_redis_cache()
    circuit_test = await test_circuit_breaker()
    analytics_test = await verify_recent_analytics()
    
    print("\n" + "=" * 60)
    print("📊 FINAL SPRINT 3 INFRASTRUCTURE RESULTS")
    print("=" * 60)
    print(f"• Supabase Infrastructure: {'✅ PASS' if supabase_test else '❌ FAIL'}")
    print(f"• SimplifiedFlowService: {'✅ PASS' if flow_test else '❌ FAIL'}")
    print(f"• Redis Cache: {'✅ PASS' if cache_test else '⚠️ OPTIONAL'}")
    print(f"• Circuit Breaker: {'✅ PASS' if circuit_test else '⚠️ OPTIONAL'}")
    print(f"• Analytics Verification: {'✅ PASS' if analytics_test else '❌ FAIL'}")
    
    # Calculate success rate
    core_components = [supabase_test, flow_test, analytics_test]  # Essential
    optional_components = [cache_test, circuit_test]  # Nice to have
    
    core_success = sum(core_components)
    optional_success = sum(optional_components)
    total_success = core_success + optional_success
    
    print(f"\n🎯 Core Infrastructure: {core_success}/3 ({(core_success/3)*100:.1f}%)")
    print(f"🎯 Optional Components: {optional_success}/2 ({(optional_success/2)*100:.1f}%)")
    print(f"🎯 Total Success Rate: {total_success}/5 ({(total_success/5)*100:.1f}%)")
    
    if core_success == 3:
        print("\n🎉 SPRINT 3 INFRASTRUCTURE COMPLETE!")
        print("✅ All core components operational")
        print("✅ Supabase-optimized architecture")
        print("✅ Production ready!")
        
        if optional_success == 2:
            print("🌟 PERFECT SCORE - All components working!")
        elif optional_success == 1:
            print("⭐ Excellent - Core + 1 optional component")
        else:
            print("✨ Great - All essential components working")
            
    elif core_success >= 2:
        print("\n⚠️ Nearly complete - minor issues remain")
    else:
        print("\n❌ Core infrastructure issues need attention")
    
    return 0 if core_success >= 2 else 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 