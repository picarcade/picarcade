#!/usr/bin/env python3
"""
Test script using production endpoint with API version header
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

async def test_production_with_version():
    """Test production endpoint with version header"""
    
    api_key = os.getenv("RUNWAY_API_KEY")
    if not api_key:
        raise Exception("RUNWAY_API_KEY not found in environment variables")
    
    print("🚀 Testing production endpoint with version header...")
    
    try:
        # Create client with production endpoint and version header
        client = RunwayML(
            api_key=api_key,
            base_url="https://api.runwayml.com",
            default_headers={
                "X-Runway-Version": "2024-11-06"
            }
        )
        
        print(f"   ✅ Production client created with version header")
        print(f"   🎯 Base URL: {getattr(client, 'base_url', 'Unknown')}")
        
        # Same exact parameters from your logs
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
        
        # Log the complete API request
        complete_api_request = {
            "endpoint": "https://api.runwayml.com",
            "headers": {"X-Runway-Version": "2024-11-06"},
            "sdk_method": "client.text_to_image.create",
            "parameters": {
                "model": "gen4_image",
                "prompt_text": prompt,
                "ratio": "1920:1080",
                "reference_images": reference_images
            }
        }
        
        print("🚀 PRODUCTION API REQUEST WITH VERSION:")
        print(json.dumps(complete_api_request, indent=2))
        
        print(f"🌟 CALLING PRODUCTION: client.text_to_image.create()")
        print(f"   - endpoint: https://api.runwayml.com")
        print(f"   - version: 2024-11-06")
        print(f"   - model: gen4_image")
        print(f"   - prompt_text: {prompt}")
        print(f"   - ratio: 1920:1080")
        print(f"   - reference_images: {len(reference_images)} images")
        
        for i, ref in enumerate(reference_images):
            print(f"     📸 Reference {i+1}: tag='{ref['tag']}', uri='{ref['uri'][:60]}...'")
        
        # Make the API call
        task = client.text_to_image.create(
            model="gen4_image",
            prompt_text=prompt,
            ratio="1920:1080",
            reference_images=reference_images
        )
        
        task_id = task.id
        print(f"✅ PRODUCTION TASK CREATED: {task_id}")
        logger.info(f"Production runway task created: {task_id}")
        
        # Poll for completion
        max_attempts = 60
        attempt = 0
        
        print(f"⏳ Polling production endpoint for completion (max {max_attempts} attempts)...")
        
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
                    logger.info(f"Production runway task {task_id} completed: {output_url}")
                    
                    return {
                        "success": True,
                        "output_url": output_url,
                        "task_id": task_id,
                        "endpoint": "production",
                        "version": "2024-11-06"
                    }
                else:
                    raise Exception("No output URL returned from production")
                    
            elif task.status == "FAILED":
                error_msg = getattr(task, 'error', None)
                failure_msg = getattr(task, 'failure', None)
                failure_code = getattr(task, 'failure_code', None)
                
                primary_error = failure_msg or error_msg or 'Unknown error'
                
                print(f"❌ PRODUCTION FAILED! Task {task_id} failed: {primary_error}")
                logger.error(f"Production runway task {task_id} failed: {primary_error}")
                if failure_code:
                    print(f"   Failure code: {failure_code}")
                    logger.error(f"Failure code: {failure_code}")
                
                return {
                    "success": False,
                    "error": primary_error,
                    "failure_code": failure_code,
                    "task_id": task_id,
                    "endpoint": "production",
                    "version": "2024-11-06"
                }
            
            else:
                print(f"   Status: {task.status}")
                
        print(f"⏰ PRODUCTION TIMEOUT! Task {task_id} timed out after {max_attempts * 2} seconds")
        return {
            "success": False,
            "error": f"Production endpoint timed out after {max_attempts * 2} seconds",
            "task_id": task_id,
            "endpoint": "production",
            "version": "2024-11-06"
        }
        
    except Exception as e:
        print(f"💥 PRODUCTION ENDPOINT ERROR: {str(e)}")
        logger.error(f"Production runway SDK error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "endpoint": "production",
            "version": "2024-11-06"
        }

async def main():
    """Main test function"""
    print("🧪 PRODUCTION API WITH VERSION HEADER TEST")
    print("=" * 60)
    print("Testing production endpoint with X-Runway-Version: 2024-11-06")
    print()
    
    try:
        result = await test_production_with_version()
        
        print()
        print("📋 FINAL PRODUCTION RESULT:")
        print(json.dumps(result, indent=2))
        
        if result.get("success"):
            print("✅ Production test completed successfully!")
            print("🎯 This should match Runway UI behavior for face preservation!")
        else:
            print("❌ Production test failed!")
            
    except Exception as e:
        print(f"💥 Test script error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 