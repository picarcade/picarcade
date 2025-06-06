#!/usr/bin/env python3
"""
Test script to verify the enhanced edit keywords work properly
"""

import asyncio
import sys
import os

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.intent_parser import BasicIntentParser

async def test_edit_keywords():
    """Test the enhanced edit keyword detection"""
    
    parser = BasicIntentParser()
    
    print("=== Enhanced Edit Keywords Test ===\n")
    
    # Test cases that should trigger edit intent
    edit_test_cases = [
        "put a hat on it",
        "add a hat to the image", 
        "give it sunglasses",
        "make it blue",
        "turn it into a cartoon",
        "place a flower on the table",
        "add the background",
        "remove the background",
        "edit this photo",
        "modify the colors",
        "change the lighting",
        "alter the composition",
        "adjust the brightness",
        "fix the contrast",
        "improve the quality",
        "update the style"
    ]
    
    # Test cases that should NOT trigger edit intent (should be generate_image)
    non_edit_test_cases = [
        "create an image of a horse",
        "draw a beautiful sunset",
        "generate a landscape painting",
        "create a logo for my company",
        "make a picture of a cat"
    ]
    
    print("🔧 Testing phrases that SHOULD trigger EDIT intent:\n")
    
    for i, prompt in enumerate(edit_test_cases, 1):
        result = await parser.analyze_intent(
            prompt=prompt,
            uploaded_images=None,
            current_working_image=None
        )
        
        is_edit = result.detected_intent.value == "edit_image"
        status = "✅ EDIT" if is_edit else "❌ NOT EDIT"
        
        print(f"{i:2d}. '{prompt}'")
        print(f"    Result: {result.detected_intent.value} (confidence: {result.confidence})")
        print(f"    Status: {status}")
        print()
    
    print("\n🎨 Testing phrases that should trigger GENERATE intent:\n")
    
    for i, prompt in enumerate(non_edit_test_cases, 1):
        result = await parser.analyze_intent(
            prompt=prompt,
            uploaded_images=None,
            current_working_image=None
        )
        
        is_generate = result.detected_intent.value == "generate_image"
        status = "✅ GENERATE" if is_generate else "❌ NOT GENERATE"
        
        print(f"{i:2d}. '{prompt}'")
        print(f"    Result: {result.detected_intent.value} (confidence: {result.confidence})")
        print(f"    Status: {status}")
        print()
    
    print("🧪 Testing priority logic with working image:\n")
    
    # Test that working image overrides keyword detection
    working_image_url = "https://example.com/previous_result.jpg"
    
    test_with_working_image = [
        "create a new sunset",  # Would normally be generate, but should be edit with working image
        "put a hat on it",      # Should be edit with high confidence
        "draw a cat"            # Would normally be generate, but should be edit with working image
    ]
    
    for i, prompt in enumerate(test_with_working_image, 1):
        result = await parser.analyze_intent(
            prompt=prompt,
            uploaded_images=None,
            current_working_image=working_image_url
        )
        
        is_edit = result.detected_intent.value == "edit_image"
        status = "✅ EDIT (working image)" if is_edit else "❌ NOT EDIT"
        confidence_ok = result.confidence >= 0.95
        
        print(f"{i:2d}. '{prompt}' + working image")
        print(f"    Result: {result.detected_intent.value} (confidence: {result.confidence})")
        print(f"    Status: {status}")
        print(f"    High confidence: {'✅' if confidence_ok else '❌'}")
        print()

if __name__ == "__main__":
    asyncio.run(test_edit_keywords()) 