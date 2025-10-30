#!/bin/bash
# TeacherAssist 系統停止腳本
# 用途: 優雅地停止所有服務

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 專案根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 工具函數
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

echo "🛑 TeacherAssist 系統停止（Docker 模式）"
echo "========================================"
echo ""

# ===== Step 1: 停止 Frontend =====
echo "Step 1: 停止 Frontend"
echo "--------------------"

# 從 PID 檔案停止
if [ -f "/tmp/frontend.pid" ]; then
    FRONTEND_PID=$(cat /tmp/frontend.pid)
    if ps -p $FRONTEND_PID >/dev/null 2>&1; then
        kill $FRONTEND_PID 2>/dev/null && print_success "Frontend 已停止 (PID: $FRONTEND_PID)"
        rm -f /tmp/frontend.pid
    else
        print_info "Frontend PID 檔案存在但程序未運行"
        rm -f /tmp/frontend.pid
    fi
else
    # 嘗試通過進程名停止
    FRONTEND_PIDS=$(ps aux | grep "python3.*http.server.*8080" | grep -v grep | awk '{print $2}')
    if [ -n "$FRONTEND_PIDS" ]; then
        print_info "停止 Frontend (PID: $FRONTEND_PIDS)..."
        echo "$FRONTEND_PIDS" | xargs kill 2>/dev/null || true
        sleep 1
        print_success "Frontend 已停止"
    else
        print_info "Frontend 未運行"
    fi
fi

echo ""

# ===== Step 2: 停止 Docker 容器 =====
echo "Step 2: 停止 Docker 容器"
echo "----------------------"

# 檢查 Docker 是否運行
if ! docker info >/dev/null 2>&1; then
    print_warning "Docker daemon 未運行，跳過容器停止"
else
    # 停止並移除容器
    print_info "停止所有 Docker 容器..."
    if docker compose ps -q | grep -q .; then
        docker compose down
        print_success "Docker 容器已停止並移除"
    else
        print_info "無運行中的 Docker 容器"
    fi
fi

echo ""

# ===== Step 3: 停止 Ollama 服務 (可選) =====
echo "Step 3: 停止 Ollama 服務（可選）"
echo "------------------------------"

if pgrep -x "ollama" > /dev/null; then
    print_warning "Ollama 服務仍在運行"
    read -p "是否要停止 Ollama 服務？(y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -x "ollama" 2>/dev/null
        sleep 2
        if pgrep -x "ollama" > /dev/null; then
            print_warning "Ollama 仍在運行，嘗試強制停止..."
            pkill -9 -x "ollama" 2>/dev/null
        fi
        print_success "Ollama 已停止"
    else
        print_info "保留 Ollama 服務運行"
    fi
else
    print_info "Ollama 未運行"
fi

echo ""

# ===== Step 4: 清理臨時文件 =====
echo "Step 4: 清理臨時文件"
echo "------------------"

# 清理日誌和 PID 文件
for file in /tmp/frontend.log /tmp/frontend.pid /tmp/ollama.log; do
    if [ -f "$file" ]; then
        rm -f "$file"
        print_success "已清理 $(basename $file)"
    fi
done

echo ""

# ===== Step 5: 驗證停止狀態 =====
echo "Step 5: 驗證停止狀態"
echo "------------------"

# 檢查 Port 佔用
check_port_free() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $port 仍被佔用 ($service)"
        lsof -Pi :$port -sTCP:LISTEN | grep -v "^COMMAND" | head -3
        return 1
    else
        print_success "Port $port 已釋放 ($service)"
        return 0
    fi
}

check_port_free 5050 "Backend"
check_port_free 8000 "Presenton"
check_port_free 8080 "Frontend"

echo ""

# ===== 完成 =====
echo "✅ 系統已停止"
echo "============"
echo ""
echo "💡 提示："
echo "  - Ollama 服務可能仍在運行（用於其他專案）"
echo "  - 輸出檔案保留在 ./output 目錄"
echo "  - 若需完全清理，請執行: docker system prune"
echo ""
echo "🚀 重新啟動系統："
echo "  ./scripts/start_system.sh"
echo ""
