# app/models/internal.py
"""
Internal Data Models for Layer-to-Layer Communication

Uses TypedDict for type-safe dict-based communication between:
- Provider ↔ Provider
- Service ↔ Provider
- Service ↔ Service
- Endpoint ↔ Service

TypedDict provides:
- Runtime dict compatibility (no conversion needed)
- Type hints for IDE support
- Validation through type checkers (mypy)
- Zero runtime overhead
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from datetime import datetime


# =============================================================================
# File Processing Data Models
# =============================================================================

class ChunkData(TypedDict, total=False):
    """
    Individual text chunk with metadata

    Used by: chunking_strategies → input_data_handle_service → retrieval_service
    """
    content: str                    # Required: Chunk text content
    chunk_index: int                # Required: Position in document
    metadata: Dict[str, Any]        # Required: Chunk metadata

    # Optional hierarchical fields
    parent_chunk_index: Optional[int]
    children_chunk_indices: Optional[List[int]]
    level: Optional[int]            # Hierarchy level (0=parent, 1=child, 2=grandchild)


class ProcessingResult(TypedDict):
    """
    File processing pipeline result

    Used by: input_data_handle_service → upload endpoint
    """
    file_id: str
    filename: str
    file_size: int
    chunks: List[ChunkData]
    chunk_count: int
    chunking_strategy: str
    extracted_text_length: int
    processing_time_ms: Optional[float]


class ValidationResult(TypedDict):
    """
    File validation result

    Used by: input_data_handle_service.validate_file()
    """
    is_valid: bool
    error_message: Optional[str]
    file_size: Optional[int]
    file_type: Optional[str]


# =============================================================================
# Vector Store Data Models
# =============================================================================

class VectorSearchResult(TypedDict):
    """
    Single vector search result

    Used by: vector_store_provider → retrieval_service
    """
    content: str
    score: float
    metadata: Dict[str, Any]

    # Optional fields
    file_id: Optional[str]
    chunk_index: Optional[int]
    milvus_id: Optional[int]


class EmbeddingData(TypedDict):
    """
    Embedding generation result

    Used by: embedding_provider → vector_store_provider
    """
    embeddings: List[List[float]]   # List of embedding vectors
    texts: List[str]                # Corresponding texts
    model_name: str
    dimension: int


# =============================================================================
# Query Enhancement Data Models
# =============================================================================

class QueryExpansionResult(TypedDict):
    """
    Query expansion result from Strategy 2

    Used by: query_enhancement_service → chat endpoint
    """
    original_query: str
    intent: str
    expanded_questions: List[str]
    reasoning: Optional[str]
    cache_hit: bool
    processing_time_ms: Optional[float]


class QueryAnalysis(TypedDict, total=False):
    """
    Detailed query analysis

    Used internally by: query_enhancement_service
    """
    query: str
    intent: Literal["definition_seeking", "how_to", "comparison", "explanation", "troubleshooting"]
    complexity: Literal["simple", "moderate", "complex"]
    keywords: List[str]
    entities: List[str]


# =============================================================================
# Chat History Data Models
# =============================================================================

class MessageData(TypedDict):
    """
    Single conversation message

    Used by: chat_history_provider → prompt_service
    """
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]]


class SessionData(TypedDict):
    """
    Complete session information

    Used by: chat_history_provider
    """
    session_id: str
    user_id: Optional[str]
    messages: List[MessageData]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]]


# =============================================================================
# File Metadata Data Models
# =============================================================================

class FileMetadata(TypedDict):
    """
    File metadata record

    Used by: file_metadata_provider → upload endpoint
    """
    file_id: str
    filename: str
    file_type: str
    file_size: int
    upload_time: datetime
    user_id: Optional[str]
    chunk_count: int
    embedding_status: Literal["pending", "completed", "failed"]
    milvus_partition: str
    metadata_json: Optional[str]


class ChunkMetadata(TypedDict):
    """
    Individual chunk metadata

    Used by: file_metadata_provider (optional tracking)
    """
    chunk_id: str
    file_id: str
    chunk_index: int
    chunk_text: str
    milvus_id: Optional[int]


# =============================================================================
# LLM Provider Data Models
# =============================================================================

class LLMMessage(TypedDict):
    """
    LLM message format (OpenAI-compatible)

    Used by: prompt_service → llm_provider
    """
    role: Literal["system", "user", "assistant"]
    content: str


class LLMResponse(TypedDict):
    """
    LLM completion response

    Used by: llm_provider → chat endpoint
    """
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]]
    model: str
    created: Optional[int]


class LLMStreamChunk(TypedDict):
    """
    LLM streaming chunk

    Used by: llm_provider → chat endpoint (SSE)
    """
    choices: List[Dict[str, Any]]
    delta: Optional[Dict[str, str]]
    finish_reason: Optional[str]


# =============================================================================
# Cache Data Models
# =============================================================================

class CacheEntry(TypedDict):
    """
    Cache entry structure

    Used by: cache_provider → query_enhancement_service
    """
    key: str
    value: Any
    ttl: Optional[int]              # Time to live in seconds
    created_at: Optional[datetime]


class CacheStats(TypedDict):
    """
    Cache statistics

    Used by: cache_provider (monitoring)
    """
    hits: int
    misses: int
    hit_rate: float
    total_keys: int
    memory_usage_mb: Optional[float]


# =============================================================================
# Retrieval Data Models
# =============================================================================

class RetrievalContext(TypedDict):
    """
    Retrieved context for RAG

    Used by: retrieval_service → prompt_service
    """
    chunks: List[VectorSearchResult]
    total_chunks: int
    query: str
    file_ids: List[str]
    retrieval_time_ms: Optional[float]


class DocumentAddResult(TypedDict):
    """
    Document addition result

    Used by: retrieval_service → upload endpoint
    """
    store_id: str
    file_id: str
    chunks_added: int
    embeddings_generated: int
    status: Literal["success", "partial", "failed"]


# =============================================================================
# Prompt Assembly Data Models
# =============================================================================

class PromptContext(TypedDict):
    """
    Complete prompt context for RAG

    Used by: prompt_service.build_rag_prompt()
    """
    system_prompt: str
    user_query: str
    context_chunks: List[str]
    chat_history: List[MessageData]
    metadata: Dict[str, Any]


class PromptMessages(TypedDict):
    """
    Assembled prompt messages

    Used by: prompt_service → llm_provider
    """
    messages: List[LLMMessage]
    total_tokens_estimate: Optional[int]
    context_chunks_count: int


# =============================================================================
# Error Handling Data Models
# =============================================================================

class ErrorDetail(TypedDict):
    """
    Structured error detail

    Used by: All layers for error propagation
    """
    error: str                      # Error type/category
    message: str                    # Human-readable message
    details: Dict[str, Any]         # Additional context
    timestamp: datetime
    layer: Literal["provider", "service", "endpoint"]
    traceback: Optional[str]


# =============================================================================
# System Status Data Models
# =============================================================================

class ServiceHealth(TypedDict):
    """
    Individual service health status

    Used by: Health check endpoint
    """
    service_name: str
    status: Literal["healthy", "degraded", "unhealthy"]
    response_time_ms: Optional[float]
    error: Optional[str]
    last_check: datetime


class SystemHealth(TypedDict):
    """
    Overall system health

    Used by: Health check endpoint
    """
    status: Literal["healthy", "degraded", "unhealthy"]
    services: Dict[str, ServiceHealth]
    version: str
    uptime_seconds: float
    timestamp: datetime


# =============================================================================
# Usage Examples (Documentation)
# =============================================================================

"""
Example 1: File Processing Pipeline
------------------------------------

