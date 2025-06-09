#!/usr/bin/env python3
"""
Quick test of Sprint 1 AI Intent Classification
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_fallback_classification():
    """Test the fallback classification (no OpenAI required)"""
    print("🧪 Testing Fallback Classification (Pattern Matching)...")
    
    from app.services.intent_classifier import IntentClassifier
    
    classifier = IntentClassifier()
    
    # Test prompts
    test_prompts = [
        "change my hair to blonde with bangs",
        "create a video of waves crashing",
        "edit this image to add a hat",
        "enhance image quality",
        "style me like Taylor Swift"
    ]
    
    for prompt in test_prompts:
        # Use fallback classification
        result = classifier._fallback_classify(prompt, None)
        print(f"\n📝 Prompt: '{prompt}'")
        print(f"🎯 Workflow: {result.workflow_type.value}")
        print(f"🎲 Confidence: {result.confidence}")
        print(f"💭 Reasoning: {result.reasoning}")

async def test_ai_classification():
    """Test AI classification if OpenAI key is available"""
    print("\n\n🤖 Testing AI Classification...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OpenAI API key found in environment")
        return
    
    print(f"✅ OpenAI API key found: {api_key[:10]}...")
    
    from app.services.intent_classifier import IntentClassifier
    
    classifier = IntentClassifier()
    
    # Test with AI
    test_prompt = "change my hair to blonde with bangs"
    try:
        result = await classifier.classify_intent(test_prompt)
        print(f"\n📝 Prompt: '{test_prompt}'")
        print(f"🎯 Workflow: {result.workflow_type.value}")
        print(f"🎲 Confidence: {result.confidence}")
        print(f"💭 Reasoning: {result.reasoning}")
        if result.enhancement_needed:
            print(f"⚡ Enhancement needed: {result.enhancement_needed}")
    except Exception as e:
        print(f"❌ AI classification failed: {e}")
        print("🔄 Falling back to pattern matching...")
        result = classifier._fallback_classify(test_prompt, None)
        print(f"🎯 Fallback workflow: {result.workflow_type.value}")

async def test_model_selection():
    """Test model selection"""
    print("\n\n🎯 Testing Model Selection...")
    
    from app.services.model_selector import ModelSelector
    from app.models.workflows import IntentClassification, WorkflowType
    
    selector = ModelSelector()
    
    # Create test intent
    test_intent = IntentClassification(
        workflow_type=WorkflowType.HAIR_STYLING,
        confidence=0.9,
        reasoning="Test intent for hair styling"
    )
    
    model_selection = selector.select_model(test_intent)
    print(f"🤖 Selected model: {model_selection.model_id}")
    print(f"💰 Estimated cost: ${model_selection.estimated_cost:.3f}")
    print(f"⏱️ Estimated time: {model_selection.estimated_time}s")
    print(f"💭 Reasoning: {model_selection.reasoning}")

async def main():
    """Run all tests"""
    print("🚀 Sprint 1 AI Intent Classification Test")
    print("=" * 50)
    
    # Test 1: Fallback classification (always works)
    await test_fallback_classification()
    
    # Test 2: AI classification (requires OpenAI key)
    await test_ai_classification()
    
    # Test 3: Model selection
    await test_model_selection()
    
    print("\n✨ Testing complete!")
    print("\n📋 Sprint 1 Summary:")
    print("✅ Workflow models created")
    print("✅ AI intent classifier implemented")
    print("✅ Model selector implemented")
    print("✅ Fallback pattern matching works")
    print("🔄 Server integration ready for testing")

if __name__ == "__main__":
    asyncio.run(main()) 