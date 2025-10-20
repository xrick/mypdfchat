# Fix: ValidationError for LLMChain - Runnable Type Expected

**Date**: 2025-10-21
**Error**: `ValidationError: 2 validation errors for LLMChain llm instance of Runnable expected`

## Error Analysis

### Full Error Message
```
ValidationError: 2 validation errors for LLMChain
llm
  instance of Runnable expected (type=type_error.arbitrary_type; expected_arbitrary_type=Runnable)
llm
  instance of Runnable expected (type=type_error.arbitrary_type; expected_arbitrary_type=Runnable)

Traceback:
File "/app.py", line 139, in main
    chain = load_qa_chain(llm, chain_type="stuff")
File "langchain/chains/question_answering/__init__.py", line 249, in load_qa_chain
    return loader_mapping[chain_type](
File "langchain/chains/question_answering/__init__.py", line 73, in _load_stuff_chain
    llm_chain = LLMChain(
File "pydantic/v1/main.py", line 347, in __init__
    raise validation_error
```

### Root Cause

The error occurred because **`init_ollama_model()` was defined as an async function but called synchronously**.

#### The Problem Code (app.py:43, 138)

```python
# Line 43: Defined as ASYNC
async def init_ollama_model(
    model: str = "gpt-oss:20b",
    base_url: str = "http://localhost:11434",
    **kwargs
) -> Ollama:
    return Ollama(model=model, base_url=base_url, **kwargs)

# Line 138: Called WITHOUT await
llm = init_ollama_model()  # ❌ Returns coroutine, NOT Ollama instance!
chain = load_qa_chain(llm, chain_type="stuff")  # ❌ Receives coroutine, not Runnable
```

#### What Happened

When you call an async function **without `await`**, Python returns a **coroutine object** instead of the actual return value:

```python
# What you expected:
llm = Ollama(model="gpt-oss:20b", base_url="http://localhost:11434")
# Type: <class 'langchain_community.llms.ollama.Ollama'>

# What you actually got:
llm = <coroutine object init_ollama_model at 0x123456>
# Type: <class 'coroutine'>
```

The `load_qa_chain()` function then receives a **coroutine** instead of an **Ollama (Runnable)** instance, causing Pydantic validation to fail.

### Type Hierarchy Check

```python
from langchain_community.llms.ollama import Ollama

# Ollama IS a Runnable:
Ollama.__mro__
# (<class 'Ollama'>,
#  <class 'BaseLLM'>,
#  <class 'BaseLanguageModel'>,
#  <class 'RunnableSerializable'>,
#  <class 'Runnable'>,  ✅ Here!
#  ...)

# But a coroutine is NOT:
type(init_ollama_model())
# <class 'coroutine'>  ❌ Not a Runnable!
```

## Solution Applied

### Fix #1: Remove `async` from `init_ollama_model`

**Before** (app.py:43):
```python
async def init_ollama_model(
    model: str = "gpt-oss:20b",
    base_url: str = "http://localhost:11434",
    **kwargs
) -> Ollama:
    return Ollama(model=model, base_url=base_url, **kwargs)
```

**After**:
```python
def init_ollama_model(  # ✅ Removed 'async'
    model: str = "gpt-oss:20b",
    base_url: str = "http://localhost:11434",
    **kwargs
) -> Ollama:
    return Ollama(model=model, base_url=base_url, **kwargs)
```

**Why**: `Ollama()` initialization is **synchronous**, so wrapping it in an async function serves no purpose and causes issues when called without `await`.

### Fix #2: Remove `async` from Embedding Functions

**Before** (app.py:69-101):
```python
async def _init_embeddings(name: str):
    return HuggingFaceEmbeddings(...)

async def get_embedder():
    global _hf_embedder
    if _hf_embedder is not None:
        return _hf_embedder
    _hf_embedder = _init_embeddings(model_name)  # ❌ Missing await!
    return _hf_embedder
```

**After**:
```python
def _init_embeddings(name: str):  # ✅ Removed 'async'
    return HuggingFaceEmbeddings(...)

def get_embedder():  # ✅ Removed 'async'
    global _hf_embedder
    if _hf_embedder is not None:
        return _hf_embedder
    _hf_embedder = _init_embeddings(model_name)  # ✅ Now correct
    return _hf_embedder
```

**Why**: `HuggingFaceEmbeddings()` is also synchronous. These functions were incorrectly marked as async.

### Fix #3: Replace `ChatOpenAI` with Ollama LLM

**Before** (app.py:161):
```python
qa = ConversationalRetrievalChain.from_llm(
    ChatOpenAI(model_name="gpt-3.5-turbo"),  # ❌ Not imported, won't work
    retriever=vectors.as_retriever(),
    return_source_documents=True
)
```

**After**:
```python
qa = ConversationalRetrievalChain.from_llm(
    llm,  # ✅ Use the Ollama instance
    retriever=vectors.as_retriever(),
    return_source_documents=True
)
```

**Why**: This was leftover code from when the app used OpenAI. Now it correctly uses the Ollama LLM instance.

## Verification

After applying fixes, test the app:

```bash
# 1. Ensure virtual environment is active
source .chatenv/bin/activate

# 2. Verify Ollama is running
curl http://localhost:11434/api/tags

# 3. Run the app
streamlit run app.py
```

