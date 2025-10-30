# DocAI 系統啟動/停止腳本使用指南

**生成日期**: 2025-10-30
**版本**: 1.0.0
**狀態**: ✅ 已完成並可用

---

## 概述

為 DocAI RAG 應用程式創建了兩個專業的 shell 腳本，用於系統的啟動和停止管理。這些腳本基於 TeacherAssist 專案的參考實現，並針對 DocAI 的架構進行了優化。

---

## 腳本文件

### 1. start_system.sh
**路徑**: `/home/mapleleaf/LCJRepos/gitprjs/DocAI/start_system.sh`
**大小**: 8.6 KB
**權限**: 可執行 (rwxrwxr-x)

### 2. stop_system.sh
**路徑**: `/home/mapleleaf/LCJRepos/gitprjs/DocAI/stop_system.sh`
**大小**: 8.8 KB
**權限**: 可執行 (rwxrwxr-x)

---

## start_system.sh 功能特性

### 🔷 前置條件檢查
- ✅ **Python 3 安裝檢測**
  - 檢查 Python 3 是否已安裝
  - 顯示當前 Python 版本
  - 如果未安裝，提供安裝指引

- ✅ **uv 套件管理工具檢測**
  - 驗證 uv 工具是否可用
  - 提供安裝命令（如果缺失）

- ✅ **虛擬環境驗證**
  - 檢查 `docaienv/` 目錄是否存在
  - 確保虛擬環境已正確配置

- ✅ **MongoDB 服務檢查**
  - 驗證 MongoDB 服務狀態
  - 自動嘗試啟動服務（如果未運行）
  - 測試 MongoDB 連接（使用 mongosh ping 命令）

- ✅ **Redis 服務檢查（可選）**
  - 檢測 Redis 服務狀態
  - 如果未配置則跳過（可選依賴）
  - 警告但不阻止啟動（如果已配置但未運行）

### 🔷 端口衝突檢測與解決
- **智能衝突處理**
  - 檢測端口 8000 是否被佔用
  - 顯示佔用進程的 PID 和進程名稱
  - 識別是否為舊的 DocAI 實例
  - 提供互動式終止選項
  - 支持自動清理舊實例

### 🔷 環境設置
- **配置文件驗證**
  - 檢查 `.env` 文件是否存在
  - 提供配置指引（如果缺失）

- **目錄結構創建**
  - 自動創建 `uploadfiles/pdf/` 目錄
  - 創建 `data/` 目錄
  - 確保所需的文件系統結構完整

### 🔷 依賴項管理
- **自動依賴檢查**
  - 驗證關鍵 Python 包：
    - fastapi
    - uvicorn
    - pymongo
    - motor
    - PyPDF2
    - langchain
  - 發現缺失依賴時自動安裝
  - 使用 `uv pip install -r requirements.txt`

### 🔷 服務器啟動與健康檢查
- **後台啟動**
  - 使用 nohup 在後台運行服務器
  - 日誌重定向到 `logs/server.log`
  - 保存進程 PID 到 `/tmp/docai_server.pid`

- **健康檢查與重試邏輯**
  - 最多等待 30 秒
  - 每秒檢查一次服務器響應
  - 驗證進程存活狀態
  - 失敗時提供日誌查看指引

### 🔷 狀態報告
- **啟動成功信息**
  - 顯示訪問 URL：
    - Web UI: http://localhost:8000
    - API 文檔: http://localhost:8000/docs
    - OpenAPI: http://localhost:8000/openapi.json
  - 提供管理命令指引
  - 顯示服務器 PID

---

## stop_system.sh 功能特性

### 🔷 優雅關閉序列
- **方法 1: PID 文件關閉**
  - 讀取 `/tmp/docai_server.pid`
  - 驗證進程是否存在
  - 發送 SIGTERM 信號（優雅關閉）
  - 等待最多 10 秒進程退出
  - 如果未響應，使用 SIGKILL 強制終止

