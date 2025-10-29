"""
Embedding Provider Module

Text embedding model interface for converting text to vectors.
Supports SentenceTransformer and HuggingFace models.
"""

from app.Providers.embedding_provider.client import EmbeddingProvider

__all__ = ["EmbeddingProvider"]
