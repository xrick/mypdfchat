"""
Phase 2: Parallel Multi-source Data Retrieval
Performs parallel retrieval from vector database (Milvus) and relational database (DuckDB)
"""
import asyncio
from datetime import datetime
from typing import AsyncIterator, Dict, Any, List, Optional
from app.domain.models import (
    Phase2RetrievalResults, SemanticMatch, SpecData, MergedProduct,
    ProgressMessage, PhaseResultMessage
)
from app.retrieval_providers.vector_db import VectorDBInterface
from app.retrieval_providers.relational_db import RelationalDBInterface
from app.infra.cache import CacheInterface, create_cache_key
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


class Phase2ParallelRetrieval:
    """
    Phase 2: Parallel Multi-source Data Retrieval Service
    
    Responsibilities:
    - Parallel retrieval from vector database (semantic search)
    - Parallel retrieval from relational database (structured query)
    - Merge and deduplicate results
    - Rank by relevance
    """
    
    def __init__(
        self,
        vector_db: VectorDBInterface,
        relational_db: RelationalDBInterface,
        embedding_model: Any,  # Model for generating embeddings
        cache: Optional[CacheInterface] = None
    ):
        """
        Initialize Phase 2 service
        
        Args:
            vector_db: Vector database interface
            relational_db: Relational database interface
            embedding_model: Model for generating query embeddings
            cache: Optional cache interface
        """
        self.vector_db = vector_db
        self.relational_db = relational_db
        self.embedding_model = embedding_model
        self.cache = cache
    
    async def retrieve(
        self,
        query: str,
        detected_products: Optional[List[str]] = None,
        top_k: int = 30
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Perform parallel retrieval from multiple sources
        
        Args:
            query: User query string
            detected_products: List of detected product models/types
            top_k: Number of results to retrieve
            
        Yields:
            Progress and result messages
        """
        phase_start = datetime.now()
        
        # Yield initial progress
        yield ProgressMessage(
            phase=2,
            message="Starting parallel data retrieval...",
            progress=25
        ).model_dump()
        
        # Check cache
        cache_key = create_cache_key(
            "phase2",
            query,
            detected_products=detected_products or [],
            top_k=top_k
        )
        
        if self.cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info("Phase 2: Using cached retrieval results")
                cached_result["from_cache"] = True
                
                yield PhaseResultMessage(
                    phase=2,
                    data=cached_result,
                    progress=40
                ).model_dump()
                return
        
        # Parallel retrieval
        yield ProgressMessage(
            phase=2,
            message="Executing parallel searches (Milvus + DuckDB)...",
            progress=30
        ).model_dump()
        
        # Execute both retrievals in parallel
        semantic_task = self._retrieve_from_milvus(query, top_k)
        structured_task = self._retrieve_from_duckdb(detected_products, top_k)
        
        semantic_matches, spec_data = await asyncio.gather(
            semantic_task,
            structured_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(semantic_matches, Exception):
            logger.error(f"Milvus retrieval failed: {semantic_matches}")
            semantic_matches = []
        
        if isinstance(spec_data, Exception):
            logger.error(f"DuckDB retrieval failed: {spec_data}")
            spec_data = []
        
        yield ProgressMessage(
            phase=2,
            message="Merging and deduplicating results...",
            progress=35
        ).model_dump()
        
        # Merge results
        merged_products = self._merge_results(semantic_matches, spec_data)
        
        # Calculate metrics
        retrieval_time = (datetime.now() - phase_start).total_seconds()
        
        result = Phase2RetrievalResults(
            semantic_matches=semantic_matches,
            spec_data=spec_data,
            merged_products=merged_products,
            total_semantic=len(semantic_matches),
            total_specs=len(spec_data),
            total_merged=len(merged_products),
            retrieval_time=retrieval_time,
            cache_used=False,
            from_cache=False
        )
        
        logger.info(
            f"Phase 2 completed in {retrieval_time:.2f}s: "
            f"{len(semantic_matches)} semantic + {len(spec_data)} specs = "
            f"{len(merged_products)} merged"
        )
        
        # Cache result
        if self.cache:
            await self.cache.set(cache_key, result.model_dump(), ttl=300)
        
        # Yield final result
        yield PhaseResultMessage(
            phase=2,
            data=result.model_dump(),
            progress=40
        ).model_dump()
    
    async def _retrieve_from_milvus(
        self,
        query: str,
        top_k: int
    ) -> List[SemanticMatch]:
        """
        Retrieve from Milvus vector database
        
        Args:
            query: Query string
            top_k: Number of results
            
        Returns:
            List of semantic matches
        """
        try:
            # Generate query embedding
            query_vector = await self._generate_embedding(query)
            
            # Search vector database
            matches = await self.vector_db.search(
                query_vector=query_vector,
                top_k=top_k
            )
            
            logger.info(f"Milvus retrieval: {len(matches)} results")
            return matches
            
        except Exception as e:
            logger.error(f"Milvus retrieval error: {e}")
            return []
    
    async def _retrieve_from_duckdb(
        self,
        detected_products: Optional[List[str]],
        top_k: int
    ) -> List[SpecData]:
        """
        Retrieve from DuckDB relational database
        
        Args:
            detected_products: List of product models/types
            top_k: Number of results
            
        Returns:
            List of specification data
        """
        try:
            if detected_products:
                # Query by specific products
                spec_data = await self.relational_db.query_by_modeltypes(
                    modeltypes=detected_products
                )
            else:
                # Query all with limit
                spec_data = await self.relational_db.query_all(limit=top_k)
            
            logger.info(f"DuckDB retrieval: {len(spec_data)} results")
            return spec_data
            
        except Exception as e:
            logger.error(f"DuckDB retrieval error: {e}")
            return []
    
    def _merge_results(
        self,
        semantic_matches: List[SemanticMatch],
        spec_data: List[SpecData]
    ) -> List[MergedProduct]:
        """
        Merge semantic and structured data, deduplicate by modelname
        
        Args:
            semantic_matches: Semantic search results
            spec_data: Structured specification data
            
        Returns:
            List of merged products
        """
        # Create lookup by modelname for deduplication
        merged_dict: Dict[str, MergedProduct] = {}
        
        # First, add all spec data
        for spec in spec_data:
            merged_dict[spec.modelname] = MergedProduct(
                modelname=spec.modelname,
                modeltype=spec.modeltype,
                specs=spec.specs,
                source="database"
            )
        
        # Then, enhance with semantic information
        for match in semantic_matches:
            modelname = match.metadata.get("modelname", match.product_id)
            
            if modelname in merged_dict:
                # Enhance existing entry
                merged_dict[modelname].semantic_score = match.similarity_score
                merged_dict[modelname].semantic_content = match.content
                merged_dict[modelname].source = "semantic+spec"
            else:
                # Create new entry from semantic data
                merged_dict[modelname] = MergedProduct(
                    modelname=modelname,
                    modeltype=match.product_id,
                    specs=match.metadata,
                    semantic_score=match.similarity_score,
                    semantic_content=match.content,
                    source="semantic"
                )
        
        # Convert to list and sort by semantic score
        merged_list = list(merged_dict.values())
        merged_list.sort(
            key=lambda x: x.semantic_score if x.semantic_score else 0.0,
            reverse=True
        )
        
        return merged_list
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        try:
            # Use sentence-transformers for embedding generation
            from sentence_transformers import SentenceTransformer
            
            if not hasattr(self, '_embedding_model_instance'):
                self._embedding_model_instance = SentenceTransformer('all-MiniLM-L6-v2')
            
            embedding = self._embedding_model_instance.encode(text, convert_to_numpy=True)
            return embedding.tolist()
            
        except ImportError:
            logger.warning("sentence-transformers not installed, using random embedding")
            import random
            return [random.random() for _ in range(384)]
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise
