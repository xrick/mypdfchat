# Prompt Constraint Enforcement Estimation
## "Answers MUST Come From Uploaded Documents Only"

**Date**: 2025-10-30  
**Requirement**: Ensure all prompts strongly enforce that answers must come exclusively from user-uploaded documents  
**Current Status**: 🟡 **MODERATE** - Constraints exist but can be strengthened

---

## Executive Summary

| Aspect | Current State | Target State | Gap | Effort |
|--------|---------------|--------------|-----|--------|
| **Primary Constraint** | ✅ Explicit | ✅ Reinforced | Minor | 1-2 hours |
| **Negative Instructions** | ⚠️ Partial | ✅ Complete | Medium | 2-3 hours |
| **Validation Checks** | ❌ Missing | ✅ Implemented | Major | 3-4 hours |
| **Multi-Level Enforcement** | ⚠️ Single layer | ✅ Multi-layer | Medium | 2-3 hours |
| **Testing & Validation** | ❌ None | ✅ Comprehensive | Major | 3-4 hours |

**Total Estimated Effort**: **11-16 hours** (1.5-2 days)  
**Confidence Level**: 85%  
**Risk Level**: 🟢 Low

---

## 1. Current State Analysis

### ✅ Strengths (What's Already Good)

#### Prompt 1: `prompt_service.py` (System Prompt)

**Line 28-35**: Strong explicit constraint
```python
**重要約束：你必須僅使用下方提供的「上下文」來回答用戶的問題。**

規則：
1. 絕對禁止使用任何內部知識或上下文之外的信息
2. 如果「上下文」中沒有足夠的信息來回答問題，你必須明確回應：
   "根據您提供的文檔，我無法找到相關信息。"
3. 不要編造、猜測或推斷上下文中未明確說明的內容
4. 只引用和總結上下文中的內容
```

**Constraint Strength**: 🟢 **8/10**
- ✅ Uses strong language: "絕對禁止", "必須", "僅"
- ✅ Provides explicit fallback response template
- ✅ Forbids fabrication and guessing
- ✅ Both Chinese and English versions present

---

#### Prompt 2: `query_enhancement_service.py` (Answer Integration)

**Line 79**: Document-only instruction
```python
5. **只使用檢索到的文檔內容，不要添加外部知識**
```

**Constraint Strength**: 🟡 **6/10**
- ✅ Explicit "only document content" instruction
- ⚠️ Buried in guideline #5 (low visibility)
- ⚠️ Lacks consequences for violation
- ❌ No negative examples

---

### ⚠️ Gaps (What Needs Improvement)

#### Gap 1: Lack of Repetition (Severity: Medium)

**Issue**: Constraint mentioned once at the beginning, not reinforced at the end

**Current**:
```python
SYSTEM_PROMPT_TEMPLATE = """你是一位嚴謹的文檔問答助手。

**重要約束：你必須僅使用下方提供的「上下文」來回答用戶的問題。**
...
請根據以上上下文回答用戶的問題。"""
```

**Problem**: No reminder before the actual response generation

---

#### Gap 2: Missing Negative Instructions (Severity: High)

**Issue**: Doesn't explicitly state what NOT to do in specific scenarios

**Missing Examples**:
- ❌ "Do NOT use general knowledge about [topic]"
- ❌ "Do NOT reference information from training data"
- ❌ "Do NOT make assumptions beyond the context"

---

#### Gap 3: No Validation/Verification Step (Severity: High)

**Issue**: No instruction to verify answer against context before responding

**Missing**:
```python
在回答之前，請執行以下檢查：
1. 我的答案中的每個事實都能在上下文中找到嗎？
2. 我是否使用了任何外部知識？
3. 如果上下文不足，我是否明確說明了？
```

---

#### Gap 4: Weak Constraint in PROMPT_2 (Severity: Medium)

**Issue**: `PROMPT_2_QUESTION_EXPANSION` has weaker constraint enforcement

**Current** (Line 79):
```python
5. **只使用檢索到的文檔內容，不要添加外部知識**
```

**Problem**: 
- Guideline #5 (low priority positioning)
- No consequence for violation
- No examples

