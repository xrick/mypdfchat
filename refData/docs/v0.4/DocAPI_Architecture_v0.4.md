/DocAI
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── router.py
│   │
│   ├── core/
│   │   └── config.py
│   │
│   ├── models/
│   │   └── schemas.py
│   │
│   ├── Providers/                   <-- 您的【Layer 1】基礎設施接口
│   │   ├── __init__.py
│   │   ├── llm_provider/            # (您的)
│   │   │   ├── __init__.py
│   │   │   └── client.py            # 統一的 OpenAI API 客戶端
│   │   │
│   │   ├── embedding_provider/      # (新增)
│   │   │   ├── __init__.py
│   │   │   └── client.py            # 嵌入模型 (例如 SentenceTransformer)
│   │   │
│   │   └── vector_store_provider/   # (新增)
│   │       ├── __init__.py
│   │       └── client.py            # 向量數據庫 (例如 ChromaDB)
│   │
│   ├── services/                    <-- 您的【Layer 2】核心業務邏輯
│   │   ├── __init__.py
│   │   ├── core_logic_service.py    # 協調器
│   │   ├── input_data_handle_service.py # 提取、分塊
│   │   ├── prompt_service.py
│   │   ├── retrieval_service.py     # <== 將使用 Providers
│   │   └── state_transition_service.py
│   │
│   └── main.py                      # FastAPI 應用實例
│
├── .env
├── requirements.txt
└── uvicorn_runner.py