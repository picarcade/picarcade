#!/usr/bin/env python3
"""
Minimal test to verify HTTP logging without aspect ratio validation
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

async def test_minimal_logging():
    """Test HTTP logging with publicly available images"""
    
    # Import the updated generator
    from app.services.generators.runway import RunwayGenerator
    
    print("🧪 Testing enhanced Runway HTTP logging...")
    
    # Initialize the generator
    generator = RunwayGenerator()
    
    if not generator.client:
        print("❌ Runway client not initialized - check your API key")
        return
    
    print("✅ Runway client initialized with enhanced logging")
    
    # Use publicly available test images that don't require validation
    prompt = "@person with the style from @reference. Do not change the face of @person."
    
    # Use small, publicly available images to avoid aspect ratio issues
    parameters = {
        "ratio": "1920:1080",
        "reference_images": [
            {
                "uri": "https://images.unsplash.com/photo-1506794778202-cad84cf45f04?w=400",
                "tag": "person"
            },
            {
                "uri": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400", 
                "tag": "reference"
            }
        ]
    }
    
    print("📋 Test parameters:")
    print(json.dumps(parameters, indent=2))
    
    try:
        print("\n🚀 Making Runway API call to demonstrate HTTP logging...")
        
        # Try the text-to-image call directly to see HTTP logging
        task = generator.client.text_to_image.create(
            model="gen4_image",
            prompt_text=prompt,
            ratio="1920:1080",
            reference_images=parameters["reference_images"]
        )
        
        print(f"\n✅ HTTP request logged successfully!")
        print(f"Task ID: {task.id}")
        print(f"Task Status: {task.status}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("But HTTP request/response should still be logged above!")

if __name__ == "__main__":
    asyncio.run(test_minimal_logging()) 