# Dependency Analysis Report - DocAI RAG Application

**Generated**: 2025-10-30  
**Analysis Type**: Comprehensive Dependency Assessment  
**Status**: 🟡 **Action Required**

---

## Executive Summary

| Category | Status | Count |
|----------|--------|-------|
| Total Declared Dependencies | ✅ | 18 packages |
| Installed Dependencies | 🟡 | 14 packages |
| **Missing Critical Dependencies** | 🔴 | **4 packages** |
| Missing Optional Dependencies | 🟡 | 2 packages |
| Version Mismatches | ⚠️ | 6 packages |

**Critical Finding**: 系統無法啟動，缺少 4 個核心 dependencies。

---

## 1. Missing Dependencies (CRITICAL)

### 🔴 P0 - Must Install (System Cannot Start)

| Package | Required Version | Status | Impact | Usage |
|---------|-----------------|--------|--------|-------|
| **PyPDF2** | 3.0.1 | ❌ Missing | 🔴 CRITICAL | PDF 文件解析 (核心功能) |
| **pymongo** | 4.6.1 | ❌ Missing | 🔴 CRITICAL | MongoDB 同步 driver |
| **motor** | 3.3.2 | ❌ Missing | 🔴 CRITICAL | MongoDB 異步 driver (chat history) |
| **aiosqlite** | 0.19.0 | ❌ Missing | 🔴 CRITICAL | SQLite 異步 driver (file metadata) |

**Error When Starting Without These**:
```python
ModuleNotFoundError: No module named 'PyPDF2'
ModuleNotFoundError: No module named 'pymongo'
ModuleNotFoundError: No module named 'motor'
ModuleNotFoundError: No module named 'aiosqlite'
```

**Affected Components**:
- `PyPDF2`: `app/Services/input_data_handle_service.py:16`
- `pymongo`: Used by `motor` backend
- `motor`: `app/Providers/chat_history_provider/client.py:29`
- `aiosqlite`: `app/Providers/file_metadata_provider/client.py:48`

---

### 🟡 P1 - Recommended (Fallback Available)

| Package | Required Version | Status | Impact | Fallback |
|---------|-----------------|--------|--------|----------|
| **sse-starlette** | 1.8.2 | ❌ Missing | 🟡 HIGH | No fallback, SSE streaming 必需 |
| **faiss-cpu** | 1.7.4 | ❌ Missing | 🟢 LOW | Can use Milvus instead |

**Note**: `sse-starlette` is **required** for chat streaming (OPMP). Without it, `/api/v1/chat/stream` endpoint will fail.

---

## 2. Installed Dependencies

### ✅ Core Dependencies (Installed)

| Package | Required | Installed | Status |
|---------|----------|-----------|--------|
| fastapi | 0.109.0 | 0.115.12 | ✅ Newer version (compatible) |
| uvicorn | 0.27.0 | 0.34.3 | ✅ Newer version (compatible) |
| python-multipart | 0.0.6 | 0.0.20 | ✅ Newer version |
| langchain | 0.1.0 | 0.3.26 | ⚠️ Major API changes |
| langchain-community | 0.0.13 | 0.3.27 | ⚠️ Major version bump |
| httpx | 0.26.0 | 0.28.1 | ✅ Minor bump |
| sentence-transformers | 2.3.1 | 5.1.1 | ⚠️ Major version bump |
| pymilvus | 2.3.5 | 2.5.12 | ✅ Minor bump |
| redis | 5.0.1 | 6.4.0 | ✅ Major bump (compatible) |
| pydantic | 2.5.3 | 2.10.3 | ✅ Minor bump within v2 |
| pydantic-settings | 2.1.0 | 2.10.1 | ✅ Minor bump |
| python-dotenv | 1.0.0 | 1.1.0 | ✅ Minor bump |

---

## 3. Version Compatibility Analysis

### 🟢 Low Risk (Backward Compatible)

```
✅ fastapi 0.109.0 → 0.115.12
   - Minor version bumps in 0.1xx series
   - No breaking changes expected
   
✅ uvicorn 0.27.0 → 0.34.3
   - Server implementation, no API changes
   
✅ pydantic 2.5.3 → 2.10.3
   - Same major version (v2), backward compatible
   
✅ pymilvus 2.3.5 → 2.5.12
   - Minor version, API stable
```

---

### 🟡 Medium Risk (API Changes Possible)

