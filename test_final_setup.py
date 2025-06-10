#!/usr/bin/env python3
"""
Sprint 3: Final Setup Verification
Tests all components are ready for Sprint 3 implementation
"""
import os
import redis
import asyncio
import time
from typing import Dict, Any
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

class Sprint3SetupVerifier:
    """Verify all Sprint 3 prerequisites are ready"""
    
    def __init__(self):
        self.results = {}
    
    def test_redis_connection(self) -> Dict[str, Any]:
        """Test Redis connection (should work after URL fix)"""
        print("🔍 Testing Redis Connection...")
        
        try:
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                return {"success": False, "error": "REDIS_URL not found"}
            
            client = redis.Redis.from_url(redis_url, decode_responses=True)
            
            # Test all operations needed for Sprint 3
            start_time = time.time()
            
            # Basic operations
            ping_result = client.ping()
            if not ping_result:
                raise Exception("Ping failed")
            
            # Cache operations (for intent classification)
            cache_key = "sprint3_cache_test"
            cache_data = {
                "workflow_type": "hair_styling",
                "confidence": 0.92,
                "reasoning": "Test cache"
            }
            import json
            client.set(cache_key, json.dumps(cache_data), ex=60)
            retrieved = json.loads(client.get(cache_key))
            
            # Rate limiting operations
            rate_key = f"rate_limit:test_user:{int(time.time() // 60)}"
            client.incr(rate_key)
            client.expire(rate_key, 60)
            
            # Cost tracking operations
            cost_key = f"cost_limit:test_user:{int(time.time() // 3600)}"
            client.incrbyfloat(cost_key, 0.05)
            client.expire(cost_key, 3600)
            
            # Cleanup
            client.delete(cache_key, rate_key, cost_key)
            
            end_time = time.time()
            latency = round((end_time - start_time) * 1000, 2)
            
            return {
                "success": True,
                "latency_ms": latency,
                "operations": ["ping", "cache", "rate_limiting", "cost_tracking"],
                "ready_for_sprint3": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "ready_for_sprint3": False
            }
    
    def test_supabase_analytics_tables(self) -> Dict[str, Any]:
        """Test if Supabase analytics tables exist"""
        print("🔍 Testing Supabase Analytics Tables...")
        
        try:
            supabase = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            )
            
            # Test each analytics table exists and is accessible
            tables_to_check = [
                "intent_classification_logs",
                "cost_tracking", 
                "model_selection_logs",
                "system_performance_logs"
            ]
            
            existing_tables = []
            for table_name in tables_to_check:
                try:
                    # Try to query the table (this will fail if table doesn't exist)
                    result = supabase.table(table_name).select("id").limit(1).execute()
                    existing_tables.append(table_name)
                except Exception as e:
                    if "does not exist" in str(e).lower() or "relation" in str(e).lower():
                        continue
                    else:
                        # Some other error
                        raise e
            
            if len(existing_tables) == len(tables_to_check):
                return {
                    "success": True,
                    "existing_tables": existing_tables,
                    "ready_for_sprint3": True,
                    "message": "All analytics tables exist"
                }
            else:
                missing_tables = [t for t in tables_to_check if t not in existing_tables]
                return {
                    "success": False,
                    "existing_tables": existing_tables,
                    "missing_tables": missing_tables,
                    "ready_for_sprint3": False,
                    "fix": "Run setup_sprint3_analytics.sql in Supabase SQL Editor"
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "ready_for_sprint3": False,
                "fix": "Check Supabase connection and run analytics SQL"
            }
    
    def test_environment_variables(self) -> Dict[str, Any]:
        """Test all required environment variables exist"""
        print("🔍 Testing Environment Variables...")
        
        required_vars = [
            "REDIS_URL",
            "RATE_LIMIT_REQUESTS_PER_MINUTE", 
            "RATE_LIMIT_REQUESTS_PER_HOUR",
            "COST_LIMIT_PER_HOUR",
            "CIRCUIT_BREAKER_FAILURE_THRESHOLD",
            "CIRCUIT_BREAKER_TIMEOUT",
            "INTENT_CACHE_TTL"
        ]
        
        missing_vars = []
        present_vars = []
        
        for var in required_vars:
            if os.getenv(var):
                present_vars.append(var)
            else:
                missing_vars.append(var)
        
        return {
            "success": len(missing_vars) == 0,
            "present_vars": present_vars,
            "missing_vars": missing_vars,
            "ready_for_sprint3": len(missing_vars) == 0,
            "fix": "Add missing variables to .env file" if missing_vars else None
        }
    
    def test_python_dependencies(self) -> Dict[str, Any]:
        """Test required Python packages are installed"""
        print("🔍 Testing Python Dependencies...")
        
        required_packages = [
            ("redis", "Redis client"),
            ("asyncio", "Async support"),
            ("json", "JSON operations"),
        ]
        
        missing_packages = []
        available_packages = []
        
        for package, description in required_packages:
            try:
                __import__(package)
                available_packages.append(package)
            except ImportError:
                missing_packages.append((package, description))
        
        # Test Redis with hiredis (performance improvement)
        try:
            import hiredis
            redis_performance = "✅ High Performance (hiredis available)"
        except ImportError:
            redis_performance = "⚠️ Standard Performance (hiredis not available, but OK)"
        
        return {
            "success": len(missing_packages) == 0,
            "available_packages": available_packages,
            "missing_packages": missing_packages,
            "redis_performance": redis_performance,
            "ready_for_sprint3": len(missing_packages) == 0
        }
    
    async def run_complete_verification(self):
        """Run complete Sprint 3 setup verification"""
        print("🚀 Starting Sprint 3 Setup Verification\n")
        
        # Test Redis
        self.results["redis"] = self.test_redis_connection()
        
        # Test Supabase Analytics
        self.results["supabase_analytics"] = self.test_supabase_analytics_tables()
        
        # Test Environment Variables
        self.results["environment"] = self.test_environment_variables()
        
        # Test Dependencies
        self.results["dependencies"] = self.test_python_dependencies()
        
        # Display results
        self.display_verification_results()
        
        return self.results
    
    def display_verification_results(self):
        """Display comprehensive verification results"""
        print("\n" + "="*70)
        print("🧪 SPRINT 3 SETUP VERIFICATION RESULTS")
        print("="*70)
        
        overall_ready = True
        
        for component, result in self.results.items():
            component_name = component.replace("_", " ").title()
            print(f"\n📋 {component_name}:")
            
            if result["success"]:
                print(f"   ✅ SUCCESS")
                if "latency_ms" in result:
                    print(f"   ⚡ Latency: {result['latency_ms']}ms")
                if "operations" in result:
                    print(f"   🔧 Operations: {', '.join(result['operations'])}")
                if "existing_tables" in result:
                    print(f"   📊 Tables: {', '.join(result['existing_tables'])}")
                if "present_vars" in result:
                    print(f"   🔧 Variables: {len(result['present_vars'])}/{len(result['present_vars']) + len(result.get('missing_vars', []))}")
                if "redis_performance" in result:
                    print(f"   {result['redis_performance']}")
            else:
                print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
                if "fix" in result:
                    print(f"   🔧 Fix: {result['fix']}")
                if "missing_vars" in result and result["missing_vars"]:
                    print(f"   📝 Missing: {', '.join(result['missing_vars'])}")
                if "missing_tables" in result and result["missing_tables"]:
                    print(f"   📊 Missing Tables: {', '.join(result['missing_tables'])}")
                overall_ready = False
        
        # Overall Status
        print(f"\n🎯 OVERALL STATUS: {'✅ READY FOR SPRINT 3' if overall_ready else '❌ SETUP INCOMPLETE'}")
        
        if overall_ready:
            print("\n🎉 Congratulations! Your setup is ready for Sprint 3 implementation!")
            print("   Next steps:")
            print("   1. Create core infrastructure files (cache.py, circuit_breaker.py, rate_limiter.py)")
            print("   2. Update IntentClassifier to use Redis and circuit breaker")
            print("   3. Add health check endpoints")
            print("   4. Start Sprint 3 implementation")
        else:
            print("\n🔧 Please complete the setup before proceeding:")
            for component, result in self.results.items():
                if not result["success"] and "fix" in result:
                    print(f"   • {component}: {result['fix']}")

async def main():
    """Main verification runner"""
    verifier = Sprint3SetupVerifier()
    results = await verifier.run_complete_verification()
    
    # Return exit code
    all_ready = all(result["success"] for result in results.values())
    return 0 if all_ready else 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 