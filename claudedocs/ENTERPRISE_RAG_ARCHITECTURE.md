# Enterprise RAG Architecture - DocAI

## 專案概述

**DocAI** 是一個企業級的 Chat-with-Files RAG (Retrieval-Augmented Generation) 應用，支援文件上傳、智能檢索和對話式查詢。

### 核心特性

1. **Two-Stage Query Enhancement** (Strategy 2: Question Expansion)
   - Stage 1: 將使用者查詢擴展為多個子問題
   - Stage 2: 使用擴展查詢進行增強檢索和回答

2. **Enterprise-Grade Storage Stack**
   - **Milvus**: 高性能向量資料庫 (分散式、可擴展)
   - **MongoDB**: 聊天歷史和會話管理
   - **Redis**: 快取層 (embeddings, query results)
   - **SQLite**: 輕量級關聯式資料 (檔案元數據)

3. **LangChain/LangGraph Integration**
   - LangChain: RAG pipeline orchestration
   - LangGraph: Multi-step reasoning workflows
   - Transformers: HuggingFace embeddings

---

## 技術架構

### Layer 1 - Providers (Infrastructure)

```
app/Providers/
├── llm_provider/              # OpenAI-compatible LLM client
│   └── client.py              # Streaming + non-streaming
│
├── embedding_provider/        # HuggingFace Transformers
│   └── client.py              # SentenceTransformer models
│
├── vector_store_provider/     # Vector DB abstraction
│   ├── client.py              # Unified interface
│   ├── milvus_client.py       # Milvus implementation ⭐
│   └── faiss_client.py        # FAISS fallback
│
├── cache_provider/            # Redis cache layer ⭐ NEW
│   └── client.py              # Embedding & query cache
│
├── chat_history_provider/     # MongoDB storage ⭐ NEW
│   └── client.py              # Conversation persistence
│
└── file_metadata_provider/    # SQLite storage ⭐ NEW
    └── client.py              # File tracking & metadata
```

### Layer 2 - Services (Business Logic)

```
app/Services/
├── core_logic_service.py           # Main RAG orchestrator
├── input_data_handle_service.py    # File extraction & chunking
├── prompt_service.py               # Prompt templates
├── retrieval_service.py            # Embedding + retrieval
├── state_transition_service.py     # Chat state management
└── query_enhancement_service.py    # Two-stage query expansion ⭐ NEW
```

### Layer 3 - API (Endpoints)

```
app/api/v1/endpoints/
├── chat.py        # POST /api/v1/chat (streaming SSE)
├── upload.py      # POST /api/v1/upload (file ingestion)
├── history.py     # GET  /api/v1/history/{session_id} ⭐ NEW
└── export.py      # GET  /api/v1/export/{session_id}
```

---

## 數據流設計

### 1. File Upload Flow

```
[User] → POST /upload
  ↓
InputDataHandleService
  ├→ Extract text (PyPDF2, python-docx)
  ├→ Chunk text (RecursiveCharacterTextSplitter)
  ├→ Generate metadata (file_id, chunk_index, timestamps)
  ↓
RetrievalService
  ├→ Generate embeddings (Transformers)
  ├→ Cache embeddings (Redis) ⭐
  ├→ Store in Milvus (with file_id partition) ⭐
  ↓
FileMetadataProvider
  ├→ Save to SQLite (file_id, filename, upload_time, user_id) ⭐
  ↓
[Response] {"file_id": "...", "chunks": 150, "status": "indexed"}
```

### 2. Chat Flow (Two-Stage Enhancement)

```
[User Query] → POST /chat
  ↓
QueryEnhancementService (Stage 1) ⭐
  ├→ Analyze query intent
  ├→ Expand to sub-questions (Strategy 2)
  ├→ Cache expansion (Redis, TTL=1h)
  ↓
RetrievalService
  ├→ For each sub-question:
  │   ├→ Check cache (Redis)
  │   ├→ Generate embedding
  │   └→ Search Milvus (top_k per question)
  ├→ Merge and deduplicate results
  ↓
PromptService (Stage 2)
  ├→ Build Prompt2 (original + expansions + context)
  ↓
LLMProviderClient
  ├→ Stream response (SSE)
  ↓
StateTransitionService
  ├→ Save to MongoDB (session_id, messages[], timestamp) ⭐
  ↓
[SSE Stream] → Client
```

