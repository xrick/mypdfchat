"""
Milvus Vector Database Client

Enterprise-grade vector database for distributed storage and retrieval.
Implements partition-based storage (one partition per file) for efficient management.
"""

import logging
from typing import List, Dict, Optional, Any
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility
)

logger = logging.getLogger(__name__)


class MilvusClient:
    """
    Milvus Vector Database Client

    Features:
    - Distributed vector storage with high performance
    - Partition-based file management (one partition per file)
    - IVF_FLAT indexing for efficient similarity search
    - Automatic connection management and error recovery

    Architecture:
    - Collection: Global container (e.g., "document_embeddings")
    - Partition: Per-file storage (e.g., "file_abc123")
    - Fields: id, file_id, chunk_index, content, embedding, timestamp
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[str] = None,
        collection_name: Optional[str] = None,
        dimension: Optional[int] = None
    ):
        """
        Initialize Milvus Client

        Args:
            host: Milvus server host (default from settings)
            port: Milvus server port (default from settings)
            collection_name: Collection name (default from settings)
            dimension: Embedding dimension (default from settings)
        """
        from app.core.config import settings

        self.host = host or settings.MILVUS_HOST
        self.port = port or settings.MILVUS_PORT
        self.collection_name = collection_name or settings.MILVUS_COLLECTION_NAME
        self.dimension = dimension or settings.EMBEDDING_DIMENSION

        # Milvus configuration
        self.index_type = settings.MILVUS_INDEX_TYPE
        self.metric_type = settings.MILVUS_METRIC_TYPE
        self.nlist = settings.MILVUS_NLIST

        # Connection state
        self._connected = False
        self._collection: Optional[Collection] = None

        logger.info(
            f"Milvus Client initialized: {self.host}:{self.port}, "
            f"collection='{self.collection_name}', dimension={self.dimension}"
        )

    def connect(self):
        """
        Establish connection to Milvus server

        Raises:
            Exception: If connection fails
        """
        if self._connected:
            logger.debug("Already connected to Milvus")
            return

        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            self._connected = True
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")

            # Initialize or load collection
            self._initialize_collection()

        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {str(e)}")
            raise

    def _initialize_collection(self):
        """
        Create collection if not exists, or load existing collection

        Collection Schema:
        - id: int64 (primary key, auto-increment)
        - file_id: varchar(64) (file identifier)
        - chunk_index: int32 (chunk position in file)
        - content: varchar(4096) (text content)
        - embedding: float_vector(dim) (embedding vector)
        - timestamp: int64 (Unix timestamp)
        """
        if utility.has_collection(self.collection_name):
            # Load existing collection
            self._collection = Collection(self.collection_name)
            self._collection.load()
            logger.info(f"Loaded existing collection '{self.collection_name}'")
        else:
            # Create new collection
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="file_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="chunk_index", dtype=DataType.INT32),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                FieldSchema(name="timestamp", dtype=DataType.INT64)
            ]

            schema = CollectionSchema(
                fields=fields,
                description="Document embeddings for RAG system"
            )

            self._collection = Collection(
                name=self.collection_name,
                schema=schema
            )

            # Create IVF_FLAT index on embedding field
            index_params = {
                "index_type": self.index_type,
                "metric_type": self.metric_type,
                "params": {"nlist": self.nlist}
            }

            self._collection.create_index(
                field_name="embedding",
                index_params=index_params
            )

            self._collection.load()
            logger.info(f"Created new collection '{self.collection_name}' with {self.index_type} index")

    def create_partition(self, file_id: str) -> str:
        """
        Create partition for a file

        Args:
            file_id: Unique file identifier

        Returns:
            Partition name (format: "file_{file_id}")

        Example:
            >>> partition_name = client.create_partition("abc123")
            >>> # partition_name = "file_abc123"
        """
        if not self._connected:
            self.connect()

        partition_name = f"file_{file_id}"

        # Check if partition already exists
        if self._collection.has_partition(partition_name):
            logger.debug(f"Partition '{partition_name}' already exists")
            return partition_name

        # Create new partition
        self._collection.create_partition(partition_name)
        logger.info(f"Created partition '{partition_name}' for file '{file_id}'")

        return partition_name

    def insert_vectors(
        self,
        file_id: str,
        texts: List[str],
        embeddings: List[List[float]],
        chunk_indices: Optional[List[int]] = None,
        timestamp: Optional[int] = None
    ) -> List[int]:
        """
        Insert vectors into file's partition

        Args:
            file_id: File identifier
            texts: List of text chunks
            embeddings: List of embedding vectors
            chunk_indices: Optional chunk indices (default: 0, 1, 2, ...)
            timestamp: Unix timestamp (default: current time)

        Returns:
            List of inserted entity IDs

        Example:
            >>> ids = client.insert_vectors(
            ...     file_id="abc123",
            ...     texts=["chunk1", "chunk2"],
            ...     embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]]
            ... )
        """
        if not self._connected:
            self.connect()

        # Create partition if not exists
        partition_name = self.create_partition(file_id)

        # Prepare data
        import time
        timestamp = timestamp or int(time.time())
        chunk_indices = chunk_indices or list(range(len(texts)))

        # Validate input lengths
        if not (len(texts) == len(embeddings) == len(chunk_indices)):
            raise ValueError(
                f"Length mismatch: texts({len(texts)}), "
                f"embeddings({len(embeddings)}), chunk_indices({len(chunk_indices)})"
            )

        # Prepare entities
        entities = [
            [file_id] * len(texts),  # file_id
            chunk_indices,            # chunk_index
            texts,                    # content
            embeddings,               # embedding
            [timestamp] * len(texts)  # timestamp
        ]

        # Insert into partition
        insert_result = self._collection.insert(
            data=entities,
            partition_name=partition_name
        )

        # Flush to ensure data persistence
        self._collection.flush()

        logger.info(
            f"Inserted {len(texts)} vectors into partition '{partition_name}' "
            f"(file_id='{file_id}')"
        )

        return insert_result.primary_keys

    def search(
        self,
        query_embedding: List[float],
        file_ids: Optional[List[str]] = None,
        top_k: int = 5,
        filters: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search

        Args:
            query_embedding: Query vector
            file_ids: Optional list of file IDs to search within
            top_k: Number of results to return
            filters: Optional filter expression (e.g., "chunk_index > 0")

        Returns:
            List of dicts with keys: id, file_id, chunk_index, content, score

        Example:
            >>> results = client.search(
            ...     query_embedding=[0.1, 0.2, ...],
            ...     file_ids=["abc123", "def456"],
            ...     top_k=5
            ... )
            >>> print(results[0]['content'], results[0]['score'])
        """
        if not self._connected:
            self.connect()

        # Determine partition names
        if file_ids:
            partition_names = [f"file_{fid}" for fid in file_ids]
        else:
            # Search all partitions
            partition_names = [p.name for p in self._collection.partitions if p.name != "_default"]

        if not partition_names:
            logger.warning("No partitions to search")
            return []

        # Search parameters
        search_params = {
            "metric_type": self.metric_type,
            "params": {"nprobe": min(16, self.nlist)}  # nprobe <= nlist
        }

        # Perform search
        try:
            search_results = self._collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=filters,
                partition_names=partition_names,
                output_fields=["file_id", "chunk_index", "content", "timestamp"]
            )

            # Format results
            results = []
            for hits in search_results:
                for hit in hits:
                    results.append({
                        "id": hit.id,
                        "file_id": hit.entity.get("file_id"),
                        "chunk_index": hit.entity.get("chunk_index"),
                        "content": hit.entity.get("content"),
                        "timestamp": hit.entity.get("timestamp"),
                        "score": float(hit.distance)
                    })

            logger.info(f"Search returned {len(results)} results from {len(partition_names)} partitions")
            return results

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    def delete_partition(self, file_id: str):
        """
        Delete partition for a file

        Args:
            file_id: File identifier

        Example:
            >>> client.delete_partition("abc123")
            >>> # Deletes partition "file_abc123"
        """
        if not self._connected:
            self.connect()

        partition_name = f"file_{file_id}"

        if not self._collection.has_partition(partition_name):
            logger.warning(f"Partition '{partition_name}' does not exist")
            return

        # Drop partition
        self._collection.drop_partition(partition_name)
        logger.info(f"Deleted partition '{partition_name}' for file '{file_id}'")

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics

        Returns:
            Dict with keys: row_count, partitions, index_type

        Example:
            >>> stats = client.get_collection_stats()
            >>> print(f"Total vectors: {stats['row_count']}")
        """
        if not self._connected:
            self.connect()

        stats = {
            "collection_name": self.collection_name,
            "row_count": self._collection.num_entities,
            "partitions": [p.name for p in self._collection.partitions],
            "index_type": self.index_type,
            "metric_type": self.metric_type,
            "dimension": self.dimension
        }

        return stats

    def disconnect(self):
        """
        Release collection and disconnect
        """
        if self._collection:
            self._collection.release()

        if self._connected:
            connections.disconnect(alias="default")
            self._connected = False
            logger.info("Disconnected from Milvus")

    def __del__(self):
        """Cleanup on garbage collection"""
        try:
            self.disconnect()
        except:
            pass


# Singleton instance for dependency injection
_milvus_client_instance: Optional[MilvusClient] = None


def get_milvus_client() -> MilvusClient:
    """
    FastAPI dependency for Milvus Client (Singleton)

    Usage in endpoints:
        @router.post("/upload")
        async def upload(
            milvus_client: MilvusClient = Depends(get_milvus_client)
        ):
            ...
    """
    global _milvus_client_instance

    if _milvus_client_instance is None:
        _milvus_client_instance = MilvusClient()
        _milvus_client_instance.connect()

    return _milvus_client_instance
