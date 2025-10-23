"""
Domain Models - Pydantic models for state management and DTOs
"""
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ProcessingPhase(str, Enum):
    """OPMP Processing Phases"""
    PHASE_1_QUERY_UNDERSTANDING = "phase_1_query_understanding"
    PHASE_2_RETRIEVAL = "phase_2_retrieval"
    PHASE_3_CONTEXT_ASSEMBLY = "phase_3_context_assembly"
    PHASE_4_GENERATION = "phase_4_generation"
    PHASE_5_POSTPROCESSING = "phase_5_postprocessing"
    COMPLETED = "completed"
    ERROR = "error"


class QueryIntent(str, Enum):
    """User query intent types"""
    COMPARE = "compare"
    RECOMMEND = "recommend"
    SPEC_QUERY = "spec_query"
    GENERAL_INQUIRY = "general_inquiry"


class ConfidenceLevel(str, Enum):
    """Confidence level for analysis"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Complexity(str, Enum):
    """Query complexity level"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


# ============= Phase 1: Query Understanding =============

class Phase1Analysis(BaseModel):
    """Output from Phase 1: Query Understanding & Entity Extraction"""
    intent: QueryIntent
    detected_products: List[str] = Field(default_factory=list)
    detected_modeltypes: List[str] = Field(default_factory=list)
    key_features: List[str] = Field(default_factory=list)
    user_focus: str = ""
    complexity: Complexity = Complexity.SIMPLE
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    from_cache: bool = False
    processing_time: float = 0.0


# ============= Phase 2: Data Retrieval =============

class SemanticMatch(BaseModel):
    """Semantic search result from vector database"""
    chunk_id: str
    product_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SpecData(BaseModel):
    """Structured specification data from relational database"""
    modeltype: str
    modelname: str
    specs: Dict[str, Any] = Field(default_factory=dict)
    source: str = "database"


class MergedProduct(BaseModel):
    """Merged product data from both semantic and structured sources"""
    modelname: str
    modeltype: str
    specs: Dict[str, Any] = Field(default_factory=dict)
    semantic_score: Optional[float] = None
    semantic_content: Optional[str] = None
    source: str = "merged"


class Phase2RetrievalResults(BaseModel):
    """Output from Phase 2: Parallel Multi-source Data Retrieval"""
    semantic_matches: List[SemanticMatch] = Field(default_factory=list)
    spec_data: List[SpecData] = Field(default_factory=list)
    merged_products: List[MergedProduct] = Field(default_factory=list)
    total_semantic: int = 0
    total_specs: int = 0
    total_merged: int = 0
    retrieval_time: float = 0.0
    cache_used: bool = False
    from_cache: bool = False


# ============= Phase 3: Context Assembly =============

class RankedProduct(BaseModel):
    """Ranked and filtered product for context"""
    modelname: str
    modeltype: str
    specs: Dict[str, Any] = Field(default_factory=dict)
    relevance_score: float = 0.0
    semantic_content: Optional[str] = None
    rank: int = 0


class Phase3Context(BaseModel):
    """Output from Phase 3: Context Assembly & Ranking"""
    products: List[RankedProduct] = Field(default_factory=list)
    token_count: int = 0
    truncation_applied: bool = False
    original_count: int = 0
    kept_count: int = 0
    from_cache: bool = False
    processing_time: float = 0.0


# ============= Phase 4: Response Generation =============

class StreamingToken(BaseModel):
    """Individual token from streaming generation"""
    token: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Phase4GeneratedResponse(BaseModel):
    """Output from Phase 4: Response Generation"""
    response: str
    tokens_generated: int = 0
    generation_time: float = 0.0
    model_used: str = ""
    from_cache: bool = False


# ============= Phase 5: Post-processing =============

class ResponseSource(BaseModel):
    """Source attribution for response"""
    product_id: str
    product_name: str
    source_type: str = "database"
    relevance_score: float = 0.0


class ResponseMetadata(BaseModel):
    """Metadata for the final response"""
    model: str
    timestamp: datetime = Field(default_factory=datetime.now)
    phase_timings: Dict[int, float] = Field(default_factory=dict)
    total_time: float = 0.0


class QualityMetrics(BaseModel):
    """Quality assessment metrics"""
    score: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    passed: bool = True


class Phase5ResponsePackage(BaseModel):
    """Final output from Phase 5: Post-processing & Formatting"""
    response: str
    metadata: ResponseMetadata
    sources: List[ResponseSource] = Field(default_factory=list)
    query: str
    timestamp: datetime = Field(default_factory=datetime.now)
    quality: QualityMetrics


# ============= State Management =============

class ConversationState(BaseModel):
    """Overall conversation state tracking"""
    session_id: str
    current_phase: ProcessingPhase = ProcessingPhase.PHASE_1_QUERY_UNDERSTANDING
    query: str = ""
    phase1_result: Optional[Phase1Analysis] = None
    phase2_result: Optional[Phase2RetrievalResults] = None
    phase3_result: Optional[Phase3Context] = None
    phase4_result: Optional[Phase4GeneratedResponse] = None
    phase5_result: Optional[Phase5ResponsePackage] = None
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


# ============= SSE Messages =============

class SSEMessage(BaseModel):
    """Server-Sent Events message format"""
    type: str
    phase: Optional[int] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    progress: Optional[int] = None
    from_cache: bool = False
    token: Optional[str] = None


class ProgressMessage(SSEMessage):
    """Progress update message"""
    type: str = "progress"
    phase: int
    message: str
    progress: int


class PhaseResultMessage(SSEMessage):
    """Phase completion result message"""
    type: str = "phase_result"
    phase: int
    data: Dict[str, Any]
    progress: int


class MarkdownTokenMessage(SSEMessage):
    """Streaming markdown token message"""
    type: str = "markdown_token"
    token: str
    phase: int = 4


class CompleteMessage(SSEMessage):
    """Final completion message"""
    type: str = "complete"
    phase: int = 5
    data: Dict[str, Any]
    progress: int = 100


class ErrorMessage(SSEMessage):
    """Error message"""
    type: str = "error"
    message: str
    phase: Optional[int] = None
    partial_results: bool = False
    phase_timings: Optional[Dict[int, float]] = None


# ============= Configuration Models =============

class LLMConfig(BaseModel):
    """LLM provider configuration"""
    provider: str = "openai"
    base_url: str = "http://localhost:11434"
    model: str = "llama3:8b-instruct"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    streaming: bool = True


class VectorDBConfig(BaseModel):
    """Vector database configuration"""
    provider: str = "milvus"
    host: str = "localhost"
    port: int = 19530
    collection_name: str = "product_embeddings"
    dimension: int = 768
    metric_type: str = "L2"


class RelationalDBConfig(BaseModel):
    """Relational database configuration"""
    provider: str = "duckdb"
    database_path: str = "./data/products.db"
    table_name: str = "products"


class CacheConfig(BaseModel):
    """Cache configuration"""
    enabled: bool = True
    provider: str = "redis"
    host: str = "localhost"
    port: int = 6379
    ttl_phase1: int = 300  # 5 minutes
    ttl_phase2: int = 300  # 5 minutes
    ttl_phase4: int = 1800  # 30 minutes


class AppConfig(BaseModel):
    """Application configuration"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)
    relationaldb: RelationalDBConfig = Field(default_factory=RelationalDBConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    max_context_tokens: int = 8000
    top_k_retrieval: int = 30