```
⚠️ langchain 0.1.0 → 0.3.26
   Risk: Major version jump (0.1 → 0.3)
   Impact: Potential API changes in text splitting and retrievers
   Affected Files:
   - app/Services/input_data_handle_service.py
   - app/Services/chunking_strategies.py
   
   Migration Notes:
   - RecursiveCharacterTextSplitter: API likely stable
   - MultiVectorRetriever: Check if import path changed
   - Document class: Verify metadata structure
   
⚠️ sentence-transformers 2.3.1 → 5.1.1
   Risk: Major version jump (2 → 5)
   Impact: Embedding model loading API may have changed
   Affected Files:
   - app/Providers/embedding_provider/client.py
   
   Action: Test embedding generation after install
```

---

### 🔴 High Risk (Breaking Changes Likely)

```
🚨 langchain-community 0.0.13 → 0.3.27
   Risk: Very early version (0.0.x) to stable (0.3.x)
   Impact: Import paths and API likely changed
   
   Check Required:
   - Verify all langchain_community imports still valid
   - Test document loaders and utilities
```

---

## 4. Dependency Usage Analysis

### 📊 Import Usage Map

| Dependency | Direct Imports | Indirect Usage | Priority |
|------------|----------------|----------------|----------|
| fastapi | 5 files | Framework core | P0 |
| uvicorn | 1 file (main.py) | ASGI server | P0 |
| sse-starlette | 1 file (chat.py) | SSE streaming | P0 |
| langchain | 2 files | Text splitting | P0 |
| PyPDF2 | 1 file | PDF extraction | P0 |
| motor | 1 file | Chat history | P0 |
| aiosqlite | 1 file | File metadata | P0 |
| redis | 1 file (cache) | Cache provider | P1 |
| pymilvus | 1 file | Vector store | P1 |
| httpx | 1 file (llm) | HTTP client | P1 |
| sentence-transformers | Indirect | Embeddings | P1 |
| pydantic | 8+ files | Schema validation | P0 |
| python-dotenv | 1 file (config) | Env loading | P0 |

---

### 🔍 Indirect/Runtime Dependencies

These are declared but not directly imported (used by FastAPI or as runtime deps):

```
python-multipart
├─ Usage: File upload handling (FastAPI)
├─ Import: Implicit by FastAPI's UploadFile
└─ Required: Yes (for PDF upload endpoint)

faiss-cpu
├─ Usage: Vector store fallback
├─ Import: Conditional (if Milvus unavailable)
└─ Required: No (can use Milvus)

langchain-community
├─ Usage: Document loaders, utilities
├─ Import: Potentially indirect via langchain
└─ Required: Verify after langchain 0.3.26 install
```

---

## 5. Missing Optional Dependencies

### python-docx (Optional)

**Status**: Not in requirements.txt  
**Code Reference**: `app/Services/input_data_handle_service.py:18-20`

```python
try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None
```

**Analysis**:
- 🟢 Has graceful fallback (try/except)
- 🟢 Only needed if user uploads DOCX files
- 📝 Current ALLOWED_EXTENSIONS = ["pdf"] only
- ✅ **Not required** for current system

**Recommendation**: Add to requirements.txt if DOCX support is planned:
```
python-docx==0.8.11  # Optional: DOCX file support
```

---

## 6. Installation Commands

### Quick Fix (Install Missing Only)

```bash
# Install critical missing dependencies
pip install PyPDF2==3.0.1 pymongo==4.6.1 motor==3.3.2 aiosqlite==0.19.0

# Install recommended (SSE streaming)
pip install sse-starlette==1.8.2

# Optional: Vector store fallback
pip install faiss-cpu==1.7.4
```

**Estimated Time**: 1-2 minutes

---

### Full Install (Recommended)

```bash
# Install all dependencies from requirements.txt
pip install -r requirements.txt

# This will:
# - Install all missing packages
# - Upgrade packages to required versions (may downgrade some)
# - Ensure exact version matching
```

**Estimated Time**: 5-10 minutes  
**Notes**: 
- `sentence-transformers` may download models (~400MB)
- `faiss-cpu` compilation may take time

---

## 7. Post-Installation Verification

### Verification Script

```bash
python3 << 'EOF'
import importlib.util

critical = ['fastapi', 'uvicorn', 'PyPDF2', 'pymongo', 'motor', 
            'aiosqlite', 'sse_starlette', 'langchain', 'redis']

missing = [m for m in critical if importlib.util.find_spec(m) is None]

if missing:
    print(f"❌ Still missing: {', '.join(missing)}")
else:
    print("✅ All critical dependencies installed!")
