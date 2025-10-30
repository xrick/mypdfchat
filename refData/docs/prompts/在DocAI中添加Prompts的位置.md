✅ 完整回答：在 DocAI 中添加 Prompts 的位置
📝 主要 Prompt 檔案（2 個）
檔案	用途	主要 Prompts
app/Services/prompt_service.py	控制 AI 如何回答問題	SYSTEM_PROMPT_TEMPLATE (中文)<br>SYSTEM_PROMPT_TEMPLATE_EN (英文)
app/Services/query_enhancement_service.py	控制問題如何擴展	QUERY_EXPANSION_PROMPT<br>PROMPT_2_QUESTION_EXPANSION
🎯 快速修改指南
1. 修改系統回答風格
檔案: app/Services/prompt_service.py (Line 26-42)
# 當前：嚴謹風格
SYSTEM_PROMPT_TEMPLATE = """你是一位嚴謹的文檔問答助手。"""

# 改為：友善風格
SYSTEM_PROMPT_TEMPLATE = """你好！我是你的文檔助手小 AI。"""

# 改為：專家風格
SYSTEM_PROMPT_TEMPLATE = """你是一位資深文檔分析專家。"""
2. 修改問題擴展策略
檔案: app/Services/query_enhancement_service.py (Line 38-59)
# 當前：3-5 個子問題
QUERY_EXPANSION_PROMPT = """請將用戶的查詢分解為3-5個相關的子問題"""

# 改為：更激進 5-7 個
QUERY_EXPANSION_PROMPT = """請將用戶的查詢分解為5-7個相關的子問題"""

# 改為：保守 2-3 個
QUERY_EXPANSION_PROMPT = """請將用戶的查詢精簡分解為2-3個核心子問題"""
🔧 修改後如何生效？
方法 1: 自動重載（開發模式，當前已啟用）
直接編輯 prompt 檔案
儲存
Uvicorn 會自動偵測並重新載入（約 1-2 秒）
方法 2: 手動重啟
pkill -f "python main.py"
docaienv/bin/python main.py
📚 完整文檔已創建
我已為你創建了完整的 Prompt 自訂指南： claudedocs/prompt_customization_guide.md 內容包括：
✅ 所有 prompt 位置的完整列表
✅ 實際的修改範例（友善、專家、醫療等風格）
✅ Query expansion 調整方法
✅ 測試 prompt 的腳本
✅ Prompt engineering 最佳實踐
✅ Troubleshooting 指南
🚀 現在你可以：
查看當前 prompts:
cat app/Services/prompt_service.py | grep -A 20 "SYSTEM_PROMPT_TEMPLATE ="
編輯 prompts:
nano app/Services/prompt_service.py
# 或
code app/Services/prompt_service.py
測試修改:
儲存檔案後，server 會自動重載
使用 frontend (http://localhost:8000) 測試對話效果
