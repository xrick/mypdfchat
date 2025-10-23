"""
LLM Providers - OpenAI-compatible client with streaming support
"""
from typing import AsyncIterator, Optional, Dict, Any, List
from app.domain.models import LLMConfig
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


class OpenAICompatClient:
    """
    OpenAI-compatible LLM client supporting both OpenAI API and Ollama
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize OpenAI-compatible client
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self._client = None
        
    def _get_client(self):
        """Get or create OpenAI client"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                
                # Support both OpenAI and Ollama
                if self.config.api_key:
                    self._client = AsyncOpenAI(
                        api_key=self.config.api_key,
                        base_url=self.config.base_url if self.config.base_url != "http://localhost:11434" else None
                    )
                else:
                    # Ollama or local server
                    self._client = AsyncOpenAI(
                        api_key="ollama",  # Dummy key for Ollama
                        base_url=self.config.base_url
                    )
            except ImportError:
                raise ImportError("openai package is required. Install with: pip install openai")
        
        return self._client
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Non-streaming chat completion
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Model name override
            
        Returns:
            Generated response text
        """
        client = self._get_client()
        
        try:
            response = await client.chat.completions.create(
                model=model or self.config.model,
                messages=messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                stream=False
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Streaming chat completion with progressive output
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Model name override
            
        Yields:
            Token strings as they are generated
        """
        client = self._get_client()
        
        try:
            stream = await client.chat.completions.create(
                model=model or self.config.model,
                messages=messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Streaming completion error: {e}")
            raise
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-ada-002"
    ) -> List[List[float]]:
        """
        Generate embeddings for texts
        
        Args:
            texts: List of text strings
            model: Embedding model name
            
        Returns:
            List of embedding vectors
        """
        client = self._get_client()
        
        try:
            response = await client.embeddings.create(
                model=model,
                input=texts
            )
            
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise


class LangChainLLM:
    """
    LangChain-based LLM wrapper for advanced features
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize LangChain LLM
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self._llm = None
        
    def _get_llm(self):
        """Get or create LangChain LLM"""
        if self._llm is None:
            try:
                from langchain_openai import ChatOpenAI
                
                self._llm = ChatOpenAI(
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    openai_api_key=self.config.api_key or "ollama",
                    openai_api_base=self.config.base_url,
                    streaming=self.config.streaming
                )
            except ImportError:
                logger.warning("langchain-openai not installed, falling back to basic client")
                return None
        
        return self._llm
    
    async def ainvoke(self, messages: List[Dict[str, str]]) -> str:
        """
        Async invoke LangChain LLM
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Generated response text
        """
        llm = self._get_llm()
        if llm is None:
            # Fallback to basic client
            from app.llm_providers.openai_compat import OpenAICompatClient
            client = OpenAICompatClient(self.config)
            return await client.chat_completion(messages)
        
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        
        # Convert to LangChain message format
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        
        response = await llm.ainvoke(lc_messages)
        return response.content
    
    async def astream(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """
        Async streaming invoke LangChain LLM
        
        Args:
            messages: List of message dictionaries
            
        Yields:
            Token strings as they are generated
        """
        llm = self._get_llm()
        if llm is None:
            # Fallback to basic client
            from app.llm_providers.openai_compat import OpenAICompatClient
            client = OpenAICompatClient(self.config)
            async for token in client.chat_completion_stream(messages):
                yield token
            return
        
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        
        # Convert to LangChain message format
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        
        async for chunk in llm.astream(lc_messages):
            if hasattr(chunk, 'content'):
                yield chunk.content
