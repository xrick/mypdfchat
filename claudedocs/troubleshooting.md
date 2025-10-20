說明

你目前看到的訊息代表從 Hugging Face 下載模型時多次逾時（10 秒），導致下載不完整；Transformers 最後以「隨機初始化」補齊缺失權重，因而出現 “Some weights … were not initialized… You should probably TRAIN this model …”。這種狀況下產生的向量品質會很差。
我已做的修正

將預設主模型改為較小、普及度高的 sentence-transformers/all-MiniLM-L6-v2，以減少逾時機率；備援改為 jinaai/jina-embeddings-v2-base-zh。
文件更新：加入提高 Hub 逾時、清除壞掉快取、與離線使用的建議。
claudedocs/embedding-model-config.md
建議的解法（擇一或合併）

走離線路徑（最穩）
在可連網機器下載：python scripts/download_model.py -m sentence-transformers/all-MiniLM-L6-v2 -o ./models/all-MiniLM-L6-v2 --method st
複製 models/all-MiniLM-L6-v2 到你的機器
設定：export EMBEDDING_MODEL=/absolute/path/to/models/all-MiniLM-L6-v2
啟動：uvicorn app_fastapi_ollama:app --reload
提升下載成功率（若可連網）
設定快取與傳輸：
export HF_HOME=/path/to/hf-cache
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_READ_TIMEOUT=60
export HF_HUB_WRITE_TIMEOUT=60
換用較小主模型（已預設為 all-MiniLM-L6-v2），必要時設備援：
export EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
export EMBEDDING_FALLBACK=jinaai/jina-embeddings-v2-base-zh
若曾下載失敗，避免壞快取：
設一個全新快取資料夾：export HF_HOME=/path/to/new-cache
或刪除該模型的快取後再試
檢查載入是否正確
啟動時不再看到 “weights not initialized” 警告
第一次下載可能需較久；之後皆從快取載入
快速指令彙總

離線使用
python scripts/download_model.py -m sentence-transformers/all-MiniLM-L6-v2 -o ./models/all-MiniLM-L6-v2 --method st
export EMBEDDING_MODEL=$(pwd)/models/all-MiniLM-L6-v2
uvicorn app_fastapi_ollama:app --reload
線上下載但增加穩定性
export HF_HOME=$(pwd)/.hf-cache
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_READ_TIMEOUT=60
export HF_HUB_WRITE_TIMEOUT=60
uvicorn app_fastapi_ollama:app --reload
需要的話，我可以幫你檢查/清理本機的 Hugging Face 快取路徑，或直接把 EMBEDDING_MODEL 改寫成你指定的本地資料夾，確保完全離線可用。