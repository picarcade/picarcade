#!/usr/bin/env python3
"""
Quick test to verify the reference parsing fix works correctly
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.reference_service import ReferenceService
from app.models.generation import ReferenceImage

async def test_reference_parsing():
    """Test that both user references and working images are properly handled"""
    
    print("=== Testing Reference Parsing Fix ===")
    
    # Mock data
    user_id = "test_user_123"
    prompt = "Add @james to the balloon"
    working_image_url = "https://example.com/balloon.jpg"
    
    print(f"Original prompt: {prompt}")
    print(f"Working image: {working_image_url}")
    
    try:
        # Test the enhanced prompt with working image function
        enhanced_prompt, references = await ReferenceService.enhance_prompt_with_working_image(
            prompt, user_id, working_image_url
        )
        
        print(f"\nEnhanced prompt: {enhanced_prompt}")
        print(f"Total references found: {len(references)}")
        
        for i, ref in enumerate(references):
            print(f"  Reference {i+1}: @{ref.tag} -> {ref.uri}")
        
        # Check if we have both james and working image references
        james_refs = [ref for ref in references if ref.tag == "james"]
        working_refs = [ref for ref in references if "working" in ref.tag.lower()]
        
        print(f"\nJames references: {len(james_refs)}")
        print(f"Working image references: {len(working_refs)}")
        
        if len(references) >= 1:
            print("✅ SUCCESS: At least one reference found")
            if len(working_refs) >= 1:
                print("✅ SUCCESS: Working image reference created")
            else:
                print("❌ ISSUE: No working image reference found")
        else:
            print("❌ ISSUE: No references found at all")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reference_parsing()) 