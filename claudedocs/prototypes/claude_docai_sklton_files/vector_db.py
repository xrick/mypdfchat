"""
Retrieval Providers - Vector database interface and Milvus implementation
"""
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from app.domain.models import VectorDBConfig, SemanticMatch
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


class VectorDBInterface(ABC):
    """Abstract vector database interface"""
    
    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_expr: Optional[str] = None
    ) -> List[SemanticMatch]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    async def insert(
        self,
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> bool:
        """Insert vectors with metadata"""
        pass


class MilvusVectorDB(VectorDBInterface):
    """Milvus vector database implementation"""
    
    def __init__(self, config: VectorDBConfig):
        """
        Initialize Milvus client
        
        Args:
            config: Vector database configuration
        """
        self.config = config
        self._client = None
        self._collection = None
        
    def _get_client(self):
        """Get or create Milvus client"""
        if self._client is None:
            try:
                from pymilvus import connections, Collection
                
                connections.connect(
                    alias="default",
                    host=self.config.host,
                    port=self.config.port
                )
                
                self._collection = Collection(self.config.collection_name)
                self._collection.load()
                
                logger.info(f"Connected to Milvus: {self.config.collection_name}")
            except ImportError:
                logger.error("pymilvus package not installed")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Milvus: {e}")
                raise
        
        return self._collection
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_expr: Optional[str] = None
    ) -> List[SemanticMatch]:
        """
        Search for similar vectors in Milvus
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_expr: Optional filter expression
            
        Returns:
            List of semantic matches
        """
        collection = self._get_client()
        
        try:
            search_params = {
                "metric_type": self.config.metric_type,
                "params": {"nprobe": 10}
            }
            
            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=["chunk_id", "product_id", "content", "metadata"]
            )
            
            matches = []
            for hits in results:
                for hit in hits:
                    match = SemanticMatch(
                        chunk_id=hit.entity.get("chunk_id", ""),
                        product_id=hit.entity.get("product_id", ""),
                        content=hit.entity.get("content", ""),
                        similarity_score=1.0 - hit.distance,  # Convert distance to similarity
                        metadata=hit.entity.get("metadata", {})
                    )
                    matches.append(match)
            
            return matches
            
        except Exception as e:
            logger.error(f"Milvus search error: {e}")
            return []
    
    async def insert(
        self,
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> bool:
        """
        Insert vectors with metadata into Milvus
        
        Args:
            vectors: List of embedding vectors
            metadata: List of metadata dictionaries
            
        Returns:
            Success status
        """
        collection = self._get_client()
        
        try:
            entities = []
            for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                entity = {
                    "embedding": vector,
                    "chunk_id": meta.get("chunk_id", f"chunk_{i}"),
                    "product_id": meta.get("product_id", ""),
                    "content": meta.get("content", ""),
                    "metadata": meta
                }
                entities.append(entity)
            
            collection.insert(entities)
            collection.flush()
            
            logger.info(f"Inserted {len(vectors)} vectors into Milvus")
            return True
            
        except Exception as e:
            logger.error(f"Milvus insert error: {e}")
            return False


class FAISSVectorDB(VectorDBInterface):
    """FAISS vector database implementation (lightweight alternative)"""
    
    def __init__(self, config: VectorDBConfig):
        """
        Initialize FAISS index
        
        Args:
            config: Vector database configuration
        """
        self.config = config
        self._index = None
        self._metadata = []
        
    def _get_index(self):
        """Get or create FAISS index"""
        if self._index is None:
            try:
                import faiss
                import numpy as np
                
                # Create L2 index
                self._index = faiss.IndexFlatL2(self.config.dimension)
                logger.info(f"Created FAISS index with dimension {self.config.dimension}")
            except ImportError:
                logger.error("faiss-cpu package not installed")
                raise
        
        return self._index
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_expr: Optional[str] = None
    ) -> List[SemanticMatch]:
        """
        Search for similar vectors in FAISS
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_expr: Optional filter expression (not implemented for FAISS)
            
        Returns:
            List of semantic matches
        """
        index = self._get_index()
        
        try:
            import numpy as np
            
            query_array = np.array([query_vector], dtype=np.float32)
            distances, indices = index.search(query_array, min(top_k, len(self._metadata)))
            
            matches = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self._metadata):
                    meta = self._metadata[idx]
                    match = SemanticMatch(
                        chunk_id=meta.get("chunk_id", ""),
                        product_id=meta.get("product_id", ""),
                        content=meta.get("content", ""),
                        similarity_score=1.0 / (1.0 + dist),  # Convert distance to similarity
                        metadata=meta
                    )
                    matches.append(match)
            
            return matches
            
        except Exception as e:
            logger.error(f"FAISS search error: {e}")
            return []
    
    async def insert(
        self,
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> bool:
        """
        Insert vectors with metadata into FAISS
        
        Args:
            vectors: List of embedding vectors
            metadata: List of metadata dictionaries
            
        Returns:
            Success status
        """
        index = self._get_index()
        
        try:
            import numpy as np
            
            vectors_array = np.array(vectors, dtype=np.float32)
            index.add(vectors_array)
            self._metadata.extend(metadata)
            
            logger.info(f"Inserted {len(vectors)} vectors into FAISS")
            return True
            
        except Exception as e:
            logger.error(f"FAISS insert error: {e}")
            return False
