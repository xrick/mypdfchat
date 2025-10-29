# Implementation Plan - API Router & Enterprise Providers

## 📋 Implementation Strategy

### Phase 1: Enterprise Providers (Foundation)
**Priority**: CRITICAL
**Estimated Time**: 4-6 hours
**Dependencies**: None (can be done in parallel)

### Phase 2: Services Layer (Business Logic)
**Priority**: HIGH
**Estimated Time**: 6-8 hours
**Dependencies**: Phase 1 complete

### Phase 3: API Layer (REST Endpoints)
**Priority**: HIGH
**Estimated Time**: 4-5 hours
**Dependencies**: Phase 1 & 2 complete

### Phase 4: Integration & Testing
**Priority**: MEDIUM
**Estimated Time**: 3-4 hours
**Dependencies**: All phases complete

---

## 🏗️ Phase 1: Enterprise Providers Implementation

### 1.1 Milvus Vector Store Provider
**File**: `app/Providers/vector_store_provider/milvus_client.py`
**Priority**: CRITICAL
**Time**: 2 hours

**Implementation Checklist**:
- [ ] Connection management with pymilvus
- [ ] Collection creation with dynamic schema
- [ ] Partition management (one per file)
- [ ] Index creation (IVF_FLAT)
- [ ] Insert operations (batch support)
- [ ] Search operations (with filters)
- [ ] Delete operations (by partition)
- [ ] Error handling and logging

**Key Methods**:
```python
class MilvusClient:
    - __init__(host, port, collection_name)
    - connect()
    - create_collection(dim: int)
    - create_partition(partition_name: str)
    - insert_vectors(partition, vectors, metadata)
    - search(query_vector, partition_names, top_k, filters)
    - delete_partition(partition_name)
    - get_collection_stats()
```

**Dependencies**:
```python
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility
)
from app.core.config import settings
```

---

### 1.2 Redis Cache Provider
**File**: `app/Providers/cache_provider/__init__.py`
**File**: `app/Providers/cache_provider/client.py`
**Priority**: HIGH
**Time**: 1.5 hours

**Implementation Checklist**:
- [ ] Async Redis connection
- [ ] Cache key namespacing
- [ ] TTL management
- [ ] JSON serialization/deserialization
- [ ] Batch operations
- [ ] Cache invalidation
- [ ] Health check

**Key Methods**:
```python
class CacheProvider:
    - async def connect()
    - async def set(key, value, ttl)
    - async def get(key)
    - async def delete(key)
    - async def exists(key)
    - async def expire(key, ttl)
    - async def get_many(keys)
    - async def set_many(mapping, ttl)
```

**Cache Strategies**:
```python
# Embedding cache
KEY_EMBEDDING = "emb:{text_hash}"       # TTL: 24h

# Query expansion cache
KEY_QUERY_EXP = "qexp:{query_hash}"     # TTL: 1h

# Search results cache
KEY_SEARCH = "search:{query}:{files}"   # TTL: 30min

# File metadata cache
KEY_FILE = "file:{file_id}"             # TTL: 6h
```

**Dependencies**:
```python
import redis.asyncio as aioredis
import hashlib
import json
from app.core.config import settings
```

---

### 1.3 MongoDB Chat History Provider
**File**: `app/Providers/chat_history_provider/__init__.py`
**File**: `app/Providers/chat_history_provider/client.py`
**Priority**: HIGH
**Time**: 1.5 hours

**Implementation Checklist**:
- [ ] Async Motor client connection
- [ ] Session management
- [ ] Message CRUD operations
- [ ] Query by session_id, user_id
- [ ] Pagination support
- [ ] Index creation
- [ ] Connection pooling
- [ ] Error handling

**Key Methods**:
```python
class ChatHistoryProvider:
    - async def connect()
    - async def create_session(user_id, file_ids) -> session_id
    - async def get_session(session_id) -> dict
    - async def add_message(session_id, role, content, metadata)
    - async def get_messages(session_id, limit, offset)
    - async def list_sessions(user_id, limit) -> List[dict]
    - async def delete_session(session_id)
    - async def update_session_metadata(session_id, metadata)
```

**MongoDB Schema**:
```python
{
    "_id": ObjectId,
    "session_id": "uuid",
    "user_id": "user_123",
    "file_ids": ["file_1", "file_2"],
    "created_at": datetime,
    "updated_at": datetime,
    "messages": [
        {
            "role": "user",
            "content": "...",
            "timestamp": datetime,
            "metadata": {...}
        }
    ],
    "metadata": {
        "total_messages": int,
        "total_tokens": int,
        "language": "zh"
    }
}
```