---

#### Gap 5: No Examples (Severity: Medium)

**Issue**: No positive/negative examples showing correct vs incorrect behavior

**Missing**:
```python
✅ 正確範例：
用戶：「產品價格是多少？」
上下文：「售價 NT$1,000」
回答：「根據文檔，產品售價為 NT$1,000。」

❌ 錯誤範例：
用戶：「產品價格是多少？」
上下文：「售價 NT$1,000」
錯誤回答：「這個價格很合理，因為市場行情...」（添加了外部知識）
```

---

## 2. Improvement Recommendations

### 🎯 Priority 1: Strengthen Primary Constraint (2-3 hours)

#### Action 1.1: Add Repetition and Reinforcement

**File**: `app/Services/prompt_service.py`

**Before** (Line 42):
```python
請根據以上上下文回答用戶的問題。"""
```

**After**:
```python
請根據以上上下文回答用戶的問題。

⚠️ **再次提醒**：
- 你的回答中的每個事實都必須來自上方的「上下文」
- 絕對不要使用任何訓練數據中的通用知識
- 如果上下文不包含答案，必須明確說「文檔中沒有此信息」
- 回答前請自我檢查：這個答案的每個部分都能在上下文中找到嗎？"""
```

**Benefit**: Reinforces constraint immediately before answer generation  
**Effort**: 15 minutes  
**Impact**: High

---

#### Action 1.2: Add Negative Instructions

**File**: `app/Services/prompt_service.py`

**Insert after Line 35**:
```python
規則：
1. 絕對禁止使用任何內部知識或上下文之外的信息
2. 如果「上下文」中沒有足夠的信息來回答問題，你必須明確回應：
   "根據您提供的文檔，我無法找到相關信息。"
3. 不要編造、猜測或推斷上下文中未明確說明的內容
4. 只引用和總結上下文中的內容

**明確禁止事項**：
❌ 禁止使用你的訓練數據中的通用知識
❌ 禁止根據常識或經驗做出推論
❌ 禁止引用上下文之外的任何來源
❌ 禁止使用「根據我的理解」、「通常來說」等措辭
❌ 禁止在上下文不足時給出模糊或不確定的答案
```

**Benefit**: Explicit negative boundaries prevent leakage  
**Effort**: 30 minutes  
**Impact**: Very High

---

#### Action 1.3: Add Verification Step

**File**: `app/Services/prompt_service.py`

**Insert before final instruction** (before Line 42):
```python
**回答前自我檢查清單**：
在生成回答前，請逐項確認：
□ 我的回答中的每個事實都直接來自上方上下文
□ 我沒有使用任何外部知識或常識推論
□ 如果上下文不足，我明確說明了
□ 我的回答沒有使用「通常」、「一般來說」等推測性措辭
□ 我能為回答中的每個論點指出上下文中的具體來源

只有當以上所有項都確認後，才能生成回答。

---

請根據以上上下文回答用戶的問題。
```

**Benefit**: Forces LLM to self-validate before answering  
**Effort**: 45 minutes  
**Impact**: Very High

---

### 🎯 Priority 2: Strengthen PROMPT_2 Constraint (1-2 hours)

#### Action 2.1: Elevate Constraint to Top Priority

**File**: `app/Services/query_enhancement_service.py`

**Before** (Line 74-79):
```python
指導原則：
1. 優先使用檢索到的上下文信息
2. 整合多個子問題的答案，形成完整回應
3. 保持回答的連貫性和邏輯性
4. 如果上下文不足，明確說明
5. **只使用檢索到的文檔內容，不要添加外部知識**
```

**After**:
```python
**核心約束（最高優先級）**：
⚠️ 你的回答必須 100% 基於以下「檢索到的相關文檔片段」
⚠️ 絕對禁止使用任何外部知識、訓練數據或常識推論
⚠️ 如果文檔片段不足以完整回答，必須明確說明

指導原則：
1. 整合多個子問題的答案，形成完整回應
2. 保持回答的連貫性和邏輯性
3. 每個論點都必須能追溯到上方的文檔片段
4. 使用「根據文檔」、「文檔中提到」等明確措辭
```

