"""
LLM Provider Client

Unified client for OpenAI-compatible API endpoints.
Supports streaming responses for real-time chat applications.
"""

import httpx
import logging
from typing import AsyncGenerator, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProviderClient:
    """
    Unified LLM Provider Client

    Communicates with any OpenAI-compatible API endpoint (Ollama, vLLM, llama.cpp).
    Provides streaming responses for optimistic progressive markdown parsing.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0
    ):
        """
        Initialize LLM Provider Client

        Args:
            base_url: Base URL of the LLM service (e.g., http://localhost:11434/v1)
            api_key: API key for authentication (optional for local services)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.LLM_PROVIDER_BASE_URL
        self.api_key = api_key or settings.LLM_PROVIDER_API_KEY or "ollama"
        self.timeout = timeout

        logger.info(f"LLM Provider initialized with base_url: {self.base_url}")

    async def get_chat_completion_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[bytes, None]:
        """
        Get streaming chat completion from LLM

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (defaults to settings.DEFAULT_LLM_MODEL)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters

        Yields:
            bytes: Server-Sent Events (SSE) formatted chunks

        Example:
            >>> messages = [
            ...     {"role": "system", "content": "You are a helpful assistant."},
            ...     {"role": "user", "content": "Hello!"}
            ... ]
            >>> async for chunk in client.get_chat_completion_stream(messages):
            ...     print(chunk)
        """
        model = model or settings.DEFAULT_LLM_MODEL

        request_body = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
        }

        if max_tokens:
            request_body["max_tokens"] = max_tokens

        # Merge additional kwargs
        request_body.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        endpoint = f"{self.base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    endpoint,
                    json=request_body,
                    headers=headers
                ) as response:
                    response.raise_for_status()

                    # Stream raw SSE chunks directly to client
                    async for chunk in response.aiter_bytes():
                        yield chunk

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from LLM provider: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error to LLM provider: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LLM provider client: {str(e)}")
            raise

    async def get_chat_completion(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> dict:
        """
        Get non-streaming chat completion from LLM

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (defaults to settings.DEFAULT_LLM_MODEL)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters

        Returns:
            dict: Complete response from LLM with 'choices', 'usage', etc.
        """
        model = model or settings.DEFAULT_LLM_MODEL

        request_body = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
        }

        if max_tokens:
            request_body["max_tokens"] = max_tokens

        request_body.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        endpoint = f"{self.base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=request_body,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from LLM provider: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error to LLM provider: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LLM provider client: {str(e)}")
            raise


# Dependency injection helper
def get_llm_provider_client() -> LLMProviderClient:
    """
    FastAPI dependency for LLM Provider Client

    Usage in endpoints:
        @router.post("/chat")
        async def chat(
            llm_client: LLMProviderClient = Depends(get_llm_provider_client)
        ):
            ...
    """
    return LLMProviderClient()