**Dependencies**:
```python
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import uuid
from app.core.config import settings
```

---

### 1.4 SQLite File Metadata Provider
**File**: `app/Providers/file_metadata_provider/__init__.py`
**File**: `app/Providers/file_metadata_provider/client.py`
**Priority**: MEDIUM
**Time**: 1 hour

**Implementation Checklist**:
- [ ] SQLite async connection (aiosqlite)
- [ ] Table creation (file_metadata, chunks_metadata)
- [ ] CRUD operations
- [ ] Query by file_id, user_id
- [ ] Transaction support
- [ ] Index creation
- [ ] Migration support

**Key Methods**:
```python
class FileMetadataProvider:
    - async def connect()
    - async def create_tables()
    - async def add_file(file_id, filename, file_type, user_id, ...)
    - async def get_file(file_id) -> dict
    - async def list_files(user_id) -> List[dict]
    - async def update_file_status(file_id, status)
    - async def delete_file(file_id)
    - async def add_chunk_metadata(file_id, chunk_index, chunk_text, milvus_id)
```

**SQLite Schema**:
```sql
CREATE TABLE file_metadata (
    file_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    chunk_count INTEGER,
    embedding_status TEXT,
    milvus_partition TEXT,
    metadata_json TEXT
);

CREATE INDEX idx_file_user ON file_metadata(user_id);
CREATE INDEX idx_file_upload_time ON file_metadata(upload_time);
```

**Dependencies**:
```python
import aiosqlite
from pathlib import Path
from app.core.config import settings
```

---

## 🔧 Phase 2: Enhanced Services Implementation

### 2.1 Query Enhancement Service (Strategy 2)
**File**: `app/Services/query_enhancement_service.py`
**Priority**: CRITICAL
**Time**: 2 hours

**Implementation Checklist**:
- [ ] Prompt1: Query analysis prompt
- [ ] LLM call for query expansion
- [ ] JSON parsing of expansion results
- [ ] Cache integration (Redis)
- [ ] Prompt2: Enhanced RAG prompt builder
- [ ] Error handling for malformed responses

**Key Methods**:
```python
class QueryEnhancementService:
    - async def analyze_and_expand_query(query) -> dict
    - async def build_enhanced_prompt(original_query, expansion, context)
    - _build_analysis_prompt(query) -> List[dict]
    - _parse_expansion_response(response) -> dict
    - _format_expanded_questions(questions) -> str
```

**Prompt Templates**:
```python
QUERY_ANALYSIS_PROMPT = """
分析以下使用者查詢，將其分解為3-5個具體的子問題。

[使用者查詢]
{original_query}

請以 JSON 格式回覆...
"""

ENHANCED_RAG_PROMPT = """
[原始查詢]
{original_query}

[擴展查詢組]
{expanded_questions}

[檢索到的文檔片段]
{context}

[回答要求]
...
"""
```

---

### 2.2 Input Data Handle Service
**File**: `app/Services/input_data_handle_service.py`
**Priority**: HIGH
**Time**: 2 hours

**Implementation Checklist**:
- [ ] PDF text extraction (PyPDF2)
- [ ] DOCX extraction (python-docx)
- [ ] TXT/MD file reading
- [ ] Text chunking (LangChain RecursiveCharacterTextSplitter)
- [ ] File validation (size, type)
- [ ] Metadata generation
- [ ] Error handling for corrupted files

**Key Methods**:
```python
class InputDataHandleService:
    - async def process_file(file: UploadFile, user_id) -> dict
    - async def extract_text(file_path, file_type) -> str
    - async def chunk_text(text, chunk_size, overlap) -> List[str]
    - async def generate_metadata(file, chunks) -> dict
    - _validate_file(file) -> bool
    - _detect_file_type(file) -> str
```

---

### 2.3 State Transition Service (Enhanced)
**File**: `app/Services/state_transition_service.py`
**Priority**: HIGH
**Time**: 1.5 hours

**Implementation Checklist**:
- [ ] MongoDB integration
- [ ] Session lifecycle management
- [ ] Message persistence
- [ ] File-to-session associations
- [ ] Query history tracking
- [ ] Async operations

**Key Methods**:
```python
class StateTransitionService:
    - async def create_session(user_id, file_ids) -> str
    - async def get_session(session_id) -> dict
    - async def add_user_message(session_id, query, metadata)
    - async def add_assistant_message(session_id, answer, metadata)
    - async def get_chat_history(session_id, limit) -> List[dict]
    - async def delete_session(session_id)
```

---

### 2.4 Core Logic Service (Main Orchestrator)
**File**: `app/Services/core_logic_service.py`
**Priority**: CRITICAL
**Time**: 2.5 hours

