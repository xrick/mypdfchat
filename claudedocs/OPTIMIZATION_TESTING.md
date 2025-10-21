# 優化驗證測試指南

本文件提供四項優化的測試驗證方法，確保所有優化功能正常運作。

---

## ✅ 優化項目概覽

| 優化項目 | 目標 | 預期提升 | 驗證方法 |
|---------|------|---------|---------|
| 1. Prompt Engineering | Token 使用效率 | ↓ 20% | 比較 prompt token 數量 |
| 2. Query 快取層 | 重複查詢速度 | ↑ 100x | 測試相同查詢回應時間 |
| 3. Embedding 本地化 | 首次啟動穩定性 | 穩定性 ↑ | 離線環境測試 |
| 4. Ollama 並發優化 | Throughput | ↑ 2-3x | 並發請求測試 |

---

## 🧪 測試準備

### 1. 環境準備

```bash
# 確保在專案目錄
cd /home/mapleleaf/LCJRepos/gitprjs/mypdfchat

# 確認 Ollama 運行
curl http://localhost:11434/api/tags

# (可選) 下載 embedding model 至本地
python scripts/download_model.py \
  -m sentence-transformers/all-MiniLM-L6-v2 \
  -o ./models/all-MiniLM-L6-v2 \
  --method st

# 設定環境變數
export EMBEDDING_MODEL=$(pwd)/models/all-MiniLM-L6-v2
```

### 2. 準備測試文件

```bash
# 使用專案中現有的 PDF 文件
ls *.pdf

# 或下載測試 PDF
# wget https://arxiv.org/pdf/2301.00234.pdf -O test_paper.pdf
```

---

## 測試 1: Prompt Engineering 優化驗證

### 目的
驗證自定義 prompt template 是否生效，並測量 token 使用效率。

### 測試步驟

1. **啟動應用**:
```bash
streamlit run app_st_20251021.py
```

2. **上傳 PDF 並提問**:
- 上傳任意 PDF 文件
- 提問: "這份文件的主要內容是什麼？"

3. **檢查日誌輸出**:
查看終端是否有以下內容確認 prompt template 已載入：
```
INFO:__main__:Loading embedding model: ...
```

4. **驗證回答品質**:
- ✅ 回答應簡潔精確
- ✅ 如文件中無相關資訊，應明確說明「文件中未提及此資訊」
- ✅ 不應有冗長的前言或廢話

### 預期結果

**優化前** (無自定義 prompt):
```
回答: 根據文件內容，我來為您詳細解釋一下。這份文件主要討論了...
（可能包含大量冗餘表述）
```

**優化後** (有自定義 prompt):
```
回答: 本文件介紹了 RAG (檢索增強生成) 架構，用於提升 LLM 回答準確性。
（簡潔直接）
```

### 定量驗證 (可選)

如需精確測量 token 使用：

```python
# 在 conversational_chat 函數中添加日誌
logger.info(f"Query tokens: {len(query.split())}")
logger.info(f"Answer tokens: {len(answer.split())}")
```

預期優化: 平均回答 token 數 ↓ 15-25%

---

## 測試 2: Query 快取層驗證

### 目的
驗證快取機制是否正常工作，測量快取命中時的速度提升。

### 測試步驟

1. **啟動應用並上傳 PDF**

2. **首次查詢** (Cache Miss):
```
問題: "這份文件的作者是誰？"
```
記錄回應時間 (例如: 5 秒)

3. **重複相同查詢** (Cache Hit):
```
問題: "這份文件的作者是誰？"
```
記錄回應時間 (例如: 0.05 秒)

4. **檢查日誌輸出**:

**首次查詢** (應看到):
```
INFO:__main__:Cache miss, executed query: 這份文件的作者是誰？...
```

**重複查詢** (應看到):
```
INFO:__main__:Cache hit for query: 這份文件的作者是誰？...
```

### 預期結果

| 查詢類型 | 回應時間 | 日誌訊息 |
|---------|---------|---------|
| 首次查詢 | 3-10 秒 | Cache miss, executed query |
| 快取命中 | < 0.1 秒 | Cache hit for query |

**速度提升**: 50-100x (取決於原始查詢複雜度)

### 驗證快取容量管理

連續執行 105 個不同查詢，驗證快取是否正確維持 100 個項目上限：

```python
# 可在 conversational_chat 函數後添加日誌
logger.info(f"Cache size: {len(st.session_state['query_cache'])}")
```

預期: Cache size 應保持在 ≤ 100

---

## 測試 3: Embedding 本地化驗證

### 目的
驗證 embedding model 可從本地路徑載入，無需網路連接。

### 測試步驟

#### 3.1 本地路徑載入測試

1. **下載模型至本地** (如尚未下載):
```bash
python scripts/download_model.py \
  -m sentence-transformers/all-MiniLM-L6-v2 \
  -o ./models/all-MiniLM-L6-v2 \
  --method st
```

2. **設定環境變數**:
```bash
export EMBEDDING_MODEL=$(pwd)/models/all-MiniLM-L6-v2
```

