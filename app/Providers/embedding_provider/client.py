"""
Embedding Provider Client

Text embedding model interface using SentenceTransformers or HuggingFace.
Converts text chunks and queries into dense vectors for similarity search.
"""

import logging
from typing import List, Optional, Union
import os

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """
    Embedding Provider for text vectorization

    Supports:
    - SentenceTransformer models (recommended)
    - HuggingFace embedding models
    - Local model loading for offline/airgapped environments
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        model_kwargs: Optional[dict] = None,
        encode_kwargs: Optional[dict] = None,
        fallback_model: Optional[str] = None
    ):
        """
        Initialize Embedding Provider

        Args:
            model_name: Model name or local path (e.g., 'all-MiniLM-L6-v2')
            model_kwargs: Model configuration (device, etc.)
            encode_kwargs: Encoding configuration (normalize_embeddings, etc.)
            fallback_model: Fallback model if primary fails
        """
        from app.core.config import settings

        self.model_name = model_name or os.getenv("EMBEDDING_MODEL") or settings.EMBEDDING_MODEL
        self.fallback_model = fallback_model or os.getenv("EMBEDDING_FALLBACK") or settings.EMBEDDING_FALLBACK

        self.model_kwargs = model_kwargs or {"device": "cpu"}
        self.encode_kwargs = encode_kwargs or {"normalize_embeddings": False}

        self._model = None  # Lazy loading
        self._initialized = False

        logger.info(f"Embedding Provider configured with model: {self.model_name}")

    def _lazy_load_model(self):
        """
        Lazy load embedding model on first use

        This prevents blocking the application startup with model loading.
        Model loading can take 5-30 seconds depending on the model size.
        """
        if self._initialized:
            return

        try:
            # Try importing HuggingFace embeddings
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
            except ImportError:
                from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings

            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs=self.model_kwargs,
                encode_kwargs=self.encode_kwargs,
            )
            self._initialized = True
            logger.info(f"Successfully loaded embedding model: {self.model_name}")

        except Exception as e:
            logger.warning(
                f"Failed to load primary embedding model '{self.model_name}': {str(e)}"
            )

            # Try fallback model
            if self.fallback_model and self.fallback_model != self.model_name:
                try:
                    logger.info(f"Attempting fallback model: {self.fallback_model}")
                    self._model = HuggingFaceEmbeddings(
                        model_name=self.fallback_model,
                        model_kwargs=self.model_kwargs,
                        encode_kwargs=self.encode_kwargs,
                    )
                    self._initialized = True
                    logger.info(f"Successfully loaded fallback model: {self.fallback_model}")
                except Exception as fallback_error:
                    logger.error(f"Fallback model also failed: {str(fallback_error)}")
                    raise RuntimeError(
                        f"Could not load embedding models. "
                        f"Primary: {self.model_name}, Fallback: {self.fallback_model}. "
                        f"Set EMBEDDING_MODEL to a local path or ensure network access to Hugging Face Hub."
                    ) from fallback_error
            else:
                raise RuntimeError(
                    f"Could not load embedding model: {self.model_name}. "
                    f"Set EMBEDDING_MODEL to a local path or ensure network access to Hugging Face Hub."
                ) from e

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple text documents

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each vector is a list of floats)

        Example:
            >>> chunks = ["Hello world", "Document chunking"]
            >>> embeddings = provider.embed_documents(chunks)
            >>> len(embeddings)  # 2
            >>> len(embeddings[0])  # 384 (model-dependent)
        """
        self._lazy_load_model()
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text

        Args:
            text: Query string to embed

        Returns:
            Embedding vector (list of floats)

        Example:
            >>> query_embedding = provider.embed_query("What is RAG?")
            >>> len(query_embedding)  # 384 (model-dependent)
        """
        self._lazy_load_model()
        return self._model.embed_query(text)

    def get_underlying_model(self):
        """
        Get the underlying HuggingFaceEmbeddings model instance

        Returns:
            HuggingFaceEmbeddings: The initialized model

        Note:
            This is useful for direct integration with LangChain components
        """
        self._lazy_load_model()
        return self._model


# Singleton instance for dependency injection
_embedding_provider_instance: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    """
    FastAPI dependency for Embedding Provider (Singleton)

    Returns the same instance across all requests to avoid reloading the model.

    Usage in endpoints:
        @router.post("/upload")
        async def upload(
            embedding_provider: EmbeddingProvider = Depends(get_embedding_provider)
        ):
            ...
    """
    global _embedding_provider_instance

    if _embedding_provider_instance is None:
        _embedding_provider_instance = EmbeddingProvider()

    return _embedding_provider_instance
