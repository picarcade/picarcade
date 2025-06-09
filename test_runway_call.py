#!/usr/bin/env python3
"""
Test script to verify exact Runway API calls
Replicates the call from the logs to ensure we're sending the right data
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

async def test_runway_call():
    """Test the exact Runway call from the logs"""
    
    # Initialize Runway client
    api_key = os.getenv("RUNWAY_API_KEY")
    if not api_key:
        raise Exception("RUNWAY_API_KEY not found in environment variables")
    
    client = RunwayML(api_key=api_key)
    
    # Exact parameters from the log
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
    
    # Log the complete, definitive API request being sent to Runway
    complete_api_request = {
        "sdk_method": "client.text_to_image.create",
        "parameters": {
            "model": "gen4_image",
            "prompt_text": prompt,
            "ratio": "1920:1080",
            "reference_images": reference_images
        }
    }
    
    print("🚀 DEFINITIVE RUNWAY API REQUEST:")
    print(json.dumps(complete_api_request, indent=2))
    logger.info("🚀 DEFINITIVE RUNWAY API REQUEST:")
    logger.info(json.dumps(complete_api_request, indent=2))
    
    try:
        print(f"🌟 CALLING: client.text_to_image.create()")
        print(f"   - model: gen4_image")
        print(f"   - prompt_text: {prompt}")
        print(f"   - ratio: 1920:1080")
        print(f"   - reference_images: {len(reference_images)} images")
        
        for i, ref in enumerate(reference_images):
            print(f"     📸 Reference {i+1}: tag='{ref['tag']}', uri='{ref['uri'][:60]}...'")
        
        # Make the actual API call
        task = client.text_to_image.create(
            model="gen4_image",
            prompt_text=prompt,
            ratio="1920:1080",
            reference_images=reference_images
        )
        
        task_id = task.id
        print(f"✅ RUNWAY TASK CREATED: {task_id}")
        logger.info(f"Runway reference task created: {task_id}")
        
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
                    print(f"🎉 SUCCESS! Task {task_id} completed")
                    print(f"🖼️  Output URL: {output_url}")
                    logger.info(f"Runway reference task {task_id} completed: {output_url}")
                    
                    return {
                        "success": True,
                        "output_url": output_url,
                        "task_id": task_id
                    }
                else:
                    raise Exception("No output URL returned from successful reference generation")
                    
            elif task.status == "FAILED":
                error_msg = getattr(task, 'error', None)
                failure_msg = getattr(task, 'failure', None)
                failure_code = getattr(task, 'failure_code', None)
                
                primary_error = failure_msg or error_msg or 'Unknown error'
                
                print(f"❌ FAILED! Task {task_id} failed: {primary_error}")
                logger.error(f"Runway task {task_id} failed: {primary_error}")
                if failure_code:
                    print(f"   Failure code: {failure_code}")
                    logger.error(f"Failure code: {failure_code}")
                
                return {
                    "success": False,
                    "error": primary_error,
                    "failure_code": failure_code,
                    "task_id": task_id
                }
            
            else:
                print(f"   Status: {task.status}")
                
        print(f"⏰ TIMEOUT! Task {task_id} timed out after {max_attempts * 2} seconds")
        return {
            "success": False,
            "error": f"Runway reference generation timed out after {max_attempts * 2} seconds",
            "task_id": task_id
        }
        
    except Exception as e:
        print(f"💥 EXCEPTION: {str(e)}")
        logger.error(f"Runway SDK reference generation error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def main():
    """Main test function"""
    print("🧪 RUNWAY API TEST SCRIPT")
    print("=" * 50)
    print("Testing the exact API call from the logs...")
    print()
    
    try:
        result = await test_runway_call()
        
        print()
        print("📋 FINAL RESULT:")
        print(json.dumps(result, indent=2))
        
        if result.get("success"):
            print("✅ Test completed successfully!")
        else:
            print("❌ Test failed!")
            
    except Exception as e:
        print(f"💥 Test script error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 