Architecture of DocAI

/DocAI
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── endpoints/
│   │       │   ├── __init__.py
│   │       │   ├── chat.py         # /chat (Streaming) 和 /upload 端點
│   │       │   └── export.py       # /export (Data Export) 端點
│   │       └── router.py           # API v1 總路由器
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py               # 應用程式配置 (例如 LLM API URL, DB 路徑)
│   │
│   ├── llm_provider/               <-- 您的【Layer 1】客戶端
│   │   ├── __init__.py
│   │   └── client.py               # 統一的 OpenAI API 客戶端 (使用 httpx)
│   │
│   ├── services/                   <-- 您的【Layer 2】核心
│   │   ├── __init__.py
│   │   ├── core_logic_service.py   # 協調器
│   │   ├── input_data_handle_service.py # 提取、分塊
│   │   ├── prompt_service.py       # 提示詞模板管理
│   │   ├── retrieval_service.py    # 嵌入和向量檢索
│   │   └── state_transition_service.py # 聊天歷史
│   │
│   ├── models/
│   │   └── schemas.py              # Pydantic 模型 (API 請求/回應)
│   │
│   └── main.py                     # FastAPI 應用實例和中間件
│
├── .env                            # 環境變數 (API Keys, LLM_PROVIDER_URL)
├── requirements.txt
└── uvicorn_runner.py               # 用於啟動 uvicorn