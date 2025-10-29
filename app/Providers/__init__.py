"""
Providers Layer (Layer 1) - Infrastructure Interfaces

This layer contains all infrastructure adapters and clients that interact with external systems.
Services layer depends on these providers through dependency injection.

Available Providers:
- llm_provider: Unified OpenAI-compatible API client for LLM inference
- embedding_provider: Text embedding model interface (SentenceTransformer)
- vector_store_provider: Vector database interface (ChromaDB/FAISS)
"""

from app.Providers.llm_provider.client import LLMProviderClient
from app.Providers.embedding_provider.client import EmbeddingProvider
from app.Providers.vector_store_provider.client import VectorStoreProvider

__all__ = [
    "LLMProviderClient",
    "EmbeddingProvider",
    "VectorStoreProvider",
]
