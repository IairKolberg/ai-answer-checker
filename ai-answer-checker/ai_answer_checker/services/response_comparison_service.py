"""Service for comparing AI agent responses with expected answers."""

import logging
from typing import Dict, Any, Optional, List, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass

from .semantic_providers import SemanticProviderFactory, SemanticProvider

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result of comparing an actual response with expected answer."""
    is_match: bool
    score: float  # 0.0 to 1.0
    method: str  # "exact", "semantic", "substring", "pattern"
    details: Optional[str] = None
    error_message: Optional[str] = None


class ResponseComparisonService:
    """Service for comparing AI responses with expected answers using multiple methods."""
    
    def __init__(self, semantic_provider: Optional[SemanticProvider] = None):
        """Initialize the response comparison service.
        
        Args:
            semantic_provider: Optional semantic similarity provider. If None, will be lazily created when needed.
        """
        self._semantic_provider = semantic_provider  # Private, may be None
        self._model_path = "/Users/iair.kolberg/models/all-MiniLM-L6-v2"
        logger.info("ResponseComparisonService initialized (semantic provider will be loaded when needed)")
        
    def compare_responses(self, actual: str, expected: str, 
                         comparison_method: str = "semantic",
                         semantic_threshold: float = 0.8,
                         substring_words: List[str] = None) -> ComparisonResult:
        """Compare actual response with expected answer using specified method.
        
        Args:
            actual: The actual response from AI agent
            expected: The expected answer from test case (for exact/semantic) or ignored (for substring)
            comparison_method: Method to use: "semantic", "exact", or "substring"
            semantic_threshold: Threshold for semantic similarity (0.0 to 1.0)
            substring_words: Required words for substring matching (only used with "substring" method)
            
        Returns:
            ComparisonResult with the match result
        """
        
        logger.debug(f"Comparing responses using method: {comparison_method}")
        logger.debug(f"Actual: {actual[:100]}{'...' if len(actual) > 100 else ''}")
        if comparison_method != "substring":
            logger.debug(f"Expected: {expected[:100]}{'...' if len(expected) > 100 else ''}")
        else:
            logger.debug(f"Required words: {substring_words}")
        
        try:
            if comparison_method == "exact":
                result = self._exact_match(actual, expected)
            elif comparison_method == "semantic":
                result = self._semantic_similarity(actual, expected, semantic_threshold)
            elif comparison_method == "substring":
                result = self._substring_match(actual, substring_words or [])
            else:
                return ComparisonResult(
                    is_match=False,
                    score=0.0,
                    method=comparison_method,
                    error_message=f"Unknown comparison method: {comparison_method}"
                )
            
            logger.info(f"Response comparison with {comparison_method}: score={result.score:.3f}, match={result.is_match}")
            return result
                
        except Exception as e:
            logger.error(f"Comparison method '{comparison_method}' failed: {e}")
            return ComparisonResult(
                is_match=False,
                score=0.0,
                method=comparison_method,
                error_message=f"Comparison failed: {e}"
            )
    
    def _exact_match(self, actual: str, expected: str) -> ComparisonResult:
        """Compare using exact string matching."""
        actual_clean = actual.strip()
        expected_clean = expected.strip()
        
        is_match = actual_clean == expected_clean
        score = 1.0 if is_match else 0.0
        
        return ComparisonResult(
            is_match=is_match,
            score=score,
            method="exact",
            details=f"Exact match: {'✓' if is_match else '✗'}"
        )
    

    
    def _substring_match(self, actual: str, required_words: List[str]) -> ComparisonResult:
        """Check if all required words are present in the actual response."""
        actual_clean = actual.strip().lower()
        
        if not required_words:
            return ComparisonResult(
                is_match=True,
                score=1.0,
                method="substring",
                details="No required words specified - match by default"
            )
        
        found_words = []
        missing_words = []
        
        for word in required_words:
            word_clean = word.strip().lower()
            if word_clean in actual_clean:
                found_words.append(word)
            else:
                missing_words.append(word)
        
        # Calculate score as percentage of words found
        score = len(found_words) / len(required_words) if required_words else 1.0
        is_match = len(missing_words) == 0
        
        details = f"Found {len(found_words)}/{len(required_words)} words"
        if missing_words:
            details += f" | Missing: {', '.join(missing_words)}"
        
        return ComparisonResult(
            is_match=is_match,
            score=score,
            method="substring",
            details=details
        )
    

    
    def _get_semantic_provider(self) -> SemanticProvider:
        """Get or create the semantic provider (lazy initialization)."""
        if self._semantic_provider is None:
            logger.info("Creating semantic provider with local model on first use...")
            self._semantic_provider = SemanticProviderFactory.create_default_provider(self._model_path)
            logger.info(f"Semantic provider created: {self._semantic_provider.name}")
        return self._semantic_provider
    
    def _semantic_similarity(self, actual: str, expected: str, threshold: float = 0.8) -> ComparisonResult:
        """Compare using semantic similarity (embeddings-based).
        
        Uses lazy-loaded semantic provider for computing embeddings-based similarity.
        """
        try:
            # Lazy load the semantic provider only when needed
            semantic_provider = self._get_semantic_provider()
            logger.debug(f"Computing semantic similarity using {semantic_provider.name}")
            
            # Compute semantic similarity using the provider
            score = semantic_provider.compute_similarity(actual, expected)
            
            # Determine if similarity meets threshold
            is_match = score >= threshold
            
            return ComparisonResult(
                is_match=is_match,
                score=score,
                method="semantic",
                details=f"Semantic similarity ({semantic_provider.name}): {score:.3f} (threshold: {threshold})"
            )
            
        except Exception as e:
            provider_name = getattr(self._semantic_provider, 'name', 'unknown') if self._semantic_provider else 'not loaded'
            logger.error(f"Semantic comparison failed with {provider_name}: {e}")
            return ComparisonResult(
                is_match=False,
                score=0.0,
                method="semantic",
                error_message=f"Semantic comparison failed: {e}"
            )
    
