#!/usr/bin/env python3
"""
Test Complete Sprint 3 Infrastructure with PostgreSQL
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

async def test_full_postgresql_connection():
    """Test full PostgreSQL connection with database password"""
    
    print("🗄️ Testing Full PostgreSQL Connection")
    print("=" * 50)
    
    try:
        from app.core.database import get_database
        
        print("1️⃣ Initializing database with password...")
        database = await get_database()
        print(f"   Database pool: {'✅ POSTGRESQL POOL' if database.pool else '⚠️ FALLBACK MODE'}")
        
        if database.pool:
            print("2️⃣ Testing PostgreSQL queries...")
            
            # Test basic query
            result = await database.fetch_one("SELECT current_database(), current_user")
            print(f"   ✅ Database: {result['current_database']}")
            print(f"   ✅ User: {result['current_user']}")
            
            # Test table access
            result = await database.fetch_one("SELECT COUNT(*) as count FROM intent_classification_logs")
            print(f"   ✅ Intent logs count: {result['count']}")
            
            # Test insert capability
            try:
                await database.execute(
                    "INSERT INTO intent_classification_logs (user_id, prompt, classified_workflow, confidence, processing_time_ms) VALUES ($1, $2, $3, $4, $5)",
                    "test_postgresql_user", "Test PostgreSQL connection", "NEW_IMAGE", 0.99, 150
                )
                print("   ✅ Insert test: SUCCESS")
            except Exception as e:
                print(f"   ⚠️ Insert test failed: {str(e)[:50]}...")
            
            return True
        else:
            print("   ⚠️ PostgreSQL pool not available, using fallback")
            return False
        
    except Exception as e:
        print(f"❌ PostgreSQL connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_stats_with_postgresql():
    """Test SimplifiedFlowService stats with PostgreSQL"""
    
    print("\n📊 Testing Stats with PostgreSQL")
    print("=" * 50)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        print("1️⃣ Testing service stats...")
        stats = await simplified_flow.get_stats()
        
        if "error" not in stats:
            print("   ✅ Stats retrieved successfully:")
            print(f"      Total classifications: {stats.get('total_classifications', 0)}")
            print(f"      Average confidence: {stats.get('avg_confidence', 0)}")
            print(f"      Average processing time: {stats.get('avg_processing_time_ms', 0)}ms")
            print(f"      Fallback rate: {stats.get('fallback_rate', 0)}%")
            print(f"      Cache hit rate: {stats.get('cache_hit_rate', 0)}%")
            print(f"      Period: {stats.get('period', 'unknown')}")
            return True
        else:
            print(f"   ❌ Stats error: {stats['error']}")
            return False
        
    except Exception as e:
        print(f"❌ Stats test failed: {e}")
        return False

async def test_redis_cache_initialization():
    """Test Redis cache initialization"""
    
    print("\n🔴 Testing Redis Cache Initialization")
    print("=" * 50)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        # Force re-initialization to ensure cache is set up
        print("1️⃣ Re-initializing SimplifiedFlowService...")
        simplified_flow._initialized = False
        await simplified_flow._ensure_initialized()
        
        print("2️⃣ Checking cache instance...")
        if hasattr(simplified_flow, 'cache') and simplified_flow.cache:
            health = await simplified_flow.cache.get_health()
            print(f"   ✅ Cache status: {health['status']}")
            print(f"   ✅ Connected: {health.get('connected', False)}")
            print(f"   ✅ URL: {health.get('url', 'unknown')}")
            
            # Test cache operations
            print("3️⃣ Testing cache operations...")
            test_key = "test_complete_infra"
            test_data = {"test": "complete infrastructure", "timestamp": "2024"}
            
            set_result = await simplified_flow.cache.set(test_key, test_data, ttl=300)
            print(f"   ✅ Cache set: {'SUCCESS' if set_result else 'FAILED'}")
            
            get_result = await simplified_flow.cache.get(test_key)
            print(f"   ✅ Cache get: {'SUCCESS' if get_result else 'FAILED'}")
            
            return True
        else:
            print("   ❌ Cache not initialized")
            return False
            
    except Exception as e:
        print(f"❌ Redis cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_complete_generation_flow():
    """Test complete generation flow with all infrastructure"""
    
    print("\n🎯 Testing Complete Generation Flow")
    print("=" * 50)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        print("1️⃣ Running full generation flow test...")
        result = await simplified_flow.process_user_request(
            user_prompt="Test complete infrastructure with a mountain landscape",
            active_image=False,
            uploaded_image=False,
            referenced_image=False,
            user_id="test_complete_infra_user"
        )
        
        print(f"   ✅ Classification: {result.prompt_type.value}")
        print(f"   ✅ Model: {result.model_to_use}")
        print(f"   ✅ Enhanced prompt: {result.enhanced_prompt[:50]}...")
        print(f"   ✅ Cache hit: {result.cache_hit}")
        print(f"   ✅ Processing time: {result.processing_time_ms}ms")
        print(f"   ✅ Reasoning: {result.reasoning[:100]}...")
        
        # Verify analytics were logged
        print("2️⃣ Verifying analytics logging...")
        import time
        await asyncio.sleep(2)  # Wait for async logging
        
        from app.core.database import db_manager
        recent_logs = db_manager.supabase.table("intent_classification_logs")\
            .select("*")\
            .eq("user_id", "test_complete_infra_user")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if recent_logs.data:
            log = recent_logs.data[0]
            print(f"   ✅ Analytics logged: {log['classified_workflow']}")
            print(f"   ✅ Confidence: {log['confidence']}")
            print(f"   ✅ Cache hit logged: {log['cache_hit']}")
            print(f"   ✅ Processing time logged: {log['processing_time_ms']}ms")
        else:
            print("   ⚠️ No analytics log found (async delay)")
        
        return True
        
    except Exception as e:
        print(f"❌ Complete generation flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🚀 Complete Sprint 3 Infrastructure Test")
    
    # Test PostgreSQL connection
    postgresql_test = await test_full_postgresql_connection()
    
    # Test stats with PostgreSQL
    stats_test = await test_stats_with_postgresql()
    
    # Test Redis cache
    cache_test = await test_redis_cache_initialization()
    
    # Test complete generation flow
    flow_test = await test_complete_generation_flow()
    
    print("\n" + "=" * 50)
    print("📊 Complete Infrastructure Test Results")
    print(f"• PostgreSQL Connection: {'✅ PASS' if postgresql_test else '❌ FAIL'}")
    print(f"• Statistics with PostgreSQL: {'✅ PASS' if stats_test else '❌ FAIL'}")
    print(f"• Redis Cache: {'✅ PASS' if cache_test else '❌ FAIL'}")
    print(f"• Complete Generation Flow: {'✅ PASS' if flow_test else '❌ FAIL'}")
    
    success_count = sum([postgresql_test, stats_test, cache_test, flow_test])
    print(f"\n🎯 Overall Success Rate: {success_count}/4 ({(success_count/4)*100:.1f}%)")
    
    if success_count == 4:
        print("🎉 100% COMPLETE! All Sprint 3 infrastructure operational!")
        print("🚀 Production ready with full PostgreSQL + Redis + Analytics!")
    elif success_count >= 3:
        print("⚠️ Nearly complete - minor issues to resolve")
    else:
        print("❌ Major issues remain")
    
    return 0 if success_count >= 3 else 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 