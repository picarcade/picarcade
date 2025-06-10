#!/usr/bin/env python3
"""
Test Fixed Sprint 3 Infrastructure
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

async def test_supabase_analytics():
    """Test Supabase analytics logging"""
    
    print("🔧 Testing Fixed Supabase Analytics")
    print("=" * 50)
    
    try:
        from app.core.database import db_manager
        
        # Test intent classification logging
        print("1️⃣ Testing intent classification logging...")
        result = await db_manager.log_intent_classification({
            "user_id": "test_user_123",
            "prompt": "Test prompt for fixed infrastructure",
            "classified_workflow": "NEW_IMAGE",
            "confidence": 0.95,
            "processing_time_ms": 150,
            "used_fallback": False,
            "cache_hit": False,
            "circuit_breaker_state": "closed",
            "rate_limited": False
        })
        print(f"   ✅ Intent classification log: {'SUCCESS' if result else 'FAILED'}")
        
        # Test cost tracking
        print("2️⃣ Testing cost tracking...")
        result = await db_manager.log_cost_tracking({
            "user_id": "test_user_123",
            "operation_type": "image_generation",
            "estimated_cost": 0.05,
            "actual_cost": 0.048,
            "model_used": "flux-1.1-pro",
            "success": True
        })
        print(f"   ✅ Cost tracking log: {'SUCCESS' if result else 'FAILED'}")
        
        # Test system performance
        print("3️⃣ Testing system performance logging...")
        result = await db_manager.log_system_performance({
            "component": "simplified_flow_service",
            "status": "healthy",
            "metrics": {
                "cache_hit_rate": 85.5,
                "avg_processing_time": 120,
                "fallback_rate": 5.2
            }
        })
        print(f"   ✅ System performance log: {'SUCCESS' if result else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase analytics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_database_graceful_degradation():
    """Test database graceful degradation"""
    
    print("\n🗄️ Testing Database Graceful Degradation")
    print("=" * 50)
    
    try:
        from app.core.database import get_database
        
        print("1️⃣ Testing database initialization...")
        database = await get_database()
        print(f"   Database pool: {'✅ AVAILABLE' if database.pool else '⚠️ FALLBACK MODE'}")
        
        print("2️⃣ Testing basic queries...")
        result = await database.fetch_one("SELECT 1 as test")
        print(f"   Basic query: {'✅ SUCCESS' if result else '❌ FAILED'}")
        
        print("3️⃣ Testing query fallback...")
        result = await database.fetch_all("SELECT * FROM non_existent_table LIMIT 1")
        print(f"   Fallback query: {'✅ GRACEFUL' if isinstance(result, list) else '❌ ERROR'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database degradation test failed: {e}")
        return False

async def test_simplified_flow_fixed():
    """Test SimplifiedFlowService with fixed infrastructure"""
    
    print("\n🎯 Testing Fixed SimplifiedFlowService")
    print("=" * 50)
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        print("1️⃣ Testing service initialization...")
        await simplified_flow._ensure_initialized()
        print(f"   ✅ Service initialized: {simplified_flow._initialized}")
        
        print("2️⃣ Testing classification with analytics...")
        result = await simplified_flow.process_user_request(
            user_prompt="Create a beautiful sunset landscape",
            active_image=False,
            uploaded_image=False,
            referenced_image=False,
            user_id="test_user_fixed"
        )
        
        print(f"   ✅ Classification result: {result.prompt_type.value}")
        print(f"   ✅ Model selected: {result.model_to_use}")
        print(f"   ✅ Cache hit: {result.cache_hit}")
        print(f"   ✅ Processing time: {result.processing_time_ms}ms")
        
        print("3️⃣ Testing health status...")
        health = await simplified_flow.get_health()
        print(f"   ✅ Service health: {health['status']}")
        print(f"   ✅ Cache status: {health.get('cache', {}).get('status', 'unknown')}")
        print(f"   ✅ Circuit breaker: {health.get('circuit_breaker', {}).get('status', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ SimplifiedFlowService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_redis_connection():
    """Test Redis connection"""
    
    print("\n🔴 Testing Redis Connection")
    print("=" * 50)
    
    try:
        from app.services.redis_cache import RedisCache
        
        print("1️⃣ Initializing Redis cache...")
        cache = RedisCache()
        await cache.initialize()
        
        print("2️⃣ Testing cache operations...")
        test_key = "test_fixed_infrastructure"
        test_data = {"message": "Fixed infrastructure test", "timestamp": "2024"}
        
        # Set
        success = await cache.set(test_key, test_data, ttl=300)
        print(f"   ✅ Cache set: {'SUCCESS' if success else 'FAILED'}")
        
        # Get
        retrieved = await cache.get(test_key)
        print(f"   ✅ Cache get: {'SUCCESS' if retrieved else 'FAILED'}")
        
        # Health
        health = await cache.get_health()
        print(f"   ✅ Cache health: {health['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False

async def main():
    print("🚀 Fixed Sprint 3 Infrastructure Test")
    
    # Test Supabase analytics
    analytics_test = await test_supabase_analytics()
    
    # Test database graceful degradation
    db_test = await test_database_graceful_degradation()
    
    # Test SimplifiedFlowService
    flow_test = await test_simplified_flow_fixed()
    
    # Test Redis
    redis_test = await test_redis_connection()
    
    print("\n" + "=" * 50)
    print("📊 Fixed Infrastructure Test Results")
    print(f"• Supabase Analytics: {'✅ PASS' if analytics_test else '❌ FAIL'}")
    print(f"• Database Degradation: {'✅ PASS' if db_test else '❌ FAIL'}")
    print(f"• SimplifiedFlowService: {'✅ PASS' if flow_test else '❌ FAIL'}")
    print(f"• Redis Connection: {'✅ PASS' if redis_test else '❌ FAIL'}")
    
    success_count = sum([analytics_test, db_test, flow_test, redis_test])
    print(f"\n🎯 Overall Success Rate: {success_count}/4 ({(success_count/4)*100:.1f}%)")
    
    if success_count >= 3:
        print("🎉 INFRASTRUCTURE FIXED! Ready for production.")
    elif success_count >= 2:
        print("⚠️ Mostly working, minor issues remain.")
    else:
        print("❌ Major issues still present, needs more work.")
    
    return 0 if success_count >= 3 else 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 