#!/usr/bin/env python3
"""
Test script to try different API version headers with the production endpoint
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

async def test_with_version_header():
    """Test with X-Runway-Version header on the production endpoint"""
    
    api_key = os.getenv("RUNWAY_API_KEY")
    if not api_key:
        raise Exception("RUNWAY_API_KEY not found in environment variables")
    
    print("🚀 Testing with X-Runway-Version header on production endpoint...")
    
    try:
        # Create client with version header
        client = RunwayML(
            api_key=api_key,
            base_url="https://api.dev.runwayml.com",  # This IS the production endpoint
            default_headers={
                "X-Runway-Version": "2024-11-06"
            }
        )
        
        print(f"   ✅ Client created with version header")
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
            "endpoint": "https://api.dev.runwayml.com (PRODUCTION)",
            "headers": {"X-Runway-Version": "2024-11-06"},
            "sdk_method": "client.text_to_image.create",
            "parameters": {
                "model": "gen4_image",
                "prompt_text": prompt,
                "ratio": "1920:1080",
                "reference_images": reference_images
            }
        }
        
        print("🚀 API REQUEST WITH VERSION HEADER:")
        print(json.dumps(complete_api_request, indent=2))
        
        print(f"🌟 CALLING WITH VERSION HEADER: client.text_to_image.create()")
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
        print(f"✅ TASK CREATED WITH VERSION HEADER: {task_id}")
        logger.info(f"Runway task with version header created: {task_id}")
        
        # Poll for completion
        max_attempts = 60
        attempt = 0
        
        print(f"⏳ Polling for completion (max {max_attempts} attempts)...")
        
        while attempt < max_attempts:
            await asyncio.sleep(2)
            attempt += 1
            
            print(f"   📊 Attempt {attempt}/{max_attempts}...")
            task = client.tasks.retrieve(task_id)
            
            if task.status == "SUCCEEDED":
                if task.output and len(task.output) > 0:
                    output_url = task.output[0]
                    print(f"🎉 SUCCESS WITH VERSION HEADER! Task {task_id} completed")
                    print(f"🖼️  Output URL: {output_url}")
                    logger.info(f"Runway task with version header {task_id} completed: {output_url}")
                    
                    return {
                        "success": True,
                        "output_url": output_url,
                        "task_id": task_id,
                        "version": "2024-11-06",
                        "face_preservation": "TO_BE_TESTED"
                    }
                else:
                    raise Exception("No output URL returned")
                    
            elif task.status == "FAILED":
                error_msg = getattr(task, 'error', None)
                failure_msg = getattr(task, 'failure', None)
                failure_code = getattr(task, 'failure_code', None)
                
                primary_error = failure_msg or error_msg or 'Unknown error'
                
                print(f"❌ FAILED WITH VERSION HEADER! Task {task_id} failed: {primary_error}")
                logger.error(f"Runway task with version header {task_id} failed: {primary_error}")
                if failure_code:
                    print(f"   Failure code: {failure_code}")
                    logger.error(f"Failure code: {failure_code}")
                
                return {
                    "success": False,
                    "error": primary_error,
                    "failure_code": failure_code,
                    "task_id": task_id,
                    "version": "2024-11-06"
                }
            
            else:
                print(f"   Status: {task.status}")
                
        print(f"⏰ TIMEOUT! Task {task_id} timed out after {max_attempts * 2} seconds")
        return {
            "success": False,
            "error": f"Timed out after {max_attempts * 2} seconds",
            "task_id": task_id,
            "version": "2024-11-06"
        }
        
    except Exception as e:
        print(f"💥 VERSION HEADER ERROR: {str(e)}")
        logger.error(f"Runway SDK with version header error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "version": "2024-11-06"
        }

async def main():
    """Main test function"""
    print("🧪 API VERSION HEADER TEST")
    print("=" * 50)
    print("Testing X-Runway-Version: 2024-11-06 header for face preservation")
    print()
    
    try:
        result = await test_with_version_header()
        
        print()
        print("📋 FINAL RESULT WITH VERSION HEADER:")
        print(json.dumps(result, indent=2))
        
        if result.get("success"):
            print("✅ Test with version header completed successfully!")
            print("🎯 Check if this has better face preservation than without the header!")
        else:
            print("❌ Test with version header failed!")
            
    except Exception as e:
        print(f"💥 Test script error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 