3. **啟動應用**:
```bash
streamlit run app_st_20251021.py
```

4. **檢查啟動日誌**:
應看到:
```
INFO:__main__:Embedding model configuration: /home/mapleleaf/LCJRepos/gitprjs/mypdfchat/models/all-MiniLM-L6-v2
INFO:__main__:Loading embedding model: /home/mapleleaf/LCJRepos/gitprjs/mypdfchat/models/all-MiniLM-L6-v2
```

5. **上傳 PDF 測試**:
- ✅ 應能正常處理 PDF
- ✅ 無網路錯誤或超時

#### 3.2 離線環境測試 (可選)

1. **模擬離線環境**:
```bash
# 暫時停用網路 (需 root 權限)
sudo iptables -A OUTPUT -p tcp --dport 443 -j DROP
sudo iptables -A OUTPUT -p tcp --dport 80 -j DROP
```

2. **啟動應用**:
```bash
export EMBEDDING_MODEL=$(pwd)/models/all-MiniLM-L6-v2
export TRANSFORMERS_OFFLINE=1
streamlit run app_st_20251021.py
```

3. **驗證功能**:
- ✅ 應能正常啟動
- ✅ 應能處理 PDF 並回答問題

4. **恢復網路**:
```bash
sudo iptables -F
```

### 預期結果

| 配置 | 啟動時間 | 網路需求 | 穩定性 |
|------|---------|---------|-------|
| Hub ID (無優化) | 10-30 秒 | ✅ 需要 | ⚠️ 中等 |
| 本地路徑 (優化後) | 2-5 秒 | ❌ 不需要 | ✅ 高 |

**穩定性提升**: 消除網路超時風險，啟動時間穩定

---

## 測試 4: Ollama 並發優化驗證

### 目的
驗證 Ollama 並發配置是否生效，測量 throughput 提升。

### 測試步驟

#### 4.1 基準測試 (優化前)

1. **停止現有 Ollama**:
```bash
pkill ollama
```

2. **以預設配置啟動** (PARALLEL=1):
```bash
ollama serve
```

3. **基準效能測試**:
```bash
# 單請求延遲
time curl -X POST http://localhost:11434/api/generate \
  -d '{
    "model": "gpt-oss:20b",
    "prompt": "Hello",
    "stream": false
  }'
```

記錄時間: 例如 `real 3.2s`

#### 4.2 優化測試 (優化後)

1. **使用優化腳本啟動**:
```bash
./start_ollama_optimized.sh
```

應看到:
```
╔════════════════════════════════════════╗
║   Ollama 優化啟動配置                 ║
╠════════════════════════════════════════╣
║ 並發請求數: 4                          ║
║ 模型保持時間: 24h                      ║
...
```

2. **重複基準測試**:
```bash
time curl -X POST http://localhost:11434/api/generate \
  -d '{
    "model": "gpt-oss:20b",
    "prompt": "Hello",
    "stream": false
  }'
```

3. **並發 throughput 測試**:
```bash
# 創建測試請求檔案
cat > request.json << 'EOF'
{
  "model": "gpt-oss:20b",
  "prompt": "Explain machine learning in one sentence",
  "stream": false
}
EOF

# 模擬多個並發用戶
for i in {1..4}; do
  (time curl -X POST http://localhost:11434/api/generate \
    -d @request.json \
    -H "Content-Type: application/json" \
    > /dev/null 2>&1) &
done
wait
```

### 預期結果

#### 單請求延遲對比

| 配置 | 延遲 | 變化 |
|------|------|------|
| PARALLEL=1 (預設) | 3.0-5.0s | 基準 |
| PARALLEL=4 (優化) | 3.2-5.5s | +5-10% |

⚠️ **注意**: 單請求延遲可能略微增加，但 throughput 顯著提升

#### Throughput 對比

| 配置 | 4 並發請求總時間 | Throughput |
|------|----------------|-----------|
| PARALLEL=1 | 12-20s (序列執行) | 0.2-0.3 req/s |
| PARALLEL=4 | 4-7s (並行執行) | 0.6-1.0 req/s |

**Throughput 提升**: 2-3x

### 驗證模型保持在記憶體

1. **發送首次請求**:
```bash
time curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "gpt-oss:20b", "prompt": "Hi", "stream": false}'
```

2. **等待 10 分鐘**

3. **發送第二次請求**:
```bash
time curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "gpt-oss:20b", "prompt": "Hi", "stream": false}'
```

**預期結果**:
- **優化前** (KEEP_ALIVE=5m): 第二次請求需重新載入模型，時間 +2-5s
- **優化後** (KEEP_ALIVE=24h): 第二次請求時間與首次相同，無載入延遲

---

## 📊 綜合效能報告範例

完成所有測試後，可生成以下報告：

