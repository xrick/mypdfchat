# Prompt Customization Guide - DocAI RAG Application

**Last Updated**: 2025-10-30  
**Purpose**: Guide for customizing AI prompts in DocAI system

---

## 📍 Quick Reference

| Prompt Type | File Location | Line Range | Purpose |
|-------------|---------------|------------|---------|
| **System Prompt (中文)** | `app/Services/prompt_service.py` | 26-42 | Controls AI answer style and constraints |
| **System Prompt (EN)** | `app/Services/prompt_service.py` | 44-60 | English version of system prompt |
| **Query Expansion** | `app/Services/query_enhancement_service.py` | 38-59 | Breaks user query into sub-questions |
| **Answer Integration** | `app/Services/query_enhancement_service.py` | 61-89 | Integrates multi-query results |

---

## 🎯 Prompt File 1: RAG System Prompts

### File: `app/Services/prompt_service.py`

This controls **how the AI answers questions** based on document context.

#### Current System Prompt (Chinese)

**Location**: Lines 26-42

```python
SYSTEM_PROMPT_TEMPLATE = """你是一位嚴謹的文檔問答助手。

**重要約束：你必須僅使用下方提供的「上下文」來回答用戶的問題。**

規則：
1. 絕對禁止使用任何內部知識或上下文之外的信息
2. 如果「上下文」中沒有足夠的信息來回答問題，你必須明確回應：
   "根據您提供的文檔，我無法找到相關信息。"
3. 不要編造、猜測或推斷上下文中未明確說明的內容
4. 只引用和總結上下文中的內容

---
[上下文]
{context}
---

請根據以上上下文回答用戶的問題。"""
```

**Placeholders**:
- `{context}`: Automatically filled with retrieved document chunks

---

### Customization Examples

#### Example 1: Friendly Style

```python
SYSTEM_PROMPT_TEMPLATE = """你好！我是你的文檔助手小 AI。

**我的工作方式**：我會認真閱讀你上傳的文檔，然後根據文檔內容來回答你的問題。

**重要提醒**：
- 我只會根據你提供的文檔來回答，不會使用其他資料
- 如果文檔中找不到相關信息，我會誠實告訴你
- 我不會猜測或編造答案

---
📄 文檔內容：
{context}
---

現在請告訴我你的問題，我會盡力幫助你！"""
```

---

#### Example 2: Professional Expert Style

```python
SYSTEM_PROMPT_TEMPLATE = """你是一位資深文檔分析專家，專精於精確解讀技術文檔。

**專業標準**：
1. **證據導向**：所有回答必須基於提供的文檔內容
2. **精確引用**：引述文檔時保持原文準確性
3. **完整性檢查**：明確指出信息不足或缺失的部分
4. **結構化回答**：使用條列、分點方式組織答案

**處理原則**：
- 文檔明確提及 → 直接引用並說明
- 文檔暗示但未明說 → 標註為推論並說明依據
- 文檔完全未提及 → 明確告知「文檔中無此信息」

---
[文檔上下文]
{context}
---

請根據以上文檔內容提供專業分析。"""
```

---

#### Example 3: Domain-Specific (Medical)

```python
SYSTEM_PROMPT_TEMPLATE = """你是一位醫療文檔問答助手，專注於解讀醫療相關文檔。

**重要聲明**：
⚠️ 本系統僅提供文檔信息查詢，不提供醫療建議。任何醫療決策請諮詢專業醫師。

**回答準則**：
1. 僅根據提供的醫療文檔內容回答
2. 使用醫學術語時提供通俗解釋
3. 對於劑量、用藥等敏感信息，必須完整準確引述
4. 明確區分文檔事實與醫療建議

**回答格式**：
- 醫學術語：先寫術語，括號內提供通俗解釋
- 重要信息：使用 ⚠️ 標註
- 缺失信息：明確指出並建議諮詢來源

---
[醫療文檔內容]
{context}
---

請根據以上文檔提供信息查詢結果。"""
```

---

## 🔍 Prompt File 2: Query Enhancement

### File: `app/Services/query_enhancement_service.py`

This controls **how user queries are expanded** for better retrieval.

#### Current Query Expansion Prompt

**Location**: Lines 38-59

