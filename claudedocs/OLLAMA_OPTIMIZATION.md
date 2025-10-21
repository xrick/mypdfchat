<!-- OLLAMA_OPTIMIZATION.md -->
# Ollama 並發優化指南

## 🎯 目的
提升 Ollama 的多用戶並發處理能力，將 throughput 提升 2-3 倍。

## ⚙️ 核心配置

### 1. 並發請求數量控制

Ollama 支援同時處理多個推理請求。預設值為 1，可透過環境變數調整：

```bash
# 設定並發請求數為 4 (建議值)
export OLLAMA_NUM_PARALLEL=4

# 重啟 Ollama 服務
ollama serve
```

**配置建議**:
| CPU 核心數 | 記憶體 | 推薦值 | 說明 |
|-----------|-------|-------|------|
| 4-8 核 | 16GB | 2 | 保守設定 |
| 8-16 核 | 32GB | 4 | 平衡設定 |
| 16+ 核 | 64GB+ | 6-8 | 高效能設定 |

### 2. 模型保持在記憶體中

預設情況下，Ollama 會在一段時間後卸載模型。保持模型常駐可減少載入延遲：

```bash
# 設定模型保持時間為 24 小時 (預設 5 分鐘)
export OLLAMA_KEEP_ALIVE=24h

# 或永久保持 (不推薦，會佔用記憶體)
export OLLAMA_KEEP_ALIVE=-1

# 重啟服務
ollama serve
```

### 3. GPU 記憶體優化 (若有 GPU)

```bash
# 設定 GPU 使用層數 (0 = 全 CPU, -1 = 全 GPU)
export OLLAMA_NUM_GPU=0  # CPU-only 環境使用此值

# 如未來有 GPU，可設定使用的 GPU 層數
# export OLLAMA_NUM_GPU=-1  # 全部使用 GPU
```

### 4. 請求超時設定

```bash
# 設定請求超時時間 (秒)
export OLLAMA_REQUEST_TIMEOUT=300  # 5 分鐘

# 對於長文檔處理，可能需要更長時間
export OLLAMA_REQUEST_TIMEOUT=600  # 10 分鐘
```

## 🚀 完整啟動腳本

創建一個優化的啟動腳本 `start_ollama_optimized.sh`:

```bash
#!/bin/bash
# Ollama 優化啟動腳本

# 並發優化
export OLLAMA_NUM_PARALLEL=4

# 模型保持在記憶體
export OLLAMA_KEEP_ALIVE=24h

# CPU-only 環境
export OLLAMA_NUM_GPU=0

# 請求超時
export OLLAMA_REQUEST_TIMEOUT=300

# 主機與端口
export OLLAMA_HOST=0.0.0.0:11434

echo "=== Ollama 優化配置 ==="
echo "並發請求數: $OLLAMA_NUM_PARALLEL"
echo "模型保持時間: $OLLAMA_KEEP_ALIVE"
echo "GPU 使用: $OLLAMA_NUM_GPU (0 = CPU-only)"
echo "請求超時: $OLLAMA_REQUEST_TIMEOUT 秒"
echo "======================="

# 啟動 Ollama
ollama serve
```

使用方式:
```bash
chmod +x start_ollama_optimized.sh
./start_ollama_optimized.sh
```

## 📊 效能基準測試

### 測試方法

1. **單請求延遲測試**:
```bash
time curl -X POST http://localhost:11434/api/generate \
  -d '{
    "model": "gpt-oss:20b",
    "prompt": "Explain RAG in one sentence",
    "stream": false
  }'
```

2. **並發 throughput 測試**:
```bash
# 安裝 Apache Bench
sudo apt-get install apache2-utils

# 執行並發測試 (100 請求, 10 並發)
ab -n 100 -c 10 -p request.json -T application/json \
  http://localhost:11434/api/generate
```

request.json 內容:
```json
{
  "model": "gpt-oss:20b",
  "prompt": "Hello",
  "stream": false
}
```

### 預期結果

| 配置 | 平均延遲 | Throughput | 並發能力 |
|------|---------|-----------|---------|
| 預設 (PARALLEL=1) | 基準 | 基準 | 1 req/time |
| PARALLEL=2 | +5-10% | +80-90% | 2 req/time |
| PARALLEL=4 | +10-15% | +150-200% | 4 req/time |
| PARALLEL=8 | +20-30% | +250-300% | 8 req/time |