- **方法 2: 端口檢測關閉（備用）**
  - 使用 lsof 檢測端口 8000 上的進程
  - 終止所有佔用端口 8000 的進程
  - 確保端口釋放

### 🔷 後台進程清理
- **進程搜索與清理**
  - 搜索 `main.py` 和 `docaienv` 相關進程
  - 顯示發現的所有相關進程
  - 提供互動式確認終止選項
  - 逐個清理殘留進程

### 🔷 數據庫服務管理（可選）
- **MongoDB 停止選項**
  - 互動式詢問是否停止 MongoDB
  - 使用 systemctl 停止服務
  - 處理權限錯誤

- **Redis 停止選項**
  - 互動式詢問是否停止 Redis
  - 支持 redis-server 和 redis 服務名稱
  - 錯誤處理與狀態報告

### 🔷 端口驗證
- **釋放確認**
  - 驗證端口 8000 已完全釋放
  - 如果仍被佔用，顯示佔用進程信息
  - 提供手動檢查命令

### 🔷 臨時文件清理
- **Python 快取清理**
  - 刪除所有 `__pycache__` 目錄
  - 清理 `.pyc` 文件

- **日誌清理（可選）**
  - 互動式詢問是否清理日誌
  - 刪除 `logs/*.log` 文件

### 🔷 最終狀態報告
- **服務狀態摘要**
  - MongoDB 運行狀態
  - Redis 運行狀態
  - DocAI 服務器狀態
  - 彩色狀態指示器
  - 重啟命令提示

---

## 使用方法

### 啟動系統
```bash
# 方法 1: 直接執行
./start_system.sh

# 方法 2: 使用 bash
bash start_system.sh
```

### 停止系統
```bash
# 方法 1: 直接執行
./stop_system.sh

# 方法 2: 使用 bash
bash stop_system.sh
```

### 查看服務器日誌
```bash
# 實時查看
tail -f logs/server.log

# 查看最近 100 行
tail -n 100 logs/server.log
```

### 檢查服務器狀態
```bash
# 檢查進程
ps aux | grep main.py

# 檢查端口
lsof -i :8000

# 讀取 PID
cat /tmp/docai_server.pid
```

---

## 彩色輸出說明

腳本使用彩色輸出來提高可讀性：

| 顏色 | 符號 | 含義 |
|------|------|------|
| 🟢 綠色 | ✅ | 成功、完成、正常運行 |
| 🔴 紅色 | ❌ | 錯誤、失敗、需要處理 |
| 🟡 黃色 | ⚠️  | 警告、需要注意 |
| 🔵 藍色 | ℹ️  | 信息、說明 |
| 🔷 青色 | 🔷 | 步驟、操作進度 |
| 🟣 紫色 | - | 標題、分隔符 |

---

## 腳本設計特點

### 來自 TeacherAssist 的參考模式
1. **完善的前置檢查**
   - 系統依賴驗證
   - 服務狀態檢測
   - 端口衝突處理

2. **彩色輸出系統**
   - 清晰的視覺反饋
   - 統一的符號語言
   - 專業的用戶體驗

3. **健壯的錯誤處理**
   - 優雅降級策略
   - 詳細的錯誤信息
   - 實用的解決方案指引

4. **互動式操作**
   - 用戶確認提示
   - 智能默認選擇
   - 安全操作保護

### DocAI 特定優化
1. **簡化的架構適配**
   - 無 Docker 依賴（不同於 TeacherAssist）
   - 單一 Python 進程管理
   - 直接的虛擬環境處理

2. **精簡的服務管理**
   - 只管理必需服務（MongoDB, Redis）
   - 無多容器編排（不同於 TeacherAssist）
   - 快速啟動和停止

3. **針對性的依賴檢查**
   - 只檢查 DocAI 的關鍵包
   - 自動安裝缺失依賴
   - uv 包管理器集成

---

