#!/usr/bin/env python3
"""
Test script to verify enhanced Runway logging is working
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

async def test_enhanced_logging():
    """Test the enhanced logging functionality"""
    
    # Import the updated generator
    from app.services.generators.runway import RunwayGenerator
    
    print("🧪 Testing enhanced Runway logging...")
    
    # Initialize the generator
    generator = RunwayGenerator()
    
    if not generator.client:
        print("❌ Runway client not initialized - check your API key")
        return
    
    print("✅ Runway client initialized with enhanced logging")
    
    # Test with a simple prompt
    prompt = "@working_image with the hairstyle from @blonde. Maintain all other features. Only update the hair style."
    
    parameters = {
        "ratio": "1920:1080",
        "reference_images": [
            {
                "uri": "https://storage.googleapis.com/pai-images/4b89bd7bb19b494ab6c37d32cc49e6fb.jpeg",
                "tag": "working_image"
            },
            {
                "uri": "https://storage.googleapis.com/pai-images/f58bb1e6ad5541acbc8ca0103c77c70a.jpeg", 
                "tag": "blonde"
            }
        ]
    }
    
    print("📋 Test parameters:")
    print(json.dumps(parameters, indent=2))
    
    try:
        print("\n🚀 Making Runway API call with enhanced logging...")
        result = await generator._generate_image_with_references(prompt, parameters)
        
        print(f"\n✅ Test completed successfully!")
        print(f"Result: {result.get('output_url', 'No URL returned')}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_logging()) 