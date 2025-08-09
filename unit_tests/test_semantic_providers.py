"""Unit tests for semantic similarity providers.

Covers:
- FallbackSemanticProvider basic behavior
- SemanticProviderFactory fallback behavior when no local model is supplied
- SentenceTransformersProvider error behavior without a model path
"""

import unittest

from ai_answer_checker.services.semantic_providers import (
    SemanticProviderFactory,
    SentenceTransformersProvider,
    FallbackSemanticProvider,
)


class TestSemanticProviders(unittest.TestCase):

    def test_fallback_provider_similarity(self):
        """Fallback provider should produce scores in [0,1] and rank similar texts higher."""
        provider = FallbackSemanticProvider()
        self.assertTrue(provider.is_available())
        self.assertEqual(provider.name, "FallbackSequenceMatcher")

        text1 = "The car is red and fast"
        text2 = "A red automobile that moves quickly"
        text3 = "I like pizza for dinner"

        s12 = provider.compute_similarity(text1, text2)
        s13 = provider.compute_similarity(text1, text3)

        # Range checks
        self.assertGreaterEqual(s12, 0.0)
        self.assertLessEqual(s12, 1.0)
        self.assertGreaterEqual(s13, 0.0)
        self.assertLessEqual(s13, 1.0)

        # Similar paraphrases should score higher than unrelated text
        self.assertGreater(s12, s13)

        # Identical text should be 1.0
        self.assertEqual(provider.compute_similarity(text1, text1), 1.0)

    def test_factory_falls_back_without_model(self):
        """Factory should fall back if no local ST model path is provided."""
        provider = SemanticProviderFactory.create_provider({
            "type": "sentence_transformers",
            # model_path intentionally omitted to avoid downloads
        })
        self.assertIsInstance(provider, FallbackSemanticProvider)

    def test_sentence_transformers_provider_without_path_raises(self):
        """Direct ST provider usage without a model path should raise a clear error.

        This ensures we never accidentally trigger remote downloads in secure environments.
        """
        try:
            import sentence_transformers  # noqa: F401
        except Exception:
            self.skipTest("sentence-transformers not installed")

        provider = SentenceTransformersProvider(model_path=None)
        with self.assertRaises(ValueError):
            provider.compute_similarity("a", "b")


if __name__ == "__main__":
    unittest.main()