### 3. History Retrieval Flow

```
[User] → GET /history/{session_id}
  ↓
StateTransitionService
  ├→ Query MongoDB (session_id)
  ├→ Retrieve messages array
  ↓
[Response] {
  "session_id": "...",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "file_ids": ["file1", "file2"]
}
```

---

## 核心實作細節

### Strategy 2: Question Expansion Implementation

**Prompt1 (Query Analysis)**
```python
QUERY_EXPANSION_PROMPT = """
你是一個查詢分析專家。將以下使用者查詢分解為3-5個具體的子問題，以便更全面地檢索相關資訊。

[使用者查詢]
{original_query}

請以 JSON 格式回覆：
{{
  "original_query": "{original_query}",
  "intent": "查詢的核心意圖",
  "expanded_questions": [
    "子問題1：更具體的問法",
    "子問題2：不同角度的問法",
    "子問題3：相關背景問題",
    ...
  ],
  "reasoning": "為什麼這樣分解的理由"
}}

要求：
1. 子問題應涵蓋原始查詢的不同面向
2. 每個子問題應該獨立且可單獨回答
3. 避免重複相似的問題
4. 保持子問題的具體性和可檢索性
"""
```

**Prompt2 (Enhanced RAG)**
```python
PROMPT_2_QUESTION_EXPANSION = """
[原始查詢]
{original_query}

[擴展查詢組]
為了更全面回答此問題，我們將其分解為以下子問題：
{expanded_questions_formatted}

[檢索到的相關文檔片段]
{retrieved_context}

[回答要求]
請綜合以上「原始查詢」和「擴展查詢組」，基於提供的文檔片段：
1. 逐一分析擴展出的子問題
2. 從文檔片段中提取相關資訊
3. 將答案整合為一個連貫、全面的回應
4. 確保完整覆蓋原始查詢的意圖
5. **僅使用文檔片段中的資訊，不添加外部知識**

最終答案應：
- 結構清晰（可使用標題、列表）
- 邏輯連貫
- 引用具體的文檔內容
- 明確指出哪些資訊來自哪個子問題的檢索結果
"""
```

---

## 技術規格

### Milvus Configuration

```python
# app/Providers/vector_store_provider/milvus_client.py

MILVUS_CONFIG = {
    "host": "localhost",
    "port": "19530",
    "collection_name": "document_embeddings",
    "dimension": 384,  # all-MiniLM-L6-v2
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "nlist": 1024
}

# Schema Design
COLLECTION_SCHEMA = {
    "fields": [
        {"name": "id", "type": "int64", "is_primary": True},
        {"name": "file_id", "type": "varchar", "max_length": 64},
        {"name": "chunk_index", "type": "int32"},
        {"name": "content", "type": "varchar", "max_length": 4096},
        {"name": "embedding", "type": "float_vector", "dim": 384},
        {"name": "timestamp", "type": "int64"}
    ]
}

# Partition Strategy: One partition per file for efficient deletion
# Partition naming: f"file_{file_id}"
```

### MongoDB Schema

```javascript
// Collection: chat_sessions
{
  "_id": ObjectId("..."),
  "session_id": "uuid-v4-string",
  "user_id": "user_123",
  "file_ids": ["file_abc", "file_def"],
  "created_at": ISODate("2025-10-29T12:00:00Z"),
  "updated_at": ISODate("2025-10-29T12:30:00Z"),
  "messages": [
    {
      "role": "user",
      "content": "What is RAG?",
      "timestamp": ISODate("2025-10-29T12:00:00Z"),
      "metadata": {
        "original_query": "What is RAG?",
        "expanded_questions": ["Q1", "Q2", "Q3"]
      }
    },
    {
      "role": "assistant",
      "content": "RAG stands for...",
      "timestamp": ISODate("2025-10-29T12:00:05Z"),
      "metadata": {
        "model": "gpt-oss:20b",
        "retrieval_sources": ["chunk_1", "chunk_2"]
      }
    }
  ],
  "metadata": {
    "total_messages": 10,
    "total_tokens": 5000,
    "language": "zh"
  }
}
```

### Redis Cache Strategy

