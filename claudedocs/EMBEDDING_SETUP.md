# Embedding Model 本地化設定指南

## 🎯 目的
將 embedding model 下載至本地，避免每次啟動時從網路載入，提升首次啟動穩定性與速度。

## 📦 下載本地模型

### 方法 1: 使用內建腳本 (推薦)
```bash
# 下載 all-MiniLM-L6-v2 至本地
python scripts/download_model.py \
  -m sentence-transformers/all-MiniLM-L6-v2 \
  -o ./models/all-MiniLM-L6-v2 \
  --method st

# 設定環境變數指向本地模型
export EMBEDDING_MODEL=$(pwd)/models/all-MiniLM-L6-v2
```

### 方法 2: 手動使用 HuggingFace CLI
```bash
# 安裝 huggingface-cli
pip install -U huggingface_hub

# 下載模型
huggingface-cli download sentence-transformers/all-MiniLM-L6-v2 \
  --local-dir ./models/all-MiniLM-L6-v2 \
  --local-dir-use-symlinks False

# 設定環境變數
export EMBEDDING_MODEL=$(pwd)/models/all-MiniLM-L6-v2
```

## ⚙️ 配置應用程式

### 方式 1: 環境變數 (推薦)
```bash
# 在 .env 檔案中添加
EMBEDDING_MODEL=/absolute/path/to/models/all-MiniLM-L6-v2

# 或在啟動前 export
export EMBEDDING_MODEL=/home/mapleleaf/LCJRepos/gitprjs/mypdfchat/models/all-MiniLM-L6-v2
streamlit run app_st_20251021.py
```

### 方式 2: 使用 Hub ID (需網路)
```bash
# 預設使用 Hub ID，首次啟動會從網路下載並快取
export EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## 🔍 驗證配置

啟動應用後，檢查日誌輸出：
```
INFO:__main__:Embedding model configuration: /path/to/models/all-MiniLM-L6-v2
INFO:__main__:Loading embedding model: /path/to/models/all-MiniLM-L6-v2
```

## 📊 效能對比

| 配置方式 | 首次啟動時間 | 網路需求 | 穩定性 |
|---------|------------|---------|-------|
| Hub ID (預設) | 5-30 秒 | ✅ 需要 | ⚠️ 中等 |
| 本地路徑 | 2-5 秒 | ❌ 不需要 | ✅ 高 |

## 🛠️ 故障排除

### 問題 1: 模型載入失敗
```
RuntimeError: Could not load embedding models
```
**解決方案**:
1. 確認路徑存在: `ls -la $EMBEDDING_MODEL`
2. 確認路徑為絕對路徑，不是相對路徑
3. 檢查目錄包含必要檔案: `config.json`, `pytorch_model.bin` 等

### 問題 2: 網路超時
```
ReadTimeoutError: Read timed out
```
**解決方案**:
```bash
# 增加超時時間
export HF_HUB_READ_TIMEOUT=120
export HF_HUB_WRITE_TIMEOUT=120

# 使用離線模式 (需先下載模型)
export TRANSFORMERS_OFFLINE=1
```

### 問題 3: 權限錯誤
```
PermissionError: [Errno 13] Permission denied
```
**解決方案**:
```bash
# 確保目錄有讀取權限
chmod -R 755 ./models/
```

## 💡 最佳實踐

1. **生產環境**: 使用本地路徑，避免網路依賴
2. **開發環境**: 可使用 Hub ID，方便切換不同模型測試
3. **離線環境**: 必須預先下載至本地
4. **Docker 部署**: 在 image build 階段下載模型，runtime 使用本地路徑

## 🔗 相關資源

- [scripts/download_model.py](scripts/download_model.py) - 模型下載工具
- [HuggingFace Models](https://huggingface.co/sentence-transformers) - 可用模型列表
- [app_st_20251021.py:38-46](app_st_20251021.py#L38-L46) - Embedding 配置程式碼
