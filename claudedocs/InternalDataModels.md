# Internal Data Models Architecture

**Purpose**: Type-safe dict-based communication between layers
**Location**: [app/models/internal.py](../app/models/internal.py)
**Pattern**: TypedDict (runtime dict + compile-time types)
**Date**: 2025-10-30

---

## 📋 Overview

### Why Internal Data Models?

**Your Requirements**:
1. ✅ **No SQLAlchemy**: Keep current dict-based approach
2. ✅ **Layer-to-Layer Communication**: Type-safe internal interfaces
3. ✅ **Class-to-Class Data Transfer**: Structured data contracts

**Solution**: **TypedDict** - Best of both worlds

```python
# Runtime: Still just a dict!
result = {
    'file_id': 'abc123',
    'chunk_count': 50
}

# Compile-time: Type checking and IDE support
result: ProcessingResult  # ← Type hint for safety
```

---

## 🏗️ Architecture

### Layer Communication Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                      API Endpoints                          │
│              (Pydantic Models - External API)               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↓ Pydantic → dict conversion
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                           │
│           (TypedDict Models - Internal Logic)               │
│                                                             │
│  • input_data_handle_service                               │
│  • retrieval_service                                       │
│  • query_enhancement_service                               │
│  • prompt_service                                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↓ TypedDict dicts
┌─────────────────────────────────────────────────────────────┐
│                    Provider Layer                           │
│           (TypedDict Models - External Systems)             │
│                                                             │
│  • file_metadata_provider (SQLite)                         │
│  • vector_store_provider (Milvus)                          │
│  • embedding_provider (HuggingFace)                        │
│  • llm_provider (Ollama)                                   │
│  • cache_provider (Redis)                                  │
│  • chat_history_provider (MongoDB)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Data Model Categories

### 1. File Processing Models

**Purpose**: Document upload and text extraction pipeline

#### ChunkData
```python
from app.models.internal import ChunkData

chunk: ChunkData = {
    'content': 'This is the chunk text...',
    'chunk_index': 0,
    'metadata': {
        'file_id': 'file_123',
        'page_number': 1,
        'section': 'Introduction'
    },
    # Optional hierarchical fields
    'parent_chunk_index': None,
    'children_chunk_indices': [1, 2],
    'level': 0
}
```

**Used by**:
- `chunking_strategies.chunk()` → returns `List[ChunkData]`
- `input_data_handle_service.chunk_text()` → returns `List[ChunkData]`
- `retrieval_service.add_document_chunks()` → accepts `List[ChunkData]`

#### ProcessingResult
```python
from app.models.internal import ProcessingResult

result: ProcessingResult = {
    'file_id': 'file_abc123',
    'filename': 'document.pdf',
    'file_size': 1024000,
    'chunks': [chunk1, chunk2, ...],  # List[ChunkData]
    'chunk_count': 150,
    'chunking_strategy': 'hierarchical',
    'extracted_text_length': 50000,
    'processing_time_ms': 1250.5
}
```

**Used by**:
- `input_data_handle_service.process_file()` → returns `ProcessingResult`
- `upload.py` endpoint → receives `ProcessingResult`

---

### 2. Vector Store Models

**Purpose**: Embedding generation and similarity search

#### VectorSearchResult
```python
from app.models.internal import VectorSearchResult

search_result: VectorSearchResult = {
    'content': 'Retrieved chunk text...',
    'score': 0.85,  # Similarity score
    'metadata': {
        'file_id': 'file_123',
        'chunk_index': 5,
        'page': 2
    },
    'file_id': 'file_123',      # Optional shortcut
    'chunk_index': 5,
    'milvus_id': 12345
}
```

**Used by**:
- `vector_store_provider.search()` → returns `List[VectorSearchResult]`
- `retrieval_service.retrieve_context()` → returns `List[VectorSearchResult]`
- `chat.py` endpoint → receives retrieval results

#### EmbeddingData
```python
from app.models.internal import EmbeddingData

embeddings: EmbeddingData = {
    'embeddings': [[0.1, 0.2, ...], [0.3, 0.4, ...]],  # 768-dim vectors
    'texts': ['text1', 'text2'],
    'model_name': 'BAAI/bge-m3',
    'dimension': 768
}
```

**Used by**:
- `embedding_provider.generate_embeddings()` → returns `EmbeddingData`
- `vector_store_provider` → consumes `EmbeddingData`