# Step 1: Service processes file
result: ProcessingResult = await input_service.process_file(content, filename)

# Step 2: Retrieval service adds chunks
add_result: DocumentAddResult = await retrieval_service.add_document_chunks(
    file_id=result['file_id'],
    chunks=[chunk['content'] for chunk in result['chunks']],
    metadata=[chunk['metadata'] for chunk in result['chunks']]
)

# Step 3: File metadata provider stores info
await file_metadata_provider.add_file(
    file_id=result['file_id'],
    filename=result['filename'],
    file_size=result['file_size'],
    chunk_count=result['chunk_count']
)


Example 2: Query Enhancement → Retrieval
----------------------------------------

# Step 1: Enhance query
expansion: QueryExpansionResult = await query_enhancement_service.expand_query(
    query=user_query,
    cache_provider=cache_provider
)

# Step 2: Retrieve for each expanded question
all_results: List[List[VectorSearchResult]] = []
for question in expansion['expanded_questions']:
    results = await retrieval_service.retrieve_context(
        query=question,
        file_ids=selected_files,
        top_k=5
    )
    all_results.append(results)


Example 3: Prompt Assembly → LLM Generation
-------------------------------------------

# Step 1: Assemble prompt
prompt_messages: PromptMessages = prompt_service.build_rag_prompt(
    query=user_query,
    context_chunks=[result['content'] for result in search_results],
    chat_history=session['messages']
)

# Step 2: Generate response
response: LLMResponse = await llm_provider.get_chat_completion(
    messages=prompt_messages['messages'],
    temperature=0.7
)


Example 4: Error Propagation
-----------------------------

try:
    result = await some_provider.operation()
except Exception as e:
    error: ErrorDetail = {
        'error': 'ProviderError',
        'message': str(e),
        'details': {'provider': 'vector_store', 'operation': 'search'},
        'timestamp': datetime.now(timezone.utc),
        'layer': 'provider',
        'traceback': traceback.format_exc()
    }
    logger.error(f"Provider error: {error}")
    raise
"""
