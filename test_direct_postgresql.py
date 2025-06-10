#!/usr/bin/env python3
"""
Test Direct PostgreSQL Connection
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_direct_connection():
    """Test direct PostgreSQL connection with different formats"""
    
    print("🔧 Testing Direct PostgreSQL Connection")
    print("=" * 50)
    
    try:
        import asyncpg
        
        db_password = "Cr00m0)_"
        project_ref = "icgwpkroorulmsfdiuoh"
        
        # Try different connection formats
        connection_strings = [
            # Standard Supabase format
            f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres",
            
            # Alternative port
            f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:6543/postgres",
            
            # Pooler format (Session mode)
            f"postgresql://postgres.{project_ref}:{db_password}@aws-0-{project_ref}.pooler.supabase.com:5432/postgres",
            
            # Pooler format (Transaction mode)  
            f"postgresql://postgres.{project_ref}:{db_password}@aws-0-{project_ref}.pooler.supabase.com:6543/postgres",
            
            # Alternative AWS region
            f"postgresql://postgres:{db_password}@aws-0-{project_ref}.pooler.supabase.com:5432/postgres",
        ]
        
        for i, conn_str in enumerate(connection_strings, 1):
            try:
                print(f"\n{i}️⃣ Testing connection format {i}...")
                safe_str = conn_str.replace(db_password, "[HIDDEN]")
                print(f"   Format: {safe_str}")
                
                # Test with short timeout
                conn = await asyncio.wait_for(
                    asyncpg.connect(conn_str), 
                    timeout=10.0
                )
                
                # Test basic query
                result = await conn.fetchval("SELECT current_database()")
                await conn.close()
                
                print(f"   ✅ SUCCESS! Database: {result}")
                return conn_str
                
            except asyncio.TimeoutError:
                print(f"   ❌ TIMEOUT - Connection took too long")
            except Exception as e:
                error_msg = str(e)
                if "getaddrinfo failed" in error_msg:
                    print(f"   ❌ DNS RESOLUTION FAILED")
                elif "authentication failed" in error_msg:
                    print(f"   ❌ AUTHENTICATION FAILED - Wrong password")
                elif "connection refused" in error_msg:
                    print(f"   ❌ CONNECTION REFUSED - Wrong port/host")
                else:
                    print(f"   ❌ ERROR: {error_msg[:60]}...")
        
        print("\n❌ All connection attempts failed")
        return None
        
    except ImportError:
        print("❌ asyncpg not installed")
        return None
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None

async def test_supabase_only_approach():
    """Test using Supabase client only for all operations"""
    
    print("\n🔧 Testing Supabase-Only Approach")
    print("=" * 50)
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        supabase = create_client(supabase_url, supabase_service_key)
        
        print("1️⃣ Testing basic operations...")
        
        # Test SELECT
        result = supabase.table("intent_classification_logs").select("count", count="exact").execute()
        print(f"   ✅ SELECT: {result.count} rows in intent_classification_logs")
        
        # Test INSERT
        test_data = {
            "user_id": "test_supabase_only",
            "prompt": "Testing Supabase-only approach",
            "classified_workflow": "NEW_IMAGE",
            "confidence": 0.98,
            "processing_time_ms": 200
        }
        
        insert_result = supabase.table("intent_classification_logs").insert(test_data).execute()
        print(f"   ✅ INSERT: {len(insert_result.data)} row inserted")
        
        # Test aggregate queries (for stats)
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        
        # Get recent stats using Supabase
        stats_result = supabase.table("intent_classification_logs")\
            .select("*")\
            .gte("created_at", yesterday)\
            .execute()
        
        if stats_result.data:
            total = len(stats_result.data)
            fallback_count = sum(1 for row in stats_result.data if row.get('used_fallback', False))
            cache_hits = sum(1 for row in stats_result.data if row.get('cache_hit', False))
            avg_confidence = sum(row.get('confidence', 0) for row in stats_result.data) / total if total > 0 else 0
            
            print(f"   ✅ STATS CALCULATION:")
            print(f"      Total: {total}")
            print(f"      Fallback rate: {(fallback_count/total)*100:.1f}%")
            print(f"      Cache hit rate: {(cache_hits/total)*100:.1f}%")
            print(f"      Avg confidence: {avg_confidence:.2f}")
        else:
            print(f"   ⚠️ No recent data for stats")
        
        print("\n✅ Supabase-only approach works perfectly!")
        return True
        
    except Exception as e:
        print(f"❌ Supabase-only test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🚀 PostgreSQL Connection Diagnosis")
    
    # Test direct PostgreSQL
    pg_result = await test_direct_connection()
    
    # Test Supabase-only approach  
    supabase_result = await test_supabase_only_approach()
    
    print("\n" + "=" * 50)
    print("📊 Connection Test Results")
    print(f"• Direct PostgreSQL: {'✅ WORKING' if pg_result else '❌ BLOCKED'}")
    print(f"• Supabase Client: {'✅ WORKING' if supabase_result else '❌ FAILED'}")
    
    if not pg_result and supabase_result:
        print("\n💡 RECOMMENDATION:")
        print("   Direct PostgreSQL is blocked (likely firewall/network)")
        print("   Use Supabase client for all operations (recommended anyway)")
        print("   This approach is actually more reliable and simpler!")
    elif pg_result:
        print(f"\n✅ PostgreSQL connection string: {pg_result}")
    else:
        print("\n❌ Both approaches failed - check credentials")

if __name__ == "__main__":
    asyncio.run(main()) 