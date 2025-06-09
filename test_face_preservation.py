#!/usr/bin/env python3
"""
Test script to verify face preservation with explicit instruction
"""

import os
import asyncio
import json
import logging
import sys
sys.path.append('.')

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging to see everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_face_preservation():
    """Test face preservation with explicit face preservation instruction"""
    
    # Import the updated generator
    from app.services.generators.runway import RunwayGenerator
    
    print("🧪 Testing face preservation with explicit instruction...")
    
    # Initialize the generator
    generator = RunwayGenerator()
    
    if not generator.client:
        print("❌ Runway client not initialized - check your API key")
        return
    
    print("✅ Runway client initialized with enhanced logging")
    
    # Test with explicit face preservation instruction
    prompt = "@working_image with the hairstyle from @blonde. Maintain all other features. Only update the hair style. Do not change the face of @working_image."
    
    # Use the same reference images as your successful generation
    parameters = {
        "ratio": "1920:1080",
        "reference_images": [
            {
                "uri": "https://dnznrvs05pmza.cloudfront.net/1d48014b-1c6d-4103-8c6f-bab7fda5364c.png",
                "tag": "blonde"
            },
            {
                "uri": "https://dnznrvs05pmza.cloudfront.net/325dd86a-bf1a-4214-a043-b5a6f2262ae1.png?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiNWE4ZTRjMDhkZDZjYjVkNiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc0OTYwMDAwMH0.B-qgAAvZ30j9bcKG5yQjvAgKqakdlG_sM8f7gyfjdFw", 
                "tag": "working_image"
            }
        ]
    }
    
    print("📋 Test parameters with face preservation:")
    print(f"Prompt: {prompt}")
    print(json.dumps(parameters, indent=2))
    
    try:
        print("\n🚀 Making Runway API call with face preservation instruction...")
        
        # Try the text-to-image call directly with enhanced prompt
        task = generator.client.text_to_image.create(
            model="gen4_image",
            prompt_text=prompt,
            ratio="1920:1080",
            reference_images=parameters["reference_images"]
        )
        
        print(f"\n✅ HTTP request sent with face preservation instruction!")
        print(f"Task ID: {task.id}")
        print(f"Task Status: {task.status}")
        
        # Poll for completion to get the result
        print("\n⏳ Polling for completion...")
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            await asyncio.sleep(2)
            attempt += 1
            
            task = generator.client.tasks.retrieve(task.id)
            print(f"   Attempt {attempt}: Status = {task.status}")
            
            if task.status == "SUCCEEDED":
                if task.output and len(task.output) > 0:
                    output_url = task.output[0]
                    print(f"\n🎉 Generation completed successfully!")
                    print(f"Result URL: {output_url}")
                    print(f"Total attempts: {attempt}")
                    return
                else:
                    print("❌ No output URL returned")
                    return
                    
            elif task.status == "FAILED":
                error_msg = getattr(task, 'error', None) or getattr(task, 'failure', None) or 'Unknown error'
                print(f"❌ Generation failed: {error_msg}")
                return
        
        print(f"⏰ Generation timed out after {max_attempts * 2} seconds")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("HTTP request details should still be logged above!")

if __name__ == "__main__":
    asyncio.run(test_face_preservation()) 