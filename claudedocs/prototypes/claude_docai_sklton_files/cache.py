"""
Infrastructure - Caching layer with Redis implementation
"""
import hashlib
import json
from typing import Optional, Any
from abc import ABC, abstractmethod
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


class CacheInterface(ABC):
    """Abstract cache interface"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass


class RedisCache(CacheInterface):
    """Redis-based cache implementation"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """
        Initialize Redis cache
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
        """
        self.host = host
        self.port = port
        self.db = db
        self._client = None
        
    async def _get_client(self):
        """Get or create Redis client"""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    decode_responses=True
                )
            except ImportError:
                logger.warning("redis package not installed, using in-memory cache")
                self._client = InMemoryCache()
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in Redis with TTL"""
        try:
            client = await self._get_client()
            serialized = json.dumps(value)
            await client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            client = await self._get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            client = await self._get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False


class InMemoryCache(CacheInterface):
    """Simple in-memory cache fallback"""
    
    def __init__(self):
        self._cache = {}
        self._expiry = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory"""
        import time
        if key in self._cache:
            if key in self._expiry and time.time() > self._expiry[key]:
                del self._cache[key]
                del self._expiry[key]
                return None
            return self._cache[key]
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in memory with TTL"""
        import time
        self._cache[key] = value
        self._expiry[key] = time.time() + ttl
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from memory"""
        if key in self._cache:
            del self._cache[key]
        if key in self._expiry:
            del self._expiry[key]
        return True
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory"""
        return key in self._cache


def create_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Create a cache key from prefix and parameters
    
    Args:
        prefix: Cache key prefix
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
        
    Returns:
        MD5 hash-based cache key
    """
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    key_string = ":".join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"{prefix}:{key_hash}"
