#!/usr/bin/env python3
"""
Simple Redis Connection Test for Upstash
"""

import os
import sys
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file with dotenv")
except ImportError:
    print("⚠️ python-dotenv not available, trying manual loading...")
    # Manual .env loading
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"')
        print("✅ Manually loaded .env file")
    else:
        print("❌ No .env file found")

# Test Redis connection
def test_redis_connection():
    redis_url = os.getenv('REDIS_URL')
    
    if not redis_url:
        print("❌ REDIS_URL not found in environment variables")
        return False
    
    print(f"🔗 Testing Redis URL: {redis_url[:30]}...")
    
    try:
        import redis
        
        # Test basic connection
        r = redis.from_url(redis_url)
        result = r.ping()
        print(f"✅ Redis PING successful: {result}")
        
        # Test basic operations
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        print(f"✅ Redis SET/GET test: {value.decode('utf-8')}")
        
        # Clean up
        r.delete('test_key')
        print("✅ Redis connection working perfectly!")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        return False
    except redis.AuthenticationError as e:
        print(f"❌ Redis authentication failed: {e}")
        print("💡 Check your Redis password/token in REDIS_URL")
        return False
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False

def main():
    print("🔧 Redis Connection Test for Upstash")
    print("=" * 50)
    
    # Check environment variables
    print("\n1️⃣ Checking Environment Variables...")
    redis_url = os.getenv('REDIS_URL')
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    print(f"REDIS_URL: {'✅ SET' if redis_url else '❌ MISSING'}")
    print(f"SUPABASE_URL: {'✅ SET' if supabase_url else '❌ MISSING'}")
    print(f"SUPABASE_KEY: {'✅ SET' if supabase_key else '❌ MISSING'}")
    
    # Test Redis connection
    print("\n2️⃣ Testing Redis Connection...")
    success = test_redis_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Redis connection test PASSED!")
        print("✅ Your Redis configuration is working correctly")
    else:
        print("❌ Redis connection test FAILED!")
        print("\n💡 Troubleshooting steps:")
        print("1. Check your REDIS_URL in the .env file")
        print("2. Get the correct Redis URL from Upstash dashboard")
        print("3. Make sure the password/token is correct")
        print("4. Check if your network allows connections to Upstash")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 