## 技術對比：DocAI vs TeacherAssist

| 特性 | TeacherAssist | DocAI |
|------|---------------|-------|
| 容器化 | ✅ Docker Compose | ❌ 原生 Python |
| LLM 服務 | Ollama (內建) | Ollama (外部) |
| 架構檢測 | AMD64/ARM64 | 不需要 |
| 前端服務 | 獨立容器 | 靜態文件服務 |
| 後端服務 | 獨立容器 | 單一 Python 進程 |
| 端口數量 | 多個 (3000, 8000, etc.) | 單一 (8000) |
| 健康檢查 | Docker healthcheck | HTTP curl |
| 進程管理 | docker compose | PID 文件 + nohup |

---

## 故障排除

### 問題 1: MongoDB 無法啟動
```bash
# 檢查 MongoDB 狀態
sudo systemctl status mongod

# 查看 MongoDB 日誌
sudo journalctl -u mongod -n 50

# 手動啟動
sudo systemctl start mongod
```

### 問題 2: 端口 8000 被佔用
```bash
# 查看佔用進程
lsof -i :8000

# 手動終止進程
kill <PID>

# 強制終止
kill -9 <PID>
```

### 問題 3: 虛擬環境缺失
```bash
# 重新創建虛擬環境
uv venv docaienv

# 安裝依賴
source docaienv/bin/activate
uv pip install -r requirements.txt
```

### 問題 4: 依賴安裝失敗
```bash
# 手動安裝關鍵依賴
source docaienv/bin/activate
uv pip install fastapi uvicorn pymongo motor PyPDF2 langchain

# 或完整安裝
uv pip install -r requirements.txt
```

### 問題 5: 服務器啟動超時
```bash
# 查看服務器日誌
tail -f logs/server.log

# 檢查 Python 錯誤
python main.py

# 驗證 .env 配置
cat .env
```

---

## 安全考慮

### PID 文件位置
- 使用 `/tmp/docai_server.pid` 存儲進程 ID
- 系統重啟後自動清理
- 避免權限問題

### 進程終止策略
1. 優先使用 SIGTERM (優雅關閉)
2. 等待 10 秒響應時間
3. 必要時使用 SIGKILL (強制終止)

### 互動式確認
- 終止外部進程前需要確認
- 停止數據庫服務前需要確認
- 清理日誌前需要確認

---

## 未來改進建議

### 短期改進
1. ⏳ **日誌輪轉**
   - 實現自動日誌輪轉
   - 限制日誌文件大小
   - 保留最近 N 天的日誌

2. ⏳ **systemd 服務**
   - 創建 systemd 服務單元
   - 支持 `systemctl start/stop docai`
   - 自動重啟機制

3. ⏳ **配置驗證**
   - 檢查 .env 文件完整性
   - 驗證必需的環境變數
   - 提供配置模板

### 長期改進
1. 🎯 **性能監控**
   - 集成健康端點監控
   - 資源使用統計
   - 自動告警機制

2. 🎯 **備份管理**
   - 數據庫自動備份
   - 配置文件備份
   - 恢復機制

3. 🎯 **多環境支持**
   - 開發/測試/生產環境切換
   - 環境特定配置
   - 端口自動分配

---

## 總結

✅ **成功創建**
- 兩個專業的系統管理腳本
- 完整的錯誤處理和用戶反饋
- 基於成熟的參考實現

✅ **功能完整**
- 前置條件檢查
- 智能衝突解決
- 優雅的啟動和關閉
- 詳細的狀態報告

✅ **用戶友好**
- 彩色輸出
- 清晰的進度指示
- 互動式確認
- 詳細的錯誤信息

✅ **即用性**
- 語法檢查通過
- 可執行權限已設置
- 與現有架構兼容
- 準備投入使用

---

**文檔版本**: 1.0.0
**最後更新**: 2025-10-30
**維護者**: Claude Code Agent
**狀態**: ✅ 生產就緒