**Implementation Checklist**:
- [ ] Complete RAG pipeline orchestration
- [ ] Query enhancement integration
- [ ] Retrieval service coordination
- [ ] Prompt service integration
- [ ] LLM streaming handling
- [ ] State management integration
- [ ] Error recovery
- [ ] SSE event generation

**Key Methods**:
```python
class CoreLogicService:
    - async def generate_response_stream(
        session_id, query, file_ids, enable_enhancement
      ) -> AsyncGenerator
    - async def _enhance_query(query) -> dict
    - async def _retrieve_context(query, file_ids, top_k) -> List[str]
    - async def _stream_llm_response(messages) -> AsyncGenerator
    - _generate_sse_event(type, data) -> str
```

---

## 🌐 Phase 3: API Layer Implementation

### 3.1 Pydantic Schemas
**File**: `app/models/__init__.py`
**File**: `app/models/schemas.py`
**Priority**: HIGH
**Time**: 1 hour

**Schemas to Implement**:
```python
# Request Models
class UploadRequest(BaseModel):
    user_id: Optional[str] = None

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    file_ids: List[str]
    options: Optional[ChatOptions] = None

class ChatOptions(BaseModel):
    enable_query_enhancement: bool = True
    top_k: int = 5
    language: str = "zh"

# Response Models
class FileInfo(BaseModel):
    file_id: str
    filename: str
    file_size: int
    chunk_count: int
    status: str
    upload_time: datetime

class UploadResponse(BaseModel):
    files: List[FileInfo]
    session_id: str

class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    file_ids: List[str]
    messages: List[MessageSchema]

class MessageSchema(BaseModel):
    role: str
    content: str
    timestamp: datetime
    metadata: Optional[dict] = None
```

---

### 3.2 Upload Endpoint
**File**: `app/api/v1/endpoints/upload.py`
**Priority**: HIGH
**Time**: 1.5 hours

**Implementation Checklist**:
- [ ] Multi-file upload handling
- [ ] File validation
- [ ] Async file processing
- [ ] Progress tracking
- [ ] Error handling
- [ ] Response formatting

**Endpoint**:
```python
@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    user_id: Optional[str] = None,
    input_service: InputDataHandleService = Depends(),
    retrieval_service: RetrievalService = Depends(),
    file_metadata_provider: FileMetadataProvider = Depends()
):
    """
    Upload and index multiple files

    Steps:
    1. Validate files
    2. Extract text
    3. Chunk text
    4. Generate embeddings
    5. Store in Milvus
    6. Save metadata to SQLite
    7. Return file info
    """
    ...
```

---

### 3.3 Chat Endpoint (SSE Streaming)
**File**: `app/api/v1/endpoints/chat.py`
**Priority**: CRITICAL
**Time**: 2 hours

**Implementation Checklist**:
- [ ] SSE streaming setup
- [ ] Request validation
- [ ] Core logic service integration
- [ ] Event generation
- [ ] Error handling in stream
- [ ] Connection management

**Endpoint**:
```python
@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    core_service: CoreLogicService = Depends()
):
    """
    Streaming chat with SSE

    SSE Events:
    - session_start
    - query_analysis (if enhancement enabled)
    - query_expansion
    - retrieval_progress
    - retrieval_complete
    - generation_start
    - token (OPMP)
    - generation_complete
    - metadata
    - complete
    - error
    """

    async def event_generator():
        try:
            async for event in core_service.generate_response_stream(...):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

---

### 3.4 History Endpoint
**File**: `app/api/v1/endpoints/history.py`
**Priority**: MEDIUM
**Time**: 1 hour

**Endpoints**:
```python
@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(user_id: str, limit: int = 20):
    """List user's chat sessions"""
    ...