**Benefit**: Makes constraint primary, not secondary  
**Effort**: 30 minutes  
**Impact**: High

---

#### Action 2.2: Add Examples

**File**: `app/Services/query_enhancement_service.py`

**Insert after Line 79**:
```python
**正確範例**：
✅ 用戶問：「產品的價格是多少？」
   文檔：「本產品售價為 NT$1,000」
   正確回答：「根據文檔，本產品售價為 NT$1,000。」

✅ 用戶問：「產品有什麼優惠嗎？」
   文檔：「本產品售價為 NT$1,000」（沒有提到優惠）
   正確回答：「文檔中僅提到產品售價為 NT$1,000，沒有提及任何優惠信息。」

**錯誤範例**：
❌ 用戶問：「這個價格合理嗎？」
   文檔：「本產品售價為 NT$1,000」
   錯誤回答：「這個價格很合理，因為市場行情通常...」
   （❌ 使用了外部知識進行價格評估）

❌ 用戶問：「產品適合什麼人？」
   文檔：「本產品售價為 NT$1,000」（沒有提到目標用戶）
   錯誤回答：「這個產品適合預算有限的消費者...」
   （❌ 根據價格做出推論，而非文檔明確說明）

---

回答時請：
```

**Benefit**: Concrete examples reduce ambiguity  
**Effort**: 45 minutes  
**Impact**: Medium-High

---

### 🎯 Priority 3: Add Validation Mechanism (3-4 hours)

#### Action 3.1: Create Prompt Validation Function

**File**: `app/Services/prompt_service.py`

**Add new method** (after Line 120):
```python
def validate_response_constraint(
    self,
    response: str,
    context: str
) -> Dict[str, Any]:
    """
    Validate if response adheres to document-only constraint
    
    This is a heuristic validation - not perfect but catches obvious violations.
    
    Args:
        response: AI-generated response
        context: Original context provided
        
    Returns:
        Dict with validation results:
        {
            "is_valid": bool,
            "warnings": List[str],
            "violations": List[str]
        }
    """
    warnings = []
    violations = []
    
    # Check for common violation patterns
    violation_patterns = [
        ("通常", "使用了「通常」等推測性措辭"),
        ("一般來說", "使用了「一般來說」等推測性措辭"),
        ("根據我的理解", "使用了「根據我的理解」等主觀表述"),
        ("眾所周知", "使用了「眾所周知」等外部知識表述"),
        ("市場上", "引用了文檔外的市場信息"),
    ]
    
    for pattern, message in violation_patterns:
        if pattern in response:
            violations.append(message)
    
    # Check if response explicitly states document source
    if "根據文檔" not in response and "文檔中" not in response and "上下文" not in response:
        warnings.append("回答未明確引用文檔來源")
    
    # Check if response is much longer than context (possible hallucination)
    if len(response) > len(context) * 1.5:
        warnings.append("回答長度顯著超過上下文，可能包含額外信息")
    
    return {
        "is_valid": len(violations) == 0,
        "warnings": warnings,
        "violations": violations
    }
```

**Benefit**: Runtime validation catches violations  
**Effort**: 2 hours  
**Impact**: Medium

---

#### Action 3.2: Integrate Validation into Chat Endpoint

**File**: `app/api/v1/endpoints/chat.py`

**Modify response generation** (around Line 250):
```python
# After collecting full response
full_response = "".join(response_tokens)

# Validate constraint adherence
validation = prompt_service.validate_response_constraint(
    response=full_response,
    context=context_strings
)

if not validation["is_valid"]:
    logger.warning(f"Response constraint violation detected: {validation['violations']}")
    # Optionally: prepend warning to response
    warning_prefix = "⚠️ 注意：此回答可能包含文檔外信息。\n\n"
    full_response = warning_prefix + full_response

if validation["warnings"]:
    logger.info(f"Response warnings: {validation['warnings']}")
```

**Benefit**: Real-time violation detection and logging  
**Effort**: 1 hour  
**Impact**: Medium