### Expected Behavior

1. **App starts without errors**
2. **Upload a PDF** - Should process successfully
3. **Ask a question** - Should get response from Ollama
4. **Check logs** - Should see:
   ```
   INFO Using embedding model: all-MiniLM-L6-v2
   ```

### Debugging Tips

If you still get errors:

**Check if Ollama is running**:
```bash
# Start Ollama service
ollama serve

# In another terminal, verify
ollama list  # Should show available models
ollama run gpt-oss:20b --version  # Check if model exists
```

**Check LLM initialization**:
```python
# Test in Python
from langchain_community.llms.ollama import Ollama

llm = Ollama(model="gpt-oss:20b", base_url="http://localhost:11434")
print(type(llm))  # Should show: <class 'langchain_community.llms.ollama.Ollama'>
print(isinstance(llm, Runnable))  # Should be: True

# Test invocation
response = llm.invoke("Say hello")
print(response)
```

## Understanding Async vs Sync in Python

### When to Use Async

Use `async def` when:
1. **You're doing I/O-bound operations** (network, disk)
2. **You need to await other async functions**
3. **You want concurrent execution** with `asyncio.gather()`

Examples:
```python
# ✅ Good use of async
async def fetch_from_api(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# ✅ Good use of async
async def process_multiple_pdfs(files: list):
    tasks = [process_pdf(file) for file in files]
    return await asyncio.gather(*tasks)  # Concurrent processing
```

### When NOT to Use Async

Avoid `async def` when:
1. **Function does synchronous work only**
2. **No await statements inside**
3. **Wrapping sync libraries** (HuggingFace, Ollama, etc.)

Examples:
```python
# ❌ Bad: Async wrapper around sync code
async def init_ollama():
    return Ollama(model="gpt-oss:20b")  # No await, no I/O

# ✅ Good: Just use sync
def init_ollama():
    return Ollama(model="gpt-oss:20b")

# ❌ Bad: Async with blocking operation
async def load_model():
    model = SentenceTransformer("all-MiniLM-L6-v2")  # Blocks event loop!
    return model

# ✅ Good: Run blocking code in thread pool
async def load_model():
    loop = asyncio.get_event_loop()
    model = await loop.run_in_executor(
        None,
        SentenceTransformer,
        "all-MiniLM-L6-v2"
    )
    return model
```

## Common Async Pitfalls

### Pitfall #1: Calling Async Without Await

```python
# ❌ Wrong
async def get_data():
    return {"key": "value"}

result = get_data()  # Returns coroutine, NOT dict!
print(result["key"])  # TypeError: 'coroutine' object is not subscriptable

# ✅ Correct
result = await get_data()  # Awaits the coroutine
print(result["key"])  # Works!
```

### Pitfall #2: Mixing Sync and Async Incorrectly

```python
# ❌ Wrong
def sync_function():
    data = await async_function()  # SyntaxError: 'await' outside async function
    return data

# ✅ Correct
async def async_function_wrapper():
    data = await async_function()
    return data

# Or use asyncio.run() in sync context
def sync_function():
    data = asyncio.run(async_function())
    return data
```

### Pitfall #3: Blocking the Event Loop

```python
# ❌ Wrong: Blocks event loop for 5 seconds
async def slow_function():
    time.sleep(5)  # Blocking!
    return "done"

# ✅ Correct: Non-blocking sleep
async def slow_function():
    await asyncio.sleep(5)  # Non-blocking
    return "done"

# ✅ Correct: Run blocking code in executor
async def slow_function():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, blocking_function)
    return result
```

## Related Issues

### Issue: "RuntimeError: This event loop is already running"

**Cause**: Trying to use `asyncio.run()` inside an async function or when Streamlit already has an event loop.

**Fix**:
```python
# ❌ Wrong
async def main():
    result = asyncio.run(some_async_func())  # Error!

# ✅ Correct
async def main():
    result = await some_async_func()  # Just await it
```

### Issue: "Ollama connection refused"

**Cause**: Ollama service not running.

**Fix**:
```bash
# Start Ollama
ollama serve

# Verify
curl http://localhost:11434/api/tags
```

### Issue: "Model 'gpt-oss:20b' not found"

**Cause**: Model not downloaded to Ollama.

**Fix**:
```bash
# List available models
ollama list

# Pull the model
ollama pull gpt-oss:20b

# Or use a different model
# Edit app.py line 44:
model: str = "llama2:7b"  # Or another available model
```

## Summary

**Problem**: `init_ollama_model()` was async but called without `await`, returning a coroutine instead of an Ollama instance.

**Root Cause**: Incorrect use of `async` keyword on functions that perform synchronous operations.

**Solution**:
1. Remove `async` from `init_ollama_model()` (line 43)
2. Remove `async` from `_init_embeddings()` and `get_embedder()` (lines 69-101)
3. Replace hardcoded `ChatOpenAI` with `llm` variable (line 161)

**Result**: `load_qa_chain()` now receives a proper `Ollama` instance that implements `Runnable`, passing Pydantic validation.

**Lesson**: Only use `async def` when you actually need to `await` something or do concurrent I/O. Don't async-wrap synchronous code unnecessarily.
