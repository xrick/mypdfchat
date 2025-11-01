# start_system.sh
#!/bin/bash

# ============================================
# DocAI RAG Application - System Startup Script
# ============================================
# Author: Auto-generated for DocAI Project
# Description: Comprehensive startup script with prerequisite checks,
#              service validation, and health monitoring
# ============================================

set -e

# ============================================
# Color Definitions
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# ============================================
# Utility Functions
# ============================================
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_step() {
    echo -e "${CYAN}🔷 $1${NC}"
}

print_header() {
    echo -e "\n${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}  $1${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# ============================================
# Environment Detection
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/docaienv"
PID_FILE="/tmp/docai_server.pid"
PORT=8000

# ============================================
# Prerequisite Checks
# ============================================
print_header "前置條件檢查"

# Check Python 3
print_step "檢查 Python 3 安裝..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 未安裝"
    print_info "請執行: sudo apt install python3 python3-pip"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
print_success "Python $PYTHON_VERSION 已安裝"

# Check uv package manager
print_step "檢查 uv 套件管理工具..."
if ! command -v uv &> /dev/null; then
    print_error "uv 未安裝"
    print_info "請執行: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
print_success "uv 已安裝"

# Check virtual environment
print_step "檢查 Python 虛擬環境..."
if [ ! -d "$VENV_DIR" ]; then
    print_error "虛擬環境目錄不存在: $VENV_DIR"
    print_info "請執行: uv venv docaienv"
    exit 1
fi
print_success "虛擬環境已就緒"

# Check MongoDB
print_step "檢查 MongoDB 服務..."

# Detect OS and check MongoDB accordingly
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use brew services
    if brew services list | grep -q "mongodb-community.*started"; then
        print_success "MongoDB 服務運行中 (Homebrew)"
    else
        print_warning "MongoDB 服務未運行"
        print_info "嘗試啟動 MongoDB..."
        if brew services start mongodb-community; then
            print_success "MongoDB 服務已啟動"
            sleep 3  # Wait for MongoDB to initialize
        else
            print_error "無法啟動 MongoDB 服務"
            print_info "請手動檢查: brew services list"
            exit 1
        fi
    fi
elif command -v systemctl &> /dev/null; then
    # Linux - use systemctl
    if ! systemctl is-active --quiet mongod; then
        print_warning "MongoDB 服務未運行"
        print_info "嘗試啟動 MongoDB..."
        if sudo systemctl start mongod; then
            print_success "MongoDB 服務已啟動"
        else
            print_error "無法啟動 MongoDB 服務"
            print_info "請手動檢查: sudo systemctl status mongod"
            exit 1
        fi
    else
        print_success "MongoDB 服務運行中"
    fi
else
    print_warning "無法檢測服務管理器，將嘗試直接連接 MongoDB"
fi

# Test MongoDB connection
print_step "測試 MongoDB 連接..."

# Cross-platform timeout function
test_mongodb_connection() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - use perl for timeout (timeout command not available by default)
        perl -e 'alarm shift; exec @ARGV' 5 mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1
    else
        # Linux - use timeout command
        timeout 5 mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1
    fi
}

if test_mongodb_connection; then
    print_success "MongoDB 連接正常"
else
    print_error "無法連接到 MongoDB"
    print_info "請檢查 MongoDB 服務狀態和配置"
    exit 1
fi

# Check Redis (if configured)
print_step "檢查 Redis 服務..."

# Check if Redis is configured in .env
if ! grep -q "redis://" "$PROJECT_ROOT/.env" 2>/dev/null; then
    print_info "Redis 未配置 (可選)"
else
    # Detect OS and check Redis accordingly
    REDIS_RUNNING=false

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - use brew services
        if brew services list | grep -q "redis.*started"; then
            REDIS_RUNNING=true
        fi
    elif command -v systemctl &> /dev/null; then
        # Linux - use systemctl
        if systemctl is-active --quiet redis-server || systemctl is-active --quiet redis; then
            REDIS_RUNNING=true
        fi
    fi

    if [ "$REDIS_RUNNING" = true ]; then
        print_success "Redis 服務運行中"
    else
        print_warning "Redis 已配置但服務未運行"
        print_info "某些快取功能可能無法使用"
    fi
fi

# Check Milvus vector database (if configured)
print_step "檢查 Milvus 向量資料庫..."

# Get Milvus configuration from .env
MILVUS_HOST=$(grep "^MILVUS_HOST=" "$PROJECT_ROOT/.env" 2>/dev/null | cut -d '=' -f2 | tr -d '"' || echo "localhost")
MILVUS_PORT=$(grep "^MILVUS_PORT=" "$PROJECT_ROOT/.env" 2>/dev/null | cut -d '=' -f2 | tr -d '"' || echo "19530")

# Test Milvus connection using nc (netcat) - cross-platform tool
if command -v nc &> /dev/null; then
    if nc -z -w 2 "$MILVUS_HOST" "$MILVUS_PORT" 2>/dev/null; then
        print_success "Milvus 服務運行中 ($MILVUS_HOST:$MILVUS_PORT)"
    else
        print_warning "Milvus 服務未運行"
        print_info "向量搜尋功能可能無法使用"
        print_info "請檢查 Milvus 服務: docker ps | grep milvus"
        print_info "或執行: docker-compose up -d milvus-standalone"
    fi
else
    print_info "無法檢查 Milvus 連接 (nc 命令不可用)"
    print_info "Python 應用層會進行詳細的 Milvus 健康檢查"
fi

# ============================================
# Port Conflict Detection
# ============================================
print_header "端口衝突檢查"