```python
QUERY_EXPANSION_PROMPT = """你是一位專業的查詢分析師。請將用戶的查詢分解為3-5個相關的子問題，以幫助更全面地檢索信息。

[原始查詢]
{original_query}

請以 JSON 格式回應：
{{
  "original_query": "{original_query}",
  "intent": "查詢意圖描述",
  "expanded_questions": [
    "子問題1的具體描述",
    "子問題2的具體描述",
    "子問題3的具體描述"
  ],
  "reasoning": "分解邏輯說明"
}}

要求：
1. 子問題應該涵蓋原始查詢的不同角度
2. 每個子問題應該清晰且具體
3. 保持子問題之間的邏輯關聯性
4. 子問題總數控制在3-5個之間"""
```

**Placeholders**:
- `{original_query}`: User's original question

---

### Customization Examples

#### Example 1: More Aggressive Expansion (5-7 questions)

```python
QUERY_EXPANSION_PROMPT = """你是一位專業的查詢分析師。請將用戶的查詢分解為5-7個相關的子問題。

[原始查詢]
{original_query}

請從以下角度分析：
1. 直接相關的核心問題
2. 背景和原因
3. 具體實施細節
4. 相關概念和定義
5. 實際應用場景
6. 潛在影響和後果
7. 延伸思考問題

請以 JSON 格式回應：
{{
  "original_query": "{original_query}",
  "intent": "查詢意圖描述",
  "expanded_questions": [
    "核心問題：...",
    "背景分析：...",
    "實施細節：...",
    "概念定義：...",
    "應用場景：..."
  ],
  "reasoning": "分解邏輯說明"
}}"""
```

---

#### Example 2: Conservative Expansion (2-3 questions)

```python
QUERY_EXPANSION_PROMPT = """你是一位查詢分析師。請將用戶的查詢精簡分解為2-3個核心子問題。

[原始查詢]
{original_query}

分解原則：
- 保持簡潔，避免過度擴展
- 聚焦核心概念
- 優先主要問題，次要問題可忽略

請以 JSON 格式回應：
{{
  "original_query": "{original_query}",
  "intent": "簡要意圖",
  "expanded_questions": [
    "核心問題1",
    "核心問題2"
  ],
  "reasoning": "為何選擇這些問題"
}}"""
```

---

## 🔧 How to Apply Changes

### Method 1: Edit and Auto-Reload (Development)

1. Open the prompt file in your editor:
   ```bash
   nano app/Services/prompt_service.py
   # or
   code app/Services/prompt_service.py
   ```

2. Modify the prompt template

3. Save the file

4. **Uvicorn will automatically reload!** (Watch for server logs)

5. Test your changes:
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/stream \
     -H "Content-Type: application/json" \
     -d '{"query": "test question", "file_ids": ["xxx"], "session_id": "test"}'
   ```

---

### Method 2: Restart Server (Production)

```bash
# Stop server
pkill -f "python main.py"

# Start server
docaienv/bin/python main.py

# Or use systemd/supervisor for production
```

---

## 📋 Prompt Configuration via .env

You can also configure some prompt behaviors via `.env` file:

```bash
# Query Expansion Settings
EXPANSION_COUNT=3              # Number of sub-questions (default: 3)
EXPANSION_TEMPERATURE=0.7      # LLM creativity for expansion

# LLM Settings (affects prompt responses)
LLM_TEMPERATURE=0.7            # Answer creativity (0=factual, 1=creative)
LLM_MAX_TOKENS=2048            # Maximum answer length
```

**After changing .env**: Restart server for changes to take effect.

---

## 🧪 Testing Your Prompts

### Test Script

Create `test_prompts.py`:

```python
#!/usr/bin/env python3
import asyncio
from app.Services.prompt_service import PromptService
from app.Services.query_enhancement_service import QueryEnhancementService

async def test_system_prompt():
    service = PromptService(language="zh")
    
    # Test prompt generation
    context = "DocAI 是一個 RAG 應用程式，支援 PDF 文檔上傳和問答。"
    messages = service.build_rag_prompt(
        query="DocAI 是什麼？",
        context_chunks=[{"content": context, "metadata": {}}],
        chat_history=[]
    )
    
    print("Generated System Prompt:")
    print(messages[0]["content"])
    print()

