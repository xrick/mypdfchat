"""
Chunking Strategies using Strategy and Factory Design Patterns

Implements multiple text chunking strategies for RAG applications:
- Recursive Character Splitting (baseline)
- Hierarchical Indexing (multi-level with parent-child relationships)

Future strategies can be added by extending ChunkingStrategy base class.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.storage import InMemoryStore
from langchain.docstore.document import Document
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# Strategy Pattern: Base Class
# =============================================================================

class ChunkingStrategy(ABC):
    """
    Abstract base class for chunking strategies

    All chunking strategies must implement the chunk() method.
    """

    def __init__(self, **kwargs):
        """
        Initialize strategy with configuration

        Args:
            **kwargs: Strategy-specific configuration
        """
        self.config = kwargs

    @abstractmethod
    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk text according to strategy

        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of chunk dicts with keys:
            - content: Chunk text
            - metadata: Chunk metadata
            - chunk_index: Position in document
            - (strategy-specific fields)
        """
        pass

    def get_strategy_name(self) -> str:
        """Return strategy name"""
        return self.__class__.__name__


# =============================================================================
# Strategy 1: Recursive Character Splitting (Baseline)
# =============================================================================

class RecursiveChunkingStrategy(ChunkingStrategy):
    """
    Standard recursive character text splitting

    Uses LangChain's RecursiveCharacterTextSplitter with configurable
    separators, chunk size, and overlap.

    Best for: General-purpose document chunking
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len
        )

        logger.info(
            f"Recursive Chunking Strategy initialized: "
            f"size={chunk_size}, overlap={chunk_overlap}"
        )

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk text using recursive character splitting

        Args:
            text: Input text
            metadata: Optional base metadata

        Returns:
            List of chunk dicts

        Example:
            >>> strategy = RecursiveChunkingStrategy(chunk_size=1000)
            >>> chunks = strategy.chunk(text)
            >>> print(len(chunks))
        """
        try:
            # Split text
            text_chunks = self.splitter.split_text(text)

            # Build chunk dicts
            chunks = []
            for i, chunk_text in enumerate(text_chunks):
                chunk = {
                    "content": chunk_text.strip(),
                    "chunk_index": i,
                    "metadata": {
                        **(metadata or {}),
                        "chunking_strategy": "recursive",
                        "chunk_size": self.chunk_size,
                        "chunk_overlap": self.chunk_overlap
                    }
                }
                chunks.append(chunk)

            logger.info(f"Recursive chunking: {len(chunks)} chunks generated")
            return chunks

        except Exception as e:
            logger.error(f"Recursive chunking failed: {str(e)}")
            raise


# =============================================================================
# Strategy 2: Hierarchical Indexing (Multi-Level)
# =============================================================================

