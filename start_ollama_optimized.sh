#!/bin/bash
# Ollama 優化啟動腳本
# 用途: 以優化配置啟動 Ollama 服務，提升並發處理能力

# ============ 配置參數 ============

# 並發請求數 (根據 CPU 核心數調整)
# 4-8 核心: 2, 8-16 核心: 4, 16+ 核心: 6-8
export OLLAMA_NUM_PARALLEL=4

# 模型保持在記憶體的時間
# 5m = 5 分鐘, 24h = 24 小時, -1 = 永久
export OLLAMA_KEEP_ALIVE=24h

# GPU 使用設定 (0 = CPU-only, -1 = 全部使用 GPU)
export OLLAMA_NUM_GPU=0

# 請求超時時間 (秒)
export OLLAMA_REQUEST_TIMEOUT=300

# 主機與端口
export OLLAMA_HOST=0.0.0.0:11434

# ============ 啟動服務 ============

echo "╔════════════════════════════════════════╗"
echo "║   Ollama 優化啟動配置                 ║"
echo "╠════════════════════════════════════════╣"
echo "║ 並發請求數: $OLLAMA_NUM_PARALLEL                       ║"
echo "║ 模型保持時間: $OLLAMA_KEEP_ALIVE                    ║"
echo "║ GPU 使用: $OLLAMA_NUM_GPU (0=CPU-only)              ║"
echo "║ 請求超時: $OLLAMA_REQUEST_TIMEOUT 秒                     ║"
echo "║ 監聽地址: $OLLAMA_HOST         ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "啟動 Ollama 服務..."
echo ""

# 檢查 Ollama 是否已安裝
if ! command -v ollama &> /dev/null; then
    echo "❌ 錯誤: Ollama 未安裝"
    echo "請訪問 https://ollama.ai 安裝 Ollama"
    exit 1
fi

# 檢查是否已有 Ollama 進程運行
if pgrep -x "ollama" > /dev/null; then
    echo "⚠️  警告: 檢測到已運行的 Ollama 進程"
    echo "請先停止現有進程: pkill ollama"
    echo "或允許此腳本自動重啟? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "正在停止現有 Ollama 進程..."
        pkill ollama
        sleep 2
    else
        echo "取消啟動"
        exit 0
    fi
fi

# 啟動 Ollama
exec ollama serve
