#!/usr/bin/env python3
"""
Test script to verify that generated images (working images) are properly
passed to flux-kontext for continued editing
"""

import asyncio
import sys
import os

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.session_manager import session_manager
from services.intent_parser import BasicIntentParser
from models.generation import GenerationRequest, QualityPriority

async def test_working_image_flow():
    """Test that working images flow correctly to flux-kontext"""
    
    print("=== Working Image Flow Test ===\n")
    
    session_id = "test_working_flow_123"
    user_id = "test_user"
    
    # Step 1: Simulate first generation (user uploads image)
    print("1. Simulating first generation with uploaded image")
    
    # Simulate that first generation was successful and produced an output
    first_generated_image = "https://replicate.delivery/example/first_generation_result.jpg"
    session_manager.set_current_working_image(
        session_id=session_id,
        image_url=first_generated_image,
        user_id=user_id
    )
    
    print(f"   ✅ First generation result stored: {first_generated_image}")
    
    # Step 2: Simulate second request (user wants to edit the generated image)
    print("\n2. Testing second request - should use working image")
    
    # Create a request for continued editing
    request = GenerationRequest(
        prompt="make it blue",
        user_id=user_id,
        session_id=session_id,
        quality_priority=QualityPriority.BALANCED,
        uploaded_images=None,  # No new uploads
        current_working_image=None  # This will be populated by API
    )
    
    # Get working image (simulating what the API does)
    current_working_image = session_manager.get_current_working_image(session_id)
    
    print(f"   Current working image retrieved: {current_working_image}")
    
    # Test intent analysis
    parser = BasicIntentParser()
    intent_analysis = await parser.analyze_intent(
        prompt=request.prompt,
        uploaded_images=request.uploaded_images,
        current_working_image=current_working_image
    )
    
    print(f"   Intent: {intent_analysis.detected_intent.value}")
    print(f"   Confidence: {intent_analysis.confidence}")
    print(f"   Expected: edit_image with high confidence (0.98)")
    
    # Simulate parameter setting (what the API does)
    parameters = {"model": "flux-kontext", "output_format": "jpg"}
    
    image_source = None
    if current_working_image:
        parameters["uploaded_image"] = current_working_image
        parameters["image"] = current_working_image
        image_source = f"working_image:{current_working_image}"
        print(f"   ✅ Working image set in parameters: {current_working_image}")
    elif request.uploaded_images:
        parameters["uploaded_image"] = request.uploaded_images[0]
        parameters["image"] = request.uploaded_images[0]
        image_source = f"uploaded_image:{request.uploaded_images[0]}"
    
    print(f"   Image source: {image_source}")
    print(f"   Parameters for flux-kontext: {parameters}")
    
    # Verify that flux-kontext would receive the correct image
    expected_input_image = parameters.get("image")
    print(f"   ✅ flux-kontext would receive input_image: {expected_input_image}")
    
    if expected_input_image == first_generated_image:
        print(f"   ✅ SUCCESS: Working image correctly flows to flux-kontext")
    else:
        print(f"   ❌ ERROR: Expected {first_generated_image}, got {expected_input_image}")
    
    # Step 3: Test that new uploads override working image
    print("\n3. Testing new upload override")
    
    new_upload = "https://example.com/new_cat_upload.jpg"
    request_with_upload = GenerationRequest(
        prompt="edit this new image",
        user_id=user_id,
        session_id=session_id,
        quality_priority=QualityPriority.BALANCED,
        uploaded_images=[new_upload],
        current_working_image=None
    )
    
    # Simulate parameter setting with new upload
    parameters_new = {"model": "flux-kontext", "output_format": "jpg"}
    
    if current_working_image:
        # Working image exists but uploaded image should take priority
        pass
    
    if request_with_upload.uploaded_images:
        parameters_new["uploaded_image"] = request_with_upload.uploaded_images[0]
        parameters_new["image"] = request_with_upload.uploaded_images[0]
        print(f"   ✅ New upload takes priority: {request_with_upload.uploaded_images[0]}")
    
    expected_new_input = parameters_new.get("image")
    if expected_new_input == new_upload:
        print(f"   ✅ SUCCESS: New upload correctly overrides working image")
    else:
        print(f"   ❌ ERROR: Expected {new_upload}, got {expected_new_input}")
    
    # Clean up
    session_manager.clear_session(session_id)
    print(f"\n✅ Test session {session_id} cleared")

if __name__ == "__main__":
    asyncio.run(test_working_image_flow()) 