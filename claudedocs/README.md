Docs Index

- FastAPI static/templates issue and fix:
  - claudedocs/fastapi-static-dir-error.md

- Embedding model configuration, timeouts, offline use:
  - claudedocs/embedding-model-config.md

- Downloading a model to disk (script):
  - scripts/download_model.py
  - Examples:
    - python scripts/download_model.py -m sentence-transformers/all-MiniLM-L6-v2 -o ./models/all-MiniLM-L6-v2 --method st
    - export EMBEDDING_MODEL=$(pwd)/models/all-MiniLM-L6-v2
    - uvicorn app_fastapi_ollama:app --reload