```python
# Cache Keys Design
REDIS_KEYS = {
    "embedding": "emb:{text_hash}",         # TTL: 24h
    "query_expansion": "qexp:{query_hash}", # TTL: 1h
    "search_results": "search:{query_hash}:{file_ids}", # TTL: 30min
    "file_metadata": "file:{file_id}",      # TTL: 6h
}

# Cache Priority
# 1. Embeddings (most expensive to compute)
# 2. Query expansions (moderate cost)
# 3. Search results (low cost but frequently accessed)
```

### SQLite Schema

```sql
-- Table: file_metadata
CREATE TABLE file_metadata (
    file_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,  -- 'pdf', 'docx', 'txt'
    file_size INTEGER,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    chunk_count INTEGER,
    embedding_status TEXT,  -- 'pending', 'completed', 'failed'
    milvus_partition TEXT,  -- Partition name in Milvus
    metadata_json TEXT      -- Additional flexible metadata
);

-- Table: chunks_metadata (optional, for tracking)
CREATE TABLE chunks_metadata (
    chunk_id TEXT PRIMARY KEY,
    file_id TEXT,
    chunk_index INTEGER,
    chunk_text TEXT,
    milvus_id INTEGER,  -- ID in Milvus
    FOREIGN KEY (file_id) REFERENCES file_metadata(file_id)
);

-- Indexes
CREATE INDEX idx_file_user ON file_metadata(user_id);
CREATE INDEX idx_file_upload_time ON file_metadata(upload_time);
```

---

## Dependencies (requirements.txt)

```txt
# Web Framework
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.9

# LangChain Stack
langchain>=0.1.13
langchain-core>=0.1.33,<0.2.0
langchain-community>=0.0.29
langgraph>=0.0.40  # For multi-step workflows
langchain-text-splitters<0.1

# LLM & Embeddings
transformers>=4.35.0
sentence-transformers>=2.5.0
torch>=2.0.0  # or torch-cpu for CPU-only

# Vector Database
pymilvus>=2.3.0  # Milvus client
faiss-cpu>=1.8.0  # Fallback option

# Storage
motor>=3.3.0  # Async MongoDB driver
pymongo>=4.6.0  # Sync MongoDB driver
redis>=5.0.0  # Redis client

# Document Processing
pypdf>=4.1.0
python-docx>=1.1.0
python-magic>=0.4.27  # File type detection

# HTTP Client
httpx>=0.26.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Monitoring & Logging
python-json-logger>=2.0.7
```

---

## 環境變數 (.env)

```bash
# Application
APP_NAME=DocAI
APP_VERSION=1.0.0
DEBUG=False

# LLM Provider
LLM_PROVIDER_BASE_URL=http://localhost:11434/v1
LLM_PROVIDER_API_KEY=ollama
DEFAULT_LLM_MODEL=gpt-oss:20b

# Embedding Model
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_FALLBACK=jinaai/jina-embeddings-v2-base-zh
EMBEDDING_DIMENSION=384

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=document_embeddings
MILVUS_USER=
MILVUS_PASSWORD=

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=docai
MONGODB_CHAT_COLLECTION=chat_sessions

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_CACHE_TTL=3600  # 1 hour

# SQLite
SQLITE_DB_PATH=./data/docai.db

# File Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=50_000_000  # 50MB
ALLOWED_EXTENSIONS=pdf,docx,txt,md

# Query Enhancement
ENABLE_QUERY_ENHANCEMENT=True
ENHANCEMENT_STRATEGY=question_expansion  # Strategy 2
EXPANSION_COUNT=3  # Number of sub-questions

# Security
SECRET_KEY=your-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## 下一步實作計劃

1. **更新 VectorStoreProvider** → 添加 `milvus_client.py`
2. **創建 CacheProvider** → Redis 整合
3. **創建 ChatHistoryProvider** → MongoDB 整合
4. **創建 FileMetadataProvider** → SQLite 整合
5. **實作 QueryEnhancementService** → Strategy 2
6. **更新 StateTransitionService** → 使用 MongoDB
7. **實作 InputDataHandleService** → 完整文件處理
8. **實作 CoreLogicService** → 整合所有組件
9. **創建 API endpoints** → 完整 REST API
10. **實作 core/config.py** → Pydantic Settings

準備好開始實作了嗎？我將從企業級 Providers 開始！
