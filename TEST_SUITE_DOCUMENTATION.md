# Enhanced Comprehensive Flow Validation Test Suite

## Overview

This enhanced test suite validates the `simplified_flow_service` with comprehensive scenarios testing **both LLM classification and fallback methods**. It ensures robustness of the AI model routing system under all conditions.

## 🎯 What This Test Suite Validates

### 1. LLM Classification Testing
- **Claude 3.7 Sonnet** intent classification via Replicate API
- Prompt enhancement quality
- Model routing decisions based on LLM analysis
- Performance metrics for AI-powered classification

### 2. Fallback Classification Testing  
- Rule-based classification when LLM is unavailable
- Circuit breaker behavior during API failures
- Fallback logic accuracy for all workflow types
- Resilience and error handling

### 3. Comprehensive Workflow Coverage
- **Image Generation**: NEW_IMAGE, NEW_IMAGE_REF, EDIT_IMAGE, EDIT_IMAGE_REF
- **Video Generation**: NEW_VIDEO, IMAGE_TO_VIDEO, with/without audio
- **Special Rules**: 2+ reference routing to Runway
- **Edge Cases**: Ambiguous prompts, complex scenarios

## 📁 Test Files

### Core Test Files
1. **`test_comprehensive_flow_validation_enhanced.py`** - Main enhanced test suite
2. **`run_comprehensive_tests.sh`** - Test runner script with multiple modes
3. **`.env.test`** - Environment configuration template

### Legacy Test File (Fallback Only)
- **`test_comprehensive_flow_validation.py`** - Original fallback-only test

## 🚀 Usage

### Quick Start
```bash
# Run with default settings (both LLM + fallback if API key available)
./run_comprehensive_tests.sh

# Test only fallback classification
./run_comprehensive_tests.sh fallback

# Test only LLM classification (requires API key)
./run_comprehensive_tests.sh llm
```

### Environment Setup
1. **Copy configuration template:**
   ```bash
   cp .env.test .env
   ```

2. **Set required environment variables in `.env`:**
   ```bash
   # Required for LLM testing
   REPLICATE_API_TOKEN=your_replicate_token_here
   
   # Required for database operations
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_KEY=your_supabase_key_here
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
   
   # Test mode (optional)
   TEST_MODE=both  # Options: llm, fallback, both
   ```

3. **Run tests:**
   ```bash
   ./run_comprehensive_tests.sh
   ```

## 📊 Test Scenarios (26 Total)

### Image Generation Flows
- **NEW_IMAGE** (3 scenarios): Basic image generation → `black-forest-labs/flux-1.1-pro`
- **NEW_IMAGE_REF** (3 scenarios): Image with references → `runway_gen4_image`
- **EDIT_IMAGE** (4 scenarios): Working image editing → `black-forest-labs/flux-kontext-max`
- **EDIT_IMAGE_REF** (3 scenarios): Working image + references → `runway_gen4_image`

### Video Generation Flows
- **NEW_VIDEO** (2 scenarios): Text-to-video → `minimax/video-01`
- **NEW_VIDEO_WITH_AUDIO** (2 scenarios): Text-to-video with audio → `google/veo-3`
- **IMAGE_TO_VIDEO** (2 scenarios): Image animation → `minimax/video-01`
- **IMAGE_TO_VIDEO_WITH_AUDIO** (2 scenarios): Image animation with audio → `minimax/video-01`
- **EDIT_IMAGE_REF_TO_VIDEO** (2 scenarios): Reference-based video → `minimax/video-01`

### Edge Cases & Complex Scenarios
- **Complex Logic** (3 scenarios): Ambiguous prompts, multiple references, etc.

## 🔍 Test Results & Analysis

### Generated Artifacts
Each test run generates:
- **`enhanced_test_results_[timestamp].json`** - Detailed JSON results
- **`enhanced_test_report_[timestamp].txt`** - Human-readable report

### Key Metrics Tracked
- **Success Rate**: Percentage of correct classifications
- **Processing Time**: Response time for each method
- **Cache Performance**: Cache hit rates
- **Circuit Breaker State**: Fallback trigger behavior
- **Agreement Rate**: LLM vs Fallback consistency

### Success Thresholds
- **LLM Classification**: ≥90% success rate
- **Fallback Classification**: ≥85% success rate
- **Overall System**: Both methods must meet thresholds

