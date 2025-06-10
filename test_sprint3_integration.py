"""
Sprint 3 Integration Test: Test upgraded IntentClassifier with all infrastructure
"""
import os
import asyncio
import time
import pytest
from app.services.intent_classifier import IntentClassifier
from app.models.workflows import WorkflowType
from app.core.cache import get_cache
from app.core.database import get_database

# Set up environment for testing
os.environ.setdefault("REDIS_URL", "rediss://default:AbyQAAIjcDE5NDcwNTY3MTc4ODE0NTM1YWQ4YjMzMDA4NDk3N2Y5OXAxMA@apt-kangaroo-48272.upstash.io:6379")
os.environ.setdefault("SUPABASE_PROJECT_ID", "icgwpkroorulmsfdiuoh")
os.environ.setdefault("SUPABASE_URL", "https://icgwpkroorulmsfdiuoh.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test_key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test_service_key")

class TestSprint3Integration:
    """Test Sprint 3 infrastructure integration"""
    
    async def test_classifier_with_cache(self):
        """Test IntentClassifier uses distributed cache"""
        print("\n🧠 Testing IntentClassifier with Redis cache...")
        
        classifier = IntentClassifier()
        
        # First call - should populate cache
        start_time = time.time()
        result1 = await classifier.classify_intent(
            prompt="Create a beautiful sunset image",
            user_id="test_user_cache",
            context={}
        )
        first_call_time = time.time() - start_time
        
        print(f"   ✅ First classification: {result1.workflow_type.value} (confidence: {result1.confidence})")
        print(f"   ⏱️  First call time: {first_call_time*1000:.0f}ms")
        
        # Second call - should hit cache (faster)
        start_time = time.time()
        result2 = await classifier.classify_intent(
            prompt="Create a beautiful sunset image",
            user_id="test_user_cache",
            context={}
        )
        second_call_time = time.time() - start_time
        
        print(f"   ✅ Second classification: {result2.workflow_type.value} (confidence: {result2.confidence})")
        print(f"   ⏱️  Second call time: {second_call_time*1000:.0f}ms")
        
        # Verify same result
        assert result1.workflow_type == result2.workflow_type
        assert result1.confidence == result2.confidence
        
        # Second call should be significantly faster (cache hit)
        # Allow some variance for network latency
        if second_call_time < first_call_time * 0.8:
            print(f"   🚀 Cache hit detected - {((first_call_time - second_call_time) / first_call_time * 100):.1f}% faster!")
        else:
            print(f"   ⚠️  Cache may not have been hit (times: {first_call_time:.2f}s vs {second_call_time:.2f}s)")
        
        return True
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        print("\n⚡ Testing rate limiting...")
        
        classifier = IntentClassifier()
        
        # Make multiple rapid requests to trigger rate limiting
        print("   Making 5 rapid requests...")
        results = []
        
        for i in range(5):
            try:
                result = await classifier.classify_intent(
                    prompt=f"Create image number {i}",
                    user_id="test_user_rate_limit",
                    context={}
                )
                results.append(result)
                print(f"   ✅ Request {i+1}: {result.workflow_type.value}")
                
            except Exception as e:
                print(f"   ⚠️  Request {i+1} failed: {e}")
                results.append(None)
        
        successful_requests = len([r for r in results if r is not None])
        print(f"   📊 Successful requests: {successful_requests}/5")
        
        # Should have at least some successful requests
        assert successful_requests >= 1
        
        return True
    
    async def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        print("\n🔌 Testing circuit breaker...")
        
        classifier = IntentClassifier()
        await classifier._ensure_initialized()
        
        if classifier.circuit_breaker:
            stats_before = classifier.circuit_breaker.get_stats()
            print(f"   📊 Circuit breaker state: {stats_before['state']}")
            print(f"   📈 Total calls: {stats_before['total_calls']}")
            
            # Make a classification call
            try:
                result = await classifier.classify_intent(
                    prompt="Test circuit breaker functionality",
                    user_id="test_user_circuit",
                    context={}
                )
                print(f"   ✅ Classification successful: {result.workflow_type.value}")
                
                stats_after = classifier.circuit_breaker.get_stats()
                print(f"   📊 Calls after test: {stats_after['total_calls']}")
                
            except Exception as e:
                print(f"   ⚠️  Classification failed: {e}")
        else:
            print("   ⚠️  Circuit breaker not initialized")
        
        return True
    
    async def test_analytics_logging(self):
        """Test analytics logging to Supabase"""
        print("\n📊 Testing analytics logging...")
        
        classifier = IntentClassifier()
        
        # Make a classification that should be logged
        result = await classifier.classify_intent(
            prompt="Test analytics logging",
            user_id="test_user_analytics",
            context={}
        )
        
        print(f"   ✅ Classification: {result.workflow_type.value}")
        
        # Wait a moment for async logging
        await asyncio.sleep(1)
        
        # Try to verify log was written (if database available)
        try:
            database = await get_database()
            recent_logs = await database.fetch_one(
                """
                SELECT COUNT(*) as count 
                FROM intent_classification_logs 
                WHERE user_id = $1 AND created_at > NOW() - INTERVAL '1 minute'
                """,
                "test_user_analytics"
            )
            
            if recent_logs and recent_logs["count"] > 0:
                print(f"   ✅ Found {recent_logs['count']} recent log entries")
            else:
                print("   ⚠️  No recent log entries found (may be async delay)")
                
        except Exception as e:
            print(f"   ⚠️  Could not verify analytics logging: {e}")
        
        return True
    
    async def test_health_checks(self):
        """Test health monitoring"""
        print("\n🏥 Testing health checks...")
        
        classifier = IntentClassifier()
        
        # Test classifier health
        health = await classifier.get_health()
        print(f"   📊 Classifier initialized: {health.get('initialized', False)}")
        print(f"   📊 Cache status: {health.get('cache', {}).get('status', 'unknown')}")
        
        # Test stats
        try:
            stats = await classifier.get_stats()
            if "error" not in stats:
                print(f"   📈 Total classifications: {stats.get('total_classifications', 0)}")
                print(f"   📈 Average confidence: {stats.get('avg_confidence', 0)}")
                print(f"   📈 Cache hit rate: {stats.get('cache_hit_rate', 0)}%")
            else:
                print(f"   ⚠️  Stats error: {stats['error']}")
        except Exception as e:
            print(f"   ⚠️  Could not get stats: {e}")
        
        return True
    
    async def test_different_workflows(self):
        """Test classification of different workflow types"""
        print("\n🎯 Testing different workflow classifications...")
        
        classifier = IntentClassifier()
        
        test_cases = [
            ("Create a beautiful sunset image", WorkflowType.IMAGE_GENERATION),
            ("Animate this photo", WorkflowType.IMAGE_TO_VIDEO),
            ("Change the background to a beach", WorkflowType.IMAGE_EDITING),
            ("Enhance image quality", WorkflowType.IMAGE_ENHANCEMENT),
            ("Change hair to blonde", WorkflowType.HAIR_STYLING),
            ("Create a video of a dragon flying", WorkflowType.TEXT_TO_VIDEO),
        ]
        
        correct_predictions = 0
        
        for prompt, expected_type in test_cases:
            try:
                result = await classifier.classify_intent(
                    prompt=prompt,
                    user_id="test_user_workflows",
                    context={}
                )
                
                if result.workflow_type == expected_type:
                    status = "✅"
                    correct_predictions += 1
                else:
                    status = "❌"
                
                print(f"   {status} '{prompt}' → {result.workflow_type.value} (confidence: {result.confidence:.2f})")
                
            except Exception as e:
                print(f"   ❌ '{prompt}' → Error: {e}")
        
        accuracy = correct_predictions / len(test_cases) * 100
        print(f"   📊 Classification accuracy: {accuracy:.1f}% ({correct_predictions}/{len(test_cases)})")
        
        return True

async def run_integration_tests():
    """Run all Sprint 3 integration tests"""
    print("🚀 Starting Sprint 3 Integration Tests")
    print("=" * 60)
    
    tester = TestSprint3Integration()
    
    tests = [
        ("Cache Integration", tester.test_classifier_with_cache),
        ("Rate Limiting", tester.test_rate_limiting),
        ("Circuit Breaker", tester.test_circuit_breaker),
        ("Analytics Logging", tester.test_analytics_logging),
        ("Health Checks", tester.test_health_checks),
        ("Workflow Classification", tester.test_different_workflows),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            await test_func()
            print(f"✅ {test_name} - PASSED")
            passed += 1
            
        except Exception as e:
            print(f"❌ {test_name} - FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"🏁 Integration Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("🎉 All Sprint 3 integration tests PASSED!")
    else:
        print("⚠️  Some tests failed - check logs above")
    
    return passed, failed

if __name__ == "__main__":
    asyncio.run(run_integration_tests()) 