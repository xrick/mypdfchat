"""
Main Application - FastAPI with OPMP Pipeline
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.presentation import http_stream
from app.services.core_logic import CoreLogicService
from app.services.phase1_query_understanding import Phase1QueryUnderstanding
from app.services.phase2_parallel_retrieval import Phase2ParallelRetrieval
from app.services.phase3_context_assembly import Phase3ContextAssembly
from app.services.phase4_response_generation import Phase4ResponseGeneration
from app.services.phase5_post_processing import Phase5PostProcessing
from app.llm_providers.openai_compat import OpenAICompatClient
from app.retrieval_providers.vector_db import MilvusVectorDB, FAISSVectorDB
from app.retrieval_providers.relational_db import DuckDBProvider
from app.infra.config import load_config
from app.infra.cache import RedisCache, InMemoryCache
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    
    Returns:
        Configured FastAPI app instance
    """
    # Load configuration
    config = load_config()
    
    # Initialize FastAPI
    app = FastAPI(
        title="LLM RAG Application",
        description="OPMP-based RAG system with progressive streaming",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize infrastructure
    logger.info("Initializing infrastructure...")
    
    # Cache
    if config.cache.enabled:
        try:
            cache = RedisCache(
                host=config.cache.host,
                port=config.cache.port
            )
            logger.info("Using Redis cache")
        except:
            cache = InMemoryCache()
            logger.warning("Redis unavailable, using in-memory cache")
    else:
        cache = InMemoryCache()
        logger.info("Using in-memory cache")
    
    # LLM Client
    llm_client = OpenAICompatClient(config.llm)
    logger.info(f"LLM client initialized: {config.llm.model}")
    
    # Vector Database
    try:
        if config.vectordb.provider == "milvus":
            vector_db = MilvusVectorDB(config.vectordb)
            logger.info("Using Milvus vector database")
        else:
            vector_db = FAISSVectorDB(config.vectordb)
            logger.info("Using FAISS vector database")
    except Exception as e:
        logger.warning(f"Vector DB initialization failed: {e}, using FAISS fallback")
        vector_db = FAISSVectorDB(config.vectordb)
    
    # Relational Database
    relational_db = DuckDBProvider(config.relationaldb)
    logger.info("DuckDB initialized")
    
    # Initialize Phase Services
    logger.info("Initializing OPMP phase services...")
    
    phase1 = Phase1QueryUnderstanding(
        llm_client=llm_client,
        cache=cache
    )
    
    phase2 = Phase2ParallelRetrieval(
        vector_db=vector_db,
        relational_db=relational_db,
        embedding_model=None,  # Will use default
        cache=cache
    )
    
    phase3 = Phase3ContextAssembly(
        max_context_tokens=config.max_context_tokens
    )
    
    phase4 = Phase4ResponseGeneration(
        llm_client=llm_client,
        cache=cache
    )
    
    phase5 = Phase5PostProcessing()
    
    # Initialize Core Logic Service
    core_service = CoreLogicService(
        phase1=phase1,
        phase2=phase2,
        phase3=phase3,
        phase4=phase4,
        phase5=phase5
    )
    
    # Inject into router
    http_stream.core_service = core_service
    
    # Register routes
    app.include_router(http_stream.router, prefix="/api", tags=["chat"])
    
    logger.info("Application initialized successfully")
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("🚀 LLM RAG Application started")
        logger.info(f"📊 OPMP Pipeline: 5 phases active")
        logger.info(f"🤖 LLM Model: {config.llm.model}")
        logger.info(f"💾 Vector DB: {config.vectordb.provider}")
        logger.info(f"📦 Cache: {config.cache.provider}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Application shutting down...")
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