## 📝 Sample Test Report Output

```
=== ENHANCED COMPREHENSIVE FLOW VALIDATION REPORT ===
Generated: 2025-06-16 05:47:01

TEST CONFIGURATION:
------------------
Total Scenarios: 26
Test Mode: both
API Key Available: true
Execution Time: 0:00:12.345678

LLM CLASSIFICATION RESULTS:
---------------------------
Tests Run: 26
Passed: 24
Failed: 2
Success Rate: 92.3%
Average Processing Time: 1,250.5ms
Cache Hits: 3

FALLBACK CLASSIFICATION RESULTS:
--------------------------------
Tests Run: 26
Passed: 21
Failed: 5
Success Rate: 80.8%
Average Processing Time: 134.4ms

LLM vs FALLBACK COMPARISON:
--------------------------
Total Compared: 26
Agreements: 21
Disagreements: 5
Agreement Rate: 80.8%
```

## 🛠️ Key Features

### 1. Dual Classification Testing
- Tests both AI-powered and rule-based classification
- Compares results between methods
- Identifies consistency and disagreements

### 2. Circuit Breaker Simulation
- Forces circuit breaker open for fallback testing
- Validates graceful degradation
- Tests error recovery behavior

### 3. Performance Analysis
- Measures processing time for each method
- Tracks cache hit rates
- Monitors system behavior under load

### 4. Comprehensive Logging
- Detailed reasoning for each classification
- Enhanced prompt outputs
- Error tracking and categorization

## 🔧 Test Modes

### Mode: `llm`
- Tests only LLM classification
- Requires `REPLICATE_API_TOKEN`
- Validates AI-powered intent detection
- Measures prompt enhancement quality

### Mode: `fallback`
- Tests only fallback classification
- Forces circuit breaker open
- Validates rule-based classification
- Tests system resilience

### Mode: `both` (Default)
- Tests both methods sequentially
- Compares results for consistency
- Provides comprehensive system validation
- Identifies optimal classification strategy

## 🎯 Validation Criteria

### Model Routing Validation
- ✅ Correct model selection for each workflow type
- ✅ Special 2+ reference routing to Runway
- ✅ Audio detection for video flows
- ✅ Fallback model mapping accuracy

### Prompt Enhancement Validation
- ✅ LLM-generated enhancements are contextually appropriate
- ✅ Fallback enhancements follow template patterns
- ✅ Enhanced prompts maintain original intent
- ✅ Reference handling (@working_image, @reference_1, etc.)

### System Behavior Validation
- ✅ Circuit breaker opens after failures
- ✅ Graceful fallback when LLM unavailable
- ✅ Cache performance optimization
- ✅ Error handling and recovery

## 🚨 Troubleshooting

### Common Issues

1. **"No API key" Error**
   - Set `REPLICATE_API_TOKEN` in `.env`
   - Use `fallback` mode for testing without API

2. **Database Connection Errors**
   - Set `SUPABASE_URL` and `SUPABASE_KEY`
   - Tests will use fallback database client

3. **Low Success Rates**
   - Check video keyword detection logic
   - Verify edit keyword patterns
   - Review CSV rule implementation

### Debug Mode
```bash
# Enable debug logging
export PYTHONPATH=/workspaces/picarcade
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
TEST_MODE=fallback python test_comprehensive_flow_validation_enhanced.py
```

## 📈 Performance Benchmarks

### Expected Performance
- **LLM Classification**: ~1,000-2,000ms per request
- **Fallback Classification**: ~50-200ms per request
- **Cache Hit Rate**: 10-30% (depends on similar prompts)
- **Overall Success Rate**: 85-95%

### Optimization Opportunities
- Cache frequently used classifications
- Optimize video keyword detection
- Improve edit intent recognition
- Fine-tune model routing rules

## 🔄 Continuous Improvement

### Regular Testing
- Run test suite after any classification logic changes
- Validate both methods maintain performance
- Monitor agreement rate between LLM and fallback
- Update test scenarios for new workflow types

### Test Expansion
- Add new edge cases as they're discovered
- Include performance regression tests
- Test with different LLM models
- Validate prompt enhancement quality

This enhanced test suite provides comprehensive validation of the AI model routing system, ensuring robust performance in both optimal (LLM available) and degraded (fallback only) conditions.