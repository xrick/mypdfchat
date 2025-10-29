📋 五種 Prompt2 設計方案
Strategy 1: Intent Clarification（意圖澄清式）
思考邏輯： 保留原始查詢，但添加 LLM 識別出的意圖和關鍵資訊需求
PROMPT_2_INTENT_CLARIFICATION = """
[原始使用者查詢]
{original_query}

[查詢分析結果]
經過分析，此查詢的核心意圖是：{answer1_intent}
使用者可能想了解的關鍵面向包括：{answer1_key_aspects}

[增強指令]
請根據上述「原始查詢」和「查詢分析」，從以下上下文中提取相關資訊回答：

[上下文]
{retrieved_context}

回答時請：
1. 直接回應原始查詢的核心問題
2. 補充「查詢分析」中識別出的關鍵面向資訊
3. 僅使用上下文中的資訊，不添加外部知識
"""
優勢： 保持原意，透明度高
適用場景： 使用者查詢簡短但意圖清晰
Strategy 2: Question Expansion（問題擴展式）
思考邏輯： 將單一問題擴展為多個子問題，提高檢索覆蓋率
PROMPT_2_QUESTION_EXPANSION = """
[原始查詢]
{original_query}

[擴展查詢組]
為了更全面回答此問題，我們將其分解為以下子問題：
{answer1_expanded_questions}

[檢索上下文]
{retrieved_context}

[回答要求]
請綜合以上「原始查詢」和「擴展查詢組」，基於提供的上下文：
1. 逐一回答擴展出的子問題
2. 將答案整合為一個連貫的回應
3. 確保完整覆蓋原始查詢的意圖
4. 僅引用上下文中的資訊

最終答案應結構清晰，邏輯連貫。
"""
優勢： 提高複雜查詢的檢索召回率
適用場景： 開放性問題，需要多角度回答
Strategy 3: Contextual Grounding（上下文錨定式）
思考邏輯： 明確查詢的背景脈絡和約束條件
PROMPT_2_CONTEXTUAL_GROUNDING = """
[使用者查詢]
{original_query}

[查詢背景分析]
此查詢的背景脈絡：{answer1_context}
隱含的約束條件：{answer1_constraints}
關鍵術語定義：{answer1_terminology}

[相關文檔片段]
{retrieved_context}

[回答指引]
基於以上分析，請回答原始查詢，並遵守以下原則：
1. 考慮「查詢背景分析」中的脈絡資訊
2. 遵守「隱含約束條件」（如時間範圍、對象限定等）
3. 使用統一的術語定義避免歧義
4. 答案必須來自「相關文檔片段」，不得推測

請提供精準且符合脈絡的答案。
"""
優勢： 處理需要特定背景知識的查詢
適用場景： 專業領域查詢，有隱含假設
Strategy 4: Semantic Enrichment（語義豐富式）
思考邏輯： 添加同義詞、相關概念，提高語義匹配
PROMPT_2_SEMANTIC_ENRICHMENT = """
[原始問題]
{original_query}

[語義擴展]
相關概念和同義詞：{answer1_related_concepts}
可能的問法變體：{answer1_query_variations}

[文檔內容]
{retrieved_context}

[回答策略]
請理解原始問題及其語義擴展，從文檔內容中查找答案：
1. 匹配原始問題的字面意思
2. 也匹配「相關概念和同義詞」中的語義等價表達
3. 考慮「問法變體」中的不同提問方式
4. 綜合所有相關資訊提供完整答案

請基於文檔內容回答，涵蓋所有語義相關的資訊點。
"""
優勢： 解決詞彙不匹配問題（vocabulary mismatch）
適用場景： 使用者用詞與文檔術語不一致
Strategy 5: Adaptive Refinement（自適應精煉式）
思考邏輯： LLM 自動判斷查詢品質，動態決定是否需要重寫
PROMPT_2_ADAPTIVE_REFINEMENT = """
[原始查詢]
{original_query}

[查詢品質評估]
查詢明確度：{answer1_clarity_score}
資訊完整度：{answer1_completeness_score}

[改進建議]
{answer1_refinement_suggestion}

[檢索結果]
{retrieved_context}

[回答指令]
基於查詢品質評估：
- 若原始查詢已足夠明確（明確度 ≥ 8/10），直接基於檢索結果回答
- 若查詢需要改進，參考「改進建議」重新理解問題意圖，然後回答

回答時：
1. 首先判斷是否需要參考改進建議
2. 基於最準確的問題理解，從檢索結果中提取答案
3. 若檢索結果不足以回答，明確說明缺失的資訊
4. 不添加文檔外的推測性內容
"""
優勢： 彈性處理不同品質的查詢
適用場景： 通用場景，自動適應不同使用者