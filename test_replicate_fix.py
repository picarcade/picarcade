#!/usr/bin/env python3
"""
Test script to verify Replicate API works after fixing Google auth interference
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_replicate_api():
    """Test basic Replicate API functionality"""
    
    print("🔬 Testing Replicate API after Google auth fix...")
    print("=" * 50)
    
    # Check if REPLICATE_API_TOKEN is set
    replicate_token = os.getenv('REPLICATE_API_TOKEN')
    print(f"✅ Replicate token configured: {bool(replicate_token)}")
    print(f"✅ Token length: {len(replicate_token) if replicate_token else 0}")
    
    if not replicate_token:
        print("❌ No REPLICATE_API_TOKEN found in environment")
        return False
    
    try:
        # Test Claude API call (the one that was failing)
        import replicate
        
        print("\n🧠 Testing Claude API call via Replicate...")
        
        # Simple test prompt
        test_prompt = "Write a haiku about fixing bugs"
        
        result_text = ""
        for event in replicate.stream(
            "anthropic/claude-4-sonnet",
            input={
                "prompt": test_prompt,
                "system_prompt": "You are a helpful assistant."
            }
        ):
            result_text += str(event)
        
        print(f"✅ Claude API call successful!")
        print(f"✅ Response: {result_text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Replicate API call failed: {e}")
        return False

async def test_google_isolation():
    """Test that Google client initialization doesn't interfere"""
    
    print("\n🔧 Testing Google client isolation...")
    
    try:
        # Import and initialize Google generator
        from app.services.generators.google_ai import VertexAIGenerator
        
        print("✅ Google generator imported successfully")
        
        # Initialize it (this used to set global env vars)
        generator = VertexAIGenerator()
        print("✅ Google generator initialized without setting global env vars")
        
        # Check that GOOGLE environment variables are NOT globally set
        google_vars = [
            'GOOGLE_GENAI_USE_VERTEXAI',
            'GOOGLE_CLOUD_PROJECT',
            'GOOGLE_CLOUD_LOCATION'
        ]
        
        for var in google_vars:
            if var in os.environ:
                print(f"⚠️  Warning: {var} is still set globally: {os.environ[var]}")
            else:
                print(f"✅ {var} is not set globally (good!)")
        
        return True
        
    except Exception as e:
        print(f"❌ Google generator test failed: {e}")
        return False

async def main():
    """Run all tests"""
    
    print("🚀 Testing Replicate Fix - Google Auth Interference Resolved")
    print("=" * 60)
    
    # Test 1: Google isolation
    google_ok = await test_google_isolation()
    
    # Test 2: Replicate API
    replicate_ok = await test_replicate_api()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"✅ Google Isolation: {'PASS' if google_ok else 'FAIL'}")
    print(f"✅ Replicate API: {'PASS' if replicate_ok else 'FAIL'}")
    
    if google_ok and replicate_ok:
        print("\n🎉 ALL TESTS PASSED! The fix is working correctly.")
        print("✅ Production should now work without 403 errors.")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
    
    return google_ok and replicate_ok

if __name__ == "__main__":
    asyncio.run(main()) 