"""
Vector Store Provider Module

Vector database interface for similarity search and retrieval.
Supports FAISS and ChromaDB backends.
"""

from app.Providers.vector_store_provider.client import VectorStoreProvider

__all__ = ["VectorStoreProvider"]
