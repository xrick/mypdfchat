# app/api/v1/endpoints/chat.py
"""
Chat Endpoint with OPMP (Optimistic Progressive Markdown Parsing)

Implements five-phase RAG pipeline with SSE streaming:
1. Query Understanding (Strategy 2: Question Expansion)
2. Parallel Retrieval
3. Context Assembly
4. Response Generation (OPMP Core)
5. Post Processing
"""

import json
import logging
import asyncio
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

# Providers
from app.Providers.llm_provider.client import LLMProviderClient, get_llm_provider
from app.Providers.embedding_provider.client import EmbeddingProvider, get_embedding_provider
from app.Providers.vector_store_provider.client import VectorStoreProvider, get_vector_store_provider
from app.Providers.chat_history_provider.client import ChatHistoryProvider, get_chat_history_provider
from app.Providers.cache_provider.client import CacheProvider, get_cache_provider

# Services
from app.Services.query_enhancement_service import QueryEnhancementService, get_query_enhancement_service
from app.Services.retrieval_service import RetrievalService, get_retrieval_service
from app.Services.prompt_service import PromptService, get_prompt_service

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class ChatRequest(BaseModel):
    """Chat request schema"""
    query: str = Field(..., description="User's question", min_length=1)
    session_id: str = Field(..., description="Session identifier")
    file_ids: List[str] = Field(..., description="Document file IDs to query against")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    language: Optional[str] = Field("zh", description="Response language (zh/en)")
    top_k: Optional[int] = Field(5, description="Number of context chunks to retrieve")
    enable_expansion: Optional[bool] = Field(True, description="Enable query expansion (Strategy 2)")


class ChatResponse(BaseModel):
    """Chat response schema (non-streaming fallback)"""
    session_id: str
    query: str
    answer: str
    context_count: int
    expanded_questions: Optional[List[str]] = None
    metadata: dict = {}


# =============================================================================
# SSE Event Helpers
# =============================================================================

def create_sse_event(event_type: str, data: dict) -> dict:
    """
    Create SSE event dict

    Args:
        event_type: Event type (progress, markdown_token, complete, error)
        data: Event data payload

    Returns:
        dict: SSE event with 'event' and 'data' keys
    """
    return {
        "event": event_type,
        "data": json.dumps(data, ensure_ascii=False)
    }


