# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a PDF Q&A chatbot using RAG (Retrieval-Augmented Generation) architecture:
- **Primary entry point**: `app_fastapi_ollama.py` (FastAPI backend with HTML/JS frontend)
- **Alternative UIs**: `app.py` and `modular_app.py` (Streamlit-based, experimental)
- **LLM**: Ollama (local inference, default model: `gpt-oss:20b`)
- **Embeddings**: HuggingFace SentenceTransformers (lazy-loaded with fallback)
- **Vector store**: FAISS (in-memory, no persistence)
- **PDF processing**: PyPDF2 + RecursiveCharacterTextSplitter (1000-char chunks, 200 overlap)

## Running the Application

### FastAPI Backend (Recommended)
```bash
# 1. Optional: Download embedding model locally (for offline use)
python scripts/download_model.py -m sentence-transformers/all-MiniLM-L6-v2 \
  -o ./models/all-MiniLM-L6-v2 --method st
export EMBEDDING_MODEL=$(pwd)/models/all-MiniLM-L6-v2

# 2. Start server
uvicorn app_fastapi_ollama:app --reload

# 3. Open http://localhost:8000/
```

### Streamlit Apps (Alternative)
```bash
streamlit run app.py
# OR
streamlit run streamlit_components/demo_app.py
```

**Important**: Do NOT run `streamlit run app_fastapi_ollama.py` - it will fail because that file is FastAPI-only.

## Environment Configuration

### Embedding Models
```bash
# Use Hub model ID (requires internet on first run)
export EMBEDDING_MODEL=all-MiniLM-L6-v2
export EMBEDDING_FALLBACK=jinaai/jina-embeddings-v2-base-zh

# OR use local path (for offline/airgapped environments)
export EMBEDDING_MODEL=/absolute/path/to/models/all-MiniLM-L6-v2
```

### Network Timeout Handling
If downloading models is slow or timing out:
```bash
export HF_HOME=$(pwd)/.hf-cache
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_READ_TIMEOUT=60
export HF_HUB_WRITE_TIMEOUT=60
```

**Warning**: Do NOT point `EMBEDDING_MODEL` to HuggingFace's cache subdirectory (e.g., `.../hub/models--<org>--<repo>`). Use either:
1. A model ID (e.g., `all-MiniLM-L6-v2`), OR
2. A directory created by `scripts/download_model.py`

### Ollama Configuration
The app expects Ollama running at `http://localhost:11434` with model `gpt-oss:20b`. To change:
- Modify `init_ollama_model()` in `app_fastapi_ollama.py` lines 55-56

## Architecture Deep Dive

### RAG Pipeline Flow
```
1. PDF Upload → PyPDF2 extracts text → RecursiveCharacterTextSplitter chunks text
2. Chunks → HuggingFaceEmbeddings (lazy-loaded) → FAISS vector store
3. Query → FAISS retrieves top-k relevant chunks → Context assembly
4. Context + Query + History → Ollama LLM → Response
```

### Critical Design Patterns

#### Lazy Singleton Embedding Initialization
`app_fastapi_ollama.py` uses a global `_hf_embedder` variable with lazy initialization in `get_embedder()` (lines 105-130):
- First call loads the model (blocks event loop 5-30s)
- Subsequent calls return cached instance
- Has fallback mechanism if primary model fails

**Implication**: First PDF upload will be slow due to model loading.

#### In-Memory State Management
Global dictionaries (lines 133-134):
- `vectors_store`: Maps `filename → FAISS index`
- `qa_chains`: Maps `filename → {llm, retriever}`

**Implication**:
- No persistence across server restarts
- Memory grows unbounded (potential leak)
- Cannot horizontally scale (session affinity required)

#### File-Relative Paths for Static Assets
Lines 44-48 use `Path(__file__).resolve().parent` to locate `static/` and `templates/`:
```python
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"
```

**Why**: Ensures paths work regardless of current working directory when running `uvicorn`.

### Known Issues & Quirks

1. **app.py has critical bugs**:
   - Line 124: `global vectores` (typo, should be `vectors`)
   - Line 161: References `ChatOpenAI` in an Ollama-based file (will fail)
   - Line 97: Unreachable exception due to indentation

2. **Async/Sync mixing**: Embedding initialization is synchronous but called from async contexts, blocking the event loop. Consider using `asyncio.to_thread()` for production.

3. **No input validation**: File uploads have no size limits, filenames are not sanitized (path traversal risk).

4. **CORS wide open**: `allow_origins=["*"]` in line 36 - restrict for production.

5. **ChromaDB unused**: Listed in `requirements.txt` but FAISS is used instead. Safe to remove.

## Key Files

- **app_fastapi_ollama.py**: Production-ready FastAPI backend (241 LOC)
- **app.py**: Experimental Streamlit version with Ollama (199 LOC, has bugs)
- **app_original.py**: Original OpenAI-based Streamlit version (121 LOC, deprecated)
- **modular_app.py**: Skeleton for parent-child RAG strategy (47 LOC, incomplete)
- **scripts/download_model.py**: CLI tool for downloading HF models to disk
- **claudedocs/**: Troubleshooting notes for embedding model issues, FastAPI setup

## API Endpoints

### `GET /`
Returns `templates/index.html`

### `POST /upload-pdf/`
- **Input**: `multipart/form-data` with `file` (PDF)
- **Output**: `{"status": "success", "filename": "example.pdf"}`
- **Side effect**: Stores FAISS index in `vectors_store[filename]`, creates QA chain in `qa_chains[filename]`

### `POST /chat/`
- **Input**: `application/x-www-form-urlencoded`
  - `query`: User question
  - `filename`: Previously uploaded PDF filename
  - `history`: JSON array of `[question, answer]` tuples
- **Output**: `{"answer": "...", "history": [[q, a], ...]}`

## Common Pitfalls

1. **"Directory 'static' does not exist"**: You ran `streamlit run app_fastapi_ollama.py`. Use `uvicorn` instead (see `claudedocs/fastapi-static-dir-error.md`).

2. **"Some weights were not initialized"**: Embedding model download timed out. See `claudedocs/troubleshooting.md` for offline setup or timeout fixes.

3. **"Path ... not found"**: `EMBEDDING_MODEL` points to invalid location. Use a model ID or path created by `scripts/download_model.py`.

4. **Signal errors when running `python app_fastapi_ollama.py`**: Lines 231-240 require `RUN_UVICORN=1` env var. Use `uvicorn` CLI instead.

## Development Notes

- **No tests exist**: Add `pytest` coverage before refactoring.
- **No linting configured**: Consider adding `ruff` or `black` for code formatting.
- **Dependencies**: `requirements.txt` uses `>=` pinning. For reproducible builds, pin exact versions.
- **Model storage**: `models/` directory (1.6GB) should be in `.gitignore` and managed separately (Git LFS or artifact registry).
