#!/usr/bin/env python3
"""
Test script to try using production endpoint instead of dev endpoint
"""

import os
import asyncio
import json
import logging
from runwayml import RunwayML
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_production_endpoint():
    """Test using production endpoint explicitly"""
    
    api_key = os.getenv("RUNWAY_API_KEY")
    if not api_key:
        raise Exception("RUNWAY_API_KEY not found in environment variables")
    
    print("🧪 Testing different endpoint configurations...")
    
    # Test different base URLs
    endpoints_to_try = [
        "https://api.runwayml.com",  # Production endpoint
        "https://api.dev.runwayml.com",  # Dev endpoint (current)
    ]
    
    for base_url in endpoints_to_try:
        print(f"\n🔄 Testing endpoint: {base_url}")
        
        try:
            # Create client with explicit base URL
            client = RunwayML(
                api_key=api_key,
                base_url=base_url
            )
            
            print(f"   ✅ Client created successfully")
            print(f"   🎯 Base URL: {getattr(client, 'base_url', 'Unknown')}")
            
            # Try a simple API call to see if endpoint responds
            try:
                # Use a basic text-to-image call to test endpoint
                task = client.text_to_image.create(
                    model="gen4_image",
                    prompt_text="A simple test image of a cat",
                    ratio="1280:720"
                )
                
                print(f"   🎉 Endpoint {base_url} WORKS!")
                print(f"   📝 Task ID: {task.id}")
                
                # Don't wait for completion, just test endpoint availability
                return base_url
                
            except Exception as api_error:
                print(f"   ❌ Endpoint {base_url} failed: {str(api_error)[:100]}")
                
        except Exception as client_error:
            print(f"   💥 Client creation failed: {str(client_error)[:100]}")
    
    return None

async def test_with_production_if_available():
    """Test the reference image call with production endpoint if available"""
    
    api_key = os.getenv("RUNWAY_API_KEY")
    
    # Try production endpoint
    try:
        print("\n🚀 Testing with production endpoint...")
        client = RunwayML(
            api_key=api_key,
            base_url="https://api.runwayml.com"
        )
        
        # Same parameters as before
        prompt = "@working_image with the hairstyle from @blonde. Maintain all other features. Only update the hair style."
        
        reference_images = [
            {
                "uri": "https://dnznrvs05pmza.cloudfront.net/1d48014b-1c6d-4103-8c6f-bab7fda5364c.png?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiNDU3M2FkY2M1YzFjZjZiZCIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc0OTYwMDAwMH0.KQfZTFDXe_wpvBedBM2BpfzcKkUCqIBt4B9vCgJnIzc",
                "tag": "blonde"
            },
            {
                "uri": "https://replicate.delivery/xezq/Yv6u3Ssp4PrKG11MWcempFgbvuriIu4bdstAezYlZCZV5D1UA/tmpaisbkdru.jpg",
                "tag": "working_image"
            }
        ]
        
        print(f"🌟 CALLING PRODUCTION: client.text_to_image.create()")
        
        task = client.text_to_image.create(
            model="gen4_image",
            prompt_text=prompt,
            ratio="1920:1080",
            reference_images=reference_images
        )
        
        task_id = task.id
        print(f"✅ PRODUCTION TASK CREATED: {task_id}")
        
        # Poll for completion
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            await asyncio.sleep(2)
            attempt += 1
            
            print(f"   📊 Production attempt {attempt}/{max_attempts}...")
            task = client.tasks.retrieve(task_id)
            
            if task.status == "SUCCEEDED":
                if task.output and len(task.output) > 0:
                    output_url = task.output[0]
                    print(f"🎉 PRODUCTION SUCCESS! Task {task_id} completed")
                    print(f"🖼️  Production Output URL: {output_url}")
                    
                    return {
                        "success": True,
                        "output_url": output_url,
                        "task_id": task_id,
                        "endpoint": "production"
                    }
                else:
                    raise Exception("No output URL returned from production")
                    
            elif task.status == "FAILED":
                error_msg = getattr(task, 'error', 'Unknown error')
                print(f"❌ PRODUCTION FAILED! Task {task_id} failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "task_id": task_id,
                    "endpoint": "production"
                }
            
            else:
                print(f"   Status: {task.status}")
                
        print(f"⏰ PRODUCTION TIMEOUT! Task {task_id} timed out")
        return {
            "success": False,
            "error": "Production endpoint timeout",
            "task_id": task_id,
            "endpoint": "production"
        }
        
    except Exception as e:
        print(f"💥 PRODUCTION ENDPOINT ERROR: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "endpoint": "production"
        }

async def main():
    """Main test function"""
    print("🧪 ENDPOINT COMPARISON TEST")
    print("=" * 50)
    
    try:
        # First test which endpoints are available
        working_endpoint = await test_production_endpoint()
        
        if working_endpoint:
            print(f"\n✅ Found working endpoint: {working_endpoint}")
            
            if working_endpoint == "https://api.runwayml.com":
                # Test with production
                result = await test_with_production_if_available()
                print("\n📋 PRODUCTION RESULT:")
                print(json.dumps(result, indent=2))
            
        else:
            print("\n❌ No working alternative endpoints found")
            
    except Exception as e:
        print(f"💥 Test script error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 