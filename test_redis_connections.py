#!/usr/bin/env python3
"""
Sprint 3: Redis Connection Test
Tests both Upstash and Redis Cloud connections to verify setup
"""
import os
import redis
import asyncio
import time
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RedisConnectionTester:
    """Test Redis connections for Sprint 3 infrastructure"""
    
    def __init__(self):
        self.results = {}
    
    def test_upstash_connection(self) -> Dict[str, Any]:
        """Test Upstash Redis connection"""
        print("🔍 Testing Upstash Redis Connection...")
        
        try:
            # Get Upstash URL from environment
            upstash_url = os.getenv("REDIS_URL")
            if not upstash_url:
                return {
                    "success": False,
                    "error": "REDIS_URL not found in environment variables",
                    "details": "Make sure REDIS_URL is set in your .env file"
                }
            
            # Create connection
            client = redis.Redis.from_url(upstash_url, decode_responses=True)
            
            # Test basic operations
            start_time = time.time()
            
            # Test ping
            ping_result = client.ping()
            if not ping_result:
                raise Exception("Ping failed")
            
            # Test set/get
            test_key = "sprint3_test_upstash"
            test_value = f"test_value_{int(time.time())}"
            
            client.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved_value = client.get(test_key)
            
            if retrieved_value != test_value:
                raise Exception(f"Set/Get failed: expected {test_value}, got {retrieved_value}")
            
            # Test increment (for rate limiting)
            counter_key = "sprint3_counter_test"
            client.incr(counter_key)
            counter_value = int(client.get(counter_key) or 0)
            
            # Test hash operations (for caching)
            hash_key = "sprint3_hash_test"
            hash_data = {"workflow": "image_generation", "confidence": "0.95"}
            client.hset(hash_key, mapping=hash_data)
            retrieved_hash = client.hgetall(hash_key)
            
            # Test expiration
            client.expire(test_key, 30)
            ttl = client.ttl(test_key)
            
            # Cleanup
            client.delete(test_key, counter_key, hash_key)
            
            end_time = time.time()
            latency = round((end_time - start_time) * 1000, 2)  # Convert to ms
            
            return {
                "success": True,
                "latency_ms": latency,
                "operations_tested": [
                    "ping", "set/get", "increment", "hash operations", "expiration"
                ],
                "url": upstash_url.split('@')[1] if '@' in upstash_url else "URL format not recognized"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": "Check your Upstash Redis URL in .env file"
            }
    
    def test_redis_cloud_connection(self) -> Dict[str, Any]:
        """Test Redis Cloud connection"""
        print("🔍 Testing Redis Cloud Connection...")
        
        try:
            # Redis Cloud connection details (from your provided info)
            redis_cloud_config = {
                'host': 'redis-18046.c337.australia-southeast1-1.gce.redns.redis-cloud.com',
                'port': 18046,
                'username': 'default',
                'password': 'Z4MHl0D250Cj6z4GlVf53loRv4W6X3rO',
                'decode_responses': True,
                'ssl': True,  # Redis Cloud typically uses SSL
                'ssl_cert_reqs': None  # For testing purposes
            }
            
            # Create connection
            client = redis.Redis(**redis_cloud_config)
            
            # Test basic operations
            start_time = time.time()
            
            # Test ping
            ping_result = client.ping()
            if not ping_result:
                raise Exception("Ping failed")
            
            # Test set/get
            test_key = "sprint3_test_cloud"
            test_value = f"test_value_{int(time.time())}"
            
            client.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved_value = client.get(test_key)
            
            if retrieved_value != test_value:
                raise Exception(f"Set/Get failed: expected {test_value}, got {retrieved_value}")
            
            # Test JSON operations (for caching complex data)
            import json
            json_key = "sprint3_json_test"
            json_data = {
                "workflow_type": "hair_styling",
                "confidence": 0.92,
                "reasoning": "Detected hair-related keywords",
                "timestamp": time.time()
            }
            client.set(json_key, json.dumps(json_data), ex=60)
            retrieved_json = json.loads(client.get(json_key))
            
            # Test list operations (for fallback tracking)
            list_key = "sprint3_list_test"
            client.lpush(list_key, "fallback1", "fallback2", "fallback3")
            list_length = client.llen(list_key)
            
            # Cleanup
            client.delete(test_key, json_key, list_key)
            
            end_time = time.time()
            latency = round((end_time - start_time) * 1000, 2)  # Convert to ms
            
            return {
                "success": True,
                "latency_ms": latency,
                "operations_tested": [
                    "ping", "set/get", "JSON operations", "list operations"
                ],
                "host": redis_cloud_config['host'],
                "port": redis_cloud_config['port']
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": "Check Redis Cloud connection details"
            }
    
    async def test_async_operations(self) -> Dict[str, Any]:
        """Test async Redis operations for production use"""
        print("🔍 Testing Async Redis Operations...")
        
        try:
            upstash_url = os.getenv("REDIS_URL")
            if not upstash_url:
                raise Exception("REDIS_URL not found")
            
            # Test async operations
            client = redis.Redis.from_url(upstash_url, decode_responses=True)
            
            start_time = time.time()
            
            # Simulate concurrent operations
            async def async_operation(key_suffix: str):
                # Use asyncio.to_thread for async Redis operations
                await asyncio.to_thread(client.set, f"async_test_{key_suffix}", f"value_{key_suffix}", ex=30)
                result = await asyncio.to_thread(client.get, f"async_test_{key_suffix}")
                await asyncio.to_thread(client.delete, f"async_test_{key_suffix}")
                return result
            
            # Run 5 concurrent operations
            tasks = [async_operation(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            latency = round((end_time - start_time) * 1000, 2)
            
            return {
                "success": True,
                "concurrent_operations": len(results),
                "latency_ms": latency,
                "all_operations_successful": all(r is not None for r in results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_all_tests(self):
        """Run all Redis connection tests"""
        print("🚀 Starting Sprint 3 Redis Connection Tests\n")
        
        # Test Upstash
        self.results["upstash"] = self.test_upstash_connection()
        
        # Test Redis Cloud
        self.results["redis_cloud"] = self.test_redis_cloud_connection()
        
        # Test async operations
        self.results["async_operations"] = await self.test_async_operations()
        
        # Display results
        self.display_results()
        
        return self.results
    
    def display_results(self):
        """Display test results in a formatted way"""
        print("\n" + "="*60)
        print("🧪 SPRINT 3 REDIS TEST RESULTS")
        print("="*60)
        
        for test_name, result in self.results.items():
            print(f"\n📋 {test_name.upper().replace('_', ' ')} TEST:")
            
            if result["success"]:
                print(f"   ✅ SUCCESS")
                if "latency_ms" in result:
                    print(f"   ⚡ Latency: {result['latency_ms']}ms")
                if "operations_tested" in result:
                    print(f"   🔧 Operations: {', '.join(result['operations_tested'])}")
                if "url" in result:
                    print(f"   🌐 Endpoint: {result['url']}")
                if "host" in result:
                    print(f"   🌐 Host: {result['host']}:{result['port']}")
            else:
                print(f"   ❌ FAILED: {result['error']}")
                if "details" in result:
                    print(f"   💡 Details: {result['details']}")
        
        # Overall status
        all_tests_passed = all(result["success"] for result in self.results.values())
        print(f"\n🎯 OVERALL STATUS: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
        
        if all_tests_passed:
            print("\n🎉 Your Redis setup is ready for Sprint 3 production infrastructure!")
            print("   Next steps:")
            print("   1. Run the Supabase SQL (setup_sprint3_analytics.sql)")
            print("   2. Implement the core infrastructure files")
            print("   3. Update your IntentClassifier to use Redis")
        else:
            print("\n🔧 Please fix the failed connections before proceeding with Sprint 3.")

async def main():
    """Main test runner"""
    tester = RedisConnectionTester()
    results = await tester.run_all_tests()
    
    # Return exit code based on test results
    return 0 if all(result["success"] for result in results.values()) else 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 