---

### 🎯 Priority 4: Testing & Validation (3-4 hours)

#### Action 4.1: Create Test Cases

**File**: `tests/test_prompt_constraints.py` (new file)

```python
import pytest
from app.Services.prompt_service import PromptService

class TestPromptConstraints:
    """Test that prompts enforce document-only constraint"""
    
    def test_constraint_present_in_system_prompt(self):
        """Verify constraint is explicitly stated"""
        service = PromptService()
        prompt = service.SYSTEM_PROMPT_TEMPLATE
        
        # Check for key constraint phrases
        assert "僅使用" in prompt or "只使用" in prompt
        assert "絕對禁止" in prompt or "不要" in prompt
        assert "上下文" in prompt or "文檔" in prompt
    
    def test_fallback_response_template(self):
        """Verify fallback response is provided"""
        service = PromptService()
        prompt = service.SYSTEM_PROMPT_TEMPLATE
        
        assert "無法找到" in prompt or "沒有" in prompt
    
    def test_validation_detects_violations(self):
        """Test validation catches common violations"""
        service = PromptService()
        context = "產品售價為 NT$1,000"
        
        # Valid response
        valid_response = "根據文檔，產品售價為 NT$1,000。"
        result = service.validate_response_constraint(valid_response, context)
        assert result["is_valid"] == True
        
        # Invalid response with external knowledge
        invalid_response = "這個價格很合理，因為市場上通常..."
        result = service.validate_response_constraint(invalid_response, context)
        assert result["is_valid"] == False
        assert len(result["violations"]) > 0
```

**Effort**: 2 hours  
**Impact**: High (ensures constraint enforcement)

---

#### Action 4.2: Manual Testing Protocol

**Create test document**: `test_constraint_enforcement.md`

```markdown
# Constraint Enforcement Test Protocol

## Test Case 1: Direct Question with Context
- Upload document: "DocAI 是一個 RAG 應用程式"
- Question: "DocAI 是什麼？"
- Expected: "根據文檔，DocAI 是一個 RAG 應用程式"
- ✅/❌ Result: ___________

## Test Case 2: Question Beyond Context
- Upload document: "DocAI 支援 PDF 上傳"
- Question: "DocAI 支援什麼檔案格式？"
- Expected: "根據文檔，DocAI 支援 PDF 上傳。文檔中沒有提及其他檔案格式。"
- ✅/❌ Result: ___________

## Test Case 3: Trick Question (Requires External Knowledge)
- Upload document: "產品售價 NT$1,000"
- Question: "這個價格合理嗎？"
- Expected: "文檔中僅提到產品售價為 NT$1,000，沒有關於價格合理性的評估。"
- ✅/❌ Result: ___________

## Test Case 4: Comparison Question (Requires External Knowledge)
- Upload document: "我們的產品有 A 功能"
- Question: "和競爭對手相比如何？"
- Expected: "文檔中提到我們的產品有 A 功能，但沒有提及競爭對手的信息。"
- ✅/❌ Result: ___________

## Test Case 5: Inference Trap
- Upload document: "公司成立於 2020 年"
- Question: "公司有幾年歷史？"
- Expected (Strict): "文檔提到公司成立於 2020 年，但沒有明確說明有幾年歷史。"
- Acceptable: "根據文檔，公司成立於 2020 年。"
- ✅/❌ Result: ___________
```

**Effort**: 1 hour  
**Impact**: High

---

## 3. Implementation Roadmap

### Phase 1: Critical Improvements (4-5 hours) - Day 1

| Task | File | Effort | Priority |
|------|------|--------|----------|
| Add repetition & reinforcement | `prompt_service.py` | 15 min | P0 |
| Add negative instructions | `prompt_service.py` | 30 min | P0 |
| Add verification checklist | `prompt_service.py` | 45 min | P0 |
| Elevate PROMPT_2 constraint | `query_enhancement_service.py` | 30 min | P0 |
| Add examples to PROMPT_2 | `query_enhancement_service.py` | 45 min | P0 |
| Create validation function | `prompt_service.py` | 2 hours | P1 |

