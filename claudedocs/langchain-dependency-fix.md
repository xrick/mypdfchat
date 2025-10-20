# Fix: ModuleNotFoundError: No module named 'langchain_core.pydantic_v1'

**Date**: 2025-10-21
**Error**: `ModuleNotFoundError: No module named 'langchain_core.pydantic_v1'` when running `streamlit run app.py`

## Root Cause Analysis

### Problem 1: Version Incompatibility
The error occurs due to **incompatible LangChain package versions**:

- `langchain==0.1.13` (old) expects `langchain-core` with `pydantic_v1` compatibility module
- `langchain-core==1.0.0` (new) **removed** the `pydantic_v1` module in favor of Pydantic v2 native support
- This creates an import chain failure:
  ```
  langchain.chains.question_answering
    → langchain.chains.combine_documents.reduce
      → langchain_core.pydantic_v1  ❌ Not found in v1.0.0!
  ```

### Problem 2: Broken Virtual Environment
The `.chatenv` virtual environment has mixed Python versions:
- Python 3.10 directory structure (`lib/python3.10/site-packages`)
- BUT actually using Python 3.11 from miniconda3
- Packages installing to wrong location

## Solution

### Option 1: Use Compatible LangChain Versions (RECOMMENDED)

Install `langchain-core < 0.2.0` to ensure `pydantic_v1` compatibility:

```bash
# 1. Delete the broken virtual environment
rm -rf .chatenv

# 2. Create fresh virtual environment with Python 3.11
python3 -m venv .chatenv

# 3. Activate
source .chatenv/bin/activate

# 4. Upgrade pip
pip install --upgrade pip

# 5. Install compatible versions
pip install \
  "langchain==0.1.13" \
  "langchain-core>=0.1.33,<0.2.0" \
  "langchain-community==0.0.29" \
  "langchain-huggingface==0.0.2" \
  "langchain-text-splitters<0.1"

# 6. Install other dependencies
pip install -r requirements.txt

# 7. Verify
python -c "from langchain.chains.question_answering import load_qa_chain; print('✅ Success!')"
```

### Option 2: Upgrade to Latest LangChain (REQUIRES CODE CHANGES)

If you want to use the latest LangChain, you'll need to update `app.py`:

```bash
# Install latest versions
pip install \
  "langchain>=0.3.0" \
  "langchain-community>=0.3.0" \
  "langchain-huggingface>=1.0.0"
```

**Then update app.py** (lines 11-17):

```python
# OLD (deprecated imports)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.question_answering import load_qa_chain
from langchain.chains import ConversationalRetrievalChain

# NEW (langchain 0.3+)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
```

### Option 3: Quick Fix (Current Session Only)

If you just need to run it once:

```bash
# Uninstall conflicting packages
pip uninstall -y langchain langchain-core langchain-community langchain-text-splitters

# Install exact versions
pip install --no-cache-dir \
  langchain==0.1.13 \
  langchain-core==0.1.53 \
  langchain-community==0.0.29

# Test
streamlit run app.py
```

## Verification Steps

After applying the fix:

```bash
# 1. Check installed versions
pip list | grep langchain

# Expected output:
# langchain                 0.1.13
# langchain-community       0.0.29
# langchain-core            0.1.53  (NOT 1.0.0!)
# langchain-huggingface     0.0.2
# langchain-text-splitters  0.0.2

# 2. Test imports
python -c "from langchain_core.pydantic_v1 import Extra; print('✅ pydantic_v1 available')"
python -c "from langchain.chains.question_answering import load_qa_chain; print('✅ Import works')"

# 3. Run app
streamlit run app.py
```

## Updated requirements.txt

Replace current [requirements.txt](../requirements.txt) with:

```txt
# LangChain stack (pinned for compatibility)
langchain==0.1.13
langchain-core>=0.1.33,<0.2.0  # MUST be < 0.2 for pydantic_v1 support
langchain-community==0.0.29
langchain-huggingface==0.0.2
langchain-text-splitters<0.1

# Streamlit
streamlit==1.32.2
streamlit-chat==0.1.1

# Vector Store
chromadb==0.4.24  # (Note: unused, FAISS is used instead)

# PDF Processing
pypdf==4.1.0

# FastAPI stack
fastapi==0.110.1
uvicorn[standard]==0.27.1
jinja2==3.1.3
python-multipart==0.0.9

# Embeddings
sentence-transformers>=2.5
huggingface-hub>=0.24

# Ollama (if using app.py instead of app_fastapi_ollama.py)
# Note: app.py currently has bugs, use app_fastapi_ollama.py instead
```

## Why This Happened

### LangChain v0.1 → v0.2 Breaking Change

In `langchain-core==0.2.0`, the developers:
1. Fully migrated to Pydantic v2
2. **Removed** the `pydantic_v1` compatibility shim
3. This broke all older `langchain` packages that still imported from `langchain_core.pydantic_v1`

### Timeline
- `langchain==0.1.13` (Jan 2024): Uses `langchain_core.pydantic_v1`
- `langchain-core==0.2.0` (Apr 2024): Removes `pydantic_v1` module
- `langchain-core==1.0.0` (Oct 2024): No backward compatibility

### Migration Path
```
langchain 0.1.x ─┬─> Requires langchain-core < 0.2.0 ✅
                 └─> BREAKS with langchain-core >= 0.2.0 ❌

langchain 0.2.x ─┬─> Compatible with langchain-core 0.2.x ✅
                 └─> Removed pydantic_v1 imports

langchain 0.3.x ──> Full Pydantic v2, new APIs
```

## Prevention

### Use Strict Version Pinning

**pyproject.toml** (recommended):
```toml
[project]
dependencies = [
    "langchain==0.1.13",
    "langchain-core>=0.1.33,<0.2.0",  # Prevents accidental upgrades
    "langchain-community==0.0.29",
]
```

### Pin All Dependencies
```bash
# Generate locked requirements
pip install pip-tools
pip-compile requirements.in --output-file=requirements.txt

# Install from locked file
pip install -r requirements.txt
```

### Use Dependabot/Renovate
Add `.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

## Related Issues

- LangChain GitHub Issue: https://github.com/langchain-ai/langchain/issues/18310
- Migration Guide: https://python.langchain.com/docs/versions/v0_2/
- Pydantic v1 → v2 Migration: https://docs.pydantic.dev/latest/migration/

## Troubleshooting

### Error: "Some weights were not initialized"
See: [troubleshooting.md](troubleshooting.md) - Embedding model download issue

### Error: "Directory 'static' does not exist"
See: [fastapi-static-dir-error.md](fastapi-static-dir-error.md) - Wrong entry point

### Import still fails after fix
```bash
# Clear pip cache
pip cache purge

# Remove all langchain packages
pip uninstall -y langchain langchain-core langchain-community langchain-text-splitters langchain-huggingface

# Manually remove residual files
rm -rf ~/.cache/pip/http/
rm -rf .chatenv/lib/python*/site-packages/langchain*

# Reinstall
pip install --no-cache-dir langchain==0.1.13 langchain-core==0.1.53 langchain-community==0.0.29
```

### Virtual environment issues
```bash
# Completely rebuild
deactivate
rm -rf .chatenv
python3 -m venv .chatenv
source .chatenv/bin/activate
pip install -r requirements.txt
```

## Summary

**Short version**: Install `langchain-core>=0.1.33,<0.2.0` instead of 1.0.0 to keep the `pydantic_v1` module that older code relies on.

**Long-term**: Upgrade to `langchain>=0.3.0` and refactor code to use new APIs.
