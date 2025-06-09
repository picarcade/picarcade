#!/usr/bin/env python3
"""
Test script to demonstrate session loss detection
This shows what happens when a user tries to edit but the session was lost
"""

import asyncio
import sys
import os

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.intent_parser import BasicIntentParser
from services.session_manager import session_manager

async def test_session_loss_detection():
    """Test that we properly detect when editing prompts fail due to session loss"""
    
    print("=== Session Loss Detection Test ===\n")
    
    parser = BasicIntentParser()
    session_id = "lost_session_123"
    user_id = "test_user"
    
    # Test prompts that should be editing but will fail due to no working image
    editing_prompts = [
        "make him look away from the camera",
        "make the shirt blue", 
        "change his expression",
        "add sunglasses",
        "make it brighter",
        "turn him around",
        "give him a hat"
    ]
    
    print("Testing editing prompts without working image (simulating session loss):\n")
    
    for i, prompt in enumerate(editing_prompts, 1):
        print(f"{i}. Testing: '{prompt}'")
        
        # Analyze intent - no working image simulates session loss
        result = await parser.analyze_intent(
            prompt=prompt,
            uploaded_images=None,
            current_working_image=None,  # Simulates session loss
            generation_id=f"test_gen_{i}"
        )
        
        print(f"   Result: {result.detected_intent.value} (confidence: {result.confidence})")
        print(f"   Model: {result.suggested_model}")
        
        # Show what the session manager would report
        working_image = session_manager.get_current_working_image(session_id)
        print(f"   Session lookup result: {working_image}")
        print()
    
    print("=== Testing with working image (normal session) ===\n")
    
    # Now test with a working image to show it works correctly
    session_manager.set_current_working_image(
        session_id=session_id,
        image_url="https://example.com/test_working_image.jpg",
        user_id=user_id
    )
    
    print("Set working image in session, testing same prompts:\n")
    
    for i, prompt in enumerate(editing_prompts[:3], 1):  # Test first 3
        print(f"{i}. Testing: '{prompt}'")
        
        # Get working image from session
        current_working_image = session_manager.get_current_working_image(session_id)
        
        result = await parser.analyze_intent(
            prompt=prompt,
            uploaded_images=None,
            current_working_image=current_working_image,
            generation_id=f"test_gen_with_image_{i}"
        )
        
        print(f"   Result: {result.detected_intent.value} (confidence: {result.confidence})")
        print(f"   Model: {result.suggested_model}")
        print(f"   Working image: {current_working_image}")
        print()
    
    # Clean up
    session_manager.clear_session(session_id)
    print("✅ Test completed and session cleaned up")

if __name__ == "__main__":
    asyncio.run(test_session_loss_detection()) 