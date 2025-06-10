#!/usr/bin/env python3
"""
Sprint 3: Redis Connection Fixer
Helps identify and fix Redis connection issues
"""
import os
import redis
import asyncio
import time
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RedisConnectionFixer:
    """Fix Redis connections for Sprint 3"""
    
    def __init__(self):
        self.results = {}
    
    def fix_upstash_connection(self) -> Dict[str, Any]:
        """Fix and test Upstash Redis connection"""
        print("🔧 Fixing Upstash Redis Connection...")
        
        current_url = os.getenv("REDIS_URL")
        print(f"   Current URL: {current_url}")
        
        if current_url and current_url.startswith("https://"):
            print("   ❌ Issue: URL is HTTPS format, not Redis format")
            print("\n   🔧 FIX NEEDED:")
            print("   1. Go to your Upstash Console: https://console.upstash.com/")
            print("   2. Click on your database")
            print("   3. Look for 'Redis URL' or 'Connection String'")
            print("   4. Copy the URL that starts with 'redis://' or 'rediss://'")
            print("   5. Replace REDIS_URL in your .env file")
            print("\n   📝 The correct format should look like:")
            print("   REDIS_URL=redis://default:password@host:port")
            print("   or")
            print("   REDIS_URL=rediss://default:password@host:port")
            
            return {
                "success": False,
                "error": "Invalid URL format",
                "fix": "Get proper Redis URL from Upstash console"
            }
        
        # Try to connect with current URL
        try:
            client = redis.Redis.from_url(current_url, decode_responses=True)
            ping_result = client.ping()
            
            if ping_result:
                print("   ✅ Connection successful!")
                return {"success": True, "message": "Upstash connection working"}
            else:
                raise Exception("Ping failed")
                
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fix": "Check Upstash URL format and credentials"
            }
    
    def test_redis_cloud_with_fixed_ssl(self) -> Dict[str, Any]:
        """Test Redis Cloud connection with corrected SSL settings"""
        print("🔧 Testing Redis Cloud with Fixed SSL Settings...")
        
        # Try different SSL configurations
        configs_to_try = [
            {
                'host': 'redis-18046.c337.australia-southeast1-1.gce.redns.redis-cloud.com',
                'port': 18046,
                'username': 'default',
                'password': 'Z4MHl0D250Cj6z4GlVf53loRv4W6X3rO',
                'decode_responses': True,
                'ssl': False,  # Try without SSL first
                'name': 'Without SSL'
            },
            {
                'host': 'redis-18046.c337.australia-southeast1-1.gce.redns.redis-cloud.com',
                'port': 18046,
                'username': 'default',
                'password': 'Z4MHl0D250Cj6z4GlVf53loRv4W6X3rO',
                'decode_responses': True,
                'ssl': True,
                'ssl_cert_reqs': None,
                'ssl_check_hostname': False,
                'name': 'With SSL (relaxed)'
            }
        ]
        
        for config in configs_to_try:
            config_name = config.pop('name')
            print(f"   Trying {config_name}...")
            
            try:
                client = redis.Redis(**config)
                ping_result = client.ping()
                
                if ping_result:
                    print(f"   ✅ {config_name} - SUCCESS!")
                    
                    # Test basic operations
                    test_key = "sprint3_cloud_test"
                    test_value = f"test_{int(time.time())}"
                    
                    client.set(test_key, test_value, ex=60)
                    retrieved = client.get(test_key)
                    client.delete(test_key)
                    
                    if retrieved == test_value:
                        return {
                            "success": True,
                            "config": config_name,
                            "message": "Redis Cloud connection working"
                        }
                    
            except Exception as e:
                print(f"   ❌ {config_name} failed: {e}")
                continue
        
        return {
            "success": False,
            "error": "All connection attempts failed",
            "fix": "Check Redis Cloud credentials and network access"
        }
    
    def generate_corrected_env_example(self):
        """Generate example .env entries with correct formats"""
        print("\n" + "="*60)
        print("📝 CORRECTED .ENV EXAMPLES")
        print("="*60)
        
        print("\n# For Upstash Redis:")
        print("# Get this URL from: https://console.upstash.com/ -> Your Database -> Redis URL")
        print("REDIS_URL=redis://default:your_password@your_host.upstash.io:port")
        print("# Example:")
        print("# REDIS_URL=redis://default:AbCdEf123456@apt-kangaroo-48272.upstash.io:6379")
        
        print("\n# Alternative Redis Cloud URL format:")
        print("# REDIS_CLOUD_URL=redis://default:Z4MHl0D250Cj6z4GlVf53loRv4W6X3rO@redis-18046.c337.australia-southeast1-1.gce.redns.redis-cloud.com:18046")
        
        print("\n🔧 STEPS TO FIX:")
        print("1. Go to Upstash Console and get the proper Redis URL")
        print("2. Replace REDIS_URL in your .env file")
        print("3. Run the test again: python test_redis_connections.py")
    
    async def run_diagnosis(self):
        """Run complete Redis diagnosis"""
        print("🩺 Starting Redis Connection Diagnosis\n")
        
        # Test Upstash
        upstash_result = self.fix_upstash_connection()
        
        # Test Redis Cloud
        redis_cloud_result = self.test_redis_cloud_with_fixed_ssl()
        
        # Generate corrected examples
        self.generate_corrected_env_example()
        
        # Summary
        print("\n" + "="*60)
        print("📊 DIAGNOSIS SUMMARY")
        print("="*60)
        
        print(f"\n🔸 Upstash: {'✅ Working' if upstash_result['success'] else '❌ Needs Fix'}")
        if not upstash_result['success']:
            print(f"   Fix: {upstash_result['fix']}")
        
        print(f"\n🔸 Redis Cloud: {'✅ Working' if redis_cloud_result['success'] else '❌ Needs Fix'}")
        if redis_cloud_result['success']:
            print(f"   Working config: {redis_cloud_result['config']}")
        else:
            print(f"   Fix: {redis_cloud_result['fix']}")
        
        return {
            "upstash": upstash_result,
            "redis_cloud": redis_cloud_result
        }

async def main():
    """Main diagnosis runner"""
    fixer = RedisConnectionFixer()
    await fixer.run_diagnosis()

if __name__ == "__main__":
    asyncio.run(main()) 