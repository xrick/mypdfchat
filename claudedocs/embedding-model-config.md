Fix: FileNotFoundError for HuggingFaceEmbeddings local path

Symptom
- Uvicorn fails to start and logs:
  `FileNotFoundError: Path /home/.../Embedding_Models/jina-embeddings-v2-base-zh not found`
  or repeated network timeouts when downloading from Hugging Face Hub.

Root cause
- `app_fastapi_ollama.py` previously hard‑coded a local model path that does not exist on your machine.

What changed
- The app now reads the embedding model from an env var `EMBEDDING_MODEL`, defaulting to a small, widely cached model: `all-MiniLM-L6-v2`.
- It prefers the newer `langchain-huggingface` package if installed, with a backward‑compatible fallback to `langchain_community`.
- If loading the primary model fails (e.g., network timeout), the app tries a fallback model specified by `EMBEDDING_FALLBACK` or `jinaai/jina-embeddings-v2-base-zh`.

How to use a local model path
1) Place your model files on disk (e.g., `/models/jina-embeddings-v2-base-zh`).
2) Export the path before starting Uvicorn:
   - macOS/Linux: `export EMBEDDING_MODEL=/models/jina-embeddings-v2-base-zh`
   - Windows (PowerShell): `$env:EMBEDDING_MODEL = "C:\\models\\jina-embeddings-v2-base-zh"`
3) Start: `uvicorn app_fastapi_ollama:app --reload`

How to use a Hub model ID
- Let the default stand, or set a different model:
  - `export EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`

Dependencies
- For the preferred import path:
  - `pip install -U langchain-huggingface sentence-transformers`
- If staying on older LangChain versions, the fallback import will be used automatically.

Notes
- Downloading a Hub model requires internet access the first time; subsequent runs will use the local cache.
- CPU use is configured by default via `model_kwargs={"device": "cpu"}`; adjust if you have GPU support.
- 請勿把 `EMBEDDING_MODEL` 指到 Hugging Face 的快取子目錄（例如 `.../hub/models--<org>--<repo>`）；這不是有效的模型路徑。
  - 正確做法：
    - 指定模型 ID（如 `all-MiniLM-L6-v2` 或 `jinaai/jina-embeddings-v2-base-zh`），或
    - 使用 `scripts/download_model.py` 把模型下載到自訂資料夾，然後把 `EMBEDDING_MODEL` 指到該資料夾。

Handling slow networks / timeouts
- Prefer setting a local cache directory to avoid repeated downloads:
  - `export HF_HOME=/path/to/hf-cache` (or `HUGGINGFACE_HUB_CACHE` / `TRANSFORMERS_CACHE`)
- Optionally enable faster transfer:
  - `export HF_HUB_ENABLE_HF_TRANSFER=1`
- If your network is flaky, point `EMBEDDING_MODEL` to a local path you prepared offline.
- If you see warnings like “Some weights of BertModel were not initialized…”, it often means the model didn’t download correctly and was partially/blank initialized. Fix by ensuring a successful download or using a verified local path.
- Increase Hub timeouts when needed:
  - `export HF_HUB_READ_TIMEOUT=60` and `export HF_HUB_WRITE_TIMEOUT=60`
- Avoid corrupted partial cache: use a fresh cache dir (HF_HOME) or remove the specific model’s cache folder before retrying.

Compatibility note
- 不要把 `cache_folder` 放進 `model_kwargs` 傳給 `HuggingFaceEmbeddings`；部分版本會與內部參數衝突，造成
  `TypeError: SentenceTransformer() got multiple values for keyword argument 'cache_folder'`。
- 如需指定快取位置，使用環境變數（`HF_HOME`/`HUGGINGFACE_HUB_CACHE`/`TRANSFORMERS_CACHE`）。
