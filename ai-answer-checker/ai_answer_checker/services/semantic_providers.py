"""Semantic similarity providers for comparing text responses."""

import logging
import numpy as np
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class SemanticProvider(ABC):
    """Abstract base class for semantic similarity providers."""
    
    @abstractmethod
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of this provider."""
        pass


class SentenceTransformersProvider(SemanticProvider):
    """Semantic similarity provider using SentenceTransformers library."""
    
    def __init__(self, model_path: Optional[str] = None, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the SentenceTransformers provider.
        
        Args:
            model_path: Path to local model directory (if None, downloads from HuggingFace)
            model_name: Name of the model to use (default: all-MiniLM-L6-v2)
        """
        self.model_path = model_path
        self.model_name = model_name
        self._model = None
        self._initialized = False
        
    def _lazy_load_model(self):
        """Lazy load the SentenceTransformer model."""
        if self._initialized:
            return
            
        try:
            from sentence_transformers import SentenceTransformer
            
            # Load from local path only - no automatic downloads
            if self.model_path and Path(self.model_path).exists():
                logger.info(f"Loading SentenceTransformer model from local path: {self.model_path}")
                self._model = SentenceTransformer(self.model_path)
                logger.info(f"Successfully loaded local SentenceTransformer model")
            else:
                if self.model_path:
                    raise FileNotFoundError(f"Local model not found at: {self.model_path}")
                else:
                    raise ValueError("No model path specified and automatic downloads are disabled for security")
                
            self._initialized = True
            logger.info(f"SentenceTransformer model loaded successfully")
            
        except ImportError:
            logger.error("sentence-transformers library not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model: {e}")
            raise
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity using sentence embeddings.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score between 0.0 and 1.0
        """
        self._lazy_load_model()
        
        if not self._model:
            raise RuntimeError("SentenceTransformer model not loaded")
        
        try:
            # Generate embeddings for both texts
            embeddings = self._model.encode([text1, text2])
            
            # Compute cosine similarity
            similarity_matrix = cosine_similarity([embeddings[0]], [embeddings[1]])
            similarity_score = similarity_matrix[0][0]
            
            # Ensure score is between 0 and 1
            similarity_score = max(0.0, min(1.0, float(similarity_score)))
            
            logger.debug(f"Semantic similarity computed: {similarity_score:.3f}")
            return similarity_score
            
        except Exception as e:
            logger.error(f"Failed to compute semantic similarity: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if SentenceTransformers is available."""
        try:
            import sentence_transformers
            # Check if model path exists (if specified)
            if self.model_path:
                return Path(self.model_path).exists()
            return True
        except ImportError:
            return False
    
    @property
    def name(self) -> str:
        """Get the name of this provider."""
        if self.model_path:
            return f"SentenceTransformers(local:{Path(self.model_path).name})"
        return f"SentenceTransformers({self.model_name})"


class FallbackSemanticProvider(SemanticProvider):
    """Fallback semantic provider using simple text similarity."""
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute simple text similarity as fallback.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            SequenceMatcher ratio between 0.0 and 1.0
        """
        from difflib import SequenceMatcher
        
        # Clean and normalize text
        text1_clean = text1.strip().lower()
        text2_clean = text2.strip().lower()
        
        # Use SequenceMatcher for basic similarity
        matcher = SequenceMatcher(None, text1_clean, text2_clean)
        score = matcher.ratio()
        
        logger.debug(f"Fallback similarity computed: {score:.3f}")
        return score
    
    def is_available(self) -> bool:
        """Fallback provider is always available."""
        return True
    
    @property
    def name(self) -> str:
        """Get the name of this provider."""
        return "FallbackSequenceMatcher"


class SemanticProviderFactory:
    """Factory for creating semantic similarity providers."""
    
    @staticmethod
    def create_provider(provider_config: dict) -> SemanticProvider:
        """Create a semantic provider based on configuration.
        
        Args:
            provider_config: Configuration dictionary with provider settings
            
        Returns:
            Configured semantic provider
        """
        provider_type = provider_config.get("type", "sentence_transformers")
        
        if provider_type == "sentence_transformers":
            model_path = provider_config.get("model_path")
            model_name = provider_config.get("model_name", "all-MiniLM-L6-v2")
            
            provider = SentenceTransformersProvider(
                model_path=model_path,
                model_name=model_name
            )
            
            # Check if provider is available, fallback if not
            if provider.is_available():
                # Test that the provider can actually work by doing a simple computation
                try:
                    test_score = provider.compute_similarity("test", "test")
                    if 0.0 <= test_score <= 1.0:
                        logger.info(f"Using semantic provider: {provider.name}")
                        return provider
                    else:
                        logger.warning(f"SentenceTransformers provider test failed, falling back")
                        return FallbackSemanticProvider()
                except Exception as e:
                    logger.warning(f"SentenceTransformers provider failed during test: {e}, falling back")
                    return FallbackSemanticProvider()
            else:
                logger.warning(f"SentenceTransformers not available, falling back to simple text similarity")
                return FallbackSemanticProvider()
        
        elif provider_type == "fallback":
            return FallbackSemanticProvider()
        
        else:
            logger.error(f"Unknown semantic provider type: {provider_type}")
            raise ValueError(f"Unknown semantic provider type: {provider_type}")
    
    @staticmethod
    def create_default_provider(model_path: Optional[str] = None) -> SemanticProvider:
        """Create a default semantic provider.
        
        Args:
            model_path: Optional path to local model
            
        Returns:
            Default semantic provider
        """
        config = {
            "type": "sentence_transformers",
            "model_path": model_path,
            "model_name": "all-MiniLM-L6-v2"
        }
        return SemanticProviderFactory.create_provider(config)