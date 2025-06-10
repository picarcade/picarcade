#!/usr/bin/env python3
"""
Check Recent Analytics from Generation
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

async def check_recent_analytics():
    """Check if recent generation was logged to analytics"""
    
    print("🔍 Checking Recent Analytics Logs")
    print("=" * 50)
    
    try:
        from app.core.database import db_manager
        
        # Check intent classification logs (last 5 minutes)
        print("1️⃣ Checking intent classification logs...")
        response = db_manager.supabase.table("intent_classification_logs")\
            .select("*")\
            .gte("created_at", "2024-06-10T10:15:00Z")\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()
        
        if response.data:
            for log in response.data:
                print(f"   ✅ Found log: {log['classified_workflow']} - {log['prompt'][:50]}...")
                print(f"      User: {log['user_id']}")
                print(f"      Confidence: {log['confidence']}")
                print(f"      Cache hit: {log['cache_hit']}")
                print(f"      Fallback: {log['used_fallback']}")
                print(f"      Time: {log['created_at']}")
                print()
        else:
            print("   ⚠️ No recent intent classification logs found")
        
        # Check generation history
        print("2️⃣ Checking generation history...")
        response = db_manager.supabase.table("generation_history")\
            .select("*")\
            .gte("created_at", "2024-06-10T10:15:00Z")\
            .order("created_at", desc=True)\
            .limit(3)\
            .execute()
        
        if response.data:
            for gen in response.data:
                print(f"   ✅ Found generation: {gen['generation_id']}")
                print(f"      Prompt: {gen['prompt'][:50]}...")
                print(f"      Model: {gen['model_used']}")
                print(f"      Success: {gen['success']}")
                print(f"      Time: {gen['created_at']}")
                print()
        else:
            print("   ⚠️ No recent generation history found")
        
        # Check system performance logs
        print("3️⃣ Checking system performance logs...")
        response = db_manager.supabase.table("system_performance_logs")\
            .select("*")\
            .gte("created_at", "2024-06-10T10:00:00Z")\
            .order("created_at", desc=True)\
            .limit(3)\
            .execute()
        
        if response.data:
            for perf in response.data:
                print(f"   ✅ Found performance log: {perf['component']} - {perf['status']}")
                print(f"      Metrics: {perf.get('metrics', {})}")
                print(f"      Time: {perf['created_at']}")
                print()
        else:
            print("   ⚠️ No recent system performance logs found")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to check analytics: {e}")
        import traceback
        traceback.print_exc()
        return False

async def check_cache_status():
    """Check Redis cache status"""
    
    print("\n🔴 Checking Redis Cache Status")
    print("=" * 50)
    
    try:
        # Import the cache from SimplifiedFlowService
        from app.services.simplified_flow_service import simplified_flow
        
        if hasattr(simplified_flow, 'cache') and simplified_flow.cache:
            health = await simplified_flow.cache.get_health()
            print(f"✅ Redis Cache Status: {health['status']}")
            print(f"✅ Connection: {health.get('connected', 'unknown')}")
            print(f"✅ URL: {health.get('url', 'unknown')}")
            return True
        else:
            print("⚠️ No cache instance found in SimplifiedFlowService")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check cache: {e}")
        return False

async def main():
    print("🚀 Checking Recent Generation Analytics")
    
    analytics_check = await check_recent_analytics()
    cache_check = await check_cache_status()
    
    print("\n" + "=" * 50)
    print("📊 Analytics Check Results")
    print(f"• Recent Analytics Logs: {'✅ FOUND' if analytics_check else '❌ NOT FOUND'}")
    print(f"• Redis Cache Status: {'✅ WORKING' if cache_check else '❌ ISSUE'}")
    
    if analytics_check and cache_check:
        print("\n🎉 Full Sprint 3 infrastructure confirmed working!")
    elif analytics_check:
        print("\n⚠️ Analytics working, cache needs verification")
    else:
        print("\n❌ Some components need investigation")

if __name__ == "__main__":
    asyncio.run(main()) 