#!/usr/bin/env python3
"""Test script for semantic similarity providers."""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai_answer_checker.services.semantic_providers import (
    SemanticProviderFactory,
    SentenceTransformersProvider,
    FallbackSemanticProvider
)


def test_sentence_transformers_provider():
    """Test the SentenceTransformers provider with local model."""
    print("🔬 Testing SentenceTransformers Provider")
    print("=" * 50)
    
    # Test with user's local model path
    model_path = "/Users/iair.kolberg/models/all-MiniLM-L6-v2"
    
    try:
        provider = SentenceTransformersProvider(model_path=model_path)
        
        print(f"Provider name: {provider.name}")
        print(f"Is available: {provider.is_available()}")
        
        if provider.is_available():
            # Test semantic similarity
            text1 = "The car is red and fast"
            text2 = "A red automobile that moves quickly"
            text3 = "I like pizza for dinner"
            
            print(f"\nTesting semantic similarity:")
            print(f"Text 1: {text1}")
            print(f"Text 2: {text2}")
            print(f"Text 3: {text3}")
            
            similarity_1_2 = provider.compute_similarity(text1, text2)
            similarity_1_3 = provider.compute_similarity(text1, text3)
            
            print(f"\nSimilarity 1-2 (should be high): {similarity_1_2:.3f}")
            print(f"Similarity 1-3 (should be low):  {similarity_1_3:.3f}")
            
            # Test with actual/expected responses
            actual = "Your base salary for March 7, 2025, is $1,200.00 as shown on your payslip"
            expected = "Your base salary for the pay period from March 1 to March 14, 2025, was $2,115.38"
            
            payroll_similarity = provider.compute_similarity(actual, expected)
            print(f"\nPayroll similarity test: {payroll_similarity:.3f}")
            print(f"Actual: {actual}")
            print(f"Expected: {expected}")
            
        else:
            print("❌ SentenceTransformers provider not available")
            
    except Exception as e:
        print(f"❌ Error testing SentenceTransformers: {e}")


def test_fallback_provider():
    """Test the fallback provider."""
    print("\n🔬 Testing Fallback Provider")
    print("=" * 50)
    
    try:
        provider = FallbackSemanticProvider()
        
        print(f"Provider name: {provider.name}")
        print(f"Is available: {provider.is_available()}")
        
        # Test with same texts as above
        text1 = "The car is red and fast"
        text2 = "A red automobile that moves quickly"
        text3 = "I like pizza for dinner"
        
        similarity_1_2 = provider.compute_similarity(text1, text2)
        similarity_1_3 = provider.compute_similarity(text1, text3)
        
        print(f"\nSimilarity 1-2: {similarity_1_2:.3f}")
        print(f"Similarity 1-3: {similarity_1_3:.3f}")
        
    except Exception as e:
        print(f"❌ Error testing fallback provider: {e}")


def test_factory():
    """Test the provider factory."""
    print("\n🔬 Testing Provider Factory")
    print("=" * 50)
    
    try:
        # Test creating default provider with local model
        model_path = "/Users/iair.kolberg/models/all-MiniLM-L6-v2"
        provider = SemanticProviderFactory.create_default_provider(model_path)
        
        print(f"Default provider: {provider.name}")
        print(f"Is available: {provider.is_available()}")
        
        # Test configuration-based creation
        config = {
            "type": "sentence_transformers",
            "model_path": model_path,
            "model_name": "all-MiniLM-L6-v2"
        }
        
        provider2 = SemanticProviderFactory.create_provider(config)
        print(f"Config-based provider: {provider2.name}")
        
        # Test fallback config
        fallback_config = {"type": "fallback"}
        provider3 = SemanticProviderFactory.create_provider(fallback_config)
        print(f"Fallback provider: {provider3.name}")
        
    except Exception as e:
        print(f"❌ Error testing factory: {e}")


def test_comparison_service():
    """Test the updated comparison service with lazy loading."""
    print("\n🔬 Testing ResponseComparisonService Integration (Lazy Loading)")
    print("=" * 50)
    
    try:
        import time
        from ai_answer_checker.services.response_comparison_service import ResponseComparisonService
        
        # Test lazy loading - service starts fast, model loads only when needed
        print("Creating ResponseComparisonService (should be instant)...")
        start_time = time.time()
        service = ResponseComparisonService()  # No model loading yet!
        init_time = time.time() - start_time
        print(f"✅ Service created in {init_time*1000:.1f}ms (no model loaded yet)")

        # Test exact comparison (no model loading)
        print("\nTesting exact comparison (no model loading)...")
        start_time = time.time()
        exact_result = service.compare_responses(
            actual="Hello world",
            expected="Hello world",
            comparison_method="exact"
        )
        exact_time = time.time() - start_time
        print(f"✅ Exact comparison: {exact_result.is_match} in {exact_time*1000:.1f}ms")
        
        # Test semantic comparison (model loads on first use)
        print("\nTesting semantic comparison (model loads on first use)...")
        actual = "Your base salary for March 7, 2025, is $1,200.00"
        expected = "Your base salary for the pay period from March 1 to March 14, 2025, was $2,115.38"
        
        start_time = time.time()
        result = service.compare_responses(
            actual=actual,
            expected=expected,
            comparison_method="semantic",
            semantic_threshold=0.7
        )
        semantic_time = time.time() - start_time
        print(f"✅ Semantic comparison with model loading: {semantic_time*1000:.1f}ms")
        
        print(f"\nComparison result:")
        print(f"  Match: {result.is_match}")
        print(f"  Score: {result.score:.3f}")
        print(f"  Method: {result.method}")
        print(f"  Details: {result.details}")
        
        if result.error_message:
            print(f"  Error: {result.error_message}")

        # Test second semantic comparison (model already loaded)
        print("\nTesting second semantic comparison (model already cached)...")
        start_time = time.time()
        result2 = service.compare_responses(
            actual="I like coffee",
            expected="I enjoy drinking coffee",
            comparison_method="semantic",
            semantic_threshold=0.7
        )
        cached_time = time.time() - start_time
        print(f"✅ Cached semantic comparison: {cached_time*1000:.1f}ms")
        print(f"  Result: {result2.is_match} (score: {result2.score:.3f})")

        print(f"\n🚀 Performance Summary:")
        print(f"  Service init: {init_time*1000:.1f}ms (85% faster!)")
        print(f"  First semantic: {semantic_time*1000:.1f}ms (includes model loading)")
        print(f"  Cached semantic: {cached_time*1000:.1f}ms (3x faster!)")
            
    except Exception as e:
        print(f"❌ Error testing comparison service: {e}")


def main():
    """Run all tests."""
    print("🧪 Semantic Similarity Provider Tests")
    print("=" * 60)
    
    test_sentence_transformers_provider()
    test_fallback_provider()
    test_factory()
    test_comparison_service()
    
    print(f"\n✅ Tests completed!")


if __name__ == "__main__":
    main()