"""
Vector Store Provider Client

Vector database interface for storing and retrieving document embeddings.
Supports FAISS (in-memory) and ChromaDB (persistent) backends.
"""

import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStoreProvider:
    """
    Vector Store Provider for similarity search

    Provides a unified interface for different vector database backends.
    Currently supports:
    - FAISS (fast in-memory search)
    - ChromaDB (persistent storage)
    """

    def __init__(
        self,
        backend: str = "faiss",
        persist_directory: Optional[str] = None,
        collection_name: str = "documents"
    ):
        """
        Initialize Vector Store Provider

        Args:
            backend: Vector store backend ("faiss" or "chroma")
            persist_directory: Directory for persistent storage (ChromaDB only)
            collection_name: Name of the vector collection
        """
        from app.core.config import settings

        self.backend = backend.lower()
        self.persist_directory = persist_directory or settings.VECTOR_STORE_PATH
        self.collection_name = collection_name

        # Storage for file-specific vector stores (in-memory mapping)
        self._stores: Dict[str, Any] = {}

        logger.info(f"Vector Store Provider initialized with backend: {self.backend}")

    def create_store_from_texts(
        self,
        texts: List[str],
        embeddings: Any,  # HuggingFaceEmbeddings instance
        metadatas: Optional[List[dict]] = None,
        file_id: Optional[str] = None
    ) -> str:
        """
        Create a vector store from text chunks and embeddings

        Args:
            texts: List of text chunks
            embeddings: Embedding provider instance
            metadatas: Metadata for each chunk (e.g., file_id, chunk_index)
            file_id: Unique identifier for this file's vector store

        Returns:
            str: Store identifier (file_id or generated ID)

        Example:
            >>> texts = ["chunk1", "chunk2"]
            >>> embeddings = get_embedding_provider()
            >>> store_id = provider.create_store_from_texts(texts, embeddings)
        """
        from langchain_community.vectorstores import FAISS

        if self.backend == "faiss":
            # Create FAISS vector store
            vector_store = FAISS.from_texts(
                texts=texts,
                embedding=embeddings,
                metadatas=metadatas
            )

            # Store in memory with file_id as key
            store_id = file_id or f"store_{len(self._stores)}"
            self._stores[store_id] = vector_store

            logger.info(f"Created FAISS store '{store_id}' with {len(texts)} chunks")
            return store_id

        elif self.backend == "chroma":
            # ChromaDB implementation
            try:
                import chromadb
                from langchain_community.vectorstores import Chroma

                # Create persistent ChromaDB
                persist_path = Path(self.persist_directory)
                persist_path.mkdir(parents=True, exist_ok=True)

                vector_store = Chroma.from_texts(
                    texts=texts,
                    embedding=embeddings,
                    metadatas=metadatas,
                    collection_name=self.collection_name,
                    persist_directory=str(persist_path)
                )

                store_id = file_id or f"store_{len(self._stores)}"
                self._stores[store_id] = vector_store

                logger.info(f"Created ChromaDB store '{store_id}' with {len(texts)} chunks")
                return store_id

            except ImportError:
                logger.error("ChromaDB not installed. Install with: pip install chromadb")
                raise
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")

    def similarity_search(
        self,
        store_id: str,
        query: str,
        k: int = 5,
        filter_dict: Optional[dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search in a vector store

        Args:
            store_id: Vector store identifier
            query: Query string
            k: Number of results to return
            filter_dict: Metadata filters (e.g., {"file_id": "doc1"})

        Returns:
            List of dicts with 'content', 'metadata', and optionally 'score'

        Example:
            >>> results = provider.similarity_search(
            ...     store_id="file_123",
            ...     query="What is RAG?",
            ...     k=3
            ... )
            >>> print(results[0]['content'])
        """
        if store_id not in self._stores:
            raise ValueError(f"Vector store '{store_id}' not found")

        vector_store = self._stores[store_id]

        try:
            # Perform similarity search
            if filter_dict:
                docs = vector_store.similarity_search(
                    query,
                    k=k,
                    filter=filter_dict
                )
            else:
                docs = vector_store.similarity_search(query, k=k)

            # Format results
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })

            logger.info(f"Found {len(results)} similar documents for store '{store_id}'")
            return results

        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            raise

    def similarity_search_with_score(
        self,
        store_id: str,
        query: str,
        k: int = 5,
        filter_dict: Optional[dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search with relevance scores

        Args:
            store_id: Vector store identifier
            query: Query string
            k: Number of results to return
            filter_dict: Metadata filters

        Returns:
            List of dicts with 'content', 'metadata', and 'score'

        Example:
            >>> results = provider.similarity_search_with_score(
            ...     store_id="file_123",
            ...     query="What is RAG?",
            ...     k=3
            ... )
            >>> print(f"Score: {results[0]['score']}, Content: {results[0]['content']}")
        """
        if store_id not in self._stores:
            raise ValueError(f"Vector store '{store_id}' not found")

        vector_store = self._stores[store_id]

        try:
            # Perform similarity search with scores
            if filter_dict:
                docs_with_scores = vector_store.similarity_search_with_score(
                    query,
                    k=k,
                    filter=filter_dict
                )
            else:
                docs_with_scores = vector_store.similarity_search_with_score(query, k=k)

            # Format results
            results = []
            for doc, score in docs_with_scores:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })

            logger.info(f"Found {len(results)} similar documents with scores for store '{store_id}'")
            return results

        except Exception as e:
            logger.error(f"Error during similarity search with score: {str(e)}")
            raise

    def get_store(self, store_id: str) -> Any:
        """
        Get raw vector store instance

        Args:
            store_id: Vector store identifier

        Returns:
            Vector store instance (FAISS or Chroma)
        """
        if store_id not in self._stores:
            raise ValueError(f"Vector store '{store_id}' not found")

        return self._stores[store_id]

    def list_stores(self) -> List[str]:
        """
        List all vector store IDs

        Returns:
            List of store identifiers
        """
        return list(self._stores.keys())

    def delete_store(self, store_id: str):
        """
        Delete a vector store

        Args:
            store_id: Vector store identifier
        """
        if store_id in self._stores:
            del self._stores[store_id]
            logger.info(f"Deleted vector store '{store_id}'")
        else:
            logger.warning(f"Attempted to delete non-existent store '{store_id}'")


# Singleton instance for dependency injection
_vector_store_provider_instance: Optional[VectorStoreProvider] = None


def get_vector_store_provider() -> VectorStoreProvider:
    """
    FastAPI dependency for Vector Store Provider (Singleton)

    Usage in endpoints:
        @router.post("/upload")
        async def upload(
            vector_provider: VectorStoreProvider = Depends(get_vector_store_provider)
        ):
            ...
    """
    global _vector_store_provider_instance

    if _vector_store_provider_instance is None:
        _vector_store_provider_instance = VectorStoreProvider()

    return _vector_store_provider_instance