async def test_query_expansion():
    service = QueryEnhancementService()
    
    # Test query expansion
    result = await service.expand_query("DocAI 如何處理 PDF？")
    
    print("Expanded Questions:")
    for i, q in enumerate(result["expanded_questions"], 1):
        print(f"{i}. {q}")
    print()

if __name__ == "__main__":
    asyncio.run(test_system_prompt())
    asyncio.run(test_query_expansion())
```

**Run test**:
```bash
docaienv/bin/python test_prompts.py
```

---

## 📊 Prompt Performance Monitoring

Monitor how your prompts perform:

```python
# Add logging to prompt_service.py
import logging
logger = logging.getLogger(__name__)

def build_rag_prompt(self, query, context_chunks, chat_history):
    # ... existing code ...
    
    # Log prompt statistics
    context_length = sum(len(c["content"]) for c in context_chunks)
    logger.info(f"Prompt built: query_len={len(query)}, context_len={context_length}, history_len={len(chat_history)}")
    
    return messages
```

**View logs**:
```bash
tail -f logs/app.log | grep "Prompt built"
```

---

## 💡 Prompt Engineering Best Practices

### 1. Clear Instructions

✅ Good:
```
規則：
1. 僅使用提供的上下文
2. 找不到信息時明確告知
3. 不編造答案
```

❌ Bad:
```
請根據上下文回答，如果不知道就說不知道。
```

---

### 2. Explicit Constraints

✅ Good:
```
**重要約束：你必須僅使用下方提供的「上下文」來回答用戶的問題。**

如果上下文中沒有信息，必須回應：
"根據您提供的文檔，我無法找到相關信息。"
```

❌ Bad:
```
請根據上下文回答問題。
```

---

### 3. Format Specifications

✅ Good (for Query Expansion):
```python
請以 JSON 格式回應：
{{
  "original_query": "{original_query}",
  "intent": "查詢意圖描述",
  "expanded_questions": ["問題1", "問題2"],
  "reasoning": "分解邏輯"
}}
```

❌ Bad:
```
請分解問題並回答。
```

---

### 4. Examples in Prompts

Consider adding few-shot examples:

```python
SYSTEM_PROMPT_TEMPLATE = """你是一位文檔問答助手。

**回答範例**：

用戶：「這個產品的價格是多少？」
上下文：「我們的產品售價為 NT$1,000」
✅ 正確回答：「根據文檔，這個產品的售價為 NT$1,000。」

用戶：「這個產品有折扣嗎？」
上下文：「我們的產品售價為 NT$1,000」
✅ 正確回答：「根據文檔內容，沒有提及折扣信息。」

---
[上下文]
{context}
---

請根據以上上下文回答用戶的問題。"""
```

---

## 🔒 Important Notes

### Security Considerations

1. **Avoid Prompt Injection**: Don't allow user input directly into prompts without sanitization
2. **Context Length Limits**: Monitor total prompt length (system + context + query)
3. **PII Protection**: Don't log full prompts if they contain sensitive data

### Performance Considerations

1. **Prompt Length**: Longer prompts = higher latency and cost
2. **Token Limits**: Respect LLM context window (e.g., 4K, 8K, 32K tokens)
3. **Caching**: Consider caching expanded queries for similar questions

---

## 📚 Additional Resources

- **Prompt Engineering Guide**: https://www.promptingguide.ai/
- **LangChain Prompt Templates**: https://python.langchain.com/docs/modules/model_io/prompts/
- **OpenAI Best Practices**: https://platform.openai.com/docs/guides/prompt-engineering

---

## 🆘 Troubleshooting

### Problem: Prompt changes not taking effect

**Solution**: 
1. Check server auto-reload logs
2. Manually restart server
3. Clear any prompt caching

### Problem: AI not following constraints

**Solution**:
1. Make constraints more explicit
2. Use stronger language ("MUST", "NEVER")
3. Add negative examples
4. Increase constraint repetition

### Problem: Query expansion too aggressive/conservative

**Solution**:
1. Adjust `EXPANSION_COUNT` in .env
2. Modify expansion prompt instructions
3. Change temperature setting

---

**End of Prompt Customization Guide**

For more help, see:
- `app/Services/prompt_service.py` - Source code with comments
- `app/Services/query_enhancement_service.py` - Query expansion implementation
- `claudedocs/core_logic_service_to_endpoint_chat.md` - Architecture explanation
