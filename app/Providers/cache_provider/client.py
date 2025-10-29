"""
Redis Cache Provider

High-performance caching layer for embeddings, query expansions, and search results.
Implements TTL-based cache invalidation with different strategies per data type.
"""

import logging
import json
import hashlib
from typing import Optional, Any, List, Dict
import redis.asyncio as aioredis
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class CacheProvider:
    """
    Redis Cache Provider for RAG application

    Cache Strategy:
    - Embeddings: 24h TTL (expensive to compute)
    - Query Expansions: 1h TTL (moderate cost)
    - Search Results: 30min TTL (low cost but frequently accessed)
    - File Metadata: 6h TTL (semi-static data)

    Key Format:
    - emb:{text_hash} - Embedding vectors
    - qexp:{query_hash} - Query expansion results
    - search:{query_hash}:{file_ids} - Search results
    - file:{file_id} - File metadata
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None
    ):
        """
        Initialize Redis Cache Provider

        Args:
            redis_url: Full Redis URL (overrides other params)
            host: Redis host (default from settings)
            port: Redis port (default from settings)
            db: Redis database number (default from settings)
            password: Redis password (default from settings)
        """
        from app.core.config import settings

        if redis_url:
            self.redis_url = redis_url
        else:
            self.redis_url = settings.redis_url

        # TTL configurations from settings
        self.embedding_ttl = settings.REDIS_EMBEDDING_TTL
        self.query_expansion_ttl = settings.REDIS_QUERY_EXPANSION_TTL
        self.search_results_ttl = settings.REDIS_SEARCH_RESULTS_TTL

        # Redis client (initialized lazily)
        self._redis: Optional[Redis] = None

        logger.info(f"Cache Provider initialized: {self.redis_url}")

    async def _get_redis(self) -> Redis:
        """
        Lazy initialization of Redis client

        Returns:
            Connected Redis client
        """
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False  # We handle encoding ourselves
            )
            logger.info("Redis client connected")

        return self._redis

    def _hash_text(self, text: str) -> str:
        """
        Generate hash for text-based keys

        Args:
            text: Input text

        Returns:
            SHA256 hash (first 16 chars)
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]

    # =========================================================================
    # Embedding Cache
    # =========================================================================

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding for text

        Args:
            text: Text to lookup

        Returns:
            Embedding vector or None if not cached

        Example:
            >>> embedding = await cache.get_embedding("sample text")
            >>> if embedding is None:
            ...     embedding = compute_embedding(text)
            ...     await cache.set_embedding(text, embedding)
        """
        try:
            redis = await self._get_redis()
            key = f"emb:{self._hash_text(text)}"

            cached = await redis.get(key)
            if cached:
                embedding = json.loads(cached)
                logger.debug(f"Embedding cache hit: {key}")
                return embedding

            logger.debug(f"Embedding cache miss: {key}")
            return None

        except Exception as e:
            logger.error(f"Failed to get embedding from cache: {str(e)}")
            return None

    async def set_embedding(self, text: str, embedding: List[float]):
        """
        Cache embedding for text

        Args:
            text: Text content
            embedding: Embedding vector

        Example:
            >>> await cache.set_embedding("sample text", [0.1, 0.2, ...])
        """
        try:
            redis = await self._get_redis()
            key = f"emb:{self._hash_text(text)}"

            await redis.setex(
                key,
                self.embedding_ttl,
                json.dumps(embedding)
            )

            logger.debug(f"Cached embedding: {key} (TTL: {self.embedding_ttl}s)")

        except Exception as e:
            logger.error(f"Failed to cache embedding: {str(e)}")

    # =========================================================================
    # Query Expansion Cache
    # =========================================================================

    async def get_query_expansion(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached query expansion

        Args:
            query: Original user query

        Returns:
            Query expansion dict or None if not cached

        Example:
            >>> expansion = await cache.get_query_expansion("What is RAG?")
            >>> if expansion:
            ...     expanded_questions = expansion['expanded_questions']
        """
        try:
            redis = await self._get_redis()
            key = f"qexp:{self._hash_text(query)}"

            cached = await redis.get(key)
            if cached:
                expansion = json.loads(cached)
                logger.debug(f"Query expansion cache hit: {key}")
                return expansion

            logger.debug(f"Query expansion cache miss: {key}")
            return None

        except Exception as e:
            logger.error(f"Failed to get query expansion from cache: {str(e)}")
            return None

    async def set_query_expansion(self, query: str, expansion: Dict[str, Any]):
        """
        Cache query expansion result

        Args:
            query: Original query
            expansion: Expansion result dict

        Example:
            >>> expansion = {
            ...     "original_query": "What is RAG?",
            ...     "expanded_questions": ["Q1", "Q2", "Q3"],
            ...     "intent": "definition_seeking"
            ... }
            >>> await cache.set_query_expansion("What is RAG?", expansion)
        """
        try:
            redis = await self._get_redis()
            key = f"qexp:{self._hash_text(query)}"

            await redis.setex(
                key,
                self.query_expansion_ttl,
                json.dumps(expansion)
            )

            logger.debug(f"Cached query expansion: {key} (TTL: {self.query_expansion_ttl}s)")

        except Exception as e:
            logger.error(f"Failed to cache query expansion: {str(e)}")

    # =========================================================================
    # Search Results Cache
    # =========================================================================

    async def get_search_results(
        self,
        query: str,
        file_ids: List[str],
        top_k: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached search results

        Args:
            query: Search query
            file_ids: List of file IDs searched
            top_k: Number of results

        Returns:
            Search results or None if not cached

        Example:
            >>> results = await cache.get_search_results(
            ...     query="RAG",
            ...     file_ids=["file1", "file2"],
            ...     top_k=5
            ... )
        """
        try:
            redis = await self._get_redis()

            # Key includes query, file_ids, and top_k
            file_ids_str = ','.join(sorted(file_ids))
            cache_key = f"{query}|{file_ids_str}|{top_k}"
            key = f"search:{self._hash_text(cache_key)}"

            cached = await redis.get(key)
            if cached:
                results = json.loads(cached)
                logger.debug(f"Search results cache hit: {key}")
                return results

            logger.debug(f"Search results cache miss: {key}")
            return None

        except Exception as e:
            logger.error(f"Failed to get search results from cache: {str(e)}")
            return None

    async def set_search_results(
        self,
        query: str,
        file_ids: List[str],
        top_k: int,
        results: List[Dict[str, Any]]
    ):
        """
        Cache search results

        Args:
            query: Search query
            file_ids: List of file IDs searched
            top_k: Number of results
            results: Search results to cache

        Example:
            >>> await cache.set_search_results(
            ...     query="RAG",
            ...     file_ids=["file1"],
            ...     top_k=5,
            ...     results=[{...}, {...}]
            ... )
        """
        try:
            redis = await self._get_redis()

            file_ids_str = ','.join(sorted(file_ids))
            cache_key = f"{query}|{file_ids_str}|{top_k}"
            key = f"search:{self._hash_text(cache_key)}"

            await redis.setex(
                key,
                self.search_results_ttl,
                json.dumps(results)
            )

            logger.debug(f"Cached search results: {key} (TTL: {self.search_results_ttl}s)")

        except Exception as e:
            logger.error(f"Failed to cache search results: {str(e)}")

    # =========================================================================
    # File Metadata Cache
    # =========================================================================

    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached file metadata

        Args:
            file_id: File identifier

        Returns:
            File metadata dict or None if not cached
        """
        try:
            redis = await self._get_redis()
            key = f"file:{file_id}"

            cached = await redis.get(key)
            if cached:
                metadata = json.loads(cached)
                logger.debug(f"File metadata cache hit: {key}")
                return metadata

            return None

        except Exception as e:
            logger.error(f"Failed to get file metadata from cache: {str(e)}")
            return None

    async def set_file_metadata(self, file_id: str, metadata: Dict[str, Any]):
        """
        Cache file metadata

        Args:
            file_id: File identifier
            metadata: File metadata dict

        Example:
            >>> metadata = {
            ...     "file_id": "file_abc",
            ...     "filename": "doc.pdf",
            ...     "chunk_count": 150
            ... }
            >>> await cache.set_file_metadata("file_abc", metadata)
        """
        try:
            redis = await self._get_redis()
            key = f"file:{file_id}"

            # 6 hour TTL for file metadata
            await redis.setex(key, 21600, json.dumps(metadata))

            logger.debug(f"Cached file metadata: {key} (TTL: 6h)")

        except Exception as e:
            logger.error(f"Failed to cache file metadata: {str(e)}")

    # =========================================================================
    # Cache Management
    # =========================================================================

    async def invalidate_file_caches(self, file_id: str):
        """
        Invalidate all caches related to a file

        Args:
            file_id: File identifier

        Example:
            >>> await cache.invalidate_file_caches("file_abc")
        """
        try:
            redis = await self._get_redis()

            # Delete file metadata
            await redis.delete(f"file:{file_id}")

            # Delete search results containing this file
            # (This is a simplified approach - in production, use Redis pattern matching)
            logger.info(f"Invalidated caches for file: {file_id}")

        except Exception as e:
            logger.error(f"Failed to invalidate file caches: {str(e)}")

    async def clear_all(self):
        """
        Clear all cache entries (use with caution)

        Example:
            >>> await cache.clear_all()
        """
        try:
            redis = await self._get_redis()
            await redis.flushdb()
            logger.warning("Cleared all cache entries")

        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dict with cache stats (keys, memory, hits, misses)

        Example:
            >>> stats = await cache.get_stats()
            >>> print(f"Total keys: {stats['total_keys']}")
        """
        try:
            redis = await self._get_redis()

            info = await redis.info("stats")
            dbsize = await redis.dbsize()

            stats = {
                "total_keys": dbsize,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "used_memory_human": info.get("used_memory_human", "N/A")
            }

            # Calculate hit rate
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            total = hits + misses
            stats["hit_rate"] = (hits / total * 100) if total > 0 else 0

            return stats

        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {}

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")

    async def __aenter__(self):
        """Async context manager entry"""
        await self._get_redis()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Singleton instance for dependency injection
_cache_provider_instance: Optional[CacheProvider] = None


async def get_cache_provider() -> CacheProvider:
    """
    FastAPI dependency for Cache Provider (Singleton)

    Usage in endpoints:
        @router.post("/chat")
        async def chat(
            cache: CacheProvider = Depends(get_cache_provider)
        ):
            ...
    """
    global _cache_provider_instance

    if _cache_provider_instance is None:
        _cache_provider_instance = CacheProvider()

    return _cache_provider_instance