---

### 3. Query Enhancement Models

**Purpose**: Query expansion and intent analysis (Strategy 2)

#### QueryExpansionResult
```python
from app.models.internal import QueryExpansionResult

expansion: QueryExpansionResult = {
    'original_query': 'What is RAG?',
    'intent': 'definition_seeking',
    'expanded_questions': [
        'What does RAG stand for?',
        'How does RAG work technically?',
        'What are the benefits of RAG?'
    ],
    'reasoning': 'User seeks comprehensive understanding',
    'cache_hit': False,
    'processing_time_ms': 523.2
}
```

**Used by**:
- `query_enhancement_service.expand_query()` → returns `QueryExpansionResult`
- `chat.py` endpoint → consumes expansion results

---

### 4. Chat History Models

**Purpose**: Conversation management and context

#### MessageData
```python
from app.models.internal import MessageData
from datetime import datetime, timezone

message: MessageData = {
    'role': 'user',
    'content': 'What is RAG?',
    'timestamp': datetime.now(timezone.utc),
    'metadata': {
        'expanded_questions': ['Q1', 'Q2'],
        'context_count': 5
    }
}
```

**Used by**:
- `chat_history_provider.add_message()` → accepts `MessageData`
- `chat_history_provider.get_chat_history()` → returns `List[MessageData]`
- `prompt_service.build_rag_prompt()` → receives `List[MessageData]`

#### SessionData
```python
from app.models.internal import SessionData

session: SessionData = {
    'session_id': 'session_xyz789',
    'user_id': 'user_123',
    'messages': [message1, message2, ...],
    'created_at': datetime(2025, 10, 30, 10, 0, 0),
    'updated_at': datetime(2025, 10, 30, 10, 30, 0),
    'metadata': {
        'total_tokens': 5000,
        'file_ids': ['file_abc', 'file_def']
    }
}
```

**Used by**:
- `chat_history_provider.get_session()` → returns `SessionData`

---

### 5. File Metadata Models

**Purpose**: File tracking and indexing status

#### FileMetadata
```python
from app.models.internal import FileMetadata

file_meta: FileMetadata = {
    'file_id': 'file_abc123',
    'filename': 'document.pdf',
    'file_type': 'pdf',
    'file_size': 1024000,
    'upload_time': datetime.now(timezone.utc),
    'user_id': 'user_123',
    'chunk_count': 150,
    'embedding_status': 'completed',
    'milvus_partition': 'file_abc123',
    'metadata_json': '{"strategy": "hierarchical"}'
}
```

**Used by**:
- `file_metadata_provider.add_file()` → accepts `FileMetadata` fields
- `file_metadata_provider.get_file()` → returns dict compatible with `FileMetadata`

---

### 6. LLM Provider Models

**Purpose**: LLM interaction (OpenAI-compatible)

#### LLMMessage
```python
from app.models.internal import LLMMessage

messages: List[LLMMessage] = [
    {
        'role': 'system',
        'content': 'You are a helpful RAG assistant.'
    },
    {
        'role': 'user',
        'content': 'What is RAG?'
    }
]
```

**Used by**:
- `prompt_service.build_rag_prompt()` → returns `List[LLMMessage]`
- `llm_provider.get_chat_completion()` → accepts `List[LLMMessage]`

---

## 🎯 Usage Patterns

### Pattern 1: File Upload Pipeline

```python
from app.models.internal import ProcessingResult, DocumentAddResult

# Step 1: Process file (Service Layer)
result: ProcessingResult = await input_service.process_file(
    file_content=content,
    filename='document.pdf'
)

# Step 2: Add to vector store (Service → Provider)
add_result: DocumentAddResult = await retrieval_service.add_document_chunks(
    file_id=result['file_id'],
    chunks=[chunk['content'] for chunk in result['chunks']],
    metadata=[chunk['metadata'] for chunk in result['chunks']]
)

# Step 3: Store metadata (Provider Layer)
await file_metadata_provider.add_file(
    file_id=result['file_id'],
    filename=result['filename'],
    file_size=result['file_size'],
    chunk_count=result['chunk_count'],
    embedding_status='completed',
    milvus_partition=f"file_{result['file_id']}",
    metadata={'chunking_strategy': result['chunking_strategy']}
)
```

