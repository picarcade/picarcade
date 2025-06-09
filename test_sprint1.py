#!/usr/bin/env python3
"""
Sprint 1 Test Script - AI Intent Classification

This script tests the new AI-powered intent classification system 
and compares it with the existing system.
"""

import asyncio
import requests
import json
from typing import Dict, Any

# Test prompts for different workflow types
TEST_PROMPTS = [
    # Hair styling tests
    "change my hair to blonde with bangs",
    "give me a bob haircut",
    "make my hair curly and brown",
    
    # Video generation tests  
    "create a video of waves crashing with ocean sounds",
    "animate this sunset image",
    "make a movie clip of a cat playing",
    
    # Image editing tests
    "edit this image to add a hat",
    "change the background to a beach",
    "remove the person from this photo",
    
    # Reference styling tests
    "put @sarah in this red dress",
    "style me like Taylor Swift at the Grammy awards",
    "virtual try-on this outfit",
    
    # Image enhancement tests
    "enhance this image quality",
    "upscale and sharpen this photo",
    "improve the resolution",
    
    # Style transfer tests
    "turn this into a painting",
    "make it look like a sketch",
    "artistic watercolor style"
]

BASE_URL = "http://localhost:8000"

async def test_ai_classification():
    """Test the AI classification service directly"""
    print("🧪 Testing AI Intent Classification Service...")
    
    from app.services.intent_classifier import IntentClassifier
    
    classifier = IntentClassifier()
    
    for prompt in TEST_PROMPTS[:5]:  # Test first 5 prompts
        try:
            result = await classifier.classify_intent(prompt)
            print(f"\n📝 Prompt: '{prompt}'")
            print(f"🎯 Workflow: {result.workflow_type.value}")
            print(f"🎲 Confidence: {result.confidence:.2f}")
            print(f"💭 Reasoning: {result.reasoning}")
            
            if result.enhancement_needed:
                print(f"⚡ Enhancement needed: {result.enhancement_needed}")
            
        except Exception as e:
            print(f"❌ Error testing prompt '{prompt}': {e}")

def test_api_endpoints():
    """Test the enhanced API endpoints"""
    print("\n\n🌐 Testing Enhanced API Endpoints...")
    
    # Test data
    test_requests = [
        {
            "prompt": "change my hair to blonde with bangs",
            "use_ai_classification": True
        },
        {
            "prompt": "create a video of sunset with music", 
            "user_preferences": {"quality": "balanced"},
            "use_ai_classification": True
        },
        {
            "prompt": "enhance this image",
            "working_image_url": "https://example.com/test.jpg",
            "use_ai_classification": True
        }
    ]
    
    for i, request_data in enumerate(test_requests):
        print(f"\n🧪 Test {i+1}: {request_data['prompt']}")
        
        try:
            # Test enhanced processing
            response = requests.post(
                f"{BASE_URL}/api/v1/enhanced/process",
                json=request_data,
                headers={"Authorization": "Bearer test-token"}  # You'll need proper auth
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success!")
                print(f"🎯 Workflow: {result.get('workflow_type')}")
                print(f"🤖 Model: {result.get('model_selection', {}).get('model_id')}")
                print(f"🎲 Confidence: {result.get('intent_confidence')}")
                print(f"⏱️ Processing time: {result.get('processing_time', 0):.3f}s")
            else:
                print(f"❌ API Error {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")

def test_comparison_endpoint():
    """Test the comparison endpoint (AI vs existing system)"""
    print("\n\n⚖️ Testing AI vs Existing System Comparison...")
    
    comparison_prompts = [
        "change my hair color to red",
        "create a video of a dog running", 
        "edit this photo to add sunglasses"
    ]
    
    for prompt in comparison_prompts:
        print(f"\n🔄 Comparing: '{prompt}'")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/enhanced/compare",
                json={"prompt": prompt, "use_ai_classification": True},
                headers={"Authorization": "Bearer test-token"}
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_result = result.get("ai_classification", {})
                existing_result = result.get("existing_system", {})
                differences = result.get("differences", {})
                
                print(f"🤖 AI System: {ai_result.get('workflow_type')} (confidence: {ai_result.get('intent_confidence', 0):.2f})")
                print(f"🔧 Existing: {existing_result.get('workflow_type')} (confidence: {existing_result.get('confidence', 0):.2f})")
                
                if any(differences.values()):
                    print(f"🔍 Differences: {differences}")
                else:
                    print("✅ Both systems agree!")
                    
            else:
                print(f"❌ Comparison failed {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Comparison request failed: {e}")

def test_metrics():
    """Test the metrics endpoint"""
    print("\n\n📊 Testing Metrics Endpoint...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/enhanced/metrics",
            headers={"Authorization": "Bearer test-token"}
        )
        
        if response.status_code == 200:
            metrics = response.json()
            print("📈 Performance Metrics:")
            print(f"   Total Classifications: {metrics.get('classifications', 0)}")
            print(f"   Cache Hit Rate: {metrics.get('cache_hit_rate', 0):.2%}")
            print(f"   Error Rate: {metrics.get('error_rate', 0):.2%}")
            print(f"   Fallbacks Used: {metrics.get('fallbacks', 0)}")
        else:
            print(f"❌ Metrics request failed {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Metrics request failed: {e}")

async def main():
    """Run all Sprint 1 tests"""
    print("🚀 Sprint 1 - AI Intent Classification Testing")
    print("=" * 50)
    
    # Test 1: Direct AI classification
    await test_ai_classification()
    
    # Test 2: API endpoints (requires running server)
    try:
        # Quick health check
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            test_api_endpoints()
            test_comparison_endpoint() 
            test_metrics()
        else:
            print("\n⚠️ Server not running - skipping API tests")
            print("💡 Start server with: uvicorn app.main:app --reload")
    except Exception:
        print("\n⚠️ Server not accessible - skipping API tests")
        print("💡 Start server with: uvicorn app.main:app --reload")
    
    print("\n✨ Sprint 1 testing complete!")
    print("\n📋 Next Steps:")
    print("1. Review test results above")
    print("2. Test via frontend integration")
    print("3. Monitor performance metrics")
    print("4. Prepare for Sprint 2 enhancements")

if __name__ == "__main__":
    asyncio.run(main()) 