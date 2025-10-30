# libs/RAG/LLM/LLMInitializer.py
from typing import Optional
from langchain_ollama import OllamaLLM
import threading

class LLMInitializer:
    """
    Thread-Safe Singleton LLM Initializer
    使用 langchain_ollama.OllamaLLM 的版本：
    - 升級至新版 OllamaLLM，消除 deprecation warnings。
    - 依模型 context window 自動計算安全的輸出 token（num_predict）。
    - 必要時自動截斷輸入，避免超過 context。
    - 使用 Singleton Pattern 確保全系統只有一個 LLM 實例，節省記憶體。
    """

    # 類變數：Singleton 實例管理
    _instance: Optional['LLMInitializer'] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    # 針對常用模型給預設情境長度（必要時自行調整/擴充）
    DEFAULT_CONTEXT_LIMITS = {
        "gpt-oss:20b": 131072     # 已知上限
        # "deepseek-r1:7b": 131072,  # 預設同 131072；若你確知其他值可改
    }

    def __new__(cls,
                model_name: str = "gpt-oss:20b",
                temperature: float = 0.3,
                request_timeout: int = 60):
        """
        覆寫 __new__ 方法實現 Singleton Pattern
        使用 Double-Checked Locking 確保執行緒安全
        """
        # First check (without lock for performance)
        if cls._instance is None:
            with cls._lock:  # Acquire lock
                # Second check (with lock for thread safety)
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        model_name: str = "gpt-oss:20b",
        temperature: float = 0.3,
        request_timeout: int = 60
        # context_limit_override: Optional[int] = None,
    ):
        """
        初始化 LLM（只在首次創建時執行，後續調用會跳過）

        :param model_name: 在 Ollama 中運行的模型名稱。
        :param temperature: 控制生成文本的隨機性。
        :param request_timeout: 請求超時（秒）。
        """
        # 防止重複初始化
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self.model_name = model_name
            self.temperature = temperature
            self.request_timeout = request_timeout
            self.llm = None

            # 取得 context window 上限
            self.max_context_tokens = (
                self.DEFAULT_CONTEXT_LIMITS.get(self.model_name, 8192)  # 萬一未知，給個保守值
            )

            # 預設建立一個基礎 LLM；實際推論時會依需求重建以帶入不同 num_predict
            self.llm = OllamaLLM(
                model=self.model_name,
                temperature=self.temperature,
            )

            self._initialized = True

    @classmethod
    def get_instance(cls,
                     model_name: str = "gpt-oss:20b",
                     temperature: float = 0.3,
                     request_timeout: int = 60) -> 'LLMInitializer':
        """
        類方法：獲取單例實例（推薦使用方式）

        使用範例:
            llm_init = LLMInitializer.get_instance()
            llm = llm_init.get_llm()

        :param model_name: 在 Ollama 中運行的模型名稱
        :param temperature: 控制生成文本的隨機性
        :param request_timeout: 請求超時（秒）
        :return: LLMInitializer 單例實例
        """
        return cls(model_name, temperature, request_timeout)

    @classmethod
    def reset_instance(cls) -> None:
        """
        類方法：重置單例實例（僅用於測試）
        ⚠️ 警告：生產環境不應調用此方法
        """
        with cls._lock:
            cls._instance = None
            cls._initialized = False

    def reconfigure(self,
                    model_name: Optional[str] = None,
                    temperature: Optional[float] = None,
                    request_timeout: Optional[int] = None) -> None:
        """
        重新配置 LLM（不創建新實例）
        ⚠️ 注意：會影響所有使用該實例的模組

        :param model_name: 新的模型名稱
        :param temperature: 新的溫度參數
        :param request_timeout: 新的超時設定
        """
        with self._lock:
            if model_name and model_name != self.model_name:
                self.model_name = model_name
                self.max_context_tokens = self.DEFAULT_CONTEXT_LIMITS.get(
                    model_name, 8192
                )

            if temperature is not None:
                self.temperature = temperature

            if request_timeout is not None:
                self.request_timeout = request_timeout

            # 重新創建 LLM 實例
            self.llm = OllamaLLM(
                model=self.model_name,
                temperature=self.temperature,
            )

    # -------------------------
    # Token 估算與截斷工具
    # -------------------------
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        簡易 token 估算：
        - ASCII（英文/符號/空白）: 約 4 字元 ≈ 1 token
        - 非 ASCII（中日韓等）: 約 2 字元 ≈ 1 token
        目的：避免引入額外 tokenizer 套件，也能有足夠準的安全邊界
        """
        if not text:
            return 0
        ascii_count = sum(1 for ch in text if ord(ch) < 128)
        non_ascii_count = len(text) - ascii_count
        est = ascii_count / 4.0 + non_ascii_count / 2.0
        return int(est) + 1  # 向上取整一點保守

    @staticmethod
    def _truncate_to_tokens(text: str, target_tokens: int) -> str:
        """
        依估算 token 反推大致可承載的字元數來截斷。
        反推：ASCII 4字/Token、非ASCII 2字/Token 的混合不好精準，
        這裡採用保守法：以「2字/Token」抓字元上限，避免超量。
        """
        if target_tokens <= 0 or not text:
            return ""
        # 保守估：每 token 至少吃掉約 2 個字元（偏向 CJK 上限）
        char_budget = target_tokens * 2
        if len(text) <= char_budget:
            return text
        return text[:char_budget]

    # -------------------------
    # 對外：安全推論介面
    # -------------------------
    def safe_completion(
        self,
        prompt: str,
        reserve_output: int = 2048,
        auto_truncate: bool = True,
        min_output: int = 64,
    ) -> str:
        """
        安全地呼叫模型：
        - 自動計算可用輸出 token（num_predict）
        - 若 prompt 太長，必要時自動截斷輸入
        - 仍使用 Ollama（LangChain 介面）

        :param prompt: 輸入字串
        :param reserve_output: 希望的輸出上限（tokens），會在安全範圍內調整
        :param auto_truncate: True 時若輸入超量會自動截斷
        :param min_output: 最小輸出 token，避免完全沒字可回
        """
        # 1) 估算輸入 token
        prompt_tokens = self._estimate_tokens(prompt)

        # 2) 計算在不截斷前提下，理論可用輸出空間
        available_for_output = self.max_context_tokens - prompt_tokens
        if available_for_output < min_output and auto_truncate:
            # 不夠輸出，先把 prompt 截到留下 reserve_output 空間
            # 預留 max(reserve_output, min_output)；如果還是不夠就退而求其次
            need_output = max(reserve_output, min_output)
            target_prompt_tokens = max(self.max_context_tokens - need_output, 0)
            truncated_prompt = self._truncate_to_tokens(prompt, target_prompt_tokens)
            prompt = truncated_prompt
            prompt_tokens = self._estimate_tokens(prompt)
            available_for_output = self.max_context_tokens - prompt_tokens

        # 3) 決定最終 num_predict（= max_tokens）
        #    不超過 available_for_output，且至少要 min_output
        final_max_tokens = max(min(reserve_output, max(available_for_output, 0)), min_output)

        # 4) 用對應的 num_predict 重新建立（一次性）LLM 實例以送出請求
        #    新版 OllamaLLM 直接支援 num_predict 參數
        llm_for_call = OllamaLLM(
            model=self.model_name,
            temperature=self.temperature,
            num_predict=int(final_max_tokens),   # 控制輸出長度
        )

        # 5) 送出請求
        return llm_for_call.invoke(prompt)

    # 若你仍想保留一個「單純」的補全方法，可提供：
    def complete(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        傳統補全（不安全檢查）。若提供 max_tokens 則以該值為 num_predict。
        """
        if max_tokens is None:
            return self.llm.invoke(prompt)

        llm_for_call = OllamaLLM(
            model=self.model_name,
            temperature=self.temperature,
            num_predict=int(max_tokens),
        )
        return llm_for_call.invoke(prompt)

    def get_llm(self):
        """
        獲取LLM實例
        """
        return self.llm