### Pattern 2: Query Processing Pipeline

```python
from app.models.internal import (
    QueryExpansionResult,
    VectorSearchResult,
    RetrievalContext
)

# Step 1: Expand query
expansion: QueryExpansionResult = await query_enhancement_service.expand_query(
    query=user_query,
    cache_provider=cache_provider
)

# Step 2: Retrieve context for each question
all_results: List[VectorSearchResult] = []
for question in expansion['expanded_questions']:
    results = await retrieval_service.retrieve_context(
        query=question,
        file_ids=selected_files,
        top_k=5
    )
    all_results.extend(results)

# Step 3: Assemble retrieval context
context: RetrievalContext = {
    'chunks': all_results,
    'total_chunks': len(all_results),
    'query': user_query,
    'file_ids': selected_files,
    'retrieval_time_ms': elapsed_time
}
```

### Pattern 3: Chat Response Generation

```python
from app.models.internal import MessageData, LLMMessage, PromptMessages

# Step 1: Get chat history
history: List[MessageData] = await chat_history_provider.get_chat_history(
    session_id=session_id,
    limit=10
)

# Step 2: Build RAG prompt
prompt_msgs: PromptMessages = prompt_service.build_rag_prompt(
    query=user_query,
    context_chunks=[result['content'] for result in search_results],
    chat_history=history,
    language='zh'
)

# Step 3: Generate response
response = await llm_provider.get_chat_completion(
    messages=prompt_msgs['messages'],
    temperature=0.7
)
```

---

## 🔍 Benefits of TypedDict

### 1. Runtime = Dict (Zero Overhead)

```python
# Still just a dict at runtime!
result: ProcessingResult = {
    'file_id': 'abc',
    'filename': 'doc.pdf',
    'file_size': 1024,
    'chunks': [],
    'chunk_count': 0,
    'chunking_strategy': 'hierarchical',
    'extracted_text_length': 0
}

# Can be passed anywhere dicts are accepted
json.dumps(result)  # ✅ Works
redis.set('key', result)  # ✅ Works
mongo.insert_one(result)  # ✅ Works
```

### 2. Compile-Time = Type Safety

```python
# Type checker (mypy) catches errors
result: ProcessingResult = {
    'file_id': 123,  # ❌ mypy error: Expected str, got int
    'filename': 'doc.pdf',
    # ❌ mypy error: Missing required key 'file_size'
}
```

### 3. IDE Autocomplete

```python
result: ProcessingResult = await service.process_file(...)

# IDE shows available keys:
result['file_id']        # ✅ Autocomplete
result['chunk_count']    # ✅ Autocomplete
result['invalid_key']    # ❌ IDE warning
```

### 4. Documentation

```python
def process_file(content: bytes, filename: str) -> ProcessingResult:
    """
    Process file and return structured result

    Returns:
        ProcessingResult with file_id, chunks, etc.
    """
    # Function signature documents return type!
```

---

## 🆚 Comparison Table

| Feature | Plain Dict | TypedDict | Pydantic | SQLAlchemy |
|---------|-----------|-----------|----------|------------|
| Runtime overhead | None | None | Medium | High |
| Type checking | ❌ | ✅ | ✅ | ✅ |
| IDE autocomplete | ❌ | ✅ | ✅ | ✅ |
| Validation | ❌ | ❌ | ✅ | ✅ |
| JSON compatible | ✅ | ✅ | ✅* | ❌ |
| DB mapping | ❌ | ❌ | ❌ | ✅ |
| **DocAI Use Case** | ❌ | ✅✅✅ | External API | Not used |

*Requires `.model_dump()` conversion

---

## 🔄 Integration with Pydantic

### API Endpoint → Internal Model

```python
from app.models.schemas import ChatRequest  # Pydantic
from app.models.internal import QueryExpansionResult  # TypedDict

@router.post("/chat")
async def chat(request: ChatRequest):  # ← Pydantic validates input
    # Convert to internal processing
    expansion: QueryExpansionResult = await query_service.expand_query(
        query=request.query  # Extract field
    )

    # Internal layers use TypedDict
    return process_expansion(expansion)
```

### Internal Model → API Response