@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session details with messages"""
    ...

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    ...
```

---

### 3.5 Export Endpoint
**File**: `app/api/v1/endpoints/export.py`
**Priority**: LOW
**Time**: 30 minutes

**Endpoint**:
```python
@router.get("/export/{session_id}")
async def export_session(
    session_id: str,
    format: str = "json"  # json, markdown, txt
):
    """Export chat history"""
    ...
```

---

### 3.6 API Router Aggregation
**File**: `app/api/__init__.py`
**File**: `app/api/v1/__init__.py`
**File**: `app/api/v1/router.py`
**Priority**: HIGH
**Time**: 30 minutes

**Router Structure**:
```python
# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import upload, chat, history, export

api_router = APIRouter()

api_router.include_router(
    upload.router,
    prefix="/upload",
    tags=["upload"]
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"]
)

api_router.include_router(
    history.router,
    prefix="/history",
    tags=["history"]
)

api_router.include_router(
    export.router,
    prefix="/export",
    tags=["export"]
)
```

---

### 3.7 Main Application Factory
**File**: `app/main.py`
**Priority**: HIGH
**Time**: 1 hour

**Implementation Checklist**:
- [ ] FastAPI app initialization
- [ ] CORS middleware
- [ ] Logging middleware
- [ ] Exception handlers
- [ ] Lifespan events (startup/shutdown)
- [ ] Router registration
- [ ] Health check endpoint

**Application Structure**:
```python
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS
    )

    # Lifespan events
    @app.on_event("startup")
    async def startup():
        # Initialize connections
        await milvus_client.connect()
        await redis_client.connect()
        await mongo_client.connect()
        await sqlite_client.connect()

    @app.on_event("shutdown")
    async def shutdown():
        # Close connections
        ...

    # Routers
    app.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX
    )

    return app

app = create_app()
```

---

## 📦 Phase 4: Supporting Files

### 4.1 Requirements.txt
**File**: `requirements.txt`
**Priority**: HIGH
**Time**: 15 minutes

```txt
# Web Framework
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.9

# LangChain Stack
langchain>=0.1.13
langchain-core>=0.1.33,<0.2.0
langchain-community>=0.0.29
langgraph>=0.0.40
langchain-text-splitters<0.1

# LLM & Embeddings
transformers>=4.35.0
sentence-transformers>=2.5.0
torch>=2.0.0

# Vector Database
pymilvus>=2.3.0
faiss-cpu>=1.8.0

# Storage
motor>=3.3.0
pymongo>=4.6.0
redis[hiredis]>=5.0.0
aiosqlite>=0.19.0

# Document Processing
pypdf>=4.1.0
python-docx>=1.1.0

# HTTP Client
httpx>=0.26.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Logging
python-json-logger>=2.0.7
```

---

### 4.2 Environment File
**File**: `.env.example`
**Priority**: MEDIUM
**Time**: 10 minutes

```bash
# Application
APP_NAME=DocAI
APP_VERSION=1.0.0
DEBUG=False

# LLM Provider
LLM_PROVIDER_BASE_URL=http://localhost:11434/v1
DEFAULT_LLM_MODEL=gpt-oss:20b

# Embedding
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=docai

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# SQLite
SQLITE_DB_PATH=./data/docai.db

# File Upload
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=50000000

# Query Enhancement
ENABLE_QUERY_ENHANCEMENT=True
ENHANCEMENT_STRATEGY=question_expansion

# Security
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

### 4.3 Entry Points
**File**: `main.py` (root)
**File**: `uvicorn_runner.py`
**Priority**: LOW
**Time**: 15 minutes

**main.py**:
```python
from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

**uvicorn_runner.py**:
```python
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
```

---

## 📅 Implementation Timeline

### Week 1: Foundation
- **Day 1-2**: Milvus + Redis Providers
- **Day 3**: MongoDB + SQLite Providers
- **Day 4**: Query Enhancement Service
- **Day 5**: Input Data Handle + State Transition Services

### Week 2: Integration
- **Day 1**: Core Logic Service
- **Day 2**: Pydantic Schemas + Upload Endpoint
- **Day 3**: Chat Endpoint (SSE)
- **Day 4**: History + Export Endpoints
- **Day 5**: Main App + Testing

---

## ✅ Implementation Checklist

### Phase 1: Providers
- [ ] Milvus Client
- [ ] Redis Cache Provider
- [ ] MongoDB Chat History Provider
- [ ] SQLite File Metadata Provider

### Phase 2: Services
- [ ] Query Enhancement Service
- [ ] Input Data Handle Service
- [ ] State Transition Service
- [ ] Core Logic Service

### Phase 3: API
- [ ] Pydantic Schemas
- [ ] Upload Endpoint
- [ ] Chat Endpoint (SSE)
- [ ] History Endpoints
- [ ] Export Endpoint
- [ ] API Router
- [ ] Main Application

### Phase 4: Supporting
- [ ] requirements.txt
- [ ] .env.example
- [ ] main.py
- [ ] uvicorn_runner.py
- [ ] README update
- [ ] API documentation

---

## 🚀 Quick Start Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start infrastructure (Docker Compose)
docker-compose up -d

# Run application
python uvicorn_runner.py

# Test endpoints
curl -X POST http://localhost:8000/api/v1/upload -F "files=@test.pdf"
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "file_ids": ["file_123"]}'
```

---

**Plan Created**: 2025-10-29
**Total Estimated Time**: 25-30 hours
**Priority**: HIGH - Critical path for MVP completion
