"""
Infrastructure - Configuration management
"""
import os
from typing import Optional
from app.domain.models import AppConfig, LLMConfig, VectorDBConfig, RelationalDBConfig, CacheConfig


def load_config() -> AppConfig:
    """
    Load application configuration from environment variables
    
    Returns:
        AppConfig instance with loaded configuration
    """
    return AppConfig(
        llm=LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434"),
            model=os.getenv("LLM_MODEL", "llama3:8b-instruct"),
            api_key=os.getenv("LLM_API_KEY"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
            streaming=os.getenv("LLM_STREAMING", "true").lower() == "true"
        ),
        vectordb=VectorDBConfig(
            provider=os.getenv("VECTORDB_PROVIDER", "milvus"),
            host=os.getenv("VECTORDB_HOST", "localhost"),
            port=int(os.getenv("VECTORDB_PORT", "19530")),
            collection_name=os.getenv("VECTORDB_COLLECTION", "product_embeddings"),
            dimension=int(os.getenv("VECTORDB_DIMENSION", "768")),
            metric_type=os.getenv("VECTORDB_METRIC", "L2")
        ),
        relationaldb=RelationalDBConfig(
            provider=os.getenv("RELATIONALDB_PROVIDER", "duckdb"),
            database_path=os.getenv("RELATIONALDB_PATH", "./data/products.db"),
            table_name=os.getenv("RELATIONALDB_TABLE", "products")
        ),
        cache=CacheConfig(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            provider=os.getenv("CACHE_PROVIDER", "redis"),
            host=os.getenv("CACHE_HOST", "localhost"),
            port=int(os.getenv("CACHE_PORT", "6379")),
            ttl_phase1=int(os.getenv("CACHE_TTL_PHASE1", "300")),
            ttl_phase2=int(os.getenv("CACHE_TTL_PHASE2", "300")),
            ttl_phase4=int(os.getenv("CACHE_TTL_PHASE4", "1800"))
        ),
        max_context_tokens=int(os.getenv("MAX_CONTEXT_TOKENS", "8000")),
        top_k_retrieval=int(os.getenv("TOP_K_RETRIEVAL", "30"))
    )
