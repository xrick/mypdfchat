# FIXED: Startup Hang - UnboundLocalError in main.py

## 問題描述 (Problem Description)

**症狀 (Symptom)**:
- 用戶報告系統在「健康檢查」階段掛起 (System hangs during health check phase)
- 實際上並非掛起，而是在啟動時立即崩潰 (Not actually hanging, but crashing immediately on startup)

**錯誤訊息 (Error Message)**:
```
UnboundLocalError: cannot access local variable 'settings' where it is not associated with a value
```

**位置 (Location)**:
- [main.py:45](main.py#L45) in `lifespan()` function

## 根本原因 (Root Cause)

### 問題分析 (Problem Analysis)

Python 的作用域規則 (Python scoping rules):
1. 檔案頂部全域匯入：`from app.core.config import settings` (line 23)
2. Milvus 健康檢查程式碼內部重複匯入：`from app.core.config import settings` (line 73)
3. Python 偵測到函式內有 `settings` 的本地賦值，將整個 `settings` 視為本地變數
4. 在 line 45 嘗試存取 `settings` 時，該變數尚未被賦值（因為賦值在 line 73）
5. 導致 `UnboundLocalError`

### 錯誤程式碼 (Problematic Code)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Line 45: 嘗試存取 settings (但 Python 認為它是未初始化的本地變數)
    logger.info(f"=� Starting {settings.APP_NAME} v{settings.APP_VERSION}")  # ❌ FAIL

    # ... 其他程式碼 ...

    # Line 73: 在 try 區塊內部重複匯入 settings
    try:
        from app.Providers.vector_store_provider.milvus_client import MilvusClient
        from app.core.config import settings  # ❌ 這會建立本地變數 shadow
```

## 解決方案 (Solution)

### 修復內容 (Fix Applied)

**檔案**: [main.py:70-74](main.py#L70-L74)

**修改前 (Before)**:
```python
try:
    from app.Providers.vector_store_provider.milvus_client import MilvusClient
    from app.core.config import settings  # ❌ 重複匯入

    logger.info(f"🔍 Checking Milvus service at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}...")
```

**修改後 (After)**:
```python
try:
    from app.Providers.vector_store_provider.milvus_client import MilvusClient
    # ✅ 移除重複的 settings 匯入，使用全域匯入的 settings

    logger.info(f"🔍 Checking Milvus service at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}...")
```

### 測試結果 (Test Results)

**語法驗證 (Syntax Validation)**:
```bash
✅ Syntax validation passed
```

**啟動測試 (Startup Test)**:
```
INFO:     Started server process [60194]
INFO:     Waiting for application startup.
⚠️  Milvus health check failed: No module named 'pkg_resources'  # 預期的警告（環境問題）
INFO:     Application startup complete.  # ✅ 成功啟動
```

**結果 (Result)**:
- ✅ 應用程式成功啟動
- ✅ 健康檢查執行（Milvus 警告是環境依賴問題，非實作問題）
- ✅ Web UI 可存取 (HTTP 200 OK)

## 預防策略 (Prevention Strategy)

### 最佳實踐 (Best Practices)

1. **避免在函式內部重複匯入全域變數 (Avoid redundant imports inside functions)**:
   ```python
   # ✅ GOOD: Use global import
   from app.core.config import settings  # Top of file

   def some_function():
       # Use settings directly, no re-import needed
       logger.info(settings.APP_NAME)
   ```

2. **如果必須在函式內部匯入，使用不同的名稱 (Use different names if re-import is necessary)**:
   ```python
   def some_function():
       from app.core.config import settings as local_settings  # Different name
       logger.info(local_settings.APP_NAME)
   ```

3. **或者在函式頂部完成所有匯入 (Or complete all imports at function top)**:
   ```python
   def some_function():
       # Import at function top, before any usage
       from app.core.config import settings
       from app.Providers.vector_store_provider.milvus_client import MilvusClient

       logger.info(settings.APP_NAME)  # Now safe to use
   ```

### 程式碼審查檢查清單 (Code Review Checklist)

- [ ] 檢查是否有變數在函式內部和外部同時匯入
- [ ] 確保全域匯入的變數不在函式內部重新匯入
- [ ] 如果需要在函式內部匯入，使用不同的名稱
- [ ] 運行語法驗證：`python -m py_compile main.py`
- [ ] 測試應用程式啟動：觀察是否有 `UnboundLocalError`

## 影響範圍 (Impact Scope)

**修改檔案 (Files Modified)**:
- `main.py` (1 file, 1 line removed)

**影響功能 (Affected Functionality)**:
- ✅ 應用程式啟動流程 (Application startup flow)
- ✅ 健康檢查功能 (Health check functionality)
- ✅ Milvus 服務偵測 (Milvus service detection)

**向後相容性 (Backward Compatibility)**:
- ✅ 完全相容 (Fully compatible)
- ✅ 無 API 變更 (No API changes)
- ✅ 無配置變更 (No configuration changes)

## 相關文件 (Related Documentation)

- 原始實作: [claudedocs/MILVUS_HEALTH_CHECK_IMPLEMENTATION.md](claudedocs/MILVUS_HEALTH_CHECK_IMPLEMENTATION.md)
- Python 作用域規則: [PEP 227 - Statically Nested Scopes](https://peps.python.org/pep-0227/)

## 結論 (Conclusion)

這是一個典型的 Python 作用域陷阱 (Python scoping gotcha)。問題不在於 Milvus 健康檢查的邏輯，而在於重複的 import 語句造成了變數 shadow。移除冗餘的 import 語句後，應用程式恢復正常啟動。

**重要提醒**: 始終避免在函式內部重複匯入已在全域匯入的變數，以防止此類作用域衝突。