```
╔═══════════════════════════════════════════════════════╗
║          PDF Chat 優化效能測試報告                    ║
╠═══════════════════════════════════════════════════════╣
║ 測試日期: 2025-10-21                                  ║
║ 測試環境: CPU-only, 16GB RAM                          ║
╠═══════════════════════════════════════════════════════╣
║ 1. Prompt Engineering                                 ║
║    Token 使用: ↓ 22% (80 → 62 tokens 平均)           ║
║    回答品質: ✅ 簡潔精準                              ║
╠═══════════════════════════════════════════════════════╣
║ 2. Query 快取層                                       ║
║    首次查詢: 4.2s                                     ║
║    快取命中: 0.04s (提升 105x)                        ║
║    快取容量管理: ✅ 正常 (100 項上限)                 ║
╠═══════════════════════════════════════════════════════╣
║ 3. Embedding 本地化                                   ║
║    啟動時間: 3.1s (優化前 18s)                        ║
║    離線測試: ✅ 通過                                  ║
║    穩定性: ✅ 無網路超時問題                          ║
╠═══════════════════════════════════════════════════════╣
║ 4. Ollama 並發優化                                    ║
║    單請求延遲: 3.8s → 4.1s (+8%)                      ║
║    4 並發 Throughput: 0.25 → 0.82 req/s (+228%)      ║
║    模型保持: ✅ 24小時常駐記憶體                      ║
╠═══════════════════════════════════════════════════════╣
║ 總結                                                  ║
║ ✅ 所有優化功能正常運作                               ║
║ ✅ 整體效能提升符合預期                               ║
║ ✅ 無發現功能退化或錯誤                               ║
╚═══════════════════════════════════════════════════════╝
```

---

## 🛠️ 故障排除

### 常見問題

#### Q1: 快取未生效
**症狀**: 相同查詢每次都顯示 "Cache miss"

**檢查**:
1. 查看 session state: 在 Streamlit sidebar 顯示快取大小
2. 驗證 hash 函數是否正確計算

**解決**:
```python
# 在 app_st_20251021.py 添加 debug 輸出
logger.debug(f"Cache key: {cache_key}")
logger.debug(f"Cache keys: {list(st.session_state['query_cache'].keys())}")
```

#### Q2: Ollama 並發配置未生效
**症狀**: 設定 PARALLEL=4 但仍只能處理 1 個請求

**檢查**:
```bash
# 查看 Ollama 進程環境變數
ps aux | grep ollama
cat /proc/$(pgrep ollama)/environ | tr '\0' '\n' | grep OLLAMA
```

**解決**:
1. 完全停止 Ollama: `pkill -9 ollama`
2. 使用優化腳本重新啟動: `./start_ollama_optimized.sh`

#### Q3: Embedding 仍從網路載入
**症狀**: 啟動時仍有下載行為

**檢查**:
```bash
# 確認環境變數
echo $EMBEDDING_MODEL

# 確認路徑存在且包含必要檔案
ls -la $EMBEDDING_MODEL
```

**解決**:
確保路徑為**絕對路徑**:
```bash
export EMBEDDING_MODEL=/home/mapleleaf/LCJRepos/gitprjs/mypdfchat/models/all-MiniLM-L6-v2
```

---

## 📝 測試檢查清單

完整測試前，確認以下項目：

### 環境準備
- [ ] Ollama 服務運行中 (`curl http://localhost:11434/api/tags`)
- [ ] 已下載 embedding model 至本地 (可選，但建議)
- [ ] 設定 `EMBEDDING_MODEL` 環境變數
- [ ] 有可用的測試 PDF 文件

### 測試執行
- [ ] ✅ Prompt Engineering 測試通過
- [ ] ✅ Query 快取層測試通過 (快取命中速度 >50x)
- [ ] ✅ Embedding 本地化測試通過 (啟動時間 <5s)
- [ ] ✅ Ollama 並發優化測試通過 (throughput +150%+)

### 功能驗證
- [ ] ✅ 所有原有功能正常 (上傳 PDF, 提問, 對話歷史)
- [ ] ✅ 無語法錯誤或 runtime 異常
- [ ] ✅ 日誌輸出正確顯示優化狀態

### 效能驗證
- [ ] ✅ Token 使用效率提升 >15%
- [ ] ✅ 快取命中速度提升 >50x
- [ ] ✅ 首次啟動穩定可靠
- [ ] ✅ 並發 throughput 提升 >2x

---

## 🎯 下一步建議

測試通過後，可考慮：

1. **生產部署**: 使用 systemd 管理 Ollama, 配置環境變數
2. **監控儀表板**: 收集效能指標，追蹤優化效果
3. **進一步優化**: 模型量化 (Q4), 更大快取容量, 智能 prompt 選擇
4. **文檔更新**: 將測試結果更新至 CLAUDE.md

---

## 🔗 相關文件

- [app_st_20251021.py](app_st_20251021.py) - 優化後的主應用程式
- [EMBEDDING_SETUP.md](EMBEDDING_SETUP.md) - Embedding 本地化詳細指南
- [OLLAMA_OPTIMIZATION.md](OLLAMA_OPTIMIZATION.md) - Ollama 優化詳細指南
- [start_ollama_optimized.sh](start_ollama_optimized.sh) - Ollama 優化啟動腳本