class HierarchicalChunkingStrategy(ChunkingStrategy):
    """
    Hierarchical multi-level chunking with parent-child relationships

    Creates multiple granularity levels:
    - Level 0 (Parent): Large chunks for context (e.g., 2000 chars)
    - Level 1 (Child): Medium chunks for retrieval (e.g., 1000 chars)
    - Level 2 (Grandchild): Small chunks for precise matching (e.g., 500 chars)

    Benefits:
    - Retrieve small chunks for precision
    - Access parent chunks for broader context
    - Better handling of long documents

    Compatible with LangChain's MultiVectorRetriever.

    Best for: Long documents, technical papers, reports
    """

    def __init__(
        self,
        chunk_sizes: Optional[List[int]] = None,
        overlap: int = 100,
        separators: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        # Default: [Parent, Child, Grandchild]
        self.chunk_sizes = chunk_sizes or [2000, 1000, 500]
        self.overlap = overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

        # Create splitter for each level
        self.splitters = [
            RecursiveCharacterTextSplitter(
                chunk_size=size,
                chunk_overlap=overlap,
                separators=self.separators,
                length_function=len
            )
            for size in self.chunk_sizes
        ]

        logger.info(
            f"Hierarchical Chunking Strategy initialized: "
            f"levels={len(self.chunk_sizes)}, sizes={self.chunk_sizes}, overlap={overlap}"
        )

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk text hierarchically with parent-child relationships

        Args:
            text: Input text
            metadata: Optional base metadata

        Returns:
            List of chunk dicts with hierarchical metadata

        Example:
            >>> strategy = HierarchicalChunkingStrategy(chunk_sizes=[2000, 1000, 500])
            >>> chunks = strategy.chunk(text)
            >>> # Chunks have parent_id, level, and children relationships
        """
        try:
            all_chunks = []
            chunk_id_map = {}  # Map level -> chunk_index -> chunk_id

            # Process each hierarchical level
            for level, splitter in enumerate(self.splitters):
                level_chunks = splitter.split_text(text)
                chunk_id_map[level] = {}

                for local_idx, chunk_text in enumerate(level_chunks):
                    # Generate unique chunk ID
                    chunk_id = str(uuid.uuid4())
                    chunk_id_map[level][local_idx] = chunk_id

                    # Determine parent chunk ID (from previous level)
                    parent_id = None
                    if level > 0:
                        # Find parent by position overlap
                        parent_level = level - 1
                        parent_idx = self._find_parent_index(
                            local_idx,
                            len(level_chunks),
                            len(chunk_id_map[parent_level])
                        )
                        parent_id = chunk_id_map[parent_level].get(parent_idx)

                    # Build chunk dict
                    chunk = {
                        "content": chunk_text.strip(),
                        "chunk_id": chunk_id,
                        "chunk_index": len(all_chunks),  # Global index
                        "level": level,
                        "level_index": local_idx,  # Index within level
                        "parent_id": parent_id,
                        "metadata": {
                            **(metadata or {}),
                            "chunking_strategy": "hierarchical",
                            "level": level,
                            "level_name": self._get_level_name(level),
                            "chunk_size": self.chunk_sizes[level],
                            "parent_id": parent_id
                        }
                    }

                    all_chunks.append(chunk)

            logger.info(
                f"Hierarchical chunking: {len(all_chunks)} chunks across "
                f"{len(self.chunk_sizes)} levels"
            )

            return all_chunks

        except Exception as e:
            logger.error(f"Hierarchical chunking failed: {str(e)}")
            raise

    def _find_parent_index(
        self,
        child_idx: int,
        child_count: int,
        parent_count: int
    ) -> int:
        """
        Determine which parent chunk this child belongs to

        Args:
            child_idx: Child chunk index
            child_count: Total number of child chunks
            parent_count: Total number of parent chunks

        Returns:
            Parent chunk index

        Logic:
        - Distribute children evenly among parents
        - Example: 10 children, 5 parents → 2 children per parent
        """
        if parent_count == 0:
            return 0

        children_per_parent = max(1, child_count / parent_count)
        parent_idx = int(child_idx / children_per_parent)

        # Ensure within bounds
        return min(parent_idx, parent_count - 1)

    def _get_level_name(self, level: int) -> str:
        """
        Get human-readable name for hierarchical level

        Args:
            level: Level index (0, 1, 2, ...)

        Returns:
            Level name ("parent", "child", "grandchild", "level_N")
        """
        names = ["parent", "child", "grandchild"]
        if level < len(names):
            return names[level]
        return f"level_{level}"

    def get_multivector_config(self) -> Dict[str, Any]:
        """
        Get configuration for LangChain MultiVectorRetriever

        Returns:
            Dict with configuration for MultiVectorRetriever setup

        Example:
            >>> config = strategy.get_multivector_config()
            >>> retriever = MultiVectorRetriever(**config)
        """
        return {
            "vector_store": None,  # To be set by caller
            "doc_store": InMemoryStore(),
            "id_key": "chunk_id",
            "search_kwargs": {"k": 5}
        }


# =============================================================================
# Factory Pattern: Strategy Selection
# =============================================================================

class ChunkingStrategyFactory:
    """
    Factory for creating chunking strategies

    Provides centralized strategy instantiation with configuration.

    Usage:
        >>> factory = ChunkingStrategyFactory()
        >>> strategy = factory.create("hierarchical", chunk_sizes=[2000, 1000])
        >>> chunks = strategy.chunk(text)
    """

    _strategies = {
        "recursive": RecursiveChunkingStrategy,
        "hierarchical": HierarchicalChunkingStrategy
    }

    @classmethod
    def create(
        cls,
        strategy_name: str,
        **kwargs
    ) -> ChunkingStrategy:
        """
        Create chunking strategy by name

        Args:
            strategy_name: Strategy name ("recursive" or "hierarchical")
            **kwargs: Strategy-specific configuration

        Returns:
            ChunkingStrategy instance

        Raises:
            ValueError: If strategy name not recognized

        Example:
            >>> strategy = ChunkingStrategyFactory.create("hierarchical")
            >>> chunks = strategy.chunk(text)
        """
        strategy_class = cls._strategies.get(strategy_name.lower())

        if strategy_class is None:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown chunking strategy: '{strategy_name}'. "
                f"Available: {available}"
            )

        logger.info(f"Creating chunking strategy: {strategy_name}")
        return strategy_class(**kwargs)

    @classmethod
    def register_strategy(
        cls,
        name: str,
        strategy_class: type
    ):
        """
        Register custom chunking strategy

        Args:
            name: Strategy name
            strategy_class: ChunkingStrategy subclass

        Example:
            >>> class MyStrategy(ChunkingStrategy):
            ...     def chunk(self, text, metadata):
            ...         return [...]
            >>> ChunkingStrategyFactory.register_strategy("my_strategy", MyStrategy)
        """
        if not issubclass(strategy_class, ChunkingStrategy):
            raise TypeError("Strategy class must inherit from ChunkingStrategy")

        cls._strategies[name.lower()] = strategy_class
        logger.info(f"Registered custom chunking strategy: {name}")

    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        List all available strategy names

        Returns:
            List of strategy names

        Example:
            >>> ChunkingStrategyFactory.list_strategies()
            >>> ['recursive', 'hierarchical']
        """
        return list(cls._strategies.keys())


# =============================================================================
# Convenience Functions
# =============================================================================

def get_default_strategy() -> ChunkingStrategy:
    """
    Get default chunking strategy from settings

    Returns:
        Configured ChunkingStrategy instance

    Example:
        >>> strategy = get_default_strategy()
        >>> chunks = strategy.chunk(text)
    """
    from app.core.config import settings

    if settings.CHUNKING_STRATEGY == "hierarchical":
        return ChunkingStrategyFactory.create(
            "hierarchical",
            chunk_sizes=settings.HIERARCHICAL_CHUNK_SIZES,
            overlap=settings.HIERARCHICAL_OVERLAP
        )
    else:
        return ChunkingStrategyFactory.create(
            "recursive",
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=settings.CHUNK_SEPARATORS
        )