```python
from app.models.schemas import UploadResponse  # Pydantic
from app.models.internal import ProcessingResult  # TypedDict

async def upload_handler(file: UploadFile):
    # Internal processing uses TypedDict
    result: ProcessingResult = await service.process_file(...)

    # Convert to Pydantic for API response
    return UploadResponse(
        file_id=result['file_id'],
        filename=result['filename'],
        file_size=result['file_size'],
        chunk_count=result['chunk_count'],
        embedding_status='completed'
    )
```

---

## 📝 Best Practices

### 1. Always Type Hint Function Signatures

```python
# ✅ GOOD: Clear type contract
def process_chunks(chunks: List[ChunkData]) -> ProcessingResult:
    ...

# ❌ BAD: No type information
def process_chunks(chunks):
    ...
```

### 2. Use `total=False` for Optional Fields

```python
class ChunkData(TypedDict, total=False):
    content: str              # Required (total=True by default)
    chunk_index: int          # Required

    parent_chunk_index: Optional[int]  # Optional (total=False)
    level: Optional[int]               # Optional
```

### 3. Document Model Purpose

```python
class ProcessingResult(TypedDict):
    """
    File processing pipeline result

    Used by: input_data_handle_service → upload endpoint

    Contains:
    - file_id: Unique identifier
    - chunks: List of ChunkData objects
    - chunk_count: Total number of chunks
    """
    file_id: str
    chunks: List[ChunkData]
    chunk_count: int
```

### 4. Keep Models Focused

```python
# ✅ GOOD: Focused, single-purpose model
class ValidationResult(TypedDict):
    is_valid: bool
    error_message: Optional[str]

# ❌ BAD: Kitchen sink model
class ValidationResult(TypedDict):
    is_valid: bool
    error_message: Optional[str]
    file_size: int
    chunks: List[dict]
    llm_response: str  # Unrelated!
```

---

## 🚀 Migration Path

### Before (Plain Dicts)

```python
def process_file(content: bytes, filename: str) -> dict:
    """Returns dict with file_id, chunks, etc."""
    return {
        'file_id': generate_id(),
        'chunks': [...],
        'chunk_count': len(chunks)
    }

# Usage (no type safety)
result = process_file(content, filename)
print(result['file_id'])  # IDE doesn't know this key exists
```

### After (TypedDict)

```python
from app.models.internal import ProcessingResult

def process_file(content: bytes, filename: str) -> ProcessingResult:
    """Returns ProcessingResult with structured data"""
    return {
        'file_id': generate_id(),
        'filename': filename,
        'file_size': len(content),
        'chunks': [...],
        'chunk_count': len(chunks),
        'chunking_strategy': 'hierarchical',
        'extracted_text_length': len(text),
        'processing_time_ms': elapsed
    }

# Usage (full type safety)
result: ProcessingResult = process_file(content, filename)
print(result['file_id'])  # ✅ IDE autocomplete
print(result['invalid'])  # ❌ IDE warning
```

---

## 📊 Model Dependency Graph

```
ProcessingResult
    └─→ ChunkData (List)
            └─→ metadata: Dict[str, Any]

RetrievalContext
    └─→ VectorSearchResult (List)
            └─→ metadata: Dict[str, Any]

SessionData
    └─→ MessageData (List)
            └─→ metadata: Dict[str, Any]

PromptMessages
    └─→ LLMMessage (List)
```

---

## 🎯 Summary

### Key Decisions

1. ✅ **TypedDict over Plain Dict**: Type safety with zero runtime cost
2. ✅ **TypedDict over Pydantic (Internal)**: No validation overhead between layers
3. ✅ **TypedDict over SQLAlchemy**: Keep dict-based, no ORM
4. ✅ **Pydantic for API Boundaries**: Validation at system edges only

### Architecture

```
External Request (JSON)
    ↓
[Pydantic Model] ← Validation happens here
    ↓
[TypedDict] ← Internal communication (no overhead)
    ↓
[TypedDict] ← Provider layer (still dicts)
    ↓
[Pydantic Model] ← Validation for response
    ↓
External Response (JSON)
```

### Where to Use Each

| Location | Model Type | Reason |
|----------|-----------|--------|
| API Endpoints | Pydantic | Input validation + OpenAPI |
| Service Layer | TypedDict | Type-safe internal logic |
| Provider Layer | TypedDict | Zero-overhead data transfer |
| Database | Dict | Native dict storage (MongoDB, Redis) |

---

*Document created: 2025-10-30 | Internal Data Models Guide | DocAI Architecture*
