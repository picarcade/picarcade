#!/bin/bash

# Comprehensive Flow Validation Test Runner
# This script runs the enhanced test suite in different modes

echo "🔬 Enhanced Comprehensive Flow Validation Test Suite"
echo "=================================================="

# Check if .env file exists
if [ -f ".env" ]; then
    echo "✅ Found .env file"
    source .env
else
    echo "⚠️  No .env file found. Create one based on .env.test for LLM testing"
fi

# Check API key availability
if [ -n "$REPLICATE_API_TOKEN" ]; then
    echo "✅ REPLICATE_API_TOKEN is set - LLM testing available"
    HAS_API_KEY=true
else
    echo "⚠️  REPLICATE_API_TOKEN not set - LLM testing disabled"
    HAS_API_KEY=false
fi

echo ""

# Default test mode
TEST_MODE=${1:-"both"}

case $TEST_MODE in
    "llm")
        if [ "$HAS_API_KEY" = true ]; then
            echo "🧠 Running LLM Classification Tests Only"
            echo "======================================="
            TEST_MODE=llm python test_comprehensive_flow_validation_enhanced.py
        else
            echo "❌ Cannot run LLM tests - No API key available"
            echo "Set REPLICATE_API_TOKEN in .env file"
            exit 1
        fi
        ;;
    "fallback")
        echo "🛡️  Running Fallback Classification Tests Only"
        echo "============================================="
        TEST_MODE=fallback python test_comprehensive_flow_validation_enhanced.py
        ;;
    "both")
        echo "🚀 Running Both LLM and Fallback Classification Tests"
        echo "==================================================="
        if [ "$HAS_API_KEY" = true ]; then
            TEST_MODE=both python test_comprehensive_flow_validation_enhanced.py
        else
            echo "⚠️  No API key - Running fallback tests only"
            TEST_MODE=fallback python test_comprehensive_flow_validation_enhanced.py
        fi
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [mode]"
        echo ""
        echo "Modes:"
        echo "  llm      - Test only LLM classification (requires API key)"
        echo "  fallback - Test only fallback classification"
        echo "  both     - Test both methods (default)"
        echo "  help     - Show this help message"
        echo ""
        echo "Environment Setup:"
        echo "  1. Copy .env.test to .env"
        echo "  2. Set REPLICATE_API_TOKEN=your_token"
        echo "  3. Set SUPABASE_URL and SUPABASE_KEY"
        echo ""
        echo "Examples:"
        echo "  $0              # Run both tests if API key available"
        echo "  $0 llm          # Test only LLM classification"
        echo "  $0 fallback     # Test only fallback classification"
        exit 0
        ;;
    *)
        echo "❌ Invalid test mode: $TEST_MODE"
        echo "Use: llm, fallback, both, or help"
        exit 1
        ;;
esac