⚠️ **注意**: 過高的並發數會導致：
- 記憶體不足
- CPU 競爭
- 延遲顯著增加

建議從 PARALLEL=2 開始測試，逐步增加至最佳值。

## 🔍 監控與調優

### 1. 檢查 Ollama 狀態

```bash
# 查看運行中的模型
curl http://localhost:11434/api/tags

# 查看模型資訊
curl http://localhost:11434/api/show -d '{"name": "gpt-oss:20b"}'
```

### 2. 系統資源監控

```bash
# 監控 CPU 與記憶體
htop

# 監控 Ollama 進程
watch -n 1 "ps aux | grep ollama"

# 記憶體使用
free -h
```

### 3. 日誌查看

```bash
# 如使用 systemd 管理
journalctl -u ollama -f

# 或直接查看輸出
ollama serve 2>&1 | tee ollama.log
```

## 💡 最佳實踐

### 生產環境部署

1. **使用 systemd 管理**:

創建 `/etc/systemd/system/ollama.service`:
```ini
[Unit]
Description=Ollama LLM Service
After=network.target

[Service]
Type=simple
User=mapleleaf
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_KEEP_ALIVE=24h"
Environment="OLLAMA_NUM_GPU=0"
Environment="OLLAMA_HOST=0.0.0.0:11434"
ExecStart=/usr/local/bin/ollama serve
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

啟動:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
sudo systemctl status ollama
```

2. **反向代理 (可選)**:

使用 nginx 提供負載均衡與請求限流:
```nginx
upstream ollama_backend {
    server 127.0.0.1:11434;
}

server {
    listen 8080;

    location / {
        proxy_pass http://ollama_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # 連接超時
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # 請求大小限制
        client_max_body_size 10M;
    }
}
```

3. **健康檢查**:

創建簡單的健康檢查腳本:
```bash
#!/bin/bash
# health_check.sh

response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags)

if [ "$response" = "200" ]; then
    echo "Ollama is healthy"
    exit 0
else
    echo "Ollama is unhealthy (HTTP $response)"
    exit 1
fi
```

## 🛠️ 故障排除

### 問題 1: 並發設定無效

**症狀**: 設定 `OLLAMA_NUM_PARALLEL` 後，仍只能處理 1 個請求

**解決方案**:
1. 確認環境變數已正確設定: `echo $OLLAMA_NUM_PARALLEL`
2. 完全重啟 Ollama: `pkill ollama && ollama serve`
3. 檢查 Ollama 版本: `ollama --version` (需 >= 0.1.20)

### 問題 2: 記憶體不足

**症狀**: `out of memory` 錯誤

**解決方案**:
1. 降低並發數: `OLLAMA_NUM_PARALLEL=2`
2. 使用量化模型: `ollama pull gpt-oss:20b-q4_0`
3. 減少模型保持時間: `OLLAMA_KEEP_ALIVE=5m`

### 問題 3: 回應緩慢

**症狀**: 並發增加後，單個請求延遲顯著增加

**解決方案**:
1. CPU 核心數不足，降低並發數
2. 檢查是否有其他進程競爭資源
3. 考慮使用更小的模型 (如 7B 而非 20B)

## 📈 進階優化

### 1. 模型量化

使用 4-bit 量化模型可顯著降低記憶體使用並提升速度：

```bash
# 下載量化版本
ollama pull gpt-oss:20b-q4_0

# 修改應用配置使用量化模型
# app_st_20251021.py line 50
# model: str = "gpt-oss:20b-q4_0"
```

**效能對比**:
| 版本 | 記憶體 | 速度 | 品質損失 |
|------|-------|------|---------|
| FP16 (預設) | 13GB | 基準 | 0% |
| Q8 | 7GB | +15% | <2% |
| Q4_0 | 4GB | +40% | ~5% |
| Q4_K_M | 4.5GB | +35% | ~3% |

### 2. 請求批次化

在應用層實作請求批次化（目前 Streamlit 版本為單用戶，此優化適用於 FastAPI 多用戶場景）。

### 3. 連接池管理

對於高並發場景，使用連接池避免重複建立連接。

## 🔗 相關資源

- [Ollama 官方文檔](https://github.com/ollama/ollama/blob/main/docs/faq.md)
- [app_st_20251021.py:49-72](app_st_20251021.py#L49-L72) - Ollama 初始化程式碼
- [Ollama API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md)