# =============================================================================
# Chat Endpoints
# =============================================================================

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    llm_client: LLMProviderClient = Depends(get_llm_provider),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    chat_history_provider: ChatHistoryProvider = Depends(get_chat_history_provider),
    cache_provider: CacheProvider = Depends(get_cache_provider),
    query_enhancement_service: QueryEnhancementService = Depends(get_query_enhancement_service)
):
    """
    Chat with documents using SSE streaming (OPMP)

    Five-Phase RAG Pipeline:
    1. Query Understanding: Expand user query into sub-questions
    2. Parallel Retrieval: Retrieve context from multiple sub-questions
    3. Context Assembly: Build enhanced RAG prompt
    4. Response Generation: Stream LLM response with OPMP
    5. Post Processing: Save chat history and metadata

    SSE Events:
    - progress: Phase progress updates (phase 1-5, progress 0-100%)
    - markdown_token: Individual tokens for progressive rendering
    - complete: Final completion event with metadata
    - error: Error event if something fails

    Example:
        >>> POST /api/v1/chat/stream
        >>> {
        ...   "query": "What is RAG?",
        ...   "session_id": "session_xyz",
        ...   "file_ids": ["file_abc"],
        ...   "language": "zh"
        ... }
    """

    async def generate_sse_events():
        """Generate SSE events for OPMP streaming"""

        full_response = ""
        expanded_questions = []
        context_chunks = []

        try:
            # =====================================================================
            # Phase 1: Query Understanding (Strategy 2: Question Expansion)
            # =====================================================================
            yield create_sse_event("progress", {
                "phase": 1,
                "phase_name": "Query Understanding",
                "progress": 0,
                "message": "Analyzing user query..."
            })

            if request.enable_expansion:
                expansion_result = await query_enhancement_service.expand_query(
                    query=request.query,
                    cache_provider=cache_provider
                )
                expanded_questions = expansion_result.get("expanded_questions", [request.query])
                logger.info(f"Query expanded into {len(expanded_questions)} sub-questions")
            else:
                expanded_questions = [request.query]

            yield create_sse_event("progress", {
                "phase": 1,
                "phase_name": "Query Understanding",
                "progress": 100,
                "message": f"Query expanded into {len(expanded_questions)} sub-questions"
            })

            # =====================================================================
            # Phase 2: Parallel Retrieval
            # =====================================================================
            yield create_sse_event("progress", {
                "phase": 2,
                "phase_name": "Parallel Retrieval",
                "progress": 0,
                "message": "Retrieving relevant context from documents..."
            })

            # Retrieve context for each expanded question in parallel
            retrieval_tasks = [
                retrieval_service.retrieve_context(
                    query=question,
                    file_ids=request.file_ids,
                    top_k=request.top_k
                )
                for question in expanded_questions
            ]

            retrieval_results = await asyncio.gather(*retrieval_tasks)

            # Merge and deduplicate context chunks
            seen_contents = set()
            for results in retrieval_results:
                for result in results:
                    content = result.get("content", "")
                    if content and content not in seen_contents:
                        context_chunks.append(result)
                        seen_contents.add(content)

            logger.info(f"Retrieved {len(context_chunks)} unique context chunks")

            yield create_sse_event("progress", {
                "phase": 2,
                "phase_name": "Parallel Retrieval",
                "progress": 100,
                "message": f"Retrieved {len(context_chunks)} relevant chunks"
            })

            # =====================================================================
            # Phase 3: Context Assembly
            # =====================================================================
            yield create_sse_event("progress", {
                "phase": 3,
                "phase_name": "Context Assembly",
                "progress": 0,
                "message": "Building enhanced RAG prompt..."
            })

            # Get chat history
            chat_history = await chat_history_provider.get_chat_history(
                session_id=request.session_id,
                limit=10  # Last 10 messages for context
            )

            # Extract content strings for prompt building
            context_strings = [chunk.get("content", "") for chunk in context_chunks]

            # Build RAG prompt
            messages = prompt_service.build_rag_prompt(
                query=request.query,
                context_chunks=context_strings,
                chat_history=chat_history,
                language=request.language
            )

            yield create_sse_event("progress", {
                "phase": 3,
                "phase_name": "Context Assembly",
                "progress": 100,
                "message": "Prompt built with context and history"
            })

            # =====================================================================
            # Phase 4: Response Generation (OPMP Core)
            # =====================================================================
            yield create_sse_event("progress", {
                "phase": 4,
                "phase_name": "Response Generation",
                "progress": 0,
                "message": "Generating answer from LLM..."
            })

            # Stream LLM response
            async for chunk in llm_client.get_chat_completion_stream(
                messages=messages,
                temperature=0.7
            ):
                # Parse SSE chunk from LLM provider
                chunk_str = chunk.decode('utf-8')

                # Handle SSE format: "data: {json}\n\n"
                for line in chunk_str.split('\n'):
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove "data: " prefix

                        if data_str.strip() == '[DONE]':
                            continue

                        try:
                            data = json.loads(data_str)

                            # Extract token from OpenAI-compatible format
                            choices = data.get('choices', [])
                            if choices:
                                delta = choices[0].get('delta', {})
                                token = delta.get('content', '')

                                if token:
                                    full_response += token

                                    # OPMP: Send token for progressive rendering
                                    yield create_sse_event("markdown_token", {
                                        "token": token
                                    })

                        except json.JSONDecodeError:
                            continue

            yield create_sse_event("progress", {
                "phase": 4,
                "phase_name": "Response Generation",
                "progress": 100,
                "message": "Answer generation complete"
            })

            # =====================================================================
            # Phase 5: Post Processing
            # =====================================================================
            yield create_sse_event("progress", {
                "phase": 5,
                "phase_name": "Post Processing",
                "progress": 0,
                "message": "Saving chat history..."
            })

            # Save user message and assistant response to chat history
            await chat_history_provider.add_message(
                session_id=request.session_id,
                role="user",
                content=request.query,
                metadata={
                    "file_ids": request.file_ids,
                    "expanded_questions": expanded_questions,
                    "context_count": len(context_chunks),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

            await chat_history_provider.add_message(
                session_id=request.session_id,
                role="assistant",
                content=full_response,
                metadata={
                    "context_count": len(context_chunks),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

            yield create_sse_event("progress", {
                "phase": 5,
                "phase_name": "Post Processing",
                "progress": 100,
                "message": "Chat history saved"
            })

            # =====================================================================
            # Completion Event
            # =====================================================================
            yield create_sse_event("complete", {
                "session_id": request.session_id,
                "query": request.query,
                "answer": full_response,
                "context_count": len(context_chunks),
                "expanded_questions": expanded_questions,
                "metadata": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "language": request.language
                }
            })

            logger.info(f"Chat streaming completed for session: {request.session_id}")

        except Exception as e:
            logger.error(f"Error in chat streaming: {str(e)}")

            # Send error event
            yield create_sse_event("error", {
                "error": str(e),
                "message": "An error occurred during chat processing"
            })

    return EventSourceResponse(generate_sse_events())


@router.post("", response_model=ChatResponse)
async def chat_non_streaming(
    request: ChatRequest,
    llm_client: LLMProviderClient = Depends(get_llm_provider),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    chat_history_provider: ChatHistoryProvider = Depends(get_chat_history_provider),
    cache_provider: CacheProvider = Depends(get_cache_provider),
    query_enhancement_service: QueryEnhancementService = Depends(get_query_enhancement_service)
):
    """
    Chat with documents (non-streaming fallback)

    Same RAG pipeline as streaming endpoint, but returns complete response.
    Use this for clients that don't support SSE.

    Example:
        >>> POST /api/v1/chat
        >>> {
        ...   "query": "What is RAG?",
        ...   "session_id": "session_xyz",
        ...   "file_ids": ["file_abc"]
        ... }
    """
    try:
        # Phase 1: Query Understanding
        expanded_questions = [request.query]
        if request.enable_expansion:
            expansion_result = await query_enhancement_service.expand_query(
                query=request.query,
                cache_provider=cache_provider
            )
            expanded_questions = expansion_result.get("expanded_questions", [request.query])

        # Phase 2: Parallel Retrieval
        retrieval_tasks = [
            retrieval_service.retrieve_context(
                query=question,
                file_ids=request.file_ids,
                top_k=request.top_k
            )
            for question in expanded_questions
        ]
        retrieval_results = await asyncio.gather(*retrieval_tasks)

        # Merge and deduplicate
        context_chunks = []
        seen_contents = set()
        for results in retrieval_results:
            for result in results:
                content = result.get("content", "")
                if content and content not in seen_contents:
                    context_chunks.append(result)
                    seen_contents.add(content)

        # Phase 3: Context Assembly
        chat_history = await chat_history_provider.get_chat_history(
            session_id=request.session_id,
            limit=10
        )

        context_strings = [chunk.get("content", "") for chunk in context_chunks]
        messages = prompt_service.build_rag_prompt(
            query=request.query,
            context_chunks=context_strings,
            chat_history=chat_history,
            language=request.language
        )

        # Phase 4: Response Generation (non-streaming)
        response = await llm_client.get_chat_completion(
            messages=messages,
            temperature=0.7
        )

        answer = response['choices'][0]['message']['content']

        # Phase 5: Post Processing
        await chat_history_provider.add_message(
            session_id=request.session_id,
            role="user",
            content=request.query,
            metadata={"file_ids": request.file_ids}
        )

        await chat_history_provider.add_message(
            session_id=request.session_id,
            role="assistant",
            content=answer
        )

        return ChatResponse(
            session_id=request.session_id,
            query=request.query,
            answer=answer,
            context_count=len(context_chunks),
            expanded_questions=expanded_questions,
            metadata={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "language": request.language
            }
        )

    except Exception as e:
        logger.error(f"Error in non-streaming chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
