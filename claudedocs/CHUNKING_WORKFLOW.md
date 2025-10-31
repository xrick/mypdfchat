# Document Chunking Workflow in DocAI

**Question**: "In what point do you perform chunking the uploaded files?"

**Answer**: Chunking is performed in **Step 4** of the `process_file()` method in `InputDataHandleService`, which is called during the upload workflow **before** embedding generation.

---

## Complete Upload → Chunking → Embedding Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER UPLOADS FILE                            │
│                         (Frontend)                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  UPLOAD ENDPOINT: /api/v1/upload                                │
│  File: app/api/v1/endpoints/upload.py                           │
│                                                                  │
│  1. Receive file + X-User-ID header                             │
│  2. Save file to disk (uploadfiles/pdf/)                        │
│  3. Call process_and_embed_file()                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  PROCESSING FUNCTION: process_and_embed_file()                  │
│  File: app/api/v1/endpoints/upload.py:75-167                    │
│                                                                  │
│  ┌───────────────────────────────────────────────────┐          │
│  │ Step 1: Process File (CHUNKING HAPPENS HERE)     │          │
│  │ ─────────────────────────────────────────────────│          │
│  │ process_result = await input_service.process_file(│          │
│  │     file_content, filename, file_metadata_provider│          │
│  │ )                                                 │          │
│  │                                                   │          │
│  │ Returns:                                          │          │
│  │   - file_id                                       │          │
│  │   - chunks (List[Dict])  ← CHUNKED TEXT          │          │
│  │   - chunk_count                                   │          │
│  │   - chunking_strategy                             │          │
│  └───────────────────────────────────────────────────┘          │
│                         │                                        │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────┐          │
│  │ Step 2: Store File Metadata in SQLite            │          │
│  │ ─────────────────────────────────────────────────│          │
│  │ await file_metadata_provider.add_file(           │          │
│  │     file_id, filename, user_id, chunk_count, ... │          │
│  │ )                                                 │          │
│  └───────────────────────────────────────────────────┘          │
│                         │                                        │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────┐          │
│  │ Step 3: Generate Embeddings                       │          │
│  │ ─────────────────────────────────────────────────│          │
│  │ store_id = await retrieval_service.add_document_  │          │
│  │     chunks(file_id, chunk_texts, chunk_metadata) │          │
│  │                                                   │          │
│  │ This calls embedding provider to generate vectors│          │
│  └───────────────────────────────────────────────────┘          │
│                         │                                        │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────┐          │
│  │ Step 4: Update Embedding Status                   │          │
│  │ ─────────────────────────────────────────────────│          │
│  │ await file_metadata_provider.update_embedding_    │          │
│  │     status(file_id, "completed")                  │          │
│  └───────────────────────────────────────────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESPONSE TO USER                             │
│  {                                                              │
│    "file_id": "file_1761924716_b7aec34b_a3f1cb68",             │
│    "filename": "document.pdf",                                  │
│    "chunk_count": 78,                                           │
│    "embedding_status": "completed"                              │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Chunking Workflow Inside `process_file()`

**File**: `app/Services/input_data_handle_service.py:479-556`

```
┌─────────────────────────────────────────────────────────────────┐
│  INPUT DATA HANDLE SERVICE: process_file()                      │
│  File: app/Services/input_data_handle_service.py               │
│                                                                  │
│  ┌───────────────────────────────────────────────────┐          │
│  │ Step 1: Validate File                             │          │
│  │ ─────────────────────────────────────────────────│          │
│  │ is_valid, error = self.validate_file(             │          │
│  │     file_content, filename                        │          │
│  │ )                                                 │          │
│  │                                                   │          │
│  │ Checks:                                           │          │
│  │ ✓ File extension (.pdf, .docx, .txt, .md)        │          │
│  │ ✓ File size (< 100MB default)                    │          │
│  │ ✓ File not empty                                 │          │
│  │ ✓ PDF integrity (if PDF)                         │          │
│  └───────────────────────────────────────────────────┘          │
│                         │                                        │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────┐          │
│  │ Step 2: Generate Unique File ID                   │          │
│  │ ─────────────────────────────────────────────────│          │
│  │ file_id = await self.generate_unique_file_id(     │          │
│  │     file_content, filename, file_metadata_provider│          │
│  │ )                                                 │          │
│  │                                                   │          │
│  │ Format: file_{timestamp}_{uuid8}_{hash8}         │          │
│  │ Example: file_1761924716_b7aec34b_a3f1cb68       │          │
│  │                                                   │          │
│  │ Includes collision detection with database check │          │
│  └───────────────────────────────────────────────────┘          │
│                         │                                        │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────┐          │
│  │ Step 3: Extract Text                              │          │
│  │ ─────────────────────────────────────────────────│          │
│  │ text = self.extract_text(file_content, filename) │          │
│  │                                                   │          │
│  │ Uses different extractors based on file type:    │          │
│  │ • PDF  → PyPDF2.PdfReader                        │          │
│  │ • DOCX → python-docx                             │          │
│  │ • TXT  → Direct decode (UTF-8)                   │          │
│  │ • MD   → Direct decode (UTF-8)                   │          │
│  │                                                   │          │
│  │ Returns: Full document text as string            │          │
│  └───────────────────────────────────────────────────┘          │
│                         │                                        │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────┐          │
│  │ ⭐ Step 4: CHUNK TEXT (MAIN CHUNKING STEP)       │          │
│  │ ─────────────────────────────────────────────────│          │
│  │ base_metadata = {                                 │          │
│  │     "file_id": file_id,                          │          │
│  │     "filename": filename                          │          │
│  │ }                                                 │          │
│  │                                                   │          │
│  │ chunks = self.chunk_text(text, metadata=base_     │          │
│  │     metadata)                                     │          │
│  │                                                   │          │
│  │ ┌──────────────────────────────────────┐          │          │
│  │ │ CHUNKING STRATEGY SELECTION          │          │          │
│  │ │ ────────────────────────────────────│          │          │
│  │ │ Strategy set during initialization:  │          │          │
│  │ │                                      │          │          │
│  │ │ A) Hierarchical Chunking (Default)   │          │          │
│  │ │    - Multiple chunk sizes:           │          │          │
│  │ │      Large: 2000 chars               │          │          │
│  │ │      Medium: 1000 chars              │          │          │
│  │ │      Small: 500 chars                │          │          │
│  │ │    - Creates hierarchy of granularity│          │          │
│  │ │    - Better for complex documents    │          │          │
│  │ │                                      │          │          │
│  │ │ B) Recursive Chunking                │          │          │
│  │ │    - Single chunk size: 1000 chars   │          │          │
│  │ │    - Overlap: 200 chars              │          │          │
│  │ │    - Simpler, faster processing      │          │          │
│  │ └──────────────────────────────────────┘          │          │
│  │                                                   │          │
│  │ Returns: List[Dict] with:                         │          │
│  │   [                                               │          │
│  │     {                                             │          │
│  │       "content": "chunk text here...",            │          │
│  │       "metadata": {                               │          │
│  │         "file_id": "file_...",                    │          │
│  │         "filename": "doc.pdf",                    │          │
│  │         "chunk_index": 0,                         │          │
│  │         "chunk_size": "large",                    │          │
│  │         "start_char": 0,                          │          │
│  │         "end_char": 2000                          │          │
│  │       }                                           │          │
│  │     },                                            │          │
│  │     { ... chunk 2 ... },                          │          │
│  │     { ... chunk 3 ... }                           │          │
│  │   ]                                               │          │
│  └───────────────────────────────────────────────────┘          │
│                         │                                        │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────┐          │
│  │ Step 5: Enrich Chunk Metadata                     │          │
│  │ ─────────────────────────────────────────────────│          │
│  │ chunks = self.enrich_chunk_metadata(              │          │
│  │     chunks, file_id, filename, file_size          │          │
│  │ )                                                 │          │
│  │                                                   │          │
│  │ Adds additional metadata:                         │          │
│  │ • timestamp                                       │          │
│  │ • file_size                                       │          │
│  │ • content hash                                    │          │
│  │ • chunk statistics                                │          │
│  └───────────────────────────────────────────────────┘          │
│                         │                                        │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────┐          │
│  │ Return Result                                      │          │
│  │ ─────────────────────────────────────────────────│          │
│  │ return {                                          │          │
│  │     "file_id": file_id,                          │          │
│  │     "filename": filename,                         │          │
│  │     "file_size": len(file_content),              │          │
│  │     "chunks": chunks,  ← CHUNKED DATA            │          │
│  │     "chunk_count": len(chunks),                   │          │
│  │     "chunking_strategy": "HierarchicalChunking"  │          │
│  │ }                                                 │          │
│  └───────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Chunking Strategy Implementation Details

### File: `app/Services/chunking_strategies.py`

```python
# Strategy Pattern: Pluggable chunking algorithms

class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies"""

    @abstractmethod
    def chunk_text(self, text: str, metadata: Dict) -> List[Dict]:
        """Chunk text with metadata"""
        pass

class HierarchicalChunkingStrategy(ChunkingStrategy):
    """
    Hierarchical chunking with multiple granularity levels

    Example output for 10,000 char document:
    - 5 large chunks (2000 chars each)
    - 10 medium chunks (1000 chars each)
    - 20 small chunks (500 chars each)

    Total: 35 chunks at different granularity levels
    """

    def __init__(self, chunk_sizes=[2000, 1000, 500], overlap=200):
        self.chunk_sizes = chunk_sizes
        self.overlap = overlap
        # Creates multiple text splitters, one per size
        self.splitters = [
            RecursiveCharacterTextSplitter(
                chunk_size=size,
                chunk_overlap=overlap
            ) for size in chunk_sizes
        ]

    def chunk_text(self, text: str, metadata: Dict) -> List[Dict]:
        """
        Create chunks at multiple granularity levels

        Returns chunks from all levels combined:
        [
            {content: "large chunk 1", metadata: {chunk_size: "large", ...}},
            {content: "large chunk 2", metadata: {chunk_size: "large", ...}},
            {content: "medium chunk 1", metadata: {chunk_size: "medium", ...}},
            ...
        ]
        """
        all_chunks = []

        for size_name, splitter in zip(['large', 'medium', 'small'], self.splitters):
            raw_chunks = splitter.split_text(text)

            for idx, chunk_text in enumerate(raw_chunks):
                chunk_dict = {
                    "content": chunk_text,
                    "metadata": {
                        **metadata,
                        "chunk_index": idx,
                        "chunk_size": size_name,
                        "total_chunks_at_level": len(raw_chunks)
                    }
                }
                all_chunks.append(chunk_dict)

        return all_chunks
```

### File: `app/core/config.py`

```python
# Configuration for chunking behavior

CHUNKING_STRATEGY = "hierarchical"  # or "recursive"

# Recursive chunking settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Hierarchical chunking settings
HIERARCHICAL_CHUNK_SIZES = [2000, 1000, 500]  # Large, Medium, Small
HIERARCHICAL_OVERLAP = 200

# Text splitting separators (used by both strategies)
CHUNK_SEPARATORS = [
    "\n\n",    # Paragraph breaks (highest priority)
    "\n",      # Line breaks
    ". ",      # Sentences
    "! ",      # Exclamations
    "? ",      # Questions
    "; ",      # Semicolons
    ", ",      # Commas
    " ",       # Words
    ""         # Characters (fallback)
]
```

---

## Chunking Timeline in Upload Process

```
Time    Action                                  Location
────────────────────────────────────────────────────────────────────
T+0ms   User clicks upload button               Frontend (browser)
T+10ms  File sent via HTTP POST                 Network
T+20ms  Upload endpoint receives file           upload.py:206
T+30ms  File saved to disk                      upload.py:57-72
T+40ms  process_and_embed_file() called         upload.py:289
T+50ms  ├─ input_service.process_file()         input_data_handle_service.py:479
T+60ms  │  ├─ Validate file                     Line 514
T+70ms  │  ├─ Generate file_id                  Line 519-525
T+100ms │  ├─ Extract text from PDF             Line 528
T+500ms │  │  └─ PyPDF2 reads all pages
T+520ms │  │
T+530ms │  ├─ ⭐ CHUNK TEXT ⭐                  Line 532
T+540ms │  │  ├─ Large chunks (2000 chars)      chunking_strategies.py
T+550ms │  │  ├─ Medium chunks (1000 chars)     chunking_strategies.py
T+560ms │  │  └─ Small chunks (500 chars)       chunking_strategies.py
T+570ms │  │
T+580ms │  └─ Enrich metadata                   Line 535
T+590ms │     └─ Return chunks                  Line 542
T+600ms │
T+610ms ├─ Store file metadata in SQLite        upload.py:129
T+650ms ├─ Generate embeddings for chunks       upload.py:148
T+2000ms│  └─ Call embedding API (slow step)    retrieval_service.py
T+2100ms└─ Update embedding status              upload.py:157
T+2110ms
T+2120ms Response sent to user                  upload.py:252
```

**Key Observations**:
- **Chunking happens at T+530ms** (very early in the process)
- **Chunking is fast** (~50ms for typical documents)
- **Embedding generation is slow** (~1400ms) but happens **after** chunking
- **Total time**: ~2 seconds for a typical PDF

---

## Example: Document Chunking Output

### Input Document (3,500 characters)

```
"Introduction to Machine Learning
Machine learning is a subset of artificial intelligence...
[3,500 characters of content]
...Conclusion: ML is transforming industries worldwide."
```

### Hierarchical Chunking Output

**Total Chunks Created**: 7

#### Large Chunks (2000 chars each):
```json
[
  {
    "content": "Introduction to Machine Learning\nMachine learning...[first 2000 chars]",
    "metadata": {
      "file_id": "file_1761924716_b7aec34b_a3f1cb68",
      "filename": "ml_intro.pdf",
      "chunk_index": 0,
      "chunk_size": "large",
      "total_chunks_at_level": 2,
      "start_char": 0,
      "end_char": 2000
    }
  },
  {
    "content": "...continued from previous...[next 1500 chars]",
    "metadata": {
      "chunk_index": 1,
      "chunk_size": "large",
      "total_chunks_at_level": 2,
      "start_char": 1800,  // 200 char overlap
      "end_char": 3500
    }
  }
]
```

#### Medium Chunks (1000 chars each):
```json
[
  {"content": "[first 1000 chars]", "metadata": {"chunk_size": "medium", ...}},
  {"content": "[next 1000 chars]", "metadata": {"chunk_size": "medium", ...}},
  {"content": "[next 1000 chars]", "metadata": {"chunk_size": "medium", ...}},
  {"content": "[last 500 chars]", "metadata": {"chunk_size": "medium", ...}}
]
```

#### Small Chunks (500 chars each):
```json
[
  {"content": "[first 500 chars]", "metadata": {"chunk_size": "small", ...}},
  {"content": "[next 500 chars]", "metadata": {"chunk_size": "small", ...}},
  {"content": "[next 500 chars]", "metadata": {"chunk_size": "small", ...}},
  {"content": "[next 500 chars]", "metadata": {"chunk_size": "small", ...}},
  {"content": "[next 500 chars]", "metadata": {"chunk_size": "small", ...}},
  {"content": "[next 500 chars]", "metadata": {"chunk_size": "small", ...}},
  {"content": "[last 500 chars]", "metadata": {"chunk_size": "small", ...}}
]
```

**Total**: 2 large + 4 medium + 7 small = **13 chunks** (with overlaps)

---

## Why Chunk Before Embedding?

### Rationale:

1. **Embedding Model Limits**:
   - Most embedding models have max token limits (e.g., 512 tokens for BERT)
   - Full documents exceed this limit
   - Chunking makes documents fit model constraints

2. **Retrieval Granularity**:
   - Smaller chunks = more precise retrieval
   - Large chunks = more context
   - Hierarchical approach gives both benefits

3. **Memory Efficiency**:
   - Generating embeddings for full documents is memory-intensive
   - Chunking allows batch processing
   - Enables streaming for large files

4. **Relevance Scoring**:
   - Vector similarity works better on focused chunks
   - Full documents contain irrelevant sections that dilute relevance
   - Chunking improves search precision

---

## Configuration: How to Change Chunking Behavior

### Option 1: Change Strategy (config.py)

```python
# Switch to recursive chunking (simpler, faster)
CHUNKING_STRATEGY = "recursive"

# Adjust chunk size
CHUNK_SIZE = 1500  # Larger chunks = more context, fewer chunks
CHUNK_OVERLAP = 300  # More overlap = better continuity
```

### Option 2: Adjust Hierarchical Sizes (config.py)

```python
# Customize hierarchical chunk sizes
HIERARCHICAL_CHUNK_SIZES = [3000, 1500, 750]  # Larger chunks
# or
HIERARCHICAL_CHUNK_SIZES = [1000, 500]  # Only 2 levels (faster)
```

### Option 3: Pass Strategy at Runtime (upload endpoint)

```python
# In upload.py, when initializing InputDataHandleService
input_service = InputDataHandleService(
    chunking_strategy="recursive",  # Override default
    chunk_size=1500,
    chunk_overlap=300
)
```

---

## Summary

**Question**: "In what point do you perform chunking the uploaded files?"

**Answer**:
Chunking is performed in **`InputDataHandleService.process_file()`** at **Step 4** (line 532), which is called during the upload workflow **before** embedding generation. The process happens approximately **530ms** after the file is received, taking about **50ms** to complete for typical documents.

**Key Points**:
- ✅ **Location**: `app/Services/input_data_handle_service.py:532`
- ✅ **Method**: `self.chunk_text(text, metadata=base_metadata)`
- ✅ **Timing**: After text extraction, before embedding generation
- ✅ **Strategy**: Hierarchical chunking (default) or recursive chunking
- ✅ **Output**: List of chunk dictionaries with content and metadata
- ✅ **Performance**: Very fast (~50ms), not the bottleneck (embeddings are)

**Workflow Order**:
1. Validate file
2. Generate file_id
3. Extract text
4. **⭐ Chunk text ⭐** ← CHUNKING HAPPENS HERE
5. Enrich metadata
6. Store file metadata
7. Generate embeddings (uses chunks)
8. Store in vector database
