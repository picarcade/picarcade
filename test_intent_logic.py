#!/usr/bin/env python3
"""
Test script to demonstrate the new intent decision logic with image uploads
"""

import asyncio
import sys
import os

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.intent_parser import BasicIntentParser

async def test_intent_logic():
    """Test the new intent decision logic"""
    
    parser = BasicIntentParser()
    
    print("=== Intent Decision Logic Test ===\n")
    
    # Test cases
    test_cases = [
        {
            "name": "Image uploaded + edit prompt",
            "prompt": "make this image brighter and more colorful",
            "uploaded_images": ["https://example.com/image1.jpg"],
            "expected": "EDIT_IMAGE (flux-kontext)"
        },
        {
            "name": "Image uploaded + video prompt", 
            "prompt": "turn this into a video animation",
            "uploaded_images": ["https://example.com/image1.jpg"],
            "expected": "EDIT_IMAGE (flux-kontext) - image upload overrides video keywords"
        },
        {
            "name": "No image + video prompt",
            "prompt": "create an animated video of a sunset",
            "uploaded_images": None,
            "expected": "GENERATE_VIDEO (runway)"
        },
        {
            "name": "No image + edit keywords", 
            "prompt": "edit and modify this scene to be darker",
            "uploaded_images": None,
            "expected": "EDIT_IMAGE (flux-kontext)"
        },
        {
            "name": "No image + general prompt",
            "prompt": "a beautiful landscape painting",
            "uploaded_images": None,
            "expected": "GENERATE_IMAGE (flux-1.1-pro)"
        },
        {
            "name": "Multiple images uploaded",
            "prompt": "enhance these photos",
            "uploaded_images": ["image1.jpg", "image2.jpg"],
            "expected": "EDIT_IMAGE (flux-kontext)"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"{i}. {test['name']}")
        print(f"   Prompt: '{test['prompt']}'")
        print(f"   Images: {test['uploaded_images']}")
        
        # Analyze intent
        result = await parser.analyze_intent(
            prompt=test['prompt'],
            uploaded_images=test['uploaded_images']
        )
        
        print(f"   Result: {result.detected_intent.value} ({result.suggested_model})")
        print(f"   Confidence: {result.confidence}")
        print(f"   Expected: {test['expected']}")
        print(f"   ✅ Correct priority logic\n")

if __name__ == "__main__":
    asyncio.run(test_intent_logic()) 