check_port_conflict() {
    local port=$1
    local service_name=$2

    print_step "檢查端口 $port ($service_name)..."

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pid=$(lsof -Pi :$port -sTCP:LISTEN -t | head -1)
        local process=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")

        print_warning "端口 $port 已被佔用 (PID: $pid, Process: $process)"

        # Check if it's our own server
        if [ -f "$PID_FILE" ] && [ "$(cat $PID_FILE)" == "$pid" ]; then
            print_info "這是 DocAI 服務本身，將先停止舊實例..."
            # Kill all processes using this port (parent and children)
            local all_pids=$(lsof -Pi :$port -sTCP:LISTEN -t)
            for p in $all_pids; do
                kill $p 2>/dev/null
            done
            sleep 2

            # Verify processes actually died
            local remaining_pids=$(lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null)
            if [ -n "$remaining_pids" ]; then
                print_warning "部分進程未響應 SIGTERM，使用 SIGKILL 強制終止..."
                for p in $remaining_pids; do
                    kill -9 $p 2>/dev/null
                done
                sleep 1
            fi
        else
            echo -n "是否終止該進程? (y/n): "
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                # Try graceful shutdown first for all processes on this port
                print_info "正在等待進程終止..."
                local all_pids=$(lsof -Pi :$port -sTCP:LISTEN -t)
                for p in $all_pids; do
                    kill $p 2>/dev/null
                done
                sleep 3

                # Verify processes actually died
                local remaining_pids=$(lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null)
                if [ -n "$remaining_pids" ]; then
                    print_warning "部分進程未響應 SIGTERM，使用 SIGKILL 強制終止..."
                    for p in $remaining_pids; do
                        kill -9 $p 2>/dev/null
                    done
                    sleep 1

                    # Final verification
                    remaining_pids=$(lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null)
                    if [ -n "$remaining_pids" ]; then
                        print_error "無法終止進程 (可能需要 sudo 權限)"
                        return 1
                    fi
                fi
                print_success "進程已終止"
            else
                print_error "端口衝突未解決，無法繼續"
                return 1
            fi
        fi

        # Final port availability check
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            print_error "端口 $port 仍被佔用，無法繼續"
            return 1
        fi
    else
        print_success "端口 $port 可用"
    fi
    return 0
}

if ! check_port_conflict $PORT "DocAI FastAPI Server"; then
    exit 1
fi

# ============================================
# Environment Setup
# ============================================
print_header "環境設置"

# Check .env file
print_step "檢查 .env 配置文件..."
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    print_error ".env 文件不存在"
    print_info "請從 .env.example 複製並配置"
    exit 1
fi
print_success ".env 文件存在"

# Create required directories
print_step "創建必需的目錄..."
mkdir -p "$PROJECT_ROOT/uploadfiles/pdf"
mkdir -p "$PROJECT_ROOT/data"
print_success "目錄結構已就緒"

# ============================================
# Dependency Check
# ============================================
print_header "依賴項檢查"

print_step "檢查 Python 依賴..."
cd "$PROJECT_ROOT"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Check critical dependencies
CRITICAL_DEPS=("fastapi" "uvicorn" "pymongo" "motor" "PyPDF2" "langchain")
MISSING_DEPS=()

for dep in "${CRITICAL_DEPS[@]}"; do
    if ! python3 -c "import ${dep//-/_}" 2>/dev/null; then
        MISSING_DEPS+=("$dep")
    fi
done

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    print_warning "缺少 ${#MISSING_DEPS[@]} 個關鍵依賴: ${MISSING_DEPS[*]}"
    print_info "正在安裝依賴..."

    if uv pip install -r requirements.txt; then
        print_success "依賴安裝完成"
    else
        print_error "依賴安裝失敗"
        exit 1
    fi
else
    print_success "所有關鍵依賴已安裝"
fi

# ============================================
# Server Startup
# ============================================
print_header "啟動 DocAI 服務"

print_step "啟動 FastAPI 服務器..."

# Start server in background
nohup docaienv/bin/python main.py > logs/server.log 2>&1 &
SERVER_PID=$!

# Save PID
echo $SERVER_PID > "$PID_FILE"
print_info "服務器 PID: $SERVER_PID"

# ============================================
# Health Check
# ============================================
print_header "健康檢查"

print_step "等待服務器啟動..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -f http://localhost:$PORT/ > /dev/null 2>&1; then
        print_success "服務器健康檢查通過"
        break
    fi

    # Check if process is still alive
    if ! ps -p $SERVER_PID > /dev/null 2>&1; then
        print_error "服務器進程意外終止"
        echo ""
        print_info "最近的錯誤日誌:"
        echo "----------------------------------------"
        tail -20 logs/server.log | grep -i "error\|exception\|failed\|errno" || tail -10 logs/server.log
        echo "----------------------------------------"
        print_info "完整日誌: tail -f logs/server.log"
        exit 1
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 1
done

echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "服務器啟動超時"
    print_info "查看日誌: tail -f logs/server.log"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# ============================================
# Final Status
# ============================================
print_header "啟動完成"

print_success "DocAI 系統已成功啟動"
echo ""
print_info "訪問地址:"
echo -e "  ${CYAN}• Web UI:${NC} http://localhost:$PORT"
echo -e "  ${CYAN}• API 文檔:${NC} http://localhost:$PORT/docs"
echo -e "  ${CYAN}• OpenAPI:${NC} http://localhost:$PORT/openapi.json"
echo ""
print_info "管理命令:"
echo -e "  ${CYAN}• 停止服務:${NC} ./stop_system.sh"
echo -e "  ${CYAN}• 查看日誌:${NC} tail -f logs/server.log"
echo -e "  ${CYAN}• 服務器 PID:${NC} $SERVER_PID"
echo ""
print_success "系統運行中，祝使用愉快！"
echo ""
