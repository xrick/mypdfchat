"""
Chat History Provider Module

MongoDB-based conversation history persistence and retrieval.
"""

from app.Providers.chat_history_provider.client import (
    ChatHistoryProvider,
    get_chat_history_provider
)

__all__ = ["ChatHistoryProvider", "get_chat_history_provider"]
