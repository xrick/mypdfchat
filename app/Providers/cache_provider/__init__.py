"""
Cache Provider Module

Redis-based caching for embeddings, query expansions, and search results.
"""

from app.Providers.cache_provider.client import CacheProvider, get_cache_provider

__all__ = ["CacheProvider", "get_cache_provider"]
