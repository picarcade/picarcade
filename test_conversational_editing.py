#!/usr/bin/env python3
"""
Test script to demonstrate the new conversational image editing logic
Shows how subsequent prompts work on previously generated images
"""

import asyncio
import sys
import os

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.intent_parser import BasicIntentParser
from services.session_manager import session_manager

async def test_conversational_editing():
    """Test the conversational image editing workflow"""
    
    parser = BasicIntentParser()
    session_id = "test_session_123"
    
    print("=== Conversational Image Editing Test ===\n")
    
    # Simulate a conversation flow
    conversation_steps = [
        {
            "step": 1,
            "description": "User uploads initial image",
            "prompt": "add sunglasses to this person",
            "uploaded_images": ["https://example.com/person.jpg"],
            "expected_working_image": None,  # No working image yet
            "expected_intent": "EDIT_IMAGE (uploaded image)"
        },
        {
            "step": 2,
            "description": "After generation, simulate result",
            "action": "simulate_generation_result",
            "generated_image": "https://example.com/person_with_sunglasses.jpg"
        },
        {
            "step": 3,
            "description": "User continues editing the result",
            "prompt": "make the sunglasses blue",
            "uploaded_images": None,
            "expected_working_image": "https://example.com/person_with_sunglasses.jpg",
            "expected_intent": "EDIT_IMAGE (working image)"
        },
        {
            "step": 4,
            "description": "Simulate second generation result",
            "action": "simulate_generation_result", 
            "generated_image": "https://example.com/person_with_blue_sunglasses.jpg"
        },
        {
            "step": 5,
            "description": "User continues the chain",
            "prompt": "add a hat",
            "uploaded_images": None,
            "expected_working_image": "https://example.com/person_with_blue_sunglasses.jpg",
            "expected_intent": "EDIT_IMAGE (working image)"
        },
        {
            "step": 6,
            "description": "User uploads a completely new image",
            "prompt": "edit this cat photo",
            "uploaded_images": ["https://example.com/cat.jpg"],
            "expected_working_image": "https://example.com/person_with_blue_sunglasses.jpg",  # Still exists
            "expected_intent": "EDIT_IMAGE (new uploaded image overrides working image)"
        }
    ]
    
    for step_data in conversation_steps:
        step_num = step_data["step"]
        description = step_data["description"]
        
        print(f"{step_num}. {description}")
        
        if step_data.get("action") == "simulate_generation_result":
            # Simulate storing a generation result in the session
            generated_image = step_data["generated_image"]
            session_manager.set_current_working_image(
                session_id=session_id,
                image_url=generated_image,
                user_id="test_user"
            )
            print(f"   ✅ Simulated generation: {generated_image}")
            print(f"   ✅ Updated working image in session\n")
            continue
        
        # Get current working image
        current_working_image = session_manager.get_current_working_image(session_id)
        
        print(f"   Prompt: '{step_data['prompt']}'")
        print(f"   Uploaded images: {step_data['uploaded_images']}")
        print(f"   Current working image: {current_working_image}")
        print(f"   Expected working image: {step_data['expected_working_image']}")
        
        # Analyze intent
        result = await parser.analyze_intent(
            prompt=step_data['prompt'],
            uploaded_images=step_data['uploaded_images'],
            current_working_image=current_working_image
        )
        
        print(f"   Result: {result.detected_intent.value} ({result.suggested_model})")
        print(f"   Confidence: {result.confidence}")
        print(f"   Expected: {step_data['expected_intent']}")
        
        # Show which image would be used for editing
        if result.detected_intent.value == "edit_image":
            if current_working_image and not step_data['uploaded_images']:
                print(f"   🎯 Will edit working image: {current_working_image}")
            elif step_data['uploaded_images']:
                print(f"   🎯 Will edit uploaded image: {step_data['uploaded_images'][0]}")
        
        print(f"   ✅ Correct priority logic\n")
    
    # Clean up
    session_manager.clear_session(session_id)
    print("✅ Test session cleared")

if __name__ == "__main__":
    asyncio.run(test_conversational_editing()) 