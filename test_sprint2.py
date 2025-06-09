#!/usr/bin/env python3
"""
Sprint 2 Test Suite: Enhanced Model Selection & Virtual Try-on
Tests the new virtual try-on capabilities, web search integration, and enhanced model selection
"""

import asyncio
import json
import time
from typing import Dict, Any, List
import os
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.enhanced_workflow_service import EnhancedWorkflowService
from app.services.web_search_service import WebSearchService
from app.services.model_selector import ModelSelector
from app.services.intent_classifier import IntentClassifier
from app.models.workflows import WorkflowType

class Sprint2TestSuite:
    """Comprehensive test suite for Sprint 2 features"""
    
    def __init__(self):
        self.enhanced_service = EnhancedWorkflowService()
        self.web_search_service = WebSearchService()
        self.model_selector = ModelSelector()
        self.intent_classifier = IntentClassifier()
        
        self.test_results = []
        self.passed_tests = 0
        self.failed_tests = 0
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
    
    async def test_virtual_tryon_detection(self):
        """Test virtual try-on intent detection"""
        print("\n🧪 Testing Virtual Try-on Detection...")
        
        virtual_tryon_prompts = [
            "put @sarah in this red dress",
            "try on this outfit",
            "dress like taylor swift at the grammy",
            "wear this designer jacket",
            "put me in a met gala outfit",
            "style like beyonce"
        ]
        
        for prompt in virtual_tryon_prompts:
            try:
                intent = await self.intent_classifier.classify_intent(prompt)
                
                is_reference_styling = intent.workflow_type == WorkflowType.REFERENCE_STYLING
                self.log_test(
                    f"Virtual try-on detection: '{prompt[:30]}...'",
                    is_reference_styling,
                    f"Detected: {intent.workflow_type.value}, Confidence: {intent.confidence:.2f}"
                )
                
            except Exception as e:
                self.log_test(
                    f"Virtual try-on detection: '{prompt[:30]}...'",
                    False,
                    f"Error: {e}"
                )
    
    async def test_web_search_detection(self):
        """Test web search requirement detection"""
        print("\n🔍 Testing Web Search Detection...")
        
        search_prompts = [
            ("taylor swift grammy outfit", True),
            ("met gala dress inspiration", True),
            ("coachella festival style", True),
            ("red carpet fashion", True),
            ("simple portrait photo", False),
            ("change hair color to blonde", False)
        ]
        
        for prompt, should_search in search_prompts:
            try:
                should_search_result, search_query = await self.web_search_service.should_search_for_reference(
                    prompt, {}
                )
                
                correct_detection = should_search_result == should_search
                self.log_test(
                    f"Web search detection: '{prompt}'",
                    correct_detection,
                    f"Expected: {should_search}, Got: {should_search_result}, Query: {search_query}"
                )
                
            except Exception as e:
                self.log_test(
                    f"Web search detection: '{prompt}'",
                    False,
                    f"Error: {e}"
                )
    
    async def test_enhanced_model_selection(self):
        """Test enhanced model selection with Sprint 2 improvements"""
        print("\n🎯 Testing Enhanced Model Selection...")
        
        test_cases = [
            {
                "workflow": WorkflowType.REFERENCE_STYLING,
                "expected_model": "flux-kontext-apps/multi-image-kontext-max",
                "context": {"working_images": ["test.jpg"]},
                "preferences": {"quality": "balanced"}
            },
            {
                "workflow": WorkflowType.VIDEO_GENERATION,
                "expected_model": "google/veo-3",
                "context": {},
                "preferences": {"quality": "quality"}
            },
            {
                "workflow": WorkflowType.IMAGE_TO_VIDEO,
                "expected_model": "lightricks/ltx-video",
                "context": {"working_images": ["test.jpg"]},
                "preferences": {"quality": "speed"}
            },
            {
                "workflow": WorkflowType.HAIR_STYLING,
                "expected_model": "flux-kontext-apps/change-haircut",
                "context": {},
                "preferences": {"quality": "balanced"}
            }
        ]
        
        for case in test_cases:
            try:
                # Create mock intent
                from app.models.workflows import IntentClassification
                intent = IntentClassification(
                    workflow_type=case["workflow"],
                    confidence=0.9,
                    reasoning="Test intent"
                )
                
                model_selection = self.model_selector.select_model(
                    intent, case["preferences"], case["context"]
                )
                
                correct_model = case["expected_model"] in model_selection.model_id
                self.log_test(
                    f"Model selection for {case['workflow'].value}",
                    correct_model,
                    f"Expected: {case['expected_model']}, Got: {model_selection.model_id}"
                )
                
            except Exception as e:
                self.log_test(
                    f"Model selection for {case['workflow'].value}",
                    False,
                    f"Error: {e}"
                )
    
    async def test_video_workflow_optimization(self):
        """Test Sprint 2 video workflow optimizations"""
        print("\n🎬 Testing Video Workflow Optimization...")
        
        video_test_cases = [
            {
                "prompt": "create a cinematic video with soundtrack",
                "expected_workflow": WorkflowType.VIDEO_GENERATION,
                "expected_features": ["audio_support", "high_quality"]
            },
            {
                "prompt": "animate this photo",
                "expected_workflow": WorkflowType.IMAGE_TO_VIDEO,
                "expected_features": ["image_animation", "cost_effective"]
            },
            {
                "prompt": "make a simple video of a sunset",
                "expected_workflow": WorkflowType.TEXT_TO_VIDEO,
                "expected_features": ["text_based", "affordable"]
            }
        ]
        
        for case in video_test_cases:
            try:
                intent = await self.intent_classifier.classify_intent(case["prompt"])
                
                correct_workflow = intent.workflow_type == case["expected_workflow"]
                self.log_test(
                    f"Video workflow detection: '{case['prompt'][:30]}...'",
                    correct_workflow,
                    f"Expected: {case['expected_workflow'].value}, Got: {intent.workflow_type.value}"
                )
                
                # Test model capabilities
                capabilities = self.model_selector.get_model_capabilities(intent.workflow_type)
                has_expected_features = any(
                    feature in capabilities.get("features", []) 
                    for feature in case["expected_features"]
                )
                
                self.log_test(
                    f"Video model features for {intent.workflow_type.value}",
                    has_expected_features,
                    f"Features: {capabilities.get('features', [])}"
                )
                
            except Exception as e:
                self.log_test(
                    f"Video workflow test: '{case['prompt'][:30]}...'",
                    False,
                    f"Error: {e}"
                )
    
    async def test_cost_estimation(self):
        """Test Sprint 2 cost estimation improvements"""
        print("\n💰 Testing Cost Estimation...")
        
        workflows_to_test = [
            WorkflowType.REFERENCE_STYLING,
            WorkflowType.VIDEO_GENERATION,
            WorkflowType.IMAGE_TO_VIDEO,
            WorkflowType.HAIR_STYLING
        ]
        
        for workflow in workflows_to_test:
            try:
                cost_estimates = self.model_selector.estimate_cost_range(workflow)
                
                has_all_profiles = all(
                    profile in cost_estimates 
                    for profile in ["speed", "balanced", "quality"]
                )
                
                reasonable_costs = all(
                    0.01 <= cost <= 10.0 
                    for cost in cost_estimates.values()
                )
                
                self.log_test(
                    f"Cost estimation for {workflow.value}",
                    has_all_profiles and reasonable_costs,
                    f"Estimates: {cost_estimates}"
                )
                
            except Exception as e:
                self.log_test(
                    f"Cost estimation for {workflow.value}",
                    False,
                    f"Error: {e}"
                )
    
    async def test_end_to_end_virtual_tryon(self):
        """Test complete virtual try-on workflow"""
        print("\n🎭 Testing End-to-End Virtual Try-on...")
        
        test_scenarios = [
            {
                "prompt": "put @sarah in taylor swift's grammy dress",
                "working_image": "https://example.com/person.jpg",
                "expected_web_search": True,
                "expected_model": "multi-image-kontext-max"
            },
            {
                "prompt": "try on this red carpet outfit",
                "working_image": "https://example.com/person.jpg",
                "expected_web_search": True,
                "expected_model": "multi-image-kontext-max"
            }
        ]
        
        for scenario in test_scenarios:
            try:
                result = await self.enhanced_service.process_request(
                    prompt=scenario["prompt"],
                    user_id="test_user",
                    working_image_url=scenario["working_image"],
                    user_preferences={"quality": "balanced"}
                )
                
                # Check workflow type
                is_reference_styling = result["workflow_type"] == "reference_styling"
                
                # Check model selection
                correct_model = scenario["expected_model"] in result["model_selection"]["model_id"]
                
                # Check web search
                web_search_used = result["metadata"].get("requires_web_search", False)
                correct_web_search = web_search_used == scenario["expected_web_search"]
                
                overall_success = is_reference_styling and correct_model and correct_web_search
                
                self.log_test(
                    f"End-to-end virtual try-on: '{scenario['prompt'][:30]}...'",
                    overall_success,
                    f"Workflow: {result['workflow_type']}, Model: {result['model_selection']['model_id']}, Web search: {web_search_used}"
                )
                
            except Exception as e:
                self.log_test(
                    f"End-to-end virtual try-on: '{scenario['prompt'][:30]}...'",
                    False,
                    f"Error: {e}"
                )
    
    async def test_performance_metrics(self):
        """Test Sprint 2 performance metrics"""
        print("\n📊 Testing Performance Metrics...")
        
        try:
            # Generate some activity
            await self.enhanced_service.process_request(
                "test prompt for metrics",
                "test_user"
            )
            
            metrics = self.enhanced_service.get_metrics()
            
            # Check for Sprint 2 metrics
            has_web_search_metrics = "web_search_rate" in metrics
            has_cache_stats = "web_search_cache_stats" in metrics
            has_basic_metrics = all(
                key in metrics for key in ["classifications", "cache_hit_rate", "error_rate"]
            )
            
            self.log_test(
                "Performance metrics collection",
                has_web_search_metrics and has_cache_stats and has_basic_metrics,
                f"Metrics keys: {list(metrics.keys())}"
            )
            
        except Exception as e:
            self.log_test(
                "Performance metrics collection",
                False,
                f"Error: {e}"
            )
    
    async def run_all_tests(self):
        """Run all Sprint 2 tests"""
        print("🚀 Starting Sprint 2 Test Suite")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run all test categories
        await self.test_virtual_tryon_detection()
        await self.test_web_search_detection()
        await self.test_enhanced_model_selection()
        await self.test_video_workflow_optimization()
        await self.test_cost_estimation()
        await self.test_end_to_end_virtual_tryon()
        await self.test_performance_metrics()
        
        end_time = time.time()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📋 Sprint 2 Test Summary")
        print("=" * 50)
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"📊 Total: {self.passed_tests + self.failed_tests}")
        print(f"⏱️  Duration: {end_time - start_time:.2f}s")
        
        success_rate = self.passed_tests / (self.passed_tests + self.failed_tests) * 100
        print(f"🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n🎉 Sprint 2 implementation is ready for deployment!")
        elif success_rate >= 60:
            print("\n⚠️  Sprint 2 needs some fixes before deployment")
        else:
            print("\n🚨 Sprint 2 requires significant fixes")
        
        return success_rate >= 80

async def main():
    """Main test runner"""
    
    # Check environment
    required_env_vars = ["OPENAI_API_KEY", "REPLICATE_API_TOKEN"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please set these variables before running tests")
        return False
    
    # Run tests
    test_suite = Sprint2TestSuite()
    success = await test_suite.run_all_tests()
    
    # Save detailed results
    with open("sprint2_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "passed": test_suite.passed_tests,
                "failed": test_suite.failed_tests,
                "success_rate": test_suite.passed_tests / (test_suite.passed_tests + test_suite.failed_tests) * 100,
                "timestamp": time.time()
            },
            "detailed_results": test_suite.test_results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to sprint2_test_results.json")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 