**Deliverable**: Strengthened prompts with multi-layer enforcement

---

### Phase 2: Validation & Testing (4-5 hours) - Day 2

| Task | File | Effort | Priority |
|------|------|--------|----------|
| Integrate validation into chat endpoint | `chat.py` | 1 hour | P1 |
| Create automated test cases | `tests/test_prompt_constraints.py` | 2 hours | P1 |
| Manual testing protocol execution | Manual | 1 hour | P1 |
| Document test results | `claudedocs/` | 30 min | P2 |
| Create constraint monitoring dashboard | Optional | 1 hour | P2 |

**Deliverable**: Validated, tested constraint enforcement system

---

### Phase 3: Monitoring & Iteration (Optional, 3-4 hours)

| Task | Effort | Priority |
|------|--------|----------|
| Add logging for constraint violations | 1 hour | P2 |
| Create metrics dashboard | 2 hours | P2 |
| Iterative refinement based on real usage | Ongoing | P3 |

---

## 4. Effort Breakdown

### By Priority

| Priority | Tasks | Total Effort | Impact |
|----------|-------|--------------|--------|
| **P0** (Must Do) | 5 tasks | 2.5 hours | Very High |
| **P1** (Should Do) | 4 tasks | 5.5 hours | High |
| **P2** (Nice to Have) | 3 tasks | 4.5 hours | Medium |

**Recommended**: Complete P0 + P1 = **8 hours (1 day)**

---

### By Component

| Component | Effort | Current Strength | Target Strength |
|-----------|--------|------------------|-----------------|
| System Prompt (Chinese) | 1.5 hours | 8/10 | 10/10 |
| System Prompt (English) | 1.5 hours | 8/10 | 10/10 |
| PROMPT_2 Enhancement | 1.5 hours | 6/10 | 9/10 |
| Validation Mechanism | 3 hours | 0/10 | 8/10 |
| Testing | 3 hours | 0/10 | 9/10 |

**Total**: 10.5 hours average, 8-13 hours range

---

## 5. Risk Assessment

### Low Risk Items (Quick Wins)

✅ **Adding repetition**: Copy-paste with minor edits (15 min)  
✅ **Adding negative instructions**: Template-based (30 min)  
✅ **PROMPT_2 elevation**: Reordering priorities (30 min)

**Total Low-Risk Improvements**: 1.25 hours, High impact

---

### Medium Risk Items

⚠️ **Verification checklist**: May increase prompt length significantly  
⚠️ **Examples**: Need careful crafting to avoid confusion  
⚠️ **Validation function**: Heuristic-based, not perfect

**Mitigation**: Test thoroughly, iterate based on results

---

### High Risk Items

🔴 **Over-constraining**: Too strict may reduce answer quality  
🔴 **False positives**: Validation may flag valid responses

**Mitigation**:
- Start with warnings, not hard blocks
- Monitor false positive rate
- Allow manual override

---

## 6. Success Metrics

### Quantitative Metrics

| Metric | Baseline (Current) | Target | How to Measure |
|--------|-------------------|--------|----------------|
| Constraint mentions per prompt | 1x | 3x | Count occurrences |
| Explicit negative instructions | 0 | 5+ | Count ❌ items |
| Validation coverage | 0% | 80% | Test cases passed |
| Response validation | No | Yes | Function exists |

---

### Qualitative Metrics

| Metric | Current | Target | Evaluation Method |
|--------|---------|--------|-------------------|
| Constraint clarity | Good | Excellent | Expert review |
| Multi-layer enforcement | Single | Triple | Code review |
| Example quality | None | High | User testing |
| Monitoring capability | None | Good | Dashboard review |

---

## 7. Cost-Benefit Analysis

### Benefits

| Benefit | Value | Confidence |
|---------|-------|------------|
| **Prevents hallucination** | Very High | 90% |
| **Increases trust** | Very High | 95% |
| **Reduces misinformation** | Very High | 90% |
| **Improves compliance** | High | 85% |
| **Better user experience** | High | 80% |

---

### Costs

| Cost Type | Amount | Impact |
|-----------|--------|--------|
| **Development time** | 8-13 hours | Medium |
| **Testing time** | 3-4 hours | Medium |
| **Maintenance** | 1-2 hours/month | Low |
| **Prompt length increase** | +30% tokens | Low (cost) |

**ROI**: Very Positive (Benefits >> Costs)

---

## 8. Recommendations

### Immediate Actions (Today)

1. ✅ **Implement P0 tasks** (2.5 hours)
   - Add repetition and negative instructions
   - Strengthen PROMPT_2 constraint
   
2. ✅ **Quick test** (30 min)
   - Upload test document
   - Ask trick questions
   - Verify constraint adherence

**Total**: 3 hours, Immediate high impact

---

### This Week

1. ✅ **Complete P1 tasks** (5.5 hours)
   - Validation function
   - Integration with chat endpoint
   - Automated test suite

2. ✅ **Manual testing** (1 hour)
   - Execute test protocol
   - Document results

**Total**: 6.5 hours, Complete enforcement system

---

### This Month (Optional)

1. **Monitoring dashboard** (2 hours)
2. **Iterative refinement** (2 hours)
3. **User feedback integration** (2 hours)

**Total**: 6 hours, Continuous improvement

---

## 9. Conclusion

### Current State: 🟡 MODERATE (7/10)

**Strengths**:
- ✅ Explicit constraint present
- ✅ Clear rules stated
- ✅ Both Chinese and English versions

**Weaknesses**:
- ⚠️ Single-layer enforcement (no repetition)
- ⚠️ No negative examples
- ❌ No validation mechanism
- ⚠️ PROMPT_2 constraint too weak

---

### Target State: 🟢 EXCELLENT (10/10)

**With recommended improvements**:
- ✅ Triple-layer enforcement (start, checklist, end)
- ✅ Explicit negative instructions
- ✅ Validation function with logging
- ✅ Comprehensive test coverage
- ✅ Clear examples (do's and don'ts)

---

### Recommended Path

**Fast Track (1 day, 8 hours)**:
- Focus on P0 + P1 tasks
- Implement core strengthening + validation
- Execute manual testing

**Complete Track (2 days, 13 hours)**:
- All P0 + P1 + selected P2 tasks
- Comprehensive testing
- Monitoring setup

**Confidence**: 85% that Fast Track achieves 9/10 target  
**Risk**: Low (changes are additive, not breaking)

---

## Appendix A: Code Templates

### Template 1: Strengthened System Prompt

```python
SYSTEM_PROMPT_TEMPLATE = """你是一位嚴謹的文檔問答助手。

**核心約束（最高優先級）**：
⚠️ 你必須 100% 僅使用下方提供的「上下文」來回答用戶的問題
⚠️ 絕對禁止使用任何訓練數據、通用知識或外部信息

**明確規則**：
1. ✅ 只引用和總結上下文中明確提到的內容
2. ✅ 如果上下文不足，必須回應："根據您提供的文檔，我無法找到相關信息。"
3. ❌ 絕對禁止編造、猜測或推斷上下文未明確說明的內容
4. ❌ 絕對禁止使用「通常」、「一般來說」、「根據常識」等措辭

**禁止事項清單**：
❌ 禁止使用訓練數據中的通用知識
❌ 禁止根據常識或經驗做推論
❌ 禁止引用上下文之外的任何來源
❌ 禁止使用推測性或不確定的表述
❌ 禁止在上下文不足時給出模糊答案

---
[上下文]
{context}
---

**回答前自我檢查**：
在生成回答前，請確認：
□ 我的每個論點都來自上方上下文
□ 我沒有使用任何外部知識
□ 如果上下文不足，我明確說明了
□ 我的回答可以追溯到具體的上下文片段

⚠️ **最後提醒**：你的回答必須 100% 基於上方「上下文」，不得添加任何外部信息。

請根據以上上下文回答用戶的問題。"""
```

---

**End of Estimation Report**

**Next Step**: Approve and implement recommended improvements  
**Timeline**: 1-2 days for core improvements  
**Expected Outcome**: Constraint enforcement strength 9/10
