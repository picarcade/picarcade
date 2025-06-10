#!/usr/bin/env python3
"""
Test Production Redis Connection
Test if the production app code can connect to Redis
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

async def test_production_redis():
    """Test if production app components can connect to Redis"""
    
    print("🔧 Testing Production App Redis Connection")
    print("=" * 50)
    
    try:
        # Test the cache system used by production
        from app.core.cache import get_cache
        
        print("1️⃣ Initializing production cache system...")
        cache = await get_cache()
        
        print("2️⃣ Testing cache operations...")
        await cache.set("production_test", "test_value", ttl=60)
        value = await cache.get("production_test")
        
        print(f"✅ Cache test: {value}")
        
        # Test cache health
        health = await cache.get_health()
        print(f"✅ Cache health: {health}")
        
        return True
        
    except Exception as e:
        print(f"❌ Production Redis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simplified_flow_init():
    """Test if SimplifiedFlowService can initialize properly"""
    
    print("\n3️⃣ Testing SimplifiedFlowService initialization...")
    
    try:
        from app.services.simplified_flow_service import simplified_flow
        
        # Test health check
        health = await simplified_flow.get_health()
        print(f"✅ SimplifiedFlow health: {health}")
        
        return health.get("cache", {}).get("status") == "connected"
        
    except Exception as e:
        print(f"❌ SimplifiedFlowService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🚀 Production Redis Connection Test")
    
    redis_test = await test_production_redis()
    flow_test = await test_simplified_flow_init()
    
    print("\n" + "=" * 50)
    
    if redis_test and flow_test:
        print("🎉 Production Redis integration is working!")
        print("✅ Your FastAPI app should work with Sprint 3 infrastructure")
        print("\n💡 If the server isn't working, restart it:")
        print("   uvicorn app.main:app --reload")
    else:
        print("❌ Production Redis integration has issues")
        print("📋 Check:")
        print("  1. Environment variables loaded correctly")
        print("  2. Redis URL format in .env")
        print("  3. Network connectivity to Upstash")
    
    return 0 if (redis_test and flow_